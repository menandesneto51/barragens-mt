"""Setores censitários IBGE 2022 no eixo Manso–Cuiabá.

Baixa (ou reusa brutos) a malha GPKG de MT + agregados básicos do Censo 2022,
filtra municípios do eixo e grava centroides com população (V0001).

Saídas:
  dados/tratados/setores_censitarios_eixo_cuiaba.csv
  dados/tratados/setores_censitarios_eixo_cuiaba.geojson  (Point)
  relatorios/setores_censitarios_eixo.md

Uso:
  python scripts/37_ibge_setores_eixo.py
  python executar.py 37
"""

from __future__ import annotations

import csv
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import comum

BRUTOS = comum.DADOS_BRUTOS / "ibge_setores"
GPKG = BRUTOS / "MT_setores_CD2022.gpkg"
ZIP_AGR = BRUTOS / "agregados_basico_BR.zip"
SAIDA_CSV = comum.DADOS_TRATADOS / "setores_censitarios_eixo_cuiaba.csv"
SAIDA_GEO = comum.DADOS_TRATADOS / "setores_censitarios_eixo_cuiaba.geojson"
REL = comum.RELATORIOS / "setores_censitarios_eixo.md"

URL_GPKG = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/"
    "gpkg/UF/MT/MT_setores_CD2022.gpkg"
)
URL_AGR = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
    "Agregados_por_setores_basico_BR_20260520.zip"
)


def municipios_eixo() -> dict[str, str]:
    path = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if not path.exists():
        raise SystemExit("cuiaba_municipios_de_interesse.json ausente — rode etapa 12")
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for m in data.get("municipios") or []:
        cod = str(m.get("codigo_ibge") or "").strip()
        nome = str(m.get("nome") or "").strip()
        if cod:
            out[cod] = nome
    return out


def _baixar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": "VIGIBARRAGENS-MT/1.0 (IBGE setores; SES-MT)"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp, destino.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)


def garantir_brutos() -> None:
    BRUTOS.mkdir(parents=True, exist_ok=True)
    if not GPKG.exists():
        print(f"Baixando malha MT…", flush=True)
        _baixar(URL_GPKG, GPKG)
    if not ZIP_AGR.exists():
        print("Baixando agregados básicos…", flush=True)
        _baixar(URL_AGR, ZIP_AGR)


def ler_populacao_mt(codigos_mun: set[str]) -> dict[str, dict[str, Any]]:
    """V0001 = pessoas residentes no setor (agregado básico)."""
    pops: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(ZIP_AGR) as zf:
        nome = zf.namelist()[0]
        with zf.open(nome) as raw:
            # Latin-1 / cp1252 nos agregados IBGE
            import io

            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                setor = (row.get("CD_SETOR") or "").strip().strip('"')
                mun = (row.get("CD_MUN") or "").strip().strip('"')
                if not setor.startswith("51") or mun not in codigos_mun:
                    continue
                v = (row.get("v0001") or row.get("V0001") or "").strip().strip('"')
                try:
                    pop = int(float(v.replace(".", "").replace(",", "."))) if v else None
                except ValueError:
                    pop = None
                vdom = (row.get("v0002") or row.get("V0002") or "").strip().strip('"')
                try:
                    dom = int(float(vdom.replace(".", "").replace(",", "."))) if vdom else None
                except ValueError:
                    dom = None
                pops[setor] = {"populacao": pop, "domicilios": dom}
    return pops


def ler_centroides(codigos_mun: set[str]) -> list[dict[str, Any]]:
    """Centroide aproximado = centro da bbox R-Tree do GeoPackage."""
    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in codigos_mun)
    sql = f"""
    SELECT s.CD_SETOR AS codigo_setor,
           s.CD_MUN AS codigo_ibge,
           s.NM_MUN AS municipio,
           s.SITUACAO AS situacao,
           s.AREA_KM2 AS area_km2,
           (r.minx + r.maxx) / 2.0 AS longitude,
           (r.miny + r.maxy) / 2.0 AS latitude
    FROM MT_setores_CD2022 s
    JOIN rtree_MT_setores_CD2022_geom r ON s.id = r.id
    WHERE s.CD_MUN IN ({placeholders})
    """
    rows = [dict(r) for r in con.execute(sql, tuple(codigos_mun))]
    con.close()
    return rows


def main() -> None:
    comum.preparar_diretorios()
    garantir_brutos()
    munis = municipios_eixo()
    cods = set(munis.keys())
    print(f"Municípios do eixo: {len(cods)}", flush=True)
    print("Lendo centroides da malha…", flush=True)
    setores = ler_centroides(cods)
    print(f"  {len(setores)} setores na malha", flush=True)
    print("Lendo população (V0001)…", flush=True)
    pops = ler_populacao_mt(cods)
    print(f"  {len(pops)} setores com agregado", flush=True)

    saida: list[dict[str, Any]] = []
    for s in setores:
        cod = s["codigo_setor"]
        popi = pops.get(cod, {})
        saida.append(
            {
                "codigo_setor": cod,
                "codigo_ibge": s["codigo_ibge"],
                "municipio": s["municipio"] or munis.get(s["codigo_ibge"], ""),
                "situacao": s.get("situacao") or "",
                "area_km2": round(float(s["area_km2"] or 0), 4) if s.get("area_km2") is not None else "",
                "populacao": popi.get("populacao") if popi.get("populacao") is not None else "",
                "domicilios": popi.get("domicilios") if popi.get("domicilios") is not None else "",
                "latitude": round(float(s["latitude"]), 6),
                "longitude": round(float(s["longitude"]), 6),
                "ano_censo": 2022,
                "fonte": "IBGE Censo 2022 — malha setores + agregados básicos (V0001)",
                "aviso": "Centroide = centro da bbox do setor; exposição proxy por centroide na mancha",
            }
        )

    campos = list(saida[0].keys()) if saida else []
    with SAIDA_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(saida)

    feats = []
    for r in saida:
        if r["populacao"] == "":
            continue
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "codigo_setor": r["codigo_setor"],
                    "municipio": r["municipio"],
                    "populacao": r["populacao"],
                    "domicilios": r["domicilios"],
                    "situacao": r["situacao"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]],
                },
            }
        )
    SAIDA_GEO.write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
        encoding="utf-8",
    )

    pop_tot = sum(int(r["populacao"]) for r in saida if r["populacao"] != "")
    pop_fmt = f"{pop_tot:,}".replace(",", ".")
    REL.write_text(
        "\n".join(
            [
                "# Setores censitários — eixo Manso–Cuiabá",
                "",
                f"- Setores: **{len(saida)}**",
                f"- Com população V0001: **{len(feats)}**",
                f"- População somada (centroides): **{pop_fmt}**",
                f"- Arquivos: `{SAIDA_CSV.name}`, `{SAIDA_GEO.name}`",
                "",
                "Uso na simulação: setor exposto se o **centroide** cai na mancha proxy "
                "(círculo / corredor / HAND). Não é população oficial da mancha PAE.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Gravado: {SAIDA_CSV.name} ({len(saida)} setores), pop={pop_tot}", flush=True)


if __name__ == "__main__":
    main()
