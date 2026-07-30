"""Extrai o inventario de barragens do SNISB (ANA) para Mato Grosso.

Fonte: camada "Barragens" do servico ArcGIS do SNIRH/ANA, que consolida o cadastro
alimentado por todos os orgaos fiscalizadores (SEMA-MT, ANM, ANEEL, ANA, IBAMA, etc.).

A extracao roda em duas passadas complementares:
  1. filtro por atributo  -> ING_SG_UFMUNICIPIO = 'MT'
  2. filtro espacial      -> envelope de Mato Grosso
A segunda passada existe porque parte dos registros chega ao SNISB sem o municipio
preenchido; nesses casos so a coordenada revela que a barragem esta em MT.

Saidas em dados/brutos e dados/tratados.
"""

from __future__ import annotations

import json
from typing import Any

import comum

URL_CONSULTA = "https://www.snirh.gov.br/arcgis/rest/services/IG/SNISB/FeatureServer/0/query"
PAGINA = 2000

# Renomeia os campos do servico para nomes legiveis, preservando a ordem de saida.
CAMPOS = {
    "BAR_CD_SNISB": "id_snisb",
    "BAR_NM_NOME": "nome",
    "BAR_NM_SECUNDARIO": "nome_secundario",
    "BAR_CD_BAR_ENT_FISCALIZADORA": "codigo_no_orgao_fiscalizador",
    "ORG_NM_ORGANIZACAO": "orgao_fiscalizador",
    "NM_EMPREENDEDOR": "empreendedor",
    "ING_SG_UFMUNICIPIO": "uf",
    "ING_NM_MUNICIPIO": "municipio",
    "BAR_NU_LATITUDE": "latitude_declarada",
    "BAR_NU_LONGITUDE": "longitude_declarada",
    "USO_PRINCIPAL": "uso_principal",
    "USO_COMPLEMENTAR": "uso_complementar",
    "TIPO_MATERIAL": "tipo_material",
    "BAR_NU_ALT_MAX_BASE_FUNDACAO": "altura_max_fundacao_m",
    "BAR_NU_ALT_MAX_NIVEL_TERRENO": "altura_max_terreno_m",
    "BAR_NU_CAP_TOTAL_RESERV": "capacidade_reservatorio_m3",
    "FASE_DE_VIDA": "fase_de_vida",
    "CATEGORIA_RISCO": "categoria_risco",
    "DANO_POTENCIAL": "dano_potencial_associado",
    "BAR_DS_CLASSE": "classe",
    "NIVEL_PERIGO": "nivel_de_perigo",
    "REGULADA_PELO_PNSB": "regulada_pelo_pnsb",
    "IC_REGULADA": "indicador_regulada",
    "POSSUI_PLANO_SEGURANCA": "possui_plano_de_seguranca",
    "POSSUI_PAE": "possui_pae",
    "POSSUI_REVISAO_PERIODICA": "possui_revisao_periodica",
    "BARRAGEM_AUTUADA": "barragem_autuada",
    "INS_DT_INSPECAO": "data_ultima_inspecao",
    "TP_INSPECAO": "tipo_ultima_inspecao",
    "COMPLETUDE": "completude_cadastro",
    "BAR_DT_CADASTRO": "data_cadastro",
    "AUT_NU_AUTORIZACAO": "numero_autorizacao",
    "AUT_DT_EMISSAO_PUB": "data_emissao_autorizacao",
    "ECL_IC_EXISTE_ECLUSA": "possui_eclusa",
    "ING_NM_REGIAO_HIDRO": "regiao_hidrografica",
    "ING_NM_BACIADNAEE": "bacia_dnaee",
    "ING_NM_TRECHO": "curso_dagua",
    "ING_CD_CURSODAGUA_TRECHO": "codigo_trecho_curso_dagua",
    "DOMINIO_CURSO_DAGUA": "dominio_curso_dagua",
    "ING_NM_COMITEFEDERAL": "comite_de_bacia_federal",
    "ING_NM_COMITEESTADUAL": "comite_de_bacia_estadual",
    "UNIDADE_DE_GESTAO": "unidade_de_gestao",
}

CAMPOS_DATA = {
    "INS_DT_INSPECAO",
    "BAR_DT_CADASTRO",
    "AUT_DT_EMISSAO_PUB",
}


def _parametros_base() -> dict[str, Any]:
    return {
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
        "orderByFields": "BAR_CD_SNISB ASC",
        "resultRecordCount": PAGINA,
    }


