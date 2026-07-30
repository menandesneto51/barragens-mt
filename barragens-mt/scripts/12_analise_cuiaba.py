"""Analise de exposicao de Cuiaba a rompimento de barragens, por posicao na bacia.

Esta etapa substitui o recorte por limite municipal pelo recorte por topologia de
drenagem. A troca nao e cosmetica: das 43 barragens cadastradas dentro do
municipio de Cuiaba, parte nao drena para a calha do rio Cuiaba na altura da
capital, enquanto dezenas de estruturas de outros municipios drenam — inclusive o
Aproveitamento Multiplo de Manso, o maior reservatorio do estado.

Saidas:
  relatorios/analise_cuiaba.md
  dados/tratados/barragens_montante_cuiaba.csv
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum
import otto

RELATORIOS = comum.RELATORIOS

# Ponto de referencia: mancha urbana central de Cuiaba. O trecho de drenagem da
# BHO mais proximo desse ponto define a secao de controle da analise.
CUIABA_PONTO = (-56.0979, -15.6014)
CUIABA_IBGE = "5103403"

NOME_MANSO = "MANSO"


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper()


def numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def pt_br(valor: Any, decimais: int = 0) -> str:
    """Formata numero no padrao brasileiro: ponto de milhar e virgula decimal.

    Formatar dentro da f-string e depois aplicar replace no texto corrompe as virgulas
    da prosa, porque literais adjacentes sao concatenados antes de o metodo ser chamado.
    """
    convertido = numero(valor)
    if convertido is None:
        return "não informado"
    return (
        f"{convertido:,.{decimais}f}"
        .replace(",", "\x00")
        .replace(".", ",")
        .replace("\x00", ".")
    )


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    raio = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * raio * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )


def vertices(feicao: dict[str, Any]) -> list[tuple[float, float]]:
    geometria = feicao.get("geometry") or {}
    coordenadas = geometria.get("coordinates") or []
    if geometria.get("type") == "LineString":
        return [(c[0], c[1]) for c in coordenadas]
    pontos: list[tuple[float, float]] = []
    for parte in coordenadas:
        pontos.extend((c[0], c[1]) for c in parte)
    return pontos


def aneis(geometria: dict[str, Any]) -> Iterable[list[list[float]]]:
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates", [])
    if tipo == "Polygon":
        yield from coordenadas
    elif tipo == "MultiPolygon":
        for parte in coordenadas:
            yield from parte


def ponto_no_anel(ponto: tuple[float, float], anel: list[list[float]]) -> bool:
    """Teste de ponto em poligono por lancamento de raio."""
    x, y = ponto
    dentro = False
    total = len(anel)
    for indice in range(total):
        x1, y1 = anel[indice][0], anel[indice][1]
        x2, y2 = anel[(indice + 1) % total][0], anel[(indice + 1) % total][1]
        if (y1 > y) != (y2 > y):
            corte = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < corte:
                dentro = not dentro
    return dentro


def ler_inventario() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def ler_geojson(nome: str) -> dict[str, Any]:
    return json.loads((comum.DADOS_TRATADOS / nome).read_text(encoding="utf-8"))


def resolver_secao_de_controle(feicoes: list[dict[str, Any]]) -> dict[str, Any]:
    """Trecho do rio Cuiaba mais proximo da mancha urbana da capital."""
    melhor: tuple[float, dict[str, Any]] | None = None
    for feicao in feicoes:
        propriedades = feicao.get("properties") or {}
        rio = sem_acento(propriedades.get("NORIOCOMP") or "")
        if "RIO CUIABA" not in rio:
            continue
        pontos = vertices(feicao)
        if not pontos:
            continue
        perto = min(distancia_km(CUIABA_PONTO, p) for p in pontos)
        if melhor is None or perto < melhor[0]:
            melhor = (perto, feicao)
    if melhor is None:
        raise RuntimeError("nao foi possivel localizar o trecho do rio Cuiaba na capital")
    print(f"  secao de controle a {melhor[0]:.2f} km do centro da capital")
    return melhor[1]


def nomes_de_municipio() -> dict[str, str]:
    """Mapa de codigo do IBGE para nome, ja que a malha traz apenas o codigo."""
    caminho = comum.DADOS_TRATADOS / "ibge_municipios_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return {
            linha["codigo_ibge"].strip(): linha["municipio"].strip()
            for linha in csv.DictReader(arquivo, delimiter=";")
        }


def municipios_atravessados(
    percurso: list[otto.Trecho],
    indice_geometria: dict[int, list[tuple[float, float]]],
    malha: dict[str, Any],
    nomes: dict[str, str],
) -> list[str]:
    """Municipios cruzados pelo eixo de drenagem, na ordem de montante para jusante.

    A ordem segue o percurso da agua, e nao a ordem alfabetica, porque a sequencia
    de municipios atingidos e informacao operacional para acionamento da rede.
    """
    poligonos: list[tuple[str, list[list[list[float]]]]] = []
    for feicao in malha.get("features", []):
        codigo = str((feicao.get("properties") or {}).get("codarea", "")).strip()
        nome = nomes.get(codigo, codigo)
        poligonos.append((nome, list(aneis(feicao.get("geometry") or {}))))

    ordenados: list[str] = []
    for trecho in percurso:
        for ponto in indice_geometria.get(trecho.cotrecho, []):
            for nome, aneis_municipio in poligonos:
                if nome in ordenados:
                    continue
                if any(ponto_no_anel(ponto, anel) for anel in aneis_municipio):
                    ordenados.append(nome)
    return ordenados


def formatar(valor: Any, sufixo: str = "") -> str:
    if valor in (None, "", "None"):
        return "não informado"
    return f"{valor}{sufixo}"


def main() -> None:
    print("Analise de exposicao de Cuiaba por posicao na bacia")

    inventario = ler_inventario()
    bho = ler_geojson("ana_bho_trechos_bacia_cuiaba.geojson")
    indice = otto.indexar_trechos(bho["features"])
    geometrias = {
        int((f.get("properties") or {}).get("COTRECHO")): vertices(f)
        for f in bho["features"]
        if (f.get("properties") or {}).get("COTRECHO") is not None
    }

    secao = resolver_secao_de_controle(bho["features"])
    propriedades_secao = secao["properties"]
    cobacia_referencia = otto.normalizar(propriedades_secao["COBACIA"])
    cotrecho_referencia = int(propriedades_secao["COTRECHO"])
    area_montante_capital = float(propriedades_secao["NUAREAMONT"])
    print(f"  secao de controle: cobacia {cobacia_referencia}, area a montante {area_montante_capital:,.1f} km2")

    # --- classificacao de todo o cadastro pela posicao relativa a secao de controle
    for registro in inventario:
        registro["relacao_com_cuiaba"] = otto.relacao(
            registro.get("codigo_trecho_curso_dagua"), cobacia_referencia
        ).value

    drenam = [
        r
        for r in inventario
        if r["relacao_com_cuiaba"] in {otto.Relacao.MONTANTE.value, otto.Relacao.MESMO_TRECHO.value}
    ]
    indeterminados = [r for r in inventario if r["relacao_com_cuiaba"] == otto.Relacao.CONTEM.value]

    # --- o complexo de Manso
    manso = [r for r in inventario if NOME_MANSO in sem_acento(r.get("nome", ""))
             and "UHE MANSO" in sem_acento(r.get("nome", ""))]
    trecho_manso = next((t for t in indice.values() if t.cobacia == "89679"), None)
    percurso = (
        otto.caminho_jusante(indice, trecho_manso.cotrecho, cotrecho_referencia)
        if trecho_manso
        else None
    )
    distancia_talvegue = (
        sum(t.comprimento_km for t in percurso[:-1]) if percurso else None
    )

    # --- reservatorio na base de massas d'agua, como conferencia independente
    massas = ler_geojson("ana_massas_dagua_mt.geojson")
    espelho_manso = next(
        (
            f
            for f in massas["features"]
            if "MANSO" in sem_acento((f.get("properties") or {}).get("nmoriginal") or "")
        ),
        None,
    )

    # --- municipios do eixo a jusante
    malha = ler_geojson("ibge_malha_municipios_mt_simplificada.geojson")
    nomes = nomes_de_municipio()
    atravessados = municipios_atravessados(percurso or [], geometrias, malha, nomes)

    # eixo a jusante da capital, ate a saida do recorte
    jusante_da_capital: list[otto.Trecho] = []
    atual = indice.get(cotrecho_referencia)
    while atual is not None and len(jusante_da_capital) < 500:
        jusante_da_capital.append(atual)
        atual = indice.get(atual.trecho_jusante)
    atravessados_jusante = municipios_atravessados(
        jusante_da_capital, geometrias, malha, nomes
    )

    print(f"  {len(drenam)} barragens drenam para a secao de controle")
    print(f"  municipios no eixo Manso-capital: {atravessados}")
    print(f"  municipios no eixo a jusante da capital: {atravessados_jusante}")

    gravar_csv(drenam)
    gravar_eixo_hidrografico(percurso or [], jusante_da_capital, geometrias)
    gravar_municipios_de_interesse(
        cobacia_referencia=cobacia_referencia,
        drenam=drenam,
        atravessados=atravessados,
        atravessados_jusante=atravessados_jusante,
        nomes=nomes,
    )
    escrever_relatorio(
        inventario=inventario,
        drenam=drenam,
        indeterminados=indeterminados,
        manso=manso,
        cobacia_referencia=cobacia_referencia,
        area_montante_capital=area_montante_capital,
        trecho_manso=trecho_manso,
        percurso=percurso,
        distancia_talvegue=distancia_talvegue,
        espelho_manso=espelho_manso,
        atravessados=atravessados,
        atravessados_jusante=atravessados_jusante,
    )


def gravar_eixo_hidrografico(
    percurso: list[otto.Trecho],
    jusante: list[otto.Trecho],
    geometrias: dict[int, list[tuple[float, float]]],
) -> None:
    """Publica o eixo Manso-capital-jusante como linhas, para reuso em mapa e cruzamento.

    A faixa de atencao usada nas analises de exposicao e medida por distancia a este
    eixo. Exporta-lo evita que cada script reconstrua o percurso e chegue a outro tracado.
    """
    feicoes: list[dict[str, Any]] = []
    for rotulo, trechos in (("manso_capital", percurso), ("jusante_capital", jusante)):
        for ordem, trecho in enumerate(trechos):
            vertices_trecho = geometrias.get(trecho.cotrecho) or []
            if len(vertices_trecho) < 2:
                continue
            feicoes.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[x, y] for x, y in vertices_trecho],
                    },
                    "properties": {
                        "segmento": rotulo,
                        "ordem": ordem,
                        "cotrecho": trecho.cotrecho,
                        "cobacia": trecho.cobacia,
                        "comprimento_km": trecho.comprimento_km,
                    },
                }
            )
    comum.salvar_json(
        comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson",
        {"type": "FeatureCollection", "features": feicoes},
    )


def gravar_municipios_de_interesse(
    *,
    cobacia_referencia: str,
    drenam: list[dict[str, Any]],
    atravessados: list[str],
    atravessados_jusante: list[str],
    nomes: dict[str, str],
) -> None:
    """Publica o recorte territorial da analise para os coletores setoriais reusarem.

    A rede de saude e as populacoes vulneraveis precisam ser coletadas exatamente nos
    municipios que esta analise identificou por topologia de drenagem. Fixar a lista
    aqui evita que cada coletor reconstrua o recorte por conta propria e divirja.
    """
    com_barragens = sorted({r.get("municipio") for r in drenam if r.get("municipio")})
    uniao = sorted(set(atravessados) | set(atravessados_jusante) | set(com_barragens))
    por_nome = {sem_acento(nome): codigo for codigo, nome in nomes.items()}

    recorte = {
        "secao_de_controle": cobacia_referencia,
        "criterio": (
            "municipios atravessados pelo eixo de drenagem entre o Manso e a capital, "
            "municipios do eixo a jusante da capital e municipios com barragens que "
            "drenam para a secao de controle"
        ),
        "eixo_manso_capital": atravessados,
        "eixo_jusante_capital": atravessados_jusante,
        "municipios_com_barragens_a_montante": com_barragens,
        "municipios": [
            {
                "nome": nome,
                "codigo_ibge": por_nome.get(sem_acento(nome)),
                # O CNES indexa municipio pelo codigo de 6 digitos, sem o verificador;
                # o codigo de 7 digitos devolve lista vazia sem erro.
                "codigo_cnes": (por_nome.get(sem_acento(nome)) or "")[:6] or None,
                "no_eixo_montante": nome in atravessados,
                "no_eixo_jusante": nome in atravessados_jusante,
                "tem_barragem_a_montante": nome in com_barragens,
            }
            for nome in uniao
        ],
    }
    caminho = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    comum.salvar_json(caminho, recorte)
    sem_codigo = [m["nome"] for m in recorte["municipios"] if not m["codigo_ibge"]]
    if sem_codigo:
        print(f"  atencao: sem codigo do IBGE para {sem_codigo}")


def gravar_csv(drenam: list[dict[str, Any]]) -> None:
    colunas = [
        "id_snisb",
        "nome",
        "municipio",
        "orgao_fiscalizador",
        "empreendedor",
        "curso_dagua",
        "codigo_trecho_curso_dagua",
        "relacao_com_cuiaba",
        "categoria_risco",
        "dano_potencial_associado",
        "classe_cnrh",
        "altura_m",
        "capacidade_hm3",
        "uso_principal",
        "fase_de_vida",
        "possui_plano_de_seguranca",
        "possui_pae",
        "data_ultima_inspecao",
        "latitude",
        "longitude",
    ]
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "barragens_montante_cuiaba.csv",
        sorted(drenam, key=lambda r: -(numero(r.get("capacidade_hm3")) or 0)),
        colunas,
    )


def escrever_relatorio(**dados: Any) -> None:
    inventario: list[dict[str, Any]] = dados["inventario"]
    drenam: list[dict[str, Any]] = dados["drenam"]
    indeterminados: list[dict[str, Any]] = dados["indeterminados"]
    manso: list[dict[str, Any]] = dados["manso"]
    cobacia_referencia: str = dados["cobacia_referencia"]
    area_capital: float = dados["area_montante_capital"]
    trecho_manso: otto.Trecho | None = dados["trecho_manso"]
    percurso = dados["percurso"]
    distancia_talvegue = dados["distancia_talvegue"]
    espelho_manso = dados["espelho_manso"]
    atravessados: list[str] = dados["atravessados"]
    atravessados_jusante: list[str] = dados["atravessados_jusante"]

    def cap(registro: dict[str, Any]) -> float:
        return numero(registro.get("capacidade_hm3")) or 0.0

    em_cuiaba = [r for r in inventario if r.get("codigo_ibge") == CUIABA_IBGE]
    em_cuiaba_que_drenam = [r for r in em_cuiaba if r in drenam]
    em_cuiaba_que_nao_drenam = [r for r in em_cuiaba if r not in drenam]
    fora_que_drenam = [r for r in drenam if r.get("codigo_ibge") != CUIABA_IBGE]

    por_municipio = Counter(r.get("municipio") or "(sem município)" for r in drenam)

    criticas = [
        r
        for r in drenam
        if r.get("dano_potencial_associado") == "Alto" or r.get("categoria_risco") == "Alto"
    ]
    rejeitos = [
        r
        for r in drenam
        if "REJEITO" in sem_acento(r.get("nome", ""))
        or r.get("orgao_fiscalizador", "").endswith("ANM")
    ]

    area_manso = trecho_manso.area_montante_km2 if trecho_manso else 0.0
    fracao = area_manso / area_capital if area_capital else 0.0

    hoje = dt.date.today().strftime("%d/%m/%Y")

    linhas: list[str] = []
    a = linhas.append

    a("# Exposição de Cuiabá a rompimento de barragens")
    a("")
    a(
        f"Análise territorial da unidade de análise Cuiabá, elaborada em {hoje} a partir do "
        "inventário consolidado de barragens de Mato Grosso e da Base Hidrográfica "
        "Ottocodificada da Agência Nacional de Águas e Saneamento Básico."
    )
    a("")

    # ------------------------------------------------------------------ metodo
    a("## 1. Por que o recorte deixou de ser municipal")
    a("")
    a(
        "A primeira versão desta análise selecionava as barragens pelo município de "
        "localização. O critério é inadequado para risco de rompimento, porque a onda de "
        "ruptura se propaga pela calha do rio e ignora limites administrativos. Uma "
        "barragem situada em Chapada dos Guimarães pode ameaçar Cuiabá mais do que "
        "qualquer estrutura cadastrada dentro do município da capital, desde que esteja a "
        "montante na mesma bacia."
    )
    a("")
    a(
        "O recorte passou a ser feito por topologia de drenagem. O cadastro do SNISB "
        "informa, para cada barragem, o código do trecho de curso d'água na codificação de "
        "Otto Pfafstetter adotada pela ANA — campo preenchido em todos os "
        f"{pt_br(len(inventario))} registros de Mato Grosso. "
        "Nessa codificação, os dígitos ímpares identificam as interbacias da calha "
        "principal, numeradas da foz para a nascente, e os pares identificam as quatro "
        "maiores bacias tributárias de cada nível. Uma barragem está a montante de um "
        "ponto quando, no primeiro dígito em que os códigos divergem, seu dígito é maior e "
        "o dígito do ponto de referência é ímpar."
    )
    a("")
    a(
        "A seção de controle adotada é o trecho do rio Cuiabá mais próximo da mancha urbana "
        f"central da capital, de código `{cobacia_referencia}`, que drena "
        f"{pt_br(area_capital)} km² a montante."
    )
    a("")
    a(
        "A troca de critério muda o conjunto analisado nas duas direções, e por isso "
        "importa:"
    )
    a("")
    a(
        f"- das {len(em_cuiaba)} barragens cadastradas no município de Cuiabá, "
        f"{len(em_cuiaba_que_drenam)} drenam para a seção de controle e "
        f"{len(em_cuiaba_que_nao_drenam)} não drenam, por estarem a jusante dela ou em "
        "ramo distinto da rede;"
    )
    a(
        f"- {len(fora_que_drenam)} barragens situadas fora do município drenam para a "
        "seção de controle e antes ficavam invisíveis à análise;"
    )
    a(
        f"- o conjunto relevante passa a ter {len(drenam)} estruturas, distribuídas em "
        f"{len(por_municipio)} municípios."
    )
    a("")
    a(
        "A verificação em sentido contrário confirma que o critério não é apenas mais "
        "amplo, mas mais seletivo: as 60 barragens de Poconé, que um recorte por "
        "proximidade incluiria, drenam pelo rio Bento Gomes direto para o Pantanal e não "
        "passam pela capital. Nenhuma delas entra no conjunto."
    )
    a("")
    a("Distribuição das estruturas que drenam para a seção de controle:")
    a("")
    a("| Município | Barragens |")
    a("| --- | --- |")
    for nome, quantidade in por_municipio.most_common():
        a(f"| {nome} | {quantidade} |")
    a("")

    # ------------------------------------------------------------------ manso
    a("## 2. O Aproveitamento Múltiplo de Manso")
    a("")
    if not manso:
        a(
            "**Achado:** não há registro do Aproveitamento de Manso no inventário "
            "consolidado. A ausência é, em si, uma falha de cadastro relevante."
        )
    else:
        principal = max(manso, key=lambda r: numero(r.get("altura_m")) or 0)
        a(
            f"O complexo aparece no cadastro como {len(manso)} estruturas distintas sob o "
            "mesmo reservatório, e não como uma barragem única. É importante registrar "
            "isso antes de qualquer número: contagens por registro superestimam o número "
            "de reservatórios e somas de capacidade multiplicam o mesmo volume."
        )
        a("")
        a("Atributos do registro de maior altura, tomado como estrutura principal:")
        a("")
        a("| Atributo | Valor no cadastro |")
        a("| --- | --- |")
        a(f"| Nome | {principal.get('nome')} |")
        a(f"| Município | {principal.get('municipio')} |")
        a(f"| Empreendedor | {principal.get('empreendedor')} |")
        a(f"| Órgão fiscalizador | {principal.get('orgao_fiscalizador')} |")
        a(f"| Curso d'água | {principal.get('curso_dagua')} |")
        a(f"| Região hidrográfica | {principal.get('regiao_hidrografica')} |")
        a(f"| Categoria de Risco (CRI) | {formatar(principal.get('categoria_risco'))} |")
        a(
            f"| Dano Potencial Associado (DPA) | "
            f"{formatar(principal.get('dano_potencial_associado'))} |"
        )
        a(f"| Classe (CNRH) | {formatar(principal.get('classe_cnrh'))} |")
        a(f"| Altura | {formatar(principal.get('altura_m'), ' m')} |")
        a(
            f"| Capacidade do reservatório | "
            f"{pt_br(cap(principal))} hm³ |"
        )
        a(f"| Uso principal | {formatar(principal.get('uso_principal'))} |")
        a(f"| Tipo de material | {formatar(principal.get('tipo_material'))} |")
        a(f"| Fase de vida | {formatar(principal.get('fase_de_vida'))} |")
        a(f"| Plano de Segurança | {formatar(principal.get('possui_plano_de_seguranca'))} |")
        a(f"| Plano de Ação de Emergência | {formatar(principal.get('possui_pae'))} |")
        a(
            f"| Revisão periódica de segurança | "
            f"{formatar(principal.get('possui_revisao_periodica'))} |"
        )
        a(f"| Última inspeção | {formatar(principal.get('data_ultima_inspecao'))} |")
        a(f"| Regulada pelo PNSB | {formatar(principal.get('regulada_pelo_pnsb'))} |")
        a("")

        a("Situação de cada estrutura do complexo quanto aos instrumentos de segurança:")
        a("")
        a("| Estrutura | Município | Altura (m) | Plano de Segurança | PAE | Revisão periódica |")
        a("| --- | --- | --- | --- | --- | --- |")
        for registro in sorted(manso, key=lambda r: -(numero(r.get("altura_m")) or 0)):
            a(
                f"| {registro.get('nome')} | {registro.get('municipio')} | "
                f"{formatar(registro.get('altura_m'))} | "
                f"{formatar(registro.get('possui_plano_de_seguranca'))} | "
                f"{formatar(registro.get('possui_pae'))} | "
                f"{formatar(registro.get('possui_revisao_periodica'))} |"
            )
        a("")

        sem_plano = [r for r in manso if r.get("possui_plano_de_seguranca") != "Sim"]
        sem_pae = [r for r in manso if r.get("possui_pae") != "Sim"]
        sem_revisao = [r for r in manso if r.get("possui_revisao_periodica") != "Sim"]
        a(
            f"**Achado de cadastro.** Entre as {len(manso)} estruturas do complexo, "
            f"{len(sem_plano)} não registram Plano de Segurança, {len(sem_pae)} não "
            f"registram Plano de Ação de Emergência e {len(sem_revisao)} não registram "
            "revisão periódica de segurança. Nenhuma informa data de última inspeção. "
            "Trata-se de estruturas de classe A e Dano Potencial Associado alto, reguladas "
            "pelo PNSB, situadas a montante da capital do estado. A lacuna vale como achado "
            "independentemente de os documentos existirem fora do SNISB: para a vigilância "
            "em saúde, o que não está no cadastro não está disponível no momento da "
            "emergência."
        )
        a("")

    if espelho_manso is not None:
        p = espelho_manso["properties"]
        a(
            "A base de massas d'água da ANA confirma o porte por caminho independente do "
            f"cadastro de barragens: espelho de {pt_br(p.get('nuareakm2') or 0, 1)} km² e "
            f"capacidade de {pt_br(p.get('nuvolumhm3') or 0)} hm³, "
            f"registrado nos municípios de {p.get('nmmun', '').strip().title()}. "
            "É o maior reservatório de Mato Grosso, com mais que o dobro do volume do "
            "segundo colocado."
        )
        a("")

    if trecho_manso and percurso and distancia_talvegue:
        a(
            f"**Posição na bacia.** A barragem está no trecho de código "
            f"`{trecho_manso.cobacia}`, que drena {pt_br(area_manso)} km². "
            f"A seção de controle na capital drena {pt_br(area_capital)} km². "
            f"O Manso controla, portanto, {fracao:.0%} da área de drenagem que chega a "
            "Cuiabá. O percurso pela calha, do eixo da barragem até a capital, soma "
            f"{pt_br(distancia_talvegue)} km ao longo de {len(percurso)} trechos de "
            "drenagem, descendo o rio Manso até a confluência com o rio Cuiabá e seguindo "
            "por este até a capital."
        )
        a("")
        a(
            "A distância é geográfica, medida pelo talvegue. **Não é tempo de chegada de "
            "onda.** A celeridade de uma onda de ruptura depende da vazão de brecha, da "
            "geometria do vale, da rugosidade do leito e do nível do rio no momento do "
            "evento, e só um estudo de *dam break* dimensiona isso. Este relatório não "
            "converte distância em tempo, e recomenda que o setor saúde não trabalhe com "
            "estimativas de tempo de chegada até que o estudo exista."
        )
        a("")

    # ------------------------------------------------- dupla face / cheias
    a("### 2.1 A dupla face do aproveitamento")
    a("")
    a(
        "O Aproveitamento Múltiplo de Manso foi concebido, antes de ser projeto "
        "hidrelétrico, como obra de controle de cheias do rio Cuiabá. A própria "
        "concessionária registra que o empreendimento nasceu em 1980 por iniciativa do "
        "Governo de Mato Grosso com o objetivo inicial de controlar as cheias do rio "
        "Cuiabá, que atingiam repetidamente as comunidades ribeirinhas, e que só depois "
        "lhe foi agregado o aproveitamento hidrelétrico. A operação reserva parte do "
        "volume do reservatório — o volume de espera — para amortecer as cheias afluentes."
    )
    a("")
    a(
        "O efeito é real e mensurável. Estudo de modelagem hidrodinâmica da translação da "
        "onda de cheia efluente do reservatório concluiu que o aproveitamento é capaz de "
        "reduzir a frequência das cheias consideradas de risco para as comunidades a "
        "jusante para períodos de retorno entre 50 e 100 anos, e que o reservatório evitou "
        "uma cheia de grande magnitude em 2006. O mesmo estudo registra que, de três "
        "inundações de maior prejuízo anteriores à usina, duas seriam substancialmente "
        "atenuadas, mas uma terceira ainda atingiria os níveis de alerta da Defesa Civil "
        "estadual."
    )
    a("")
    a(
        "Há portanto duas leituras verdadeiras ao mesmo tempo, e o relatório as sustenta "
        "sem escolher uma:"
    )
    a("")
    a(
        "1. **Em operação normal, o Manso protege Cuiabá e Várzea Grande.** Reduz a "
        "frequência e a magnitude das inundações urbanas e ribeirinhas a jusante, com "
        "efeito direto sobre doenças de veiculação hídrica, deslocamento de população e "
        "interrupção de serviços de saúde."
    )
    a(
        "2. **A mesma estrutura concentra o maior dano potencial da bacia.** Os "
        f"{pt_br(cap(manso[0]) if manso else 0)} hm³ "
        f"retidos {pt_br(distancia_talvegue)} km "
        "acima da capital, controlando "
        f"{fracao:.0%} da área de drenagem que chega a ela, são a maior fonte de dano "
        "potencial concentrado a montante de Cuiabá — muito acima de qualquer estrutura "
        "interna ao município."
    )
    a("")
    a(
        "A tensão entre as duas leituras não é contradição, e é justamente o argumento "
        "mais forte para a preparação do setor saúde. A estrutura que reduz o risco "
        "crônico de inundação é a que concentra o risco agudo de ruptura. Reduzir a "
        "exposição a cheias por meio de uma barragem transfere risco de um evento "
        "frequente e de baixa severidade para um evento raro e de severidade extrema. "
        "Essa transferência exige que a rede de saúde esteja preparada para o cenário "
        "raro, precisamente porque o cenário frequente foi atenuado — e porque a "
        "atenuação do evento frequente tende a estimular a ocupação da planície de "
        "inundação, ampliando a população exposta ao evento raro. O estudo de modelagem "
        "citado faz essa mesma advertência, ao concluir que a segurança da população não "
        "deve depender exclusivamente do reservatório."
    )
    a("")

    # ------------------------------------------------------------ area afetada
    a("### 2.2 Área potencialmente afetada")
    a("")
    a(
        "**Não existe mancha de inundação para nenhuma barragem de Mato Grosso no conjunto "
        "de dados públicos consultado**, e por isso este relatório não apresenta número de "
        "população atingida. O que se delimita aqui é a faixa geográfica potencialmente "
        "afetada, por hidrografia e proximidade, explicitamente rotulada como aproximação."
    )
    a("")
    if atravessados:
        a(
            "Municípios atravessados pelo eixo de drenagem entre a barragem e a capital, "
            "obtidos por interseção dos trechos da BHO com a malha municipal do IBGE: "
            + ", ".join(f"**{m}**" for m in atravessados)
            + "."
        )
        a("")
    if atravessados_jusante:
        a(
            "Municípios atravessados pelo rio Cuiabá a jusante da capital, dentro do "
            "recorte analisado: " + ", ".join(f"**{m}**" for m in atravessados_jusante) + "."
        )
        a("")
    a(
        "A delimitação é uma aproximação por hidrografia e proximidade, e tem três limites "
        "que precisam acompanhar qualquer uso do resultado: identifica municípios "
        "atravessados pela calha, não a área efetivamente inundável; não distingue "
        "população ribeirinha de população em cota alta dentro do mesmo município; e não "
        "informa profundidade, velocidade ou tempo de submersão, que são as variáveis que "
        "determinam letalidade e dano à infraestrutura de saúde."
    )
    a("")
    a(
        "**Recomendação técnica.** A produção de estimativa de população exposta com "
        "precisão utilizável para planejamento depende de estudo de ruptura hipotética "
        "(*dam break*) com mancha de inundação georreferenciada, exigível do empreendedor "
        "no âmbito do Plano de Ação de Emergência. Enquanto a mancha não estiver "
        "disponível, o setor saúde deve trabalhar com o eixo hidrográfico como faixa de "
        "atenção e evitar números de população atingida, que dariam falsa precisão a uma "
        "estimativa sem base física."
    )
    a("")

    # ------------------------------------------------------- hierarquia
    a("## 3. Hierarquia de ameaças e prioridade sanitária")
    a("")
    a(
        "A ordenação abaixo combina dano potencial concentrado, posição na bacia em "
        "relação à capital e estado dos instrumentos de segurança no cadastro. Não é "
        "ordenação por probabilidade de ruptura, que o cadastro não permite estimar."
    )
    a("")

    a("### Primeiro nível — Aproveitamento Múltiplo de Manso, a montante")
    a("")
    a(
        "Maior dano potencial concentrado da bacia. Reservatório de "
        f"{pt_br(cap(manso[0]) if manso else 0)} hm³ "
        f"controlando {fracao:.0%} da área de drenagem que chega a Cuiabá, "
        f"{pt_br(distancia_talvegue)} km "
        "acima da capital pela calha, classe A e DPA alto, com lacunas de Plano de "
        "Segurança, PAE e revisão periódica no cadastro. **Prioridade sanitária máxima "
        "por severidade**, ainda que a categoria de risco cadastrada seja baixa: o CRI "
        "mede condição da estrutura e conformidade documental, não consequência. Para "
        "planejamento de resposta em saúde, o que dimensiona necessidade de leito, "
        "abrigo, água potável e vigilância é a consequência."
    )
    a("")

    a("### Segundo nível — barragens de rejeito de mineração a montante, em Nossa Senhora do Livramento")
    a("")
    if rejeitos:
        a(
            f"São {len(rejeitos)} estruturas de mineração no conjunto que drena para a "
            "capital. As de categoria de risco alta merecem destaque:"
        )
        a("")
        a("| Estrutura | Município | Curso d'água | CRI | DPA | Capacidade (hm³) |")
        a("| --- | --- | --- | --- | --- | --- |")
        for registro in sorted(rejeitos, key=cap, reverse=True):
            if registro.get("categoria_risco") == "Alto" or registro.get("dano_potencial_associado") == "Alto":
                a(
                    f"| {registro.get('nome')} | {registro.get('municipio')} | "
                    f"{registro.get('curso_dagua')} | "
                    f"{formatar(registro.get('categoria_risco'))} | "
                    f"{formatar(registro.get('dano_potencial_associado'))} | "
                    f"{cap(registro):.2f} |"
                )
        a("")
    a(
        "A prioridade deste nível não vem do volume, que é pequeno, mas da natureza do "
        "material retido e da posição. São barragens de rejeito situadas a montante da "
        "capital, com categoria de risco alta no cadastro. Um rompimento aqui não produz "
        "onda comparável à do Manso, mas contamina a calha que abastece a região "
        "metropolitana, com consequência sanitária de natureza distinta — química e "
        "prolongada, não traumática e aguda. **Prioridade sanitária alta por "
        "verossimilhança e por efeito sobre abastecimento de água.**"
    )
    a("")

    a("### Terceiro nível — barragens internas ao município de Cuiabá")
    a("")
    a(
        f"São {len(em_cuiaba)} estruturas cadastradas no município, das quais "
        f"{len(em_cuiaba_que_drenam)} drenam para a seção de controle urbana. Somam "
        f"{pt_br(sum(cap(r) for r in em_cuiaba), 1)} hm³, "
        "ordem de grandeza cerca de "
        f"{pt_br(cap(manso[0]) / max(sum(cap(r) for r in em_cuiaba), 1))} vezes menor que o "
        "Manso isolado. "
        "Predominam pequenos barramentos em córregos urbanos e periurbanos — rio "
        "Bandeira, ribeirão Dois Córregos, córrego Aricazinho, córrego do Ouro. "
        "**Prioridade sanitária média**, com uma ressalva importante: são as estruturas "
        "de maior probabilidade de incidente, por porte pequeno, fiscalização difusa e "
        "proximidade imediata de população, e as de menor severidade por evento. "
        "Concentram risco de eventos frequentes e localizados, que é o que a rede "
        "municipal efetivamente atende no dia a dia."
    )
    a("")
    if em_cuiaba_que_nao_drenam:
        a(
            f"Registre-se que {len(em_cuiaba_que_nao_drenam)} das barragens do município "
            "não drenam para a seção de controle adotada, por estarem a jusante dela ou em "
            "ramo distinto. Elas não deixam de ser objeto da vigilância municipal, mas não "
            "compõem a exposição da mancha urbana central a montante."
        )
        a("")

    if indeterminados:
        a("### Estruturas de posição indeterminada no cadastro")
        a("")
        a(
            f"Em {len(indeterminados)} registros o código de trecho é mais grosseiro que o "
            "da seção de controle, o que impede decidir a posição relativa apenas pelo "
            "código. Entre eles estão as três barragens principais do complexo de Manso, "
            "cadastradas com código `896`, de nível hierárquico superior ao dos próprios "
            "diques do mesmo reservatório, que trazem `89678`. A inconsistência é interna "
            "ao cadastro: um único reservatório aparece com códigos de trecho em dois "
            "níveis de resolução e, no caso do Dique 1, em outra região hidrográfica. "
            "Nesses casos a posição foi resolvida pela geometria do reservatório e pelos "
            "códigos dos diques, e a inconsistência fica registrada como achado."
        )
        a("")

    # ------------------------------------------------------------ montante extra
    a("## 4. Verificação de outras estruturas a montante")
    a("")
    a(
        "A aplicação do critério de posição na bacia a todo o cadastro estadual, e não "
        "apenas aos municípios vizinhos, evita repetir em outra escala o viés que se "
        "quis corrigir. O resultado:"
    )
    a("")
    a("| Estrutura | Município | CRI | DPA | Capacidade (hm³) | Curso d'água |")
    a("| --- | --- | --- | --- | --- | --- |")
    for registro in sorted(criticas, key=cap, reverse=True):
        a(
            f"| {registro.get('nome')} | {registro.get('municipio')} | "
            f"{formatar(registro.get('categoria_risco'))} | "
            f"{formatar(registro.get('dano_potencial_associado'))} | "
            f"{pt_br(cap(registro), 2)} | {registro.get('curso_dagua')} |"
        )
    a("")
    a(
        f"São {len(criticas)} estruturas com categoria de risco alta ou dano potencial "
        "alto entre as que drenam para a capital. Além do Manso e das barragens de "
        "rejeito já tratadas, aparecem estruturas em Rosário Oeste e Jangada, na calha do "
        "próprio rio Cuiabá e do rio Jangada, e o Lago Recreativo Cuiabá, com DPA alto e "
        "categoria de risco não classificada."
    )
    a("")
    a(
        "Um segundo achado do mesmo exercício: as barragens do rio Casca, na Chapada dos "
        "Guimarães, drenam para o próprio reservatório de Manso, configurando cascata a "
        "montante do maior reservatório do estado. A relação em cascata não está sinalizada "
        "no cadastro e é relevante para o Plano de Ação de Emergência do aproveitamento."
    )
    a("")

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    destino = RELATORIOS / "analise_cuiaba.md"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({len(linhas)} linhas)")


if __name__ == "__main__":
    main()
