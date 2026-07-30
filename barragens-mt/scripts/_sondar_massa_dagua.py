"""Descobre o esquema da camada de massa d'agua da ANA para filtrar so os grandes espelhos."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum

CAMADA = "https://www.snirh.gov.br/arcgis/rest/services/SPR/Massa_dagua/FeatureServer/0"

# Recorte apertado no reservatorio de Manso, a partir das coordenadas das barragens.
BBOX_MANSO = (-56.10, -15.10, -55.30, -14.40)


def main() -> None:
    with comum.cliente(verificar_tls=False) as cli:
        print("metadados da camada")
        meta = comum.requisitar_json(cli, CAMADA, {"f": "json"}, tentativas=2)
        print(f"  nome: {meta.get('name')}")
        print(f"  geometria: {meta.get('geometryType')}  maxRecordCount: {meta.get('maxRecordCount')}")
        print("  campos:")
        for campo in meta.get("fields", []):
            print(f"    {campo.get('name'):20s} {campo.get('type'):26s} {campo.get('alias')}")

        geometria = json.dumps(
            {
                "xmin": BBOX_MANSO[0],
                "ymin": BBOX_MANSO[1],
                "xmax": BBOX_MANSO[2],
                "ymax": BBOX_MANSO[3],
                "spatialReference": {"wkid": 4326},
            }
        )
        base = {
            "geometry": geometria,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "f": "json",
        }

        print("\ncontagem no recorte do Manso, sem filtro de area")
        contagem = comum.requisitar_json(
            cli, f"{CAMADA}/query", {**base, "where": "1=1", "returnCountOnly": "true"}, tentativas=2
        )
        print(f"  {contagem}")

        print("\namostra de 5 feicoes no recorte, ordenadas pela maior area")
        campo_area = next(
            (
                c.get("name")
                for c in meta.get("fields", [])
                if "AREA" in (c.get("name") or "").upper()
            ),
            None,
        )
        print(f"  campo de area detectado: {campo_area}")
        amostra = comum.requisitar_json(
            cli,
            f"{CAMADA}/query",
            {
                **base,
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "false",
                "orderByFields": f"{campo_area} DESC" if campo_area else None,
                "resultRecordCount": 5,
            },
            tentativas=2,
        )
        for feicao in amostra.get("features", []):
            print(f"    {feicao.get('attributes')}")


if __name__ == "__main__":
    main()
