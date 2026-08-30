"""Manchas PAE oficiais (GeoJSON) — gancho pós-etapa 58.

Sem arquivos em `dados/brutos/pae_manchas/`, retorna vazio.
Não inventa geometria; proxies Circular/Trajeto/HAND permanecem rotulados.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TRATADOS = RAIZ / "dados" / "tratados"
INDEX = TRATADOS / "pae_manchas_index.csv"
COBERTURA = TRATADOS / "pae_manchas_cobertura.csv"


def carregar_indice() -> pd.DataFrame:
    if not INDEX.is_file():
        return pd.DataFrame()
    return pd.read_csv(INDEX, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def tem_mancha_pae(id_snisb: str) -> bool:
    bid = str(id_snisb or "").strip()
    if not bid:
        return False
    idx = carregar_indice()
    if idx.empty or "id_snisb" not in idx.columns:
        return False
    return bool((idx["id_snisb"].astype(str) == bid).any())


def _ring_lonlat(coords: list) -> list[list[float]]:
    """GeoJSON [lon,lat] → Leaflet [lat,lon]."""
    out: list[list[float]] = []
    for c in coords:
        if not isinstance(c, (list, tuple)) or len(c) < 2:
            continue
        try:
            lon, lat = float(c[0]), float(c[1])
        except (TypeError, ValueError):
            continue
        out.append([lat, lon])
    return out


def _poligonos_de_geom(geom: dict[str, Any]) -> list[list[list[float]]]:
    if not geom:
        return []
    t = str(geom.get("type") or "")
    coords = geom.get("coordinates")
    polys: list[list[list[float]]] = []
    if t == "Polygon" and coords:
        ring = _ring_lonlat(coords[0])
        if len(ring) >= 3:
            polys.append(ring)
    elif t == "MultiPolygon" and coords:
        for poly in coords:
            if not poly:
                continue
            ring = _ring_lonlat(poly[0])
            if len(ring) >= 3:
                polys.append(ring)
    elif t == "GeometryCollection":
        for g in geom.get("geometries") or []:
            polys.extend(_poligonos_de_geom(g))
    return polys


def _area_km2_ring(ring_latlon: list[list[float]]) -> float:
    """Shoelace em graus com correção cos(lat) aproximada (EPSG:4326)."""
    if len(ring_latlon) < 3:
        return 0.0
    lat0 = sum(p[0] for p in ring_latlon) / len(ring_latlon)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * max(0.2, math.cos(math.radians(lat0)))
    pts = [(p[1] * m_per_deg_lon, p[0] * m_per_deg_lat) for p in ring_latlon]
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    area = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5 / 1_000_000.0


def ponto_em_poligono(lat: float, lon: float, ring_latlon: list[list[float]]) -> bool:
    """Ray casting; ring em [lat, lon]."""
    n = len(ring_latlon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = ring_latlon[i][0], ring_latlon[i][1]
        yj, xj = ring_latlon[j][0], ring_latlon[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def ponto_em_manchas(lat: float, lon: float, poligonos: list[list[list[float]]]) -> bool:
    return any(ponto_em_poligono(lat, lon, ring) for ring in poligonos)


def carregar_mancha(id_snisb: str) -> dict[str, Any]:
    """Carrega polígonos oficiais para a barragem, se indexados."""
    bid = str(id_snisb or "").strip()
    vazio: dict[str, Any] = {
        "ok": False,
        "id_snisb": bid,
        "poligonos": [],
        "area_km2": 0.0,
        "fonte": "",
        "caminho": "",
        "aviso": "sem mancha PAE indexada",
    }
    if not bid:
        return vazio
    idx = carregar_indice()
    if idx.empty:
        return vazio
    hit = idx[idx["id_snisb"].astype(str) == bid]
    if hit.empty:
        return vazio
    row = hit.iloc[0]
    caminho = Path(str(row.get("caminho_geojson") or ""))
    if not caminho.is_file():
        # relativo à raiz
        alt = RAIZ / str(row.get("caminho_geojson") or "")
        caminho = alt if alt.is_file() else caminho
    if not caminho.is_file():
        vazio["aviso"] = f"arquivo ausente: {row.get('caminho_geojson')}"
        return vazio
    try:
        gj = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        vazio["aviso"] = f"falha ao ler GeoJSON: {exc}"
        return vazio

    polys: list[list[list[float]]] = []
    if gj.get("type") == "FeatureCollection":
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            fid = str(
                props.get("id_snisb")
                or props.get("codigo_snisb")
                or props.get("COD_SNISB")
                or ""
            ).strip()
            if fid and fid != bid:
                continue
            polys.extend(_poligonos_de_geom(feat.get("geometry") or {}))
    elif gj.get("type") == "Feature":
        polys.extend(_poligonos_de_geom(gj.get("geometry") or {}))
    else:
        polys.extend(_poligonos_de_geom(gj))

    if not polys:
        vazio["aviso"] = "GeoJSON sem polígono associável ao id_snisb"
        return vazio
    area = sum(_area_km2_ring(p) for p in polys)
    return {
        "ok": True,
        "id_snisb": bid,
        "poligonos": polys,
        "area_km2": round(area, 3),
        "fonte": str(row.get("fonte") or "PAE oficial"),
        "caminho": str(row.get("caminho_geojson") or ""),
        "crs": str(row.get("crs") or "EPSG:4326"),
        "aviso": "",
    }
