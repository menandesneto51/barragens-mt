"""Extrai atributos complementares do painel Power BI oficial do SNISB (ANA).

    FONTE NAO CONFORME - DESATIVADA POR PADRAO

A Especificacao Funcional e Tecnica do VIGIBARRAGENS-MT (Produto 04) classifica esta
fonte como PBI-01, disponibilidade classe E, com a diretriz explicita "nao usar como
fonte", e coloca a raspagem do relatorio fora de escopo enquanto as bases subjacentes
nao forem identificadas junto a ANA. A restricao e de governanca, nao de viabilidade
tecnica: o endpoint responde e a extracao funciona.

Por isso o script exige ativacao explicita e o pipeline (executar.py) pula a etapa 04
por padrao. O inventario consolidado opera sem este CSV; os campos abaixo ficam vazios
e sao marcados como de origem nao conforme em 05_consolidar_inventario.py.

Para ativar, de forma consciente e apenas em investigacao exploratoria:
    python scripts/04_powerbi_snisb.py --confirmar-fonte-nao-conforme
    ou VIGIBARRAGENS_PERMITIR_POWERBI=1

Caminho de regularizacao: solicitar formalmente a ANA o conjunto de dados que alimenta
o relatorio, ou obter os mesmos campos por servico oficial documentado.

--- Nota tecnica original ---
O servico ArcGIS usado em 01_snisb_mt.py expoe 43 campos, enquanto o modelo semantico
por tras do painel publico do SNISB expoe 73. Campos como comprimento do coroamento,
data da ultima fiscalizacao, data da ultima autuacao e tipo de empreendedor so existem
aqui. O PBIX publicado e um instantaneo, enquanto o ArcGIS costuma estar mais atual;
portanto o inventario base continua sendo o do script 01 e estes campos entrariam como
enriquecimento, casados por BAR_CD_SNISB. O painel e publish-to-web, logo a consulta e
anonima.
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from typing import Any

import httpx

import comum

warnings.filterwarnings("ignore")

ARGUMENTO_ATIVACAO = "--confirmar-fonte-nao-conforme"
VARIAVEL_ATIVACAO = "VIGIBARRAGENS_PERMITIR_POWERBI"

AVISO_NAO_CONFORME = f"""
{'=' * 78}
ETAPA 04 IGNORADA - FONTE CLASSIFICADA COMO NAO CONFORME
{'=' * 78}
O Produto 04 classifica o painel Power BI do SNISB como PBI-01, disponibilidade
classe E, "nao usar como fonte", e poe a raspagem fora de escopo ate que as bases
subjacentes sejam identificadas junto a ANA.

O pipeline segue sem esta fonte. Os campos exclusivos dela (comprimento do
coroamento, data da ultima fiscalizacao, data da ultima autuacao, tipo de
empreendedor, corpo hidrico) ficarao vazios no inventario consolidado.