def paginar(cli, parametros: dict[str, Any], rotulo: str) -> list[dict[str, Any]]:
    """Percorre todas as paginas da consulta e devolve as feicoes cruas."""
    feicoes: list[dict[str, Any]] = []
    deslocamento = 0
    while True:
        consulta = dict(parametros)
        consulta["resultOffset"] = deslocamento
        resposta = comum.requisitar_json(cli, URL_CONSULTA, consulta)
        if "error" in resposta:
            raise RuntimeError(f"servico retornou erro: {resposta['error']}")
        pagina = resposta.get("features", [])
        feicoes.extend(pagina)
        print(f"  [{rotulo}] offset {deslocamento}: {len(pagina)} feicoes (total {len(feicoes)})")
        if len(pagina) < PAGINA and not resposta.get("exceededTransferLimit"):
            break
        if not pagina:
            break
        deslocamento += len(pagina)
    return feicoes


def normalizar(feicao: dict[str, Any]) -> dict[str, Any]:
    atributos = feicao.get("attributes", {})
    geometria = feicao.get("geometry") or {}

    registro: dict[str, Any] = {}
    for origem, destino in CAMPOS.items():
        valor = atributos.get(origem)
        if origem in CAMPOS_DATA and isinstance(valor, (int, float)):
            # O ArcGIS devolve datas como epoch em milissegundos.
            import datetime as dt

            valor = dt.datetime.fromtimestamp(valor / 1000, tz=dt.timezone.utc).date().isoformat()
        if isinstance(valor, str):
            valor = valor.strip() or None
        registro[destino] = valor

    # A coordenada da geometria e a fonte de verdade; a declarada fica como conferencia.
    registro["longitude"] = geometria.get("x")
    registro["latitude"] = geometria.get("y")
    return registro


def main() -> None:
    comum.preparar_diretorios()
    print("Extraindo barragens do SNISB para Mato Grosso")

    with comum.cliente() as cli:
        por_atributo = paginar(
            cli,
            {**_parametros_base(), "where": f"ING_SG_UFMUNICIPIO = '{comum.UF_SIGLA}'"},
            "uf=MT",
        )

        oeste, sul, leste, norte = comum.BBOX_MT
        por_geometria = paginar(
            cli,
            {
                **_parametros_base(),
                "where": "1=1",
                "geometry": json.dumps(
                    {"xmin": oeste, "ymin": sul, "xmax": leste, "ymax": norte,
                     "spatialReference": {"wkid": 4326}}
                ),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
            },
            "envelope MT",
        )

    comum.salvar_json(
        comum.DADOS_BRUTOS / "snisb_mt_atributo.json",
        {"features": por_atributo},
    )
    comum.salvar_json(
        comum.DADOS_BRUTOS / "snisb_mt_envelope.json",
        {"features": por_geometria},
    )

    indexado: dict[Any, dict[str, Any]] = {}
    ids_por_atributo: set[Any] = set()
    for feicao in por_atributo:
        registro = normalizar(feicao)
        indexado[registro["id_snisb"]] = registro
        ids_por_atributo.add(registro["id_snisb"])

    somente_espacial: set[Any] = set()
    for feicao in por_geometria:
        registro = normalizar(feicao)
        chave = registro["id_snisb"]
        if chave in indexado:
            continue
        if registro.get("uf") and registro["uf"] != comum.UF_SIGLA:
            continue  # barragem de UF vizinha que apenas cai dentro do envelope
        indexado[chave] = registro
        somente_espacial.add(chave)

    registros = sorted(indexado.values(), key=lambda r: (r.get("municipio") or "", r.get("nome") or ""))
    for registro in registros:
        registro["origem_do_registro"] = (
            "envelope_sem_uf" if registro["id_snisb"] in somente_espacial else "atributo_uf"
        )

    colunas = [*CAMPOS.values(), "longitude", "latitude", "origem_do_registro"]
    comum.salvar_csv(comum.DADOS_TRATADOS / "snisb_barragens_mt.csv", registros, colunas)
    comum.salvar_geojson(comum.DADOS_TRATADOS / "snisb_barragens_mt.geojson", registros)

    print(f"\nResumo: {len(registros)} barragens")
    print(f"  por atributo UF='MT': {len(ids_por_atributo)}")
    print(f"  acrescentadas pelo filtro espacial: {len(somente_espacial)}")


if __name__ == "__main__":
    main()
