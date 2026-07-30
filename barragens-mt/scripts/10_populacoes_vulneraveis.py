"""Coleta as bases de populacoes e territorios vulneraveis de Mato Grosso.

O briefing do Produto 04 exige nominalmente o recorte de comunidades indigenas,
comunidades quilombolas, assentamentos rurais e populacoes ribeirinhas. Nenhum desses
recortes existe no cadastro de barragens, e por isso precisam vir de bases proprias:

  FUNAI    terras indigenas (poligono) e aldeias (ponto), via WFS do GeoServer
  INCRA    assentamentos e territorios quilombolas de MT, via WFS do Acervo Fundiario
  Palmares comunidades quilombolas certificadas, planilha oficial por municipio

Notas de protocolo, descobertas por sondagem e registradas para nao se perderem:
  - o GeoServer da FUNAI recusa WFS 2.0.0 para camadas poligonais, mas atende 1.1.0
    com `typeName` e `maxFeatures`, e entrega `application/json`;
  - o WFS do INCRA e MapServer e so entrega GML2, sem opcao de JSON, o que exige o
    parser deste modulo;
  - a base do INCRA nao traz populacao ribeirinha; ela e tratada no script 12 por
    aproximacao a partir da hidrografia, e rotulada como tal.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Iterable

import comum

FUNAI = "https://geoserver.funai.gov.br/geoserver/ows"
INCRA = "https://acervofundiario.incra.gov.br/i3geo/ogc.php"
PALMARES = (
    "https://docs.google.com/spreadsheets/d/"
    "1WBjixnnjJWrDXsA2WvElj65rrZ4nkNM-u5LclRV0lGs/export?format=csv&gid=680278480"
)

ESPACOS_GML = {"gml": "http://www.opengis.net/gml", "ms": "http://www.omsug.ca/osgis2004"}
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper().strip()


# --------------------------------------------------------------------------- FUNAI


def baixar_funai(camada: str, filtro_cql: str | None = None) -> dict[str, Any]:
    parametros: dict[str, Any] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": camada,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    if filtro_cql:
        parametros["CQL_FILTER"] = filtro_cql
    with comum.cliente(verificar_tls=False) as cli:
        cli.headers.update(NAVEGADOR)
        dados = comum.requisitar_json(cli, FUNAI, parametros)
    feicoes = dados.get("features", [])
    print(f"  {camada}: {len(feicoes)} feicoes")
    return {"type": "FeatureCollection", "features": feicoes}


# --------------------------------------------------------------------------- INCRA


def _coordenadas(texto: str) -> list[list[float]]:
    """Converte uma lista de coordenadas GML2 ('x,y x,y ...') em pares [lon, lat]."""
    pares: list[list[float]] = []
    for bruto in texto.split():
        partes = bruto.split(",")
        if len(partes) < 2:
            continue
        try:
            pares.append([float(partes[0]), float(partes[1])])
        except ValueError:
            continue
    return pares


def _aneis_do_poligono(poligono: ET.Element) -> list[list[list[float]]]:
    aneis: list[list[list[float]]] = []
    for caminho in ("gml:outerBoundaryIs", "gml:innerBoundaryIs"):
        for fronteira in poligono.findall(caminho, ESPACOS_GML):
            for coords in fronteira.iter(f"{{{ESPACOS_GML['gml']}}}coordinates"):
                anel = _coordenadas(coords.text or "")
                if len(anel) >= 4:
                    aneis.append(anel)
    return aneis


def feicoes_de_gml(texto: str, tema: str) -> list[dict[str, Any]]:
    """Converte a resposta GML2 do MapServer do INCRA em feicoes GeoJSON."""
    raiz = ET.fromstring(texto)
    feicoes: list[dict[str, Any]] = []
    for membro in raiz.iter(f"{{{ESPACOS_GML['gml']}}}featureMember"):
        corpo = membro.find(f"{{{ESPACOS_GML['ms']}}}{tema}")
        if corpo is None:
            continue

        propriedades: dict[str, Any] = {}
        for filho in corpo:
            etiqueta = filho.tag.split("}")[-1]
            if etiqueta in {"msGeometry", "boundedBy"}:
                continue
            valor = (filho.text or "").strip()
            propriedades[etiqueta] = valor or None

        poligonos = [
            _aneis_do_poligono(p)
            for p in corpo.iter(f"{{{ESPACOS_GML['gml']}}}Polygon")
        ]
        poligonos = [p for p in poligonos if p]
        if not poligonos:
            continue
        geometria = (
            {"type": "Polygon", "coordinates": poligonos[0]}
            if len(poligonos) == 1
            else {"type": "MultiPolygon", "coordinates": poligonos}
        )
        feicoes.append(
            {"type": "Feature", "geometry": geometria, "properties": propriedades}
        )
    return feicoes


def baixar_incra(tema: str) -> dict[str, Any]:
    with comum.cliente(verificar_tls=False) as cli:
        cli.headers.update(NAVEGADOR)
        resposta = cli.get(
            INCRA,
            params={
                "tema": tema,
                "service": "WFS",
                "version": "1.0.0",
                "request": "GetFeature",
                "typeName": tema,
            },
        )
        resposta.raise_for_status()
        bruto = resposta.text
    (comum.DADOS_BRUTOS / f"incra_{tema}.gml").write_text(bruto, encoding="utf-8")
    feicoes = feicoes_de_gml(bruto, tema)
    print(f"  {tema}: {len(feicoes)} feicoes")
    return {"type": "FeatureCollection", "features": feicoes}


# ------------------------------------------------------------------------ Palmares


def baixar_palmares() -> list[dict[str, Any]]:
    with comum.cliente(verificar_tls=False) as cli:
        cli.headers.update(NAVEGADOR)
        resposta = cli.get(PALMARES)
        resposta.raise_for_status()
        bruto = resposta.text
    (comum.DADOS_BRUTOS / "palmares_quilombolas_brasil.csv").write_text(
        bruto, encoding="utf-8"
    )

    leitor = csv.reader(io.StringIO(bruto))
    linhas = list(leitor)
    cabecalho = [c.strip() for c in linhas[0]]

    # A coluna de UF vem sem rotulo na planilha; identificamos pelo conteudo.
    def parece_uf(indice: int) -> bool:
        amostra = [l[indice].strip() for l in linhas[1:60] if len(l) > indice]
        validos = [v for v in amostra if re.fullmatch(r"[A-Z]{2}", v)]
        return len(validos) > len(amostra) * 0.7

    indice_uf = next((i for i in range(len(cabecalho)) if parece_uf(i)), None)
    if indice_uf is None:
        raise RuntimeError("coluna de UF nao identificada na planilha da Palmares")
    cabecalho[indice_uf] = cabecalho[indice_uf] or "UF"
    print(f"  coluna de UF na posicao {indice_uf}")

    registros: list[dict[str, Any]] = []
    for linha in linhas[1:]:
        if len(linha) <= indice_uf:
            continue
        if linha[indice_uf].strip().upper() != comum.UF_SIGLA:
            continue
        registro = {
            (cabecalho[i] if i < len(cabecalho) and cabecalho[i] else f"coluna_{i}"): (
                valor.strip() or None
            )
            for i, valor in enumerate(linha)
        }
        registros.append(registro)
    print(f"  Palmares: {len(registros)} comunidades certificadas em {comum.UF_SIGLA}")
    return registros


# ---------------------------------------------------------------------- utilidades


def gravar(nome: str, colecao: dict[str, Any], colunas: Iterable[str] | None = None) -> None:
    comum.salvar_json(comum.DADOS_TRATADOS / f"{nome}.geojson", colecao)
    registros = [f.get("properties", {}) for f in colecao["features"]]
    if not registros:
        return
    chaves = list(colunas) if colunas else sorted({k for r in registros for k in r})
    comum.salvar_csv(comum.DADOS_TRATADOS / f"{nome}.csv", registros, chaves)


VAZIA: dict[str, Any] = {"type": "FeatureCollection", "features": []}


def tentar(rotulo: str, acao, indisponiveis: list[str]):
    """Executa a coleta de uma fonte sem deixar que a falha dela derrube as demais.

    O produto tem prazo fixo: e melhor entregar o recorte parcial com a lacuna
    declarada do que perder todas as fontes por causa de um portal fora do ar.
    """
    try:
        return acao()
    except Exception as exc:  # noqa: BLE001
        print(f"  INDISPONIVEL {rotulo}: {type(exc).__name__} {str(exc)[:160]}")
        indisponiveis.append(rotulo)
        return None


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando bases de populacoes e territorios vulneraveis de Mato Grosso")
    indisponiveis: list[str] = []

    print("\nFUNAI — terras indigenas")
    # Terras indigenas podem abranger mais de uma UF; o LIKE mantem as que tocam MT.
    terras = tentar(
        "FUNAI terras indigenas",
        lambda: baixar_funai("Funai:tis_poligonais", "uf_sigla LIKE '%MT%'"),
        indisponiveis,
    ) or VAZIA
    gravar("funai_terras_indigenas_mt", terras)

    print("\nFUNAI — aldeias")
    # A requisicao nacional sem filtro devolve 403, e o filtro por nome de UF nao casa
    # porque a camada grava 'Mato Grosso' em caixa mista. O prefixo 51 do codigo do IBGE
    # identifica Mato Grosso sem ambiguidade e e resolvido no servidor.
    aldeias = tentar(
        "FUNAI aldeias",
        lambda: baixar_funai("Funai:aldeias_pontos", "cod_municipio LIKE '51%'"),
        indisponiveis,
    ) or VAZIA
    fora = [
        f
        for f in aldeias["features"]
        if sem_acento((f.get("properties") or {}).get("nomuf") or "") != "MATO GROSSO"
    ]
    if fora:
        print(f"  atencao: {len(fora)} aldeias com UF divergente do codigo municipal")
    gravar("funai_aldeias_mt", aldeias)

    print("\nINCRA — assentamentos e territorios quilombolas")
    assentamentos = tentar(
        "INCRA assentamentos", lambda: baixar_incra("assentamentos_mt"), indisponiveis
    ) or VAZIA
    gravar("incra_assentamentos_mt", assentamentos)
    quilombolas = tentar(
        "INCRA quilombolas", lambda: baixar_incra("quilombolas_mt"), indisponiveis
    ) or VAZIA
    gravar("incra_quilombolas_mt", quilombolas)

    print("\nFundacao Cultural Palmares — comunidades certificadas")
    certificadas = tentar("Palmares", baixar_palmares, indisponiveis) or []
    if certificadas:
        comum.salvar_csv(
            comum.DADOS_TRATADOS / "palmares_quilombolas_mt.csv",
            certificadas,
            list(certificadas[0].keys()),
        )

    familias = sum(
        int(float((f["properties"].get("num_familias") or 0)))
        for f in assentamentos["features"]
        if (f["properties"].get("num_familias") or "").replace(".", "").isdigit()
    )
    print("\nResumo")
    print(f"  terras indigenas que tocam MT: {len(terras['features'])}")
    print(f"  aldeias em MT: {len(aldeias['features'])}")
    print(f"  assentamentos em MT: {len(assentamentos['features'])} ({familias} familias)")
    print(f"  territorios quilombolas (INCRA) em MT: {len(quilombolas['features'])}")
    print(f"  comunidades quilombolas certificadas (Palmares) em MT: {len(certificadas)}")
    if indisponiveis:
        print(f"\n  fontes indisponiveis nesta execucao: {', '.join(indisponiveis)}")


if __name__ == "__main__":
    main()