Para executar ainda assim, de forma deliberada:
  python scripts/04_powerbi_snisb.py {ARGUMENTO_ATIVACAO}
  ou defina {VARIAVEL_ATIVACAO}=1
{'=' * 78}
"""


def ativado() -> bool:
    return ARGUMENTO_ATIVACAO in sys.argv or os.environ.get(VARIAVEL_ATIVACAO) == "1"

CHAVE_RECURSO = "6efe9238-3013-4c9b-801f-82d47d834186"
CLUSTER = "https://wabi-brazil-south-d-primary-api.analysis.windows.net"
ID_MODELO = 779622
ID_CONJUNTO = "511244c9-ac00-4fea-8d4c-f3420e1f72e8"
ID_RELATORIO = "c0636a3b-d171-451e-8c61-fd5563ab3a00"
ID_VISUAL = "0c81d8e2c31014a23f6b"
ENTIDADE = "VW_RELATORIO_BARRAGENS"

# Chave de casamento + campos que o servico ArcGIS nao entrega.
COLUNAS = [
    ("BAR_CD_SNISB", "id_snisb"),
    ("BAR_NM_NOME", "nome_powerbi"),
    ("ING_NM_MUNICIPIO", "municipio_powerbi"),
    ("COMPRIMENTO_COROAMENTO", "comprimento_coroamento_m"),
    ("ALTURAESTIMADA", "altura_estimada_m"),
    ("CAPACIDADETOTALESTIMADA", "capacidade_estimada_m3"),
    ("DATA_ULT_FISCALIZACAO", "data_ultima_fiscalizacao"),
    ("DATA_ULT_AUTUACAO", "data_ultima_autuacao"),
    ("FASE_DE_VIDA_DATA_INICIO", "data_inicio_fase_de_vida"),
    ("CTF_DT_INSPSEGREG", "data_inspecao_seguranca_regular"),
    ("TIPO_EMPREENDEDOR", "tipo_empreendedor"),
    ("ING_NM_CORPOHIDRICO", "corpo_hidrico"),
    ("BAR_DT_ATUALIZACAO", "data_atualizacao_registro"),
    ("CLR_DS", "situacao_cadastro"),
]

JANELA = 5000

CABECALHOS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "X-PowerBI-ResourceKey": CHAVE_RECURSO,
    "ActivityId": "11111111-1111-1111-1111-111111111111",
    "RequestId": "33333333-3333-3333-3333-333333333333",
    "Origin": "https://app.powerbi.com",
    "Referer": "https://app.powerbi.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
}


def montar_consulta(colunas: list[str], reinicio: Any = None) -> dict[str, Any]:
    seletores = [
        {
            "Column": {"Expression": {"SourceRef": {"Source": "v"}}, "Property": coluna},
            "Name": f"v.{coluna}",
        }
        for coluna in colunas
    ]
    janela: dict[str, Any] = {"Count": JANELA}
    if reinicio:
        janela["RestartTokens"] = reinicio

    return {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [{"Name": "v", "Entity": ENTIDADE, "Type": 0}],
                                    "Select": seletores,
                                    "Where": [
                                        {
                                            "Condition": {
                                                "In": {
                                                    "Expressions": [
                                                        {
                                                            "Column": {
                                                                "Expression": {"SourceRef": {"Source": "v"}},
                                                                "Property": "ING_SG_UFMUNICIPIO",
                                                            }
                                                        }
                                                    ],
                                                    "Values": [[{"Literal": {"Value": f"'{comum.UF_SIGLA}'"}}]],
                                                }
                                            }
                                        }
                                    ],
                                    "OrderBy": [
                                        {
                                            "Direction": 1,
                                            "Expression": {
                                                "Column": {
                                                    "Expression": {"SourceRef": {"Source": "v"}},
                                                    "Property": "BAR_CD_SNISB",
                                                }
                                            },
                                        }
                                    ],
                                },
                                "Binding": {
                                    "Primary": {"Groupings": [{"Projections": list(range(len(colunas)))}]},
                                    "DataReduction": {"DataVolume": 3, "Primary": {"Window": janela}},
                                    "Version": 1,
                                },
                                "ExecutionMetricsKind": 1,
                            }
                        }
                    ]
                },
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": ID_CONJUNTO,
                    "Sources": [{"ReportId": ID_RELATORIO, "VisualId": ID_VISUAL}],
                },
            }
        ],
        "cancelQueries": [],
        "modelId": ID_MODELO,
    }


TIPO_DATA = 7


def decodificar_dsr(dsr: dict[str, Any]) -> tuple[list[list[Any]], list[dict[str, Any]], Any]:
    """Expande o formato compactado DSR do Power BI em linhas planas.

    Cada linha traz apenas os valores que mudaram em relacao a anterior: o inteiro R
    marca, bit a bit, as colunas repetidas e o inteiro sob a chave 'O cortado' marca as
    colunas nulas. Ambas ficam ausentes do vetor C, entao o cursor so avanca nas demais.
    Colunas com dicionario (DN) guardam indices para ValueDicts.

    O esquema das colunas vem embutido na primeira linha do bloco, nao no cabecalho do
    conjunto, por isso e capturado na primeira iteracao e reaproveitado nas seguintes.
    """
    conjunto = dsr["DS"][0]
    dicionarios = conjunto.get("ValueDicts", {})

    esquema: list[dict[str, Any]] = []
    linhas: list[list[Any]] = []
    anterior: list[Any] = []

    for bloco in conjunto.get("PH", []):
        for chave, cruas in bloco.items():
            if not chave.startswith("DM"):
                continue
            for crua in cruas:
                if "S" in crua:
                    esquema = crua["S"]
                    anterior = [None] * len(esquema)
                if not esquema:
                    raise RuntimeError("bloco DSR sem esquema de colunas")

                valores = crua.get("C", [])
                repetidas = crua.get("R", 0)
                nulas = crua.get("\u00d8", 0)
                atual: list[Any] = []
                cursor = 0
                for indice, coluna in enumerate(esquema):
                    marca = 1 << indice
                    if nulas & marca:
                        atual.append(None)
                    elif repetidas & marca:
                        atual.append(anterior[indice])
                    else:
                        valor = valores[cursor] if cursor < len(valores) else None
                        cursor += 1
                        nome_dicionario = coluna.get("DN")
                        if nome_dicionario is not None and isinstance(valor, int):
                            tabela = dicionarios.get(nome_dicionario, [])
                            valor = tabela[valor] if 0 <= valor < len(tabela) else valor
                        atual.append(valor)
                anterior = atual
                linhas.append(atual)

    return linhas, esquema, conjunto.get("RT")


def consultar(cli: httpx.Client, colunas: list[str]) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    todas: list[list[Any]] = []
    esquema: list[dict[str, Any]] = []
    reinicio = None
    while True:
        resposta = cli.post(
            f"{CLUSTER}/public/reports/querydata",
            params={"synchronous": "true"},
            json=montar_consulta(colunas, reinicio),
        )
        resposta.raise_for_status()
        corpo = resposta.json()
        resultado = corpo["results"][0]["result"]
        if "data" not in resultado:
            raise RuntimeError(f"resposta inesperada: {json.dumps(corpo)[:600]}")
        linhas, esquema_pagina, reinicio = decodificar_dsr(resultado["data"]["dsr"])
        esquema = esquema or esquema_pagina
        todas.extend(linhas)
        print(f"  recebidas {len(linhas)} linhas (acumulado {len(todas)})")
        if not reinicio or not linhas:
            break
    return todas, esquema


def main() -> None:
    if not ativado():
        print(AVISO_NAO_CONFORME)
        return

    comum.preparar_diretorios()
    origem = [coluna for coluna, _ in COLUNAS]
    destino = [apelido for _, apelido in COLUNAS]

    print("ATENCAO: executando coleta de fonte classificada como NAO CONFORME (PBI-01).")
    print(f"Consultando o modelo do painel SNISB ({len(origem)} colunas, UF={comum.UF_SIGLA})")
    # O ambiente tem proxy TLS interceptador; o conteudo e publico e anonimo.
    with httpx.Client(timeout=180, headers=CABECALHOS, follow_redirects=True, verify=False) as cli:
        linhas, esquema = consultar(cli, origem)

    import datetime as dt

    eh_data = [coluna.get("T") == TIPO_DATA for coluna in esquema]
    registros = []
    for linha in linhas:
        valores = []
        for indice, valor in enumerate(linha):
            # Colunas de data chegam como epoch em milissegundos.
            if indice < len(eh_data) and eh_data[indice] and isinstance(valor, (int, float)):
                valor = (
                    dt.datetime.fromtimestamp(valor / 1000, tz=dt.timezone.utc).date().isoformat()
                )
            valores.append(valor)
        registros.append(dict(zip(destino, valores)))

    comum.salvar_json(comum.DADOS_BRUTOS / "powerbi_snisb_mt.json", registros)
    comum.salvar_csv(comum.DADOS_TRATADOS / "powerbi_snisb_mt.csv", registros, destino)

    preenchidos = {
        campo: sum(1 for r in registros if r.get(campo) not in (None, ""))
        for campo in destino
    }
    print("\nPreenchimento por campo:")
    for campo, quantidade in preenchidos.items():
        pct = 100 * quantidade / len(registros) if registros else 0
        print(f"  {campo:34s} {quantidade:5d} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
