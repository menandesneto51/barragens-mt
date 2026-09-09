"""Ativos essenciais no eixo (proxy C5) via OpenStreetMap.

Complementa escolas/captações/pontes com:
  - ETA / water_works
  - ETE / wastewater_plant
  - Subestações de energia
  - Abrigos / pontos de reunião
  - Bases de ambulância (quando mapeadas)

Saídas:
  dados/tratados/ativos_essenciais_osm_eixo.csv
  dados/tratados/ativos_essenciais_osm_eixo.geojson
  relatorios/ativos_essenciais_osm_eixo.md

Uso:
  python scripts/46_ativos_essenciais_osm_eixo.py
  python executar.py 46
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.DADOS_TRATADOS / "ativos_essenciais_osm_eixo.csv"
SAIDA_GEO = comum.DADOS_TRATADOS / "ativos_essenciais_osm_eixo.geojson"
REL = comum.RELATORIOS / "ativos_essenciais_osm_eixo.md"
EIXO_GEO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)
UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; ativos essenciais eixo)"

CAMPOS = [
    "categoria",
    "nome",
    "municipio",
    "latitude",
    "longitude",
    "osm_tipo",
    "osm_id",
    "tags_resumo",
    "fonte",
    "observacao",
]


def bbox_eixo() -> tuple[float, float, float, float]:
    if EIXO_GEO.exists():
        try:
            gj = json.loads(EIXO_GEO.read_text(encoding="utf-8"))
            lats: list[float] = []
            lons: list[float] = []

            def _walk(coords: Any) -> None:
                if isinstance(coords, (list, tuple)) and coords:
                    if isinstance(coords[0], (int, float)):
                        lons.append(float(coords[0]))
                        lats.append(float(coords[1]))
                    else:
                        for c in coords:
                            _walk(c)

            for f in gj.get("features") or []:
                _walk((f.get("geometry") or {}).get("coordinates"))
            if lats and lons:
                pad = 0.10
                return (
                    min(lats) - pad,
                    min(lons) - pad,
                    max(lats) + pad,
                    max(lons) + pad,
                )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return (-16.15, -56.55, -15.20, -55.55)


def _post_overpass(q: str) -> dict[str, Any] | None:
    data = urllib.parse.urlencode({"data": q}).encode()
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": UA,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  Overpass {url}: {exc}")
            time.sleep(2)
    return None


def _centroide(el: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])
    geom = el.get("geometry") or []
    if geom:
        lats = [float(p["lat"]) for p in geom if "lat" in p]
        lons = [float(p["lon"]) for p in geom if "lon" in p]
        if lats and lons:
            return sum(lats) / len(lats), sum(lons) / len(lons)
    center = el.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def _classificar(tags: dict[str, str]) -> str | None:
    mm = (tags.get("man_made") or "").lower()
    ww = (tags.get("waterway") or "").lower()
    power = (tags.get("power") or "").lower()
    amenity = (tags.get("amenity") or "").lower()
    social = (tags.get("social_facility") or "").lower()
    emergency = (tags.get("emergency") or "").lower()
    if mm in {"water_works", "water_tower", "water_well"} or ww == "water_works":
        return "eta_agua"
    if mm in {"wastewater_plant", "wastewater_tank"}:
        return "ete_esgoto"
    if power == "substation" or mm == "substation":
        return "subestacao_energia"
    if (
        amenity == "shelter"
        or social in {"shelter", "emergency_shelter"}
        or emergency in {"assembly_point", "shelter"}
    ):
        return "abrigo"
    if amenity == "ambulance_station" or emergency == "ambulance_station":
        return "base_ambulancia"
    return None


def coletar() -> list[dict[str, Any]]:
    south, west, north, east = bbox_eixo()
    q = f"""
[out:json][timeout:70];
(
  node["man_made"~"^(water_works|wastewater_plant|water_tower|substation)$"]({south},{west},{north},{east});
  way["man_made"~"^(water_works|wastewater_plant|water_tower|substation)$"]({south},{west},{north},{east});
  node["power"="substation"]({south},{west},{north},{east});
  way["power"="substation"]({south},{west},{north},{east});
  node["amenity"="shelter"]({south},{west},{north},{east});
  node["social_facility"~"shelter"]({south},{west},{north},{east});
  node["emergency"~"^(assembly_point|shelter|ambulance_station)$"]({south},{west},{north},{east});
  node["amenity"="ambulance_station"]({south},{west},{north},{east});
  way["amenity"="ambulance_station"]({south},{west},{north},{east});
);
out center tags;
""".strip()
    print(f"  Overpass bbox {south:.3f},{west:.3f},{north:.3f},{east:.3f}", flush=True)
    raw = _post_overpass(q)
    if not raw:
        return []

    vistos: set[str] = set()
    out: list[dict[str, Any]] = []
    for el in raw.get("elements") or []:
        tags = {str(k): str(v) for k, v in (el.get("tags") or {}).items()}
        cat = _classificar(tags)
        if not cat:
            continue
        xy = _centroide(el)
        if not xy:
            continue
        lat, lon = xy
        osm_id = f"{el.get('type')}/{el.get('id')}"
        if osm_id in vistos:
            continue
        vistos.add(osm_id)
        nome = tags.get("name") or tags.get("operator") or cat.replace("_", " ").title()
        resumo = ";".join(
            f"{k}={tags[k]}"
            for k in ("man_made", "power", "amenity", "emergency", "social_facility")
            if k in tags
        )
        out.append(
            {
                "categoria": cat,
                "nome": nome[:120],
                "municipio": tags.get("addr:city") or "",
                "latitude": f"{lat:.6f}",
                "longitude": f"{lon:.6f}",
                "osm_tipo": str(el.get("type") or ""),
                "osm_id": str(el.get("id") or ""),
                "tags_resumo": resumo[:200],
                "fonte": "OSM",
                "observacao": "Proxy espacial C5 — preferir cadastros oficiais SES/Defesa Civil/concessionárias",
            }
        )
    return sorted(out, key=lambda r: (r["categoria"], r["nome"]))


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando ativos essenciais OSM no eixo…", flush=True)
    regs = coletar()
    if not regs:
        raise SystemExit("nenhum ativo essencial retornado pelo Overpass")

    comum.salvar_csv(SAIDA, regs, CAMPOS)
    feats = []
    for r in regs:
        feats.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r["longitude"]), float(r["latitude"])],
                },
                "properties": {k: r.get(k, "") for k in CAMPOS},
            }
        )
    comum.salvar_json(SAIDA_GEO, {"type": "FeatureCollection", "features": feats})

    por_cat: dict[str, int] = {}
    for r in regs:
        por_cat[r["categoria"]] = por_cat.get(r["categoria"], 0) + 1
    linhas = [
        "# Ativos essenciais OSM — eixo Manso–Cuiabá",
        "",
        f"- Total: **{len(regs)}**",
        "",
        "| Categoria | N |",
        "| --- | ---: |",
    ]
    for k, n in sorted(por_cat.items()):
        linhas.append(f"| `{k}` | {n} |")
    linhas += [
        "",
        f"- Arquivos: `{SAIDA.relative_to(comum.RAIZ)}`, `{SAIDA_GEO.relative_to(comum.RAIZ)}`",
        "",
        "Proxy OpenStreetMap para C5 (ETA/ETE/energia/abrigos/ambulância).",
        "Não substitui cadastro oficial de concessionárias ou Defesa Civil.",
        "",
    ]
    REL.write_text("\n".join(linhas), encoding="utf-8")
    print(f"  {len(regs)} ativos · {por_cat}")
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
