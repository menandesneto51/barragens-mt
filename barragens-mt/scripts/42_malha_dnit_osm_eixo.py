"""Malha rodoviária federal/estadual no eixo (proxy DNIT via OSM).

O portal DNIT/dnitcloud costuma falhar neste ambiente. Como proxy aberto e
gratuito, consulta Overpass por vias com `ref` BR-* / MT-* (e pontes) no bbox
do eixo Manso–Cuiabá.

Saídas:
  dados/tratados/malha_dnit_osm_eixo.csv
  dados/tratados/malha_dnit_osm_eixo.geojson
  relatorios/malha_dnit_osm_eixo.md

Uso:
  python scripts/42_malha_dnit_osm_eixo.py
  python executar.py 42
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.DADOS_TRATADOS / "malha_dnit_osm_eixo.csv"
SAIDA_GEO = comum.DADOS_TRATADOS / "malha_dnit_osm_eixo.geojson"
REL = comum.RELATORIOS / "malha_dnit_osm_eixo.md"
EIXO_GEO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)
UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; malha DNIT/OSM eixo)"

CAMPOS = [
    "ref",
    "nome",
    "highway",
    "bridge",
    "jurisdicao",
    "km_aprox",
    "latitude",
    "longitude",
    "osm_id",
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
                pad = 0.12
                return (
                    min(lats) - pad,
                    min(lons) - pad,
                    max(lats) + pad,
                    max(lons) + pad,
                )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return (-16.15, -56.55, -15.20, -55.55)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


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


def _jurisdicao(ref: str) -> str:
    refs = [p.strip().upper() for p in ref.replace(",", ";").split(";") if p.strip()]
    tem_br = any(r.startswith("BR-") or r.startswith("BR ") for r in refs)
    tem_mt = any(r.startswith("MT-") or r.startswith("MT ") for r in refs)
    if tem_br and tem_mt:
        return "federal_estadual"
    if tem_br:
        return "federal"
    if tem_mt:
        return "estadual"
    return "outra"


def coletar() -> list[dict[str, Any]]:
    south, west, north, east = bbox_eixo()
    q = f"""
[out:json][timeout:70];
(
  way["highway"~"^(motorway|trunk|primary|secondary)$"]["ref"~"^(BR|MT)-"]({south},{west},{north},{east});
  way["bridge"~"yes|viaduct"]["ref"~"^(BR|MT)-"]({south},{west},{north},{east});
);
out geom tags;
""".strip()
    print(f"  Overpass bbox {south:.3f},{west:.3f},{north:.3f},{east:.3f}", flush=True)
    raw = _post_overpass(q)
    if not raw:
        return []

    # Agrega por ref principal (primeiro código)
    por_ref: dict[str, dict[str, Any]] = {}
    for el in raw.get("elements") or []:
        tags = el.get("tags") or {}
        ref = (tags.get("ref") or "").strip()
        if not ref:
            continue
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        coords = [(float(p["lat"]), float(p["lon"])) for p in geom]
        km = 0.0
        for i in range(1, len(coords)):
            km += _haversine_km(
                coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1]
            )
        mid = coords[len(coords) // 2]
        chave = ref
        slot = por_ref.get(chave)
        if slot is None:
            por_ref[chave] = {
                "ref": ref,
                "nome": (tags.get("name") or ref).strip(),
                "highway": tags.get("highway") or "",
                "bridge": "sim"
                if str(tags.get("bridge") or "").lower()
                in {"yes", "viaduct", "aqueduct"}
                else "nao",
                "jurisdicao": _jurisdicao(ref),
                "km_aprox": round(km, 2),
                "latitude": f"{mid[0]:.6f}",
                "longitude": f"{mid[1]:.6f}",
                "osm_id": str(el.get("id") or ""),
                "fonte": "OSM",
                "observacao": "Proxy DNIT/Sinfra — refs BR/MT no OSM; substituir por SNV oficial quando o portal responder",
                "_coords": [[lo, la] for la, lo in coords],
            }
        else:
            slot["km_aprox"] = round(float(slot["km_aprox"]) + km, 2)
            if slot["bridge"] != "sim" and str(tags.get("bridge") or "").lower() in {
                "yes",
                "viaduct",
            }:
                slot["bridge"] = "sim"

    return sorted(por_ref.values(), key=lambda r: (-float(r["km_aprox"]), r["ref"]))


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando malha BR/MT (proxy DNIT via OSM)…", flush=True)
    regs = coletar()
    if not regs:
        raise SystemExit("nenhum trecho BR/MT retornado pelo Overpass")

    rows = [{k: r.get(k, "") for k in CAMPOS} for r in regs]
    comum.salvar_csv(SAIDA, rows, CAMPOS)

    feats = []
    for r in regs:
        coords = r.get("_coords") or []
        if len(coords) < 2:
            continue
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {k: r.get(k, "") for k in CAMPOS},
            }
        )
    comum.salvar_json(SAIDA_GEO, {"type": "FeatureCollection", "features": feats})

    n_br = sum(1 for r in regs if "federal" in r["jurisdicao"])
    n_mt = sum(1 for r in regs if "estadual" in r["jurisdicao"])
    km = sum(float(r["km_aprox"]) for r in regs)
    n_ponte = sum(1 for r in regs if r["bridge"] == "sim")
    REL.write_text(
        "\n".join(
            [
                "# Malha rodoviária BR/MT no eixo (proxy DNIT)",
                "",
                f"- Trechos (por `ref`): **{len(regs)}**",
                f"- Com componente federal (BR-): **{n_br}**",
                f"- Com componente estadual (MT-): **{n_mt}**",
                f"- Extensão aproximada: **{km:.0f} km**",
                f"- Refs com ponte: **{n_ponte}**",
                f"- Arquivos: `{SAIDA.relative_to(comum.RAIZ)}`, `{SAIDA_GEO.relative_to(comum.RAIZ)}`",
                "",
                "Fonte espacial: OpenStreetMap (`ref` BR-/MT-). O SNV/DNIT oficial",
                "permanece a fonte preferida quando o download institucional estiver disponível.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")
    print(f"  {len(regs)} refs · {km:.0f} km · pontes={n_ponte}")


if __name__ == "__main__":
    main()
