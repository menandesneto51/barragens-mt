"""Sondagem exploratoria dos servicos de dados de populacoes vulneraveis.

Nao faz parte do pipeline. Serve para descobrir quais endpoints respondem, quais
camadas existem e em que formato, antes de escrever o coletor 09.
"""

from __future__ import annotations

import json
import re
import warnings

import httpx

warnings.filterwarnings("ignore")

FUNAI = "https://geoserver.funai.gov.br/geoserver/ows"
INCRA = "https://acervofundiario.incra.gov.br/i3geo/ogc.php"
PLANILHA_PALMARES = "1WBjixnnjJWrDXsA2WvElj65rrZ4nkNM-u5LclRV0lGs"


def cabecalho(titulo: str) -> None:
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")


def main() -> None:
    cabecalhos = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    with httpx.Client(timeout=180, verify=False, follow_redirects=True, headers=cabecalhos) as cli:
        cabecalho("FUNAI — descreve tis_poligonais e conta feicoes em MT")
        try:
            resposta = cli.get(
                FUNAI,
                params={
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": "Funai:tis_poligonais",
                    "count": 1,
                    "outputFormat": "application/json",
                    "srsName": "EPSG:4326",
                },
            )
            print(f"  HTTP {resposta.status_code} | {resposta.headers.get('content-type')}")
            if resposta.status_code == 200 and "json" in (resposta.headers.get("content-type") or ""):
                dados = resposta.json()
                feicoes = dados.get("features", [])
                if feicoes:
                    print(f"  atributos: {sorted(feicoes[0].get('properties', {}).keys())}")
                    print(f"  geometria: {feicoes[0].get('geometry', {}).get('type')}")
            else:
                print(f"  corpo: {resposta.text[:400]}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERRO {type(exc).__name__} {str(exc)[:200]}")

        for tema in ("assentamentos_mt", "quilombolas_mt", "reconhecimento_mt"):
            cabecalho(f"INCRA i3geo — tema={tema}")
            try:
                resposta = cli.get(
                    INCRA,
                    params={
                        "tema": tema,
                        "service": "WFS",
                        "version": "1.0.0",
                        "request": "GetCapabilities",
                    },
                )
                print(f"  HTTP {resposta.status_code} | {resposta.headers.get('content-type')}")
                texto = resposta.text
                nomes = re.findall(r"<Name>([^<]+)</Name>", texto)
                print(f"  Name encontrados: {nomes[:12]}")
                formatos = re.findall(r"<(?:ows:)?Value>([^<]*json[^<]*)</(?:ows:)?Value>", texto, re.I)
                print(f"  formatos json: {formatos[:6]}")
                if resposta.status_code != 200 or not nomes:
                    print(f"  corpo: {texto[:400]}")
            except Exception as exc:  # noqa: BLE001
                print(f"  ERRO {type(exc).__name__} {str(exc)[:200]}")

        cabecalho("Palmares — exportacao CSV da planilha de comunidades certificadas")
        for gid in ("680278480", "0"):
            url = f"https://docs.google.com/spreadsheets/d/{PLANILHA_PALMARES}/export?format=csv&gid={gid}"
            try:
                resposta = cli.get(url)
                print(f"  gid={gid}: HTTP {resposta.status_code} | {len(resposta.content)/1024:.0f} KB")
                if resposta.status_code == 200:
                    linhas = resposta.text.splitlines()
                    for linha in linhas[:4]:
                        print(f"    {linha[:200]}")
                    print(f"    ... total de linhas: {len(linhas)}")
                    break
            except Exception as exc:  # noqa: BLE001
                print(f"  gid={gid}: ERRO {type(exc).__name__} {str(exc)[:160]}")

        cabecalho("SipamHidro / Censipam")
        for nome, url in {
            "hidro.sipam.gov.br": "https://hidro.sipam.gov.br/",
            "panorama": "https://panorama.sipam.gov.br/home",
        }.items():
            try:
                resposta = cli.get(url)
                print(f"  {nome}: HTTP {resposta.status_code} | {len(resposta.content)/1024:.0f} KB")
            except Exception as exc:  # noqa: BLE001
                print(f"  {nome}: ERRO {type(exc).__name__} {str(exc)[:160]}")


if __name__ == "__main__":
    main()
