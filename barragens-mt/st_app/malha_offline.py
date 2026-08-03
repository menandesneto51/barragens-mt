"""Malha viária offline (GeoJSON tratado) — fallback quando o Overpass falha.

Converte `malha_dnit_osm_eixo.geojson` (e caches OSM locais) no formato
elements (nodes/ways) consumido por `vias_isolamento.analisar_isolamento`.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
MALHA_GEO = TRATADOS / "malha_dnit_osm_eixo.geojson"


def _node_id(lat: float, lon: float) -> int:
    """ID estável por coordenada (~1 m) — negativo para não colidir com OSM."""
    # 1e5 ≈ 1 m em latitude
    return -1 - (int(round(lat * 1e5)) * 2_000_000 + int(round(lon * 1e5)) % 2_000_000)


@lru_cache(maxsize=1)
def _features_malha() -> tuple[dict[str, Any], ...]:
    if not MALHA_GEO.is_file():
        return ()
    try:
        gj = json.loads(MALHA_GEO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    feats = []
    for f in gj.get("features") or []:
        if not isinstance(f, dict):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        feats.append(f)
    return tuple(feats)


def malha_offline_elements(
    *,
    south: float | None = None,
    west: float | None = None,
    north: float | None = None,
    east: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    raio_km: float | None = None,
) -> dict[str, Any]:
    """Monta payload estilo Overpass a partir do GeoJSON local."""
    feats = _features_malha()
    if not feats:
        return {
            "elements": [],
            "erro": "malha offline indisponível (rode scripts/42_malha_dnit_osm_eixo.py)",
            "_meta": {"fonte": "offline", "n_features": 0},
        }

    nodes: dict[int, dict[str, Any]] = {}
    ways: list[dict[str, Any]] = []
    n_keep = 0

    def _aceita(la: float, lo: float) -> bool:
        if south is not None and west is not None and north is not None and east is not None:
            return south <= la <= north and west <= lo <= east
        if lat is not None and lon is not None and raio_km is not None:
            # haversine leve
            r = 6371.0
            p1, p2 = math.radians(lat), math.radians(la)
            dphi = math.radians(la - lat)
            dl = math.radians(lo - lon)
            a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
            return 2 * r * math.asin(math.sqrt(min(1.0, a))) <= float(raio_km)
        return True

    for i, f in enumerate(feats):
        props = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        pts: list[tuple[float, float]] = []
        for c in coords:
            if not isinstance(c, (list, tuple)) or len(c) < 2:
                continue
            lo, la = float(c[0]), float(c[1])
            pts.append((la, lo))
        if len(pts) < 2:
            continue
        if not any(_aceita(la, lo) for la, lo in pts):
            # ainda aceita se o meio do trecho entra no filtro
            mid = pts[len(pts) // 2]
            if not _aceita(mid[0], mid[1]):
                continue

        nds: list[int] = []
        for la, lo in pts:
            nid = _node_id(la, lo)
            nodes[nid] = {"type": "node", "id": nid, "lat": la, "lon": lo}
            nds.append(nid)
        if len(nds) < 2:
            continue
        n_keep += 1
        bridge = str(props.get("bridge") or "").lower()
        tags = {
            "highway": str(props.get("highway") or "primary"),
            "name": str(props.get("nome") or props.get("ref") or ""),
            "ref": str(props.get("ref") or ""),
        }
        if bridge in {"sim", "yes", "1", "true"}:
            tags["bridge"] = "yes"
        ways.append(
            {
                "type": "way",
                "id": int(props.get("osm_id") or -(i + 1)),
                "nodes": nds,
                "tags": tags,
            }
        )

    elements: list[dict[str, Any]] = list(nodes.values()) + ways
    return {
        "elements": elements,
        "erro": None if elements else "nenhum trecho offline na área",
        "_meta": {
            "fonte": "malha_dnit_osm_eixo.geojson (offline)",
            "n_features": n_keep,
            "n_nodes": len(nodes),
            "n_ways": len(ways),
        },
    }
