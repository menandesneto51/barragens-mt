"""Sondagem: descobre qual filtro CQL a camada de aldeias da FUNAI aceita.

Nao faz parte do pipeline. A requisicao nacional sem filtro devolve 403, entao o
recorte precisa ser feito no servidor.
"""

from __future__ import annotations

import warnings

import httpx

warnings.filterwarnings("ignore")

BASE = "https://geoserver.funai.gov.br/geoserver/ows"
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

FILTROS = [
    "nomuf='MATO GROSSO'",
    "nomuf LIKE 'MATO GROSSO'",
    "cod_municipio LIKE '51%'",
    "nomuf IN ('MATO GROSSO')",
    "BBOX(geom,-61.85,-18.25,-50.00,-7.15)",
]


def main() -> None:
    with httpx.Client(timeout=180, verify=False, follow_redirects=True, headers=NAVEGADOR) as cli:
        for filtro in FILTROS:
            parametros = {
                "service": "WFS",
                "version": "1.1.0",
                "request": "GetFeature",
                "typeName": "Funai:aldeias_pontos",
                "outputFormat": "application/json",
                "srsName": "EPSG:4326",
                "CQL_FILTER": filtro,
            }
            try:
                resposta = cli.get(BASE, params=parametros)
                tipo = resposta.headers.get("content-type") or ""
                print(f"{filtro!r}: HTTP {resposta.status_code} {len(resposta.content) // 1024} KB")
                if resposta.status_code == 200 and "json" in tipo:
                    feicoes = resposta.json().get("features", [])
                    ufs = sorted({(f.get("properties") or {}).get("nomuf") for f in feicoes})
                    print(f"   feicoes: {len(feicoes)} | ufs: {ufs[:6]}")
                else:
                    print("   ", resposta.text[:200].replace("\n", " "))
            except Exception as exc:  # noqa: BLE001
                print(f"{filtro!r}: ERRO {type(exc).__name__} {str(exc)[:140]}")


if __name__ == "__main__":
    main()
