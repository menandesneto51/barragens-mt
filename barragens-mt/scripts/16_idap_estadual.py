"""Calcula o IDAP-Barragens para todo o inventário de Mato Grosso.

Princípio (docs/11-principio-estadual-e-sequencia.md): o sistema é estadual; o município
de sede da barragem não limita o impacto. Este script:

  1. monta o estado de cada barragem a partir do inventário consolidado (dimensões B, C8 e
     D1, que já existem no cadastro);
  2. deixa A (hidro) e o restante de C/D como lacuna explícita — serão preenchidos pelos
     coletores SisClima/TITAN e pela mancha de inundação;
  3. estima municípios potencialmente afetados a jusante pela topologia de Otto, usando
     como seção de controle provisória o código de trecho mais a jusante entre as
     barragens de cada município.

Saídas:
  dados/tratados/idap_estadual_mt.csv
  dados/tratados/impacto_extraterritorial_mt.csv
  relatorios/idap_estadual_mt.md
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import comum
import otto

# Garante import do pacote idap tanto via pipeline quanto execução direta.
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from idap.calculo import calcular_idap  # noqa: E402
from idap.modelo import (  # noqa: E402
    CapacidadeResposta,
    CondicaoEstrutura,
    EstadoBarragem,
    ExposicaoSanitaria,
    PressaoHidroclimatica,
    SinaisOperacionais,
)
from idap.pesos import STATUS_VERSAO_PESOS, VERSAO_PESOS  # noqa: E402
from idap.regras import aplicar_regras  # noqa: E402

FUSO = ZoneInfo("America/Cuiaba")


def ler_inventario() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}. Rode o pipeline até a etapa 05.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def ler_hidro_por_barragem() -> dict[str, dict[str, Any]]:
    """Lê a saída de 17_hidro_sisclima_titan.py, se existir."""
    caminho = comum.DADOS_TRATADOS / "hidro_barragens_mt.csv"
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return {
            (r.get("id_snisb") or "").strip(): r
            for r in csv.DictReader(arquivo, delimiter=";")
            if (r.get("id_snisb") or "").strip()
        }


def ler_cnes_por_municipio() -> dict[str, dict[str, int]]:
    """Contagens CNES do eixo — prioriza UBS/ESF/UPA/hospital (C3 proxy)."""
    from cnes_tipos import classificar_estabelecimento

    caminho = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv"
    if not caminho.exists():
        return {}
    contagem: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "com_internacao": 0,
            "sem_internacao": 0,
            "hospital_ref": 0,
            "ubs_esf": 0,
            "upa_ps": 0,
            "prioritarios": 0,
        }
    )
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for r in csv.DictReader(arquivo, delimiter=";"):
            mun = (r.get("municipio") or "").strip()
            if not mun:
                continue
            cls = classificar_estabelecimento(
                codigo_tipo=r.get("codigo_tipo_unidade"),
                nome=r.get("nome_fantasia") or r.get("nome_razao_social"),
                atendimento_hospitalar=r.get("atendimento_hospitalar"),
            )
            if cls["hospitalar"]:
                contagem[mun]["com_internacao"] += 1
                esfera = (r.get("descricao_esfera_administrativa") or "").upper()
                if "ESTADUAL" in esfera or "FEDERAL" in esfera or cls["tipo"].startswith("hospital"):
                    contagem[mun]["hospital_ref"] += 1
            else:
                contagem[mun]["sem_internacao"] += 1
            if cls["ubs_esf"]:
                contagem[mun]["ubs_esf"] += 1
            if cls["upa_ps"]:
                contagem[mun]["upa_ps"] += 1
            if cls["prioritario"]:
                contagem[mun]["prioritarios"] += 1
    return dict(contagem)


def ler_populacao_por_municipio() -> dict[str, int]:
    caminho = comum.DADOS_TRATADOS / "ibge_populacao_municipios_mt.csv"
    if not caminho.exists():
        return {}
    out: dict[str, int] = {}
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for r in csv.DictReader(arquivo, delimiter=";"):
            mun = (r.get("municipio") or "").strip()
            try:
                pop = int(float(str(r.get("populacao") or "0").replace(",", ".")))
            except ValueError:
                continue
            if mun and pop > 0:
                out[mun] = pop
    return out


def exposicao_proxy(
    contaminante_txt: str | None,
    municipios_afetados: list[str],
    cnes: dict[str, dict[str, int]],
    populacao: dict[str, int] | None = None,
) -> ExposicaoSanitaria:
    """C8 do cadastro + C3 por CNES prioritário + pop IBGE nos afetados (proxy)."""
    com = 0
    sem = 0
    ref = False
    tem_cnes = False
    ubs = 0
    upa = 0
    for mun in municipios_afetados:
        dados = cnes.get(mun)
        if not dados:
            continue
        tem_cnes = True
        com += dados["com_internacao"]
        # Atenção primária e urgência contam como exposição assistencial (C3).
        sem += dados["sem_internacao"]
        ubs += dados.get("ubs_esf", 0)
        upa += dados.get("upa_ps", 0)
        if dados["hospital_ref"] > 0:
            ref = True
    pop_zas = None
    if populacao:
        total = sum(populacao.get(m, 0) for m in municipios_afetados)
        if total > 0:
            # Proxy: fração da pop municipal potencialmente na mancha ainda não existe;
            # registramos a soma dos municípios afetados como teto de exposição.
            pop_zas = total
    if not tem_cnes and pop_zas is None:
        return ExposicaoSanitaria(contaminante_predominante=contaminante_txt)
    return ExposicaoSanitaria(
        contaminante_predominante=contaminante_txt,
        unidades_saude_com_internacao=com if tem_cnes else None,
        unidades_saude_sem_internacao=sem if tem_cnes else None,
        hospital_referencia_ameacado=(
            ref or (com >= 1 and "Cuiabá" in municipios_afetados) if tem_cnes else None
        ),
        populacao_zas=pop_zas,
        metodo_estimativa_populacao="ibge_soma_municipios_afetados" if pop_zas else None,
        detalhe_estimativa_populacao=(
            f"Soma da população IBGE dos municípios a jusante (Otto). "
            f"UBS/ESF={ubs}, UPA/PS={upa}, hospitais={com}."
            if pop_zas
            else None
        ),
    )


def sinais_de_hidro(hidro: dict[str, Any] | None) -> SinaisOperacionais:
    if not hidro:
        return SinaisOperacionais()
    cem = (hidro.get("alerta_cemaden_nivel") or "").lower()
    ana = (hidro.get("alerta_ana_nivel") or "").lower()
    inmet = (hidro.get("alerta_inmet_nivel") or "").lower()
    inmet_evt = (hidro.get("alerta_inmet") or "").lower()
    integrado = (hidro.get("nivel_alerta_integrado") or "").lower() or None
    comp = (hidro.get("componente_dominante") or "").lower()
    motivo = (hidro.get("motivo_integrado") or "").lower()
    prev = num_br(hidro.get("chuva_prevista_24_72h_mm"))
    from idap.pesos import LIMIAR_CHUVA_PREVISTA_EXTREMA_MM

    hidro_cem = bool(cem) and cem not in {"verde", "baixo", "baixa", "nenhum"}
    if "hidrolog" in (hidro.get("alerta_cemaden") or "").lower():
        hidro_cem = True
    if cem in {"moderado", "moderada", "alto", "alta", "muito alto", "laranja", "vermelho", "roxa"}:
        hidro_cem = True

    # INMET: só eventos de chuva/tempestade/inundação (ignora onda de calor).
    inmet_chuva = any(
        k in inmet_evt for k in ("chuva", "tempestade", "vendaval", "inunda", "precipita")
    )
    alerta_inmet_ok = inmet_chuva and bool(inmet) and inmet not in {"verde"}

    # Alerta integrado SIS: só propaga se o componente/motivo for hidro/solo/chuva
    # (o estágio "roxa" por calor não deve elevar IDAP de barragem).
    texto_int = f"{comp} {motivo} {hidro.get('alerta_cemaden') or ''}"
    integrado_hidro = any(
        k in texto_int
        for k in ("hidro", "solo", "chuva", "cemaden", "inunda", "vazao", "cota", "precip")
    )
    nivel_integrado_util = integrado if integrado_hidro else None

    return SinaisOperacionais(
        alerta_cemaden_hidrologico=hidro_cem,
        alerta_inmet_relevante=alerta_inmet_ok,
        alerta_ana_acima_atencao=ana
        in {"amarelo", "amarela", "laranja", "vermelho", "vermelha", "roxa", "roxo"},
        nivel_alerta_integrado_sis=nivel_integrado_util,
        chuva_prevista_extrema=prev is not None and prev >= LIMIAR_CHUVA_PREVISTA_EXTREMA_MM,
    )


def ler_alertabilidade() -> dict[str, dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "alertabilidade_piloto.csv"
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return {
            (r.get("id_snisb") or "").strip(): r
            for r in csv.DictReader(arquivo, delimiter=";")
            if (r.get("id_snisb") or "").strip()
        }


def texto(valor: Any) -> str | None:
    if valor is None:
        return None
    limpo = str(valor).strip()
    return limpo or None


def num_br(valor: Any) -> float | None:
    """Converte número pt-BR (vírgula decimal) ou ponto para float."""
    if valor is None:
        return None
    texto_valor = str(valor).strip()
    if not texto_valor:
        return None
    try:
        return float(texto_valor.replace(",", "."))
    except (TypeError, ValueError):
        return None


def pressao_de_hidro(hidro: dict[str, Any] | None) -> PressaoHidroclimatica:
    if not hidro:
        return PressaoHidroclimatica()
    dias = num_br(hidro.get("dias_consecutivos_chuva_intensa"))
    return PressaoHidroclimatica(
        chuva_24h_mm=num_br(hidro.get("chuva_24h_mm")),
        chuva_72h_mm=num_br(hidro.get("chuva_72h_mm")),
        chuva_prevista_24_72h_mm=num_br(hidro.get("chuva_prevista_24_72h_mm")),
        percentil_climatologico=num_br(hidro.get("percentil_climatologico")),
        saturacao_antecedente=num_br(hidro.get("saturacao_antecedente")),
        razao_nivel_cota_alerta=num_br(hidro.get("razao_nivel_cota_alerta")),
        dias_consecutivos_chuva_intensa=int(dias) if dias is not None else None,
    )


def situacao_pae(registro: dict[str, Any]) -> str | None:
    pae = texto(registro.get("possui_pae"))
    if pae is None:
        return None
    if pae.lower() == "sim":
        # O SNISB não informa se o PAE está articulado com o município.
        return "Vigente sem articulação municipal"
    if pae.lower() == "não":
        return "Inexistente"
    return None


def contaminante(registro: dict[str, Any]) -> str | None:
    uso = (texto(registro.get("uso_principal")) or "").lower()
    orgao = (texto(registro.get("orgao_fiscalizador")) or "").lower()
    if "rejeito" in uso or "mineração" in orgao or "mineracao" in orgao:
        return "Rejeito não inerte ou perigoso"
    if uso:
        return "Água sem rejeito"
    return None


def nivel_emergencia(registro: dict[str, Any]) -> str | None:
    # Preferência: declaração do SIGBM; senão, nível de perigo do SNISB.
    sigbm = texto(registro.get("sigbm_nivel_emergencia"))
    if sigbm:
        return sigbm
    return texto(registro.get("nivel_de_perigo"))


def estado_de_registro(
    registro: dict[str, Any],
    instante: datetime,
    hidro: dict[str, Any] | None = None,
    *,
    exposicao: ExposicaoSanitaria | None = None,
    contatos_validados_90d: bool | None = None,
    municipios_zas: tuple[str, ...] = (),
) -> EstadoBarragem:
    return EstadoBarragem(
        id_barragem=texto(registro.get("id_snisb")) or "sem-id",
        nome=texto(registro.get("nome")) or "sem nome",
        municipio=texto(registro.get("municipio")) or "não informado",
        instante=instante,
        orgao_fiscalizador=texto(registro.get("orgao_fiscalizador")),
        empreendedor=texto(registro.get("empreendedor")),
        uso_principal=texto(registro.get("uso_principal")),
        municipios_zas=municipios_zas,
        pressao=pressao_de_hidro(hidro),
        estrutura=CondicaoEstrutura(
            categoria_risco=texto(registro.get("categoria_risco")),
            nivel_emergencia=nivel_emergencia(registro),
            situacao_estabilidade=texto(registro.get("sigbm_status_dce")),
            situacao_telemetria=None,
        ),
        exposicao=exposicao
        or ExposicaoSanitaria(contaminante_predominante=contaminante(registro)),
        capacidade=CapacidadeResposta(
            situacao_plano_emergencia=situacao_pae(registro),
            contatos_validados_90d=contatos_validados_90d,
        ),
        sinais=sinais_de_hidro(hidro),
    )


def secoes_controle_por_municipio(
    inventario: list[dict[str, Any]],
) -> dict[str, str]:
    """Proxy de seção de controle: código Otto mais longo (mais específico) do município.

    Enquanto a BHO estadual completa não estiver carregada, o código de trecho das
    barragens do próprio município é a melhor âncora disponível. Códigos mais longos
    reduzem falso positivo de topologia; quando existir seção oficial (ex.: Cuiabá
    896573, da análise do eixo Manso), ela prevalece.
    """
    por_municipio: dict[str, list[str]] = defaultdict(list)
    for registro in inventario:
        municipio = texto(registro.get("municipio"))
        codigo = otto.normalizar(registro.get("codigo_trecho_curso_dagua"))
        if municipio and codigo:
            por_municipio[municipio].append(codigo)

    secoes: dict[str, str] = {}
    for municipio, codigos in por_municipio.items():
        # Preferir o código mais específico (maior comprimento).
        secoes[municipio] = sorted(codigos, key=lambda c: (-len(c), c))[0]

    # Seção de controle validada na análise Cuiabá (script 12), quando disponível.
    recorte = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if recorte.exists():
        import json

        dados = json.loads(recorte.read_text(encoding="utf-8"))
        cobacia = otto.normalizar(dados.get("secao_de_controle"))
        if cobacia:
            secoes["Cuiabá"] = cobacia
    secoes.setdefault("Cuiabá", "896573")
    return secoes


# Prefixo Otto mínimo para aceitar MONTANTE entre barragem e seção municipal.
# Com 3 dígitos exige a mesma sub-bacia regional (ex.: 896…); evita 896×895.
MIN_PREFIXO_OTTO_AFETADO = 3


def municipios_afetados(
    codigo_barragem: str,
    municipio_sede: str,
    secoes: dict[str, str],
    *,
    min_prefixo: int = MIN_PREFIXO_OTTO_AFETADO,
) -> tuple[list[str], list[str]]:
    """Municípios a jusante da barragem, e casos de posição indeterminada (CONTEM).

    CONTEM (código da barragem mais grosseiro que a seção) não entra como afetado
    automático: geraria falso positivo em bacias inteiras (ex.: trecho `896` do Manso).
    Esses casos saem em lista própria para resolução geométrica.

    MONTANTE exige prefixo Otto comum ≥ `min_prefixo` (ver `otto.drena_para`).
    """
    afetados: list[str] = []
    indeterminados: list[str] = []
    for municipio, secao in secoes.items():
        if otto.drena_para(codigo_barragem, secao, min_prefixo=min_prefixo):
            afetados.append(municipio)
        elif (
            otto.relacao(codigo_barragem, secao) == otto.Relacao.CONTEM
            and municipio != municipio_sede
        ):
            indeterminados.append(municipio)
    return sorted(afetados), sorted(indeterminados)


def main() -> None:
    comum.preparar_diretorios()
    instante = datetime.now(tz=FUSO)
    inventario = ler_inventario()
    hidro_por_id = ler_hidro_por_barragem()
    cnes_por_mun = ler_cnes_por_municipio()
    pop_por_mun = ler_populacao_por_municipio()
    alertab_por_id = ler_alertabilidade()
    print(f"IDAP estadual — {len(inventario)} barragens — pesos {VERSAO_PESOS}")
    print(f"  {STATUS_VERSAO_PESOS}")
    n_tel = sum(
        1
        for h in hidro_por_id.values()
        if (h.get("aproximacao_espacial") or "") == "ponto_barragem_telemetria"
        or bool(h.get("fonte_telemetria_a"))
        or str(h.get("fonte_precip") or "").startswith(("inmet_", "openmeteo_ponto"))
    )
    print(
        f"  hidro SisClima/TITAN: {len(hidro_por_id)} barragens "
        f"({n_tel} com telemetria pontual etapa 39)"
    )
    print(f"  CNES eixo (proxy C3): {len(cnes_por_mun)} municípios")
    print(f"  população IBGE: {len(pop_por_mun)} municípios")
    print(f"  alertabilidade: {len(alertab_por_id)} barragens")

    secoes = secoes_controle_por_municipio(inventario)
    print(f"  seções de controle provisórias: {len(secoes)} municípios")

    linhas_idap: list[dict[str, Any]] = []
    linhas_impacto: list[dict[str, Any]] = []
    por_nivel: dict[str, int] = defaultdict(int)
    extraterritoriais = 0

    for registro in inventario:
        id_snisb = texto(registro.get("id_snisb")) or ""
        mun_sede = texto(registro.get("municipio")) or "não informado"
        codigo = otto.normalizar(registro.get("codigo_trecho_curso_dagua"))
        if codigo:
            afetados, indeterminados = municipios_afetados(codigo, mun_sede, secoes)
        else:
            afetados, indeterminados = [], []
        # Caso Manso: barragens principais com código grosseiro `896`. Enquanto a
        # resolução geométrica não estiver no lote estadual, força o vínculo com a
        # seção de controle validada de Cuiabá (e Várzea Grande na mesma mancha).
        nome_tmp = (texto(registro.get("nome")) or "").upper()
        if (
            "UHE MANSO" in nome_tmp
            and "Cuiabá" not in afetados
            and otto.relacao(codigo, secoes.get("Cuiabá", "896573"))
            in {otto.Relacao.CONTEM, otto.Relacao.MONTANTE, otto.Relacao.MESMO_TRECHO}
        ):
            afetados = sorted(set(afetados) | {"Cuiabá", "Várzea Grande", mun_sede})
            indeterminados = [m for m in indeterminados if m not in {"Cuiabá", "Várzea Grande"}]

        alert = alertab_por_id.get(id_snisb, {})
        contatos_ok: bool | None
        if alert:
            contatos_ok = (alert.get("contatos_validados_90d") or "").lower() == "sim"
        else:
            contatos_ok = None

        hidro = hidro_por_id.get(id_snisb)
        exposicao = exposicao_proxy(
            contaminante(registro), afetados, cnes_por_mun, pop_por_mun
        )
        estado = estado_de_registro(
            registro,
            instante,
            hidro,
            exposicao=exposicao,
            contatos_validados_90d=contatos_ok,
            municipios_zas=tuple(afetados),
        )
        resultado = calcular_idap(estado)
        final = aplicar_regras(estado, resultado)

        afetados_externos = [m for m in afetados if m != estado.municipio]
        if afetados_externos:
            extraterritoriais += 1

        por_nivel[final.nivel_final.rotulo] += 1
        lacunas = ";".join(resultado.lacunas)
        regras = ";".join(r.codigo for r in final.regras_disparadas)

        linhas_idap.append(
            {
                "id_snisb": estado.id_barragem,
                "nome": estado.nome,
                "municipio_sede": estado.municipio,
                "orgao_fiscalizador": estado.orgao_fiscalizador or "",
                "uso_principal": estado.uso_principal or "",
                "dano_potencial_associado": texto(registro.get("dano_potencial_associado")) or "",
                "categoria_risco": texto(registro.get("categoria_risco")) or "",
                "codigo_trecho_curso_dagua": codigo,
                "idap": resultado.idap,
                "nivel": final.nivel_final.rotulo,
                "nivel_por_pontuacao": resultado.nivel.rotulo,
                "completude": f"{resultado.completude:.3f}".replace(".", ","),
                "confiabilidade": resultado.confiabilidade,
                "idap_projetado": f"{resultado.idap_projetado:.1f}".replace(".", ","),
                "pontos_a": resultado.dimensao("A").pontos,
                "pontos_b": resultado.dimensao("B").pontos,
                "pontos_c": resultado.dimensao("C").pontos,
                "pontos_d": resultado.dimensao("D").pontos,
                "alertavel": alert.get("alertavel") or "não avaliado",
                "contatos_validados_90d": (
                    "sim" if contatos_ok is True else "não" if contatos_ok is False else ""
                ),
                "regras_disparadas": regras,
                "lacunas": lacunas,
                "municipios_potencialmente_afetados": " | ".join(afetados),
                "municipios_posicao_indeterminada": " | ".join(indeterminados),
                "n_municipios_afetados": len(afetados),
                "n_municipios_extraterritoriais": len(afetados_externos),
                "versao_pesos": VERSAO_PESOS,
                "instante": instante.isoformat(timespec="seconds"),
            }
        )

        for municipio in afetados_externos:
            linhas_impacto.append(
                {
                    "id_snisb": estado.id_barragem,
                    "nome_barragem": estado.nome,
                    "municipio_sede": estado.municipio,
                    "municipio_potencialmente_afetado": municipio,
                    "codigo_trecho_barragem": codigo,
                    "codigo_secao_controle_afetado": secoes.get(municipio, ""),
                    "relacao_otto": otto.relacao(codigo, secoes.get(municipio, "")).value,
                    "idap": resultado.idap,
                    "nivel": final.nivel_final.rotulo,
                    "dano_potencial_associado": texto(registro.get("dano_potencial_associado")) or "",
                }
            )

    campos_idap = list(linhas_idap[0].keys()) if linhas_idap else []
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "idap_estadual_mt.csv",
        linhas_idap,
        campos_idap,
    )
    campos_impacto = list(linhas_impacto[0].keys()) if linhas_impacto else [
        "id_snisb",
        "nome_barragem",
        "municipio_sede",
        "municipio_potencialmente_afetado",
    ]
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "impacto_extraterritorial_mt.csv",
        linhas_impacto,
        campos_impacto,
    )

    escrever_relatorio(
        total=len(inventario),
        por_nivel=dict(por_nivel),
        extraterritoriais=extraterritoriais,
        n_vinculos=len(linhas_impacto),
        linhas=linhas_idap,
        n_hidro=len(hidro_por_id),
    )

    gravar_historico(instante, linhas_idap, dict(por_nivel))

    print(f"  gravado dados/tratados/idap_estadual_mt.csv ({len(linhas_idap)} registros)")
    print(
        f"  gravado dados/tratados/impacto_extraterritorial_mt.csv "
        f"({len(linhas_impacto)} vínculos sede≠afetado)"
    )
    print(f"  barragens com impacto extraterritorial: {extraterritoriais}")
    for nivel in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        print(f"  {nivel}: {por_nivel.get(nivel, 0)}")


def gravar_historico(
    instante: datetime,
    linhas: list[dict[str, Any]],
    por_nivel: dict[str, int],
) -> None:
    """Append-only: cada rodada vira um snapshot + linha no índice (docs/06 calculo_idap)."""
    pasta = comum.DADOS_TRATADOS / "historico_idap"
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = instante.strftime("%Y%m%d_%H%M%S")
    snapshot = pasta / f"idap_{carimbo}.csv"
    campos = list(linhas[0].keys()) if linhas else []
    comum.salvar_csv(snapshot, linhas, campos)

    indice = pasta / "indice.csv"
    resumo = {
        "instante": instante.isoformat(timespec="seconds"),
        "arquivo": snapshot.name,
        "n_barragens": len(linhas),
        "versao_pesos": VERSAO_PESOS,
        "roxo": por_nivel.get("Roxo", 0),
        "vermelho": por_nivel.get("Vermelho", 0),
        "laranja": por_nivel.get("Laranja", 0),
        "amarelo": por_nivel.get("Amarelo", 0),
        "verde": por_nivel.get("Verde", 0),
    }
    existentes: list[dict[str, Any]] = []
    if indice.exists():
        with indice.open(encoding="utf-8-sig", newline="") as arquivo:
            existentes = list(csv.DictReader(arquivo, delimiter=";"))
    existentes.append(resumo)
    comum.salvar_csv(indice, existentes, list(resumo.keys()))
    print(f"  histórico: {snapshot.relative_to(comum.RAIZ)} (+ índice)")


def escrever_relatorio(
    *,
    total: int,
    por_nivel: dict[str, int],
    extraterritoriais: int,
    n_vinculos: int,
    linhas: list[dict[str, Any]],
    n_hidro: int = 0,
) -> None:
    ordenadas = sorted(linhas, key=lambda r: (-int(r["idap"]), r["municipio_sede"], r["nome"]))
    top = ordenadas[:25]

    partes = [
        "# IDAP estadual — Mato Grosso",
        "",
        f"Cálculo em lote das **{total}** barragens do inventário consolidado, com pesos "
        f"`{VERSAO_PESOS}`.",
        "",
        f"> {STATUS_VERSAO_PESOS}",
        "",
        "## Princípio",
        "",
        "O sistema é **estadual**. O município de sede da barragem não limita o impacto: "
        "uma estrutura em Chapada dos Guimarães pode exigir preparação em Cuiabá. Ver "
        "`docs/11-principio-estadual-e-sequencia.md`.",
        "",
        "## Completude desta rodada",
        "",
        "Nesta versão entram apenas indicadores já presentes no cadastro:",
        "",
        "- **B** — categoria de risco, nível de emergência / DCE (quando houver)",
        "- **C8** — material do reservatório (água vs. rejeito)",
        "- **D1** — existência de PAE no SNISB",
        "",
        "A dimensão **A** (pressão hidroclimática) fica vazia de propósito: será "
        "preenchida pelos coletores do **SIS Clima Saúde** e do **TITAN**. As demais "
        "parcelas de C e D dependem de mancha de inundação e de cadastros operacionais "
        "ainda não integrados. Por isso a completude média é baixa e a "
        "**confiabilidade** tende a `insuficiente` ou `parcial` — isso é diagnóstico "
        "honesto, não falha do cálculo.",
        "",
        "## Distribuição por faixa",
        "",
        "| Faixa | Barragens |",
        "| --- | ---: |",
    ]
    for nivel in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        partes.append(f"| {nivel} | {por_nivel.get(nivel, 0)} |")

    partes += [
        "",
        "## Impacto extraterritorial",
        "",
        f"- Barragens com ao menos um município afetado diferente da sede: "
        f"**{extraterritoriais}**",
        f"- Vínculos sede → município afetado: **{n_vinculos}** "
        f"(arquivo `impacto_extraterritorial_mt.csv`)",
        "",
        "A seção de controle por município é provisória (código Otto mais específico "
        "entre as barragens daquele município; Cuiabá usa a seção `896573` validada). "
        "Códigos grosseiros demais para decidir (relação Otto `contem`) saem na coluna "
        "`municipios_posicao_indeterminada`, exceto o complexo de Manso, forçado ao "
        "vínculo com Cuiabá/Várzea Grande pela geometria do reservatório. A BHO estadual "
        "completa e a mancha de inundação oficial substituirão este proxy.",
        "",
        "## Maiores IDAP desta rodada (top 25)",
        "",
        "| IDAP | Nível | Completude | Sede | Nome | Municípios afetados (n) |",
        "| ---: | --- | ---: | --- | --- | ---: |",
    ]
    for linha in top:
        partes.append(
            f"| {linha['idap']} | {linha['nivel']} | {linha['completude']} | "
            f"{linha['municipio_sede']} | {linha['nome']} | "
            f"{linha['n_municipios_afetados']} |"
        )

    partes += [
        "",
        "## Pressão hidroclimática (dimensão A)",
        "",
        f"- Barragens com linha SisClima/TITAN: **{n_hidro}** "
        f"(`hidro_barragens_mt.csv`, etapa 17).",
        "- Onde a etapa 39 rodou: chuva A1–A4 no **ponto da barragem** "
        "(INMET ≤80 km ou Open-Meteo pontual); demais usam município-sede/montante.",
        "- Alertas Cemaden/INMET/ANA do contrato municipal são preservados na mescla.",
        "",
        "## Próximos passos",
        "",
        "1. Expandir BHO além da bacia do Cuiabá e agregar chuva/solo na drenagem.",
        "2. Preferir série INMET/ANA HidroWeb quando a API diária estiver estável.",
        "",
    ]
    destino = comum.RELATORIOS / "idap_estadual_mt.md"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
