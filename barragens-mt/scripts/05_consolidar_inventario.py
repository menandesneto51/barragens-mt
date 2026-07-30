"""Consolida o inventario unico de barragens de Mato Grosso.

Junta as coletas em uma base analitica:
  - 01_snisb_mt.py       -> espinha dorsal (todas as barragens, todos os fiscalizadores)
  - 02_sigbm_anm.py      -> detalhe de engenharia das barragens de rejeito de mineracao
  - 04_powerbi_snisb.py  -> OPCIONAL e NAO CONFORME (PBI-01). Se o CSV nao existir, os
                            campos exclusivos dessa fonte ficam vazios e a coluna
                            origem_campos_nao_conformes registra "ausente".

E aqui que os problemas de qualidade viram colunas explicitas, em vez de ficarem
escondidos: nome de municipio com caixa inconsistente, altura negativa, coordenada
fora do estado e ausencia de classificacao de risco.

Nota de unidade: o campo BAR_NU_CAP_TOTAL_RESERV do SNISB esta em hm3 (milhoes de m3),
apesar do nome sugerir m3. A maior barragem de MT, o reservatorio de Manso, aparece
com 7.337 - que sao 7,337 bilhoes de m3, valor correto para o empreendimento.
"""

from __future__ import annotations

import csv
import unicodedata
from typing import Any

import comum

# Matriz de classificacao da Resolucao CNRH no 143/2012: cruza Categoria de Risco (CRI)
# com Dano Potencial Associado (DPA) para definir a classe da barragem.
MATRIZ_CLASSE = {
    ("Alto", "Alto"): "A",
    ("Medio", "Alto"): "A",
    ("Baixo", "Alto"): "A",
    ("Alto", "Medio"): "B",
    ("Medio", "Medio"): "C",
    ("Baixo", "Medio"): "C",
    ("Alto", "Baixo"): "C",
    ("Medio", "Baixo"): "D",
    ("Baixo", "Baixo"): "E",
}

PESO_CRI = {"Alto": 3, "Medio": 2, "Baixo": 1}
PESO_DPA = {"Alto": 3, "Medio": 2, "Baixo": 1}

# Grafias usadas pelos orgaos fiscalizadores que divergem do nome oficial do IBGE.
VARIANTES_MUNICIPIO = {
    "SANTO ANTONIO DO LEVERGER": "SANTO ANTONIO DE LEVERGER",
}

# Campos cuja unica origem e a fonte nao conforme PBI-01. Ficam sempre no esquema, para
# que o CSV tenha as mesmas colunas com ou sem a etapa 04, e vazios quando ela nao roda.
CAMPOS_NAO_CONFORMES = (
    "comprimento_coroamento_m",
    "altura_estimada_m",
    "capacidade_estimada_m3",
    "data_ultima_fiscalizacao",
    "data_ultima_autuacao",
    "tipo_empreendedor",
    "corpo_hidrico",
    "data_atualizacao_registro",
)


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def chave_municipio(nome: str | None) -> str:
    chave = sem_acento((nome or "").strip()).upper()
    return VARIANTES_MUNICIPIO.get(chave, chave)


