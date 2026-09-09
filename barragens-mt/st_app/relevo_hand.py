"""Proxy HAND (Height Above Nearest Drainage) no eixo Manso–Cuiabá.

Lê a grade gerada por `scripts/35_mde_hand_piloto.py` e expõe predicado
espacial + geometria Leaflet para a Simulação de cenário.

Não é mancha PAE nem dam break.
"""

from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

RAIZ = Path(__file__).resolve().parents[1]
TRATADOS = RAIZ / "dados" / "tratados"
GRADE = TRATADOS / "hand_piloto_manso_cuiaba_grade.csv"
GEOJSON = TRATADOS / "hand_piloto_manso_cuiaba.geojson"
META = TRATADOS / "hand_piloto_manso_cuiaba_meta.json"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

# Distância máxima da barragem à grade para oferecer o modo Relevo.
DIST_MAX_EIXO_KM = 25.0
# Raio da célula proxy (~passo lateral 0,5 km).
RAIO_CELULA_KM = 0.55


def hand_arquivos_ok() -> bool:
    return GRADE.exists() and META.exists()


@lru_cache(maxsize=1)
def carregar_meta() -> dict[str, Any]:
    if not META.exists():
        return {}
    try:
        return json.loads(META.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@lru_cache(maxsize=1)
def carregar_grade() -> tuple[dict[str, Any], ...]:
    if not GRADE.exists():
        return ()
    rows: list[dict[str, Any]] = []
    with GRADE.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            try:
                la = float(r["latitude"])
                lo = float(r["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            hm = r.get("hand_m")
            try:
                hand = float(hm) if hm not in (None, "") else None
            except (TypeError, ValueError):
                hand = None
            rows.append({"la": la, "lo": lo, "hand_m": hand})
    return tuple(rows)


@lru_cache(maxsize=1)
def carregar_geojson() -> dict[str, Any]:
    if not GEOJSON.exists():
        return {"type": "FeatureCollection", "features": []}
    try:
        return json.loads(GEOJSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"type": "FeatureCollection", "features": []}


def limiares_disponiveis() -> list[float]:
    meta = carregar_meta()
    lims = meta.get("limiares_m") or []
    out = [float(x) for x in lims]
    return out or [2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0]


def limiar_para_lamina(profundidade_m: float) -> float:
    """Escolhe o limiar HAND mais próximo da lâmina proxy (m)."""
    lims = limiares_disponiveis()
    p = max(0.5, float(profundidade_m))
    return min(lims, key=lambda x: abs(x - p))


def hand_disponivel_para(lat: float, lon: float) -> bool:
    if not hand_arquivos_ok():
        return False
    grade = carregar_grade()
    if not grade:
        return False
    # Amostra a cada ~20 células para custo baixo
    passo = max(1, len(grade) // 40)
    dmin = min(
        haversine_km(lat, lon, g["la"], g["lo"]) for g in grade[::passo]
    )
    return dmin <= DIST_MAX_EIXO_KM


def celulas_alagadas(limiar_m: float) -> list[dict[str, float]]:
    lim = float(limiar_m)
    out: list[dict[str, float]] = []
    for g in carregar_grade():
        h = g.get("hand_m")
        if h is None or h > lim:
            continue
        out.append({"la": g["la"], "lo": g["lo"], "hand_m": float(h)})
    return out


def bbox_hand(limiar_m: float, pad_deg: float = 0.02) -> tuple[float, float, float, float] | None:
    cells = celulas_alagadas(limiar_m)
    if not cells:
        return None
    lats = [c["la"] for c in cells]
    lons = [c["lo"] for c in cells]
    return (
        min(lats) - pad_deg,
        min(lons) - pad_deg,
        max(lats) + pad_deg,
        max(lons) + pad_deg,
    )


def ponto_na_mancha_hand(lat: float, lon: float, limiar_m: float) -> bool:
    """True se o ponto cai perto de uma célula com HAND ≤ limiar."""
    lim = float(limiar_m)
    for g in carregar_grade():
        h = g.get("hand_m")
        if h is None or h > lim:
            continue
        if haversine_km(lat, lon, g["la"], g["lo"]) <= RAIO_CELULA_KM:
            return True
    return False


def predicate_hand(limiar_m: float) -> Callable[[float, float], bool]:
    cells = celulas_alagadas(limiar_m)
    if not cells:
        return lambda _la, _lo: False

    # Grade espacial grosseira para acelerar
    buckets: dict[tuple[int, int], list[dict[str, float]]] = {}
    for c in cells:
        key = (int(c["la"] * 50), int(c["lo"] * 50))
        buckets.setdefault(key, []).append(c)

    r = RAIO_CELULA_KM

    def _pred(la: float, lo: float, _b=buckets, _r=r) -> bool:
        i0, j0 = int(la * 50), int(lo * 50)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for c in _b.get((i0 + di, j0 + dj), ()):
                    if haversine_km(la, lo, c["la"], c["lo"]) <= _r:
                        return True
        return False

    return _pred


def geojson_limiar(limiar_m: float) -> dict[str, Any] | None:
    """Feature MultiPolygon do limiar (ou o mais próximo disponível)."""
    alvo = float(limiar_m)
    feats = (carregar_geojson().get("features") or [])
    if not feats:
        return None
    melhor = None
    dist = math.inf
    for f in feats:
        props = f.get("properties") or {}
        try:
            hm = float(props.get("hand_max_m"))
        except (TypeError, ValueError):
            continue
        d = abs(hm - alvo)
        if d < dist:
            dist = d
            melhor = f
    return melhor


def poligonos_leaflet(limiar_m: float) -> list[list[list[float]]]:
    """Lista de anéis [lat, lon] para desenhar no Leaflet."""
    feat = geojson_limiar(limiar_m)
    if not feat:
        return []
    geom = feat.get("geometry") or {}
    if geom.get("type") != "MultiPolygon":
        return []
    aneis: list[list[list[float]]] = []
    for poly in geom.get("coordinates") or []:
        if not poly:
            continue
        exterior = poly[0]
        # GeoJSON lon,lat → Leaflet lat,lon
        aneis.append([[float(p[1]), float(p[0])] for p in exterior if len(p) >= 2])
    return aneis


def resumo_hand(limiar_m: float) -> dict[str, Any]:
    cells = celulas_alagadas(limiar_m)
    meta = carregar_meta()
    # área proxy: cada célula ~ (2*RAIO)^2
    lado = 2 * RAIO_CELULA_KM
    area_proxy = round(len(cells) * lado * lado, 1)
    return {
        "ok": bool(cells),
        "limiar_m": float(limiar_m),
        "n_celulas": len(cells),
        "area_proxy_km2": area_proxy,
        "fonte": meta.get("dataset") or "srtm30m",
        "aviso": meta.get("aviso")
        or "Proxy SRTM/HAND — não é mancha PAE nem dam break.",
        "poligonos": poligonos_leaflet(limiar_m),
    }