def ler_csv(caminho) -> list[dict[str, Any]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def numero(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def main() -> None:
    comum.preparar_diretorios()

    barragens = ler_csv(comum.DADOS_TRATADOS / "snisb_barragens_mt.csv")

    # Fonte PBI-01: nao conforme, portanto opcional. A ausencia do arquivo e o caminho
    # normal do pipeline, nao um erro.
    caminho_powerbi = comum.DADOS_TRATADOS / "powerbi_snisb_mt.csv"
    if caminho_powerbi.exists():
        complementos = {linha["id_snisb"]: linha for linha in ler_csv(caminho_powerbi)}
        print("AVISO: enriquecendo com PBI-01, fonte classificada como nao conforme.")
    else:
        complementos = {}
        print("Fonte nao conforme PBI-01 ausente: campos exclusivos dela ficarao vazios.")

    municipios_ibge = ler_csv(comum.DADOS_TRATADOS / "ibge_municipios_mt.csv")
    print(f"SNISB {len(barragens)} | PBI-01 {len(complementos)} | IBGE {len(municipios_ibge)}")

    indice_ibge = {chave_municipio(m["municipio"]): m for m in municipios_ibge}

    # As barragens de mineracao sao casadas por nome + municipio porque o SIGBM nao
    # carrega o identificador do SNISB.
    sigbm = ler_csv(comum.DADOS_TRATADOS / "sigbm_barragens_mt.csv")
    indice_sigbm = {
        (chave_municipio(linha.get("Nome")), chave_municipio(linha.get("Município"))): linha
        for linha in sigbm
    }

    consolidado: list[dict[str, Any]] = []
    alertas = {
        "municipio_sem_correspondencia_ibge": 0,
        "altura_negativa": 0,
        "coordenada_fora_do_estado": 0,
        "sem_classificacao_de_risco": 0,
        "casado_com_sigbm": 0,
        "enriquecido_pelo_powerbi": 0,
    }

    for origem in barragens:
        registro: dict[str, Any] = dict(origem)

        nome_municipio = (origem.get("municipio") or "").strip()
        chave = chave_municipio(nome_municipio)
        correspondencia = indice_ibge.get(chave)
        if correspondencia:
            # Nome oficial do IBGE resolve a divergencia de caixa entre orgaos.
            registro["municipio"] = correspondencia["municipio"]
            registro["codigo_ibge"] = correspondencia["codigo_ibge"]
            registro["mesorregiao"] = correspondencia["mesorregiao"]
            registro["regiao_intermediaria"] = correspondencia["regiao_intermediaria"]
        else:
            registro["codigo_ibge"] = None
            registro["mesorregiao"] = None
            registro["regiao_intermediaria"] = None
            if nome_municipio:
                alertas["municipio_sem_correspondencia_ibge"] += 1

        altura = numero(origem.get("altura_max_terreno_m"))
        altura_fundacao = numero(origem.get("altura_max_fundacao_m"))
        # Altura negativa e erro de digitacao no cadastro; preserva-se o valor original
        # em coluna separada para nao mascarar o problema na fonte.
        registro["altura_m"] = abs(altura) if altura is not None else None
        if (altura is not None and altura < 0) or (altura_fundacao is not None and altura_fundacao < 0):
            alertas["altura_negativa"] += 1
            registro["alerta_altura_negativa"] = "sim"
        else:
            registro["alerta_altura_negativa"] = "nao"

        capacidade_hm3 = numero(origem.get("capacidade_reservatorio_m3"))
        registro["capacidade_hm3"] = capacidade_hm3
        registro["capacidade_m3"] = capacidade_hm3 * 1_000_000 if capacidade_hm3 is not None else None

        longitude, latitude = numero(origem.get("longitude")), numero(origem.get("latitude"))
        if not comum.dentro_do_bbox(longitude, latitude):
            alertas["coordenada_fora_do_estado"] += 1
            registro["alerta_coordenada"] = "sim"
        else:
            registro["alerta_coordenada"] = "nao"

        cri = sem_acento((origem.get("categoria_risco") or "").strip())
        dpa = sem_acento((origem.get("dano_potencial_associado") or "").strip())
        registro["classe_cnrh"] = MATRIZ_CLASSE.get((cri, dpa))
        if cri not in PESO_CRI or dpa not in PESO_DPA:
            alertas["sem_classificacao_de_risco"] += 1
            registro["prioridade_fiscalizacao"] = None
        else:
            # Escala 1-9: o produto CRI x DPA ordena a fila de fiscalizacao.
            registro["prioridade_fiscalizacao"] = PESO_CRI[cri] * PESO_DPA[dpa]

        complemento = complementos.get(origem["id_snisb"])
        for campo in CAMPOS_NAO_CONFORMES:
            registro[campo] = (complemento.get(campo) or None) if complemento else None
        registro["origem_campos_nao_conformes"] = "PBI-01" if complemento else "ausente"
        if complemento:
            alertas["enriquecido_pelo_powerbi"] += 1

        mineracao = indice_sigbm.get((chave_municipio(origem.get("nome")), chave))
        if mineracao:
            alertas["casado_com_sigbm"] += 1
            registro["sigbm_metodo_construtivo"] = mineracao.get("Método construtivo da barragem")
            registro["sigbm_tipo_alteamento"] = mineracao.get("Tipo de alteamento")
            registro["sigbm_nivel_emergencia"] = mineracao.get("Nível de Emergência")
            registro["sigbm_situacao_operacional"] = mineracao.get("Situação Operacional")
            registro["sigbm_status_dce"] = mineracao.get("Status da DCO Atual")
            registro["sigbm_populacao_jusante"] = mineracao.get("Existência de população a jusante")
            registro["sigbm_pessoas_afetadas"] = mineracao.get(
                "Número de pessoas possivelmente afetadas a jusante em caso de rompimento da barragem"
            )
            registro["sigbm_minerio"] = mineracao.get("Minério principal presente no reservatório")

        consolidado.append(registro)

    colunas = list(dict.fromkeys(chave for registro in consolidado for chave in registro))
    comum.salvar_csv(comum.DADOS_TRATADOS / "inventario_barragens_mt.csv", consolidado, colunas)
    comum.salvar_geojson(comum.DADOS_TRATADOS / "inventario_barragens_mt.geojson", consolidado)

    print("\nQualidade e cobertura:")
    for rotulo, quantidade in alertas.items():
        print(f"  {rotulo:38s} {quantidade:5d}")

    sem_ibge = sorted(
        {
            (r.get("municipio") or "(vazio)")
            for r in consolidado
            if r.get("codigo_ibge") in (None, "")
        }
    )
    if sem_ibge:
        print(f"\nMunicipios sem correspondencia no IBGE ({len(sem_ibge)}):")
        for nome in sem_ibge:
            print(f"  - {nome}")


if __name__ == "__main__":
    main()
