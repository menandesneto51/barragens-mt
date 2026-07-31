"""Trajeto hidráulico proxy ao longo do eixo Manso–Cuiabá (BHO/Otto).

Não é mancha PAE nem dam break. Usa o eixo hidrografico já tratado no repositório
como calha preferencial jusante e espalha a área equivalente numa faixa (corredor).

Fórmula do comprimento ao longo do rio:
  L_km ≈ área_km² / (2 × semi_largura_km)
porque a área do retângulo aproximado = comprimento × largura total.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

RAIZ = Path(__file__).resolve().parents[1]
EIXO_PATH = RAIZ / "dados" / "tratados" / "eixo_hidrografico_manso_cuiaba.geojson"

# Distância máxima da barragem ao eixo para aceitar o trajeto (km).
MAX_DIST_EIXO_KM = 25.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _plano(lon: float, lat: float, lat_ref: float) -> tuple[float, float]:
    f = math.cos(math.radians(lat_ref))
    return (
        math.radians(lon) * 6371.0 * f,
        math.radians(lat) * 6371.0,
    )


def dist_ponto_segmento_km(
    lat: float,
    lon: float,
    a_lat: float,
    a_lon: float,
    b_lat: float,
    b_lon: float,
) -> float:
    lat_ref = (a_lat + b_lat) / 2.0
    px, py = _plano(lon, lat, lat_ref)
    ax, ay = _plano(a_lon, a_lat, lat_ref)
    bx, by = _plano(b_lon, b_lat, lat_ref)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


@lru_cache(maxsize=1)
def _carregar_eixo_ordenado() -> list[dict[str, Any]]:
    """Features do eixo ordenadas: manso_capital (ordem) depois jusante_capital."""
    if not EIXO_PATH.exists():
        return []
    geo = json.loads(EIXO_PATH.read_text(encoding="utf-8"))
    feats = list(geo.get("features") or [])

    def chave(f: dict[str, Any]) -> tuple[int, int]:
        p = f.get("properties") or {}
        seg = str(p.get("segmento") or "")
        ordem = int(p.get("ordem") or 0)
        # manso_capital primeiro, depois jusante
        pri = 0 if seg == "manso_capital" else (1 if seg == "jusante_capital" else 2)
        return (pri, ordem)

    feats.sort(key=chave)
    return feats


def _coords_latlon(feat: dict[str, Any]) -> list[tuple[float, float]]:
    geom = feat.get("geometry") or {}
    if geom.get("type") != "LineString":
        return []
    out: list[tuple[float, float]] = []
    for c in geom.get("coordinates") or []:
        if len(c) >= 2:
            out.append((float(c[1]), float(c[0])))  # lat, lon
    return out


def _polyline_completa() -> list[tuple[float, float]]:
    """Polyline contínua do eixo (dedup de vértices consecutivos)."""
    poly: list[tuple[float, float]] = []
    for feat in _carregar_eixo_ordenado():
        for la, lo in _coords_latlon(feat):
            if poly and abs(poly[-1][0] - la) < 1e-9 and abs(poly[-1][1] - lo) < 1e-9:
                continue
            poly.append((la, lo))
    return poly


def _projecao_no_eixo(
    lat: float, lon: float, poly: list[tuple[float, float]]
) -> tuple[int, float, float, float]:
    """Retorna (índice do segmento, t∈[0,1], dist_km, comprimento acumulado até o ponto)."""
    melhor = (0, 0.0, float("inf"), 0.0)
    acum = 0.0
    for i in range(1, len(poly)):
        a_la, a_lo = poly[i - 1]
        b_la, b_lo = poly[i]
        seg_len = haversine_km(a_la, a_lo, b_la, b_lo)
        # t pela projeção plana
        lat_ref = (a_la + b_la) / 2.0
        px, py = _plano(lon, lat, lat_ref)
        ax, ay = _plano(a_lo, a_la, lat_ref)
        bx, by = _plano(b_lo, b_la, lat_ref)
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            t = 0.0
            d = math.hypot(px - ax, py - ay)
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if d < melhor[2]:
            melhor = (i - 1, t, d, acum + t * seg_len)
        acum += seg_len
    return melhor


def construir_trajeto(
    *,
    lat: float,
    lon: float,
    area_km2: float,
    semi_largura_km: float = 2.0,
    incluir_jusante_capital: bool = True,
) -> dict[str, Any]:
    """Monta corredor jusante a partir da barragem ao longo do eixo.

    Retorna polyline [[lat,lon],...], comprimento, largura e metadados.
    """
    poly = _polyline_completa()
    if len(poly) < 2:
        return {
            "ok": False,
            "aviso": "Eixo hidrografico ausente — rode a etapa 12 (analise_cuiaba).",
            "polyline": [],
            "largura_km": float(semi_largura_km),
            "comprimento_km": 0.0,
            "dist_eixo_km": None,
            "area_km2": float(area_km2),
            "fonte": "eixo_hidrografico_manso_cuiaba",
        }

    idx, t, dist, s0 = _projecao_no_eixo(lat, lon, poly)
    if dist > MAX_DIST_EIXO_KM:
        return {
            "ok": False,
            "aviso": (
                f"Barragem a {dist:.1f} km do eixo Manso–Cuiabá "
                f"(limite {MAX_DIST_EIXO_KM:.0f} km). Use o modo circular ou carregue "
                "mancha PAE / Otto da bacia local."
            ),
            "polyline": [],
            "largura_km": float(semi_largura_km),
            "comprimento_km": 0.0,
            "dist_eixo_km": round(dist, 2),
            "area_km2": float(area_km2),
            "fonte": "eixo_hidrografico_manso_cuiaba",
        }

    w = max(0.3, float(semi_largura_km))
    area = max(0.1, float(area_km2))
    # Comprimento necessário para cobrir a área equivalente na faixa.
    L_alvo = area / (2.0 * w)
    # Piso operacional: pelo menos alguns km jusante para o corredor ser legível.
    L_alvo = max(5.0, min(L_alvo, 400.0))

    # Ponto de partida = projeção da barragem no eixo.
    a_la, a_lo = poly[idx]
    b_la, b_lo = poly[idx + 1]
    start = (a_la + t * (b_la - a_la), a_lo + t * (b_lo - a_lo))

    # Índice máximo de vértice no eixo (corta em Cuiabá se não incluir jusante).
    fim_vertice = len(poly) - 1
    if not incluir_jusante_capital:
        ultimo_manso: tuple[float, float] | None = None
        for feat in _carregar_eixo_ordenado():
            props = feat.get("properties") or {}
            if props.get("segmento") != "manso_capital":
                break
            coords_f = _coords_latlon(feat)
            if coords_f:
                ultimo_manso = coords_f[-1]
        if ultimo_manso:
            for i, p in enumerate(poly):
                if abs(p[0] - ultimo_manso[0]) < 1e-6 and abs(p[1] - ultimo_manso[1]) < 1e-6:
                    fim_vertice = i
                    break

    def _andar(
        origem: tuple[float, float],
        alvo_km: float,
        sequencia: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """Caminha ao longo de `sequencia` a partir de pontos já alinhados ao eixo."""
        if alvo_km <= 0 or len(sequencia) < 1:
            return [origem]
        out = [origem]
        cur = origem
        restante = alvo_km
        for nxt in sequencia:
            d = haversine_km(cur[0], cur[1], nxt[0], nxt[1])
            if d <= 1e-6:
                continue
            if d <= restante:
                out.append(nxt)
                restante -= d
                cur = nxt
            else:
                frac = restante / d
                out.append(
                    (
                        cur[0] + frac * (nxt[0] - cur[0]),
                        cur[1] + frac * (nxt[1] - cur[1]),
                    )
                )
                break
        return out

    # Jusante: do start até poly[idx+1], poly[idx+2], … fim_vertice
    seq_jusante = [poly[j] for j in range(idx + 1, fim_vertice + 1)]
    ramo_jusante = _andar(start, L_alvo, seq_jusante)

    # Montante curto (espelho / aproximação do reservatório)
    L_montante = min(3.0, L_alvo * 0.05)
    seq_montante = [poly[j] for j in range(idx, -1, -1)]
    ramo_montante = _andar(start, L_montante, seq_montante)
    # ramo_montante[0] == start; inverter sem duplicar start
    montante_rev = list(reversed(ramo_montante[1:]))

    trajeto = montante_rev + ramo_jusante

    # Dedup
    limpo: list[tuple[float, float]] = []
    for p in trajeto:
        if limpo and abs(limpo[-1][0] - p[0]) < 1e-8 and abs(limpo[-1][1] - p[1]) < 1e-8:
            continue
        limpo.append(p)

    comp = 0.0
    for i in range(1, len(limpo)):
        comp += haversine_km(limpo[i - 1][0], limpo[i - 1][1], limpo[i][0], limpo[i][1])

    return {
        "ok": True,
        "aviso": None,
        "polyline": [[la, lo] for la, lo in limpo],
        "largura_km": w,
        "comprimento_km": round(comp, 2),
        "comprimento_alvo_km": round(L_alvo, 2),
        "dist_eixo_km": round(dist, 2),
        "area_km2": round(area, 2),
        "area_corredor_km2": round(comp * 2 * w, 1),
        "fonte": "eixo_hidrografico_manso_cuiaba (BHO/Otto)",
        "rotulo": "Corredor jusante ao longo da calha (proxy — não é mancha PAE)",
    }


def ponto_no_corredor(
    lat: float,
    lon: float,
    polyline: list[list[float]] | list[tuple[float, float]],
    semi_largura_km: float,
) -> bool:
    if not polyline or semi_largura_km <= 0:
        return False
    w = float(semi_largura_km)
    # bbox rápido
    lats = [float(p[0]) for p in polyline]
    lons = [float(p[1]) for p in polyline]
    pad = (w / 111.0) + 0.02
    if lat < min(lats) - pad or lat > max(lats) + pad:
        return False
    if lon < min(lons) - pad or lon > max(lons) + pad:
        return False
    melhor = float("inf")
    for i in range(1, len(polyline)):
        a_la, a_lo = float(polyline[i - 1][0]), float(polyline[i - 1][1])
        b_la, b_lo = float(polyline[i][0]), float(polyline[i][1])
        d = dist_ponto_segmento_km(lat, lon, a_la, a_lo, b_la, b_lo)
        if d < melhor:
            melhor = d
            if melhor <= w:
                return True
    return melhor <= w


def segmento_cruza_corredor(
    coords: list[tuple[float, float]],
    polyline: list[list[float]],
    semi_largura_km: float,
) -> bool:
    """True se algum vértice ou amostra do segmento está no corredor."""
    if not coords or not polyline:
        return False
    for la, lo in coords:
        if ponto_no_corredor(la, lo, polyline, semi_largura_km):
            return True
    # amostra pontos médios
    for i in range(1, len(coords)):
        mla = (coords[i - 1][0] + coords[i][0]) / 2
        mlo = (coords[i - 1][1] + coords[i][1]) / 2
        if ponto_no_corredor(mla, mlo, polyline, semi_largura_km):
            return True
    return False


def filtrar_pontos_corredor(
    pontos: list[dict[str, Any]],
    polyline: list[list[float]],
    semi_largura_km: float,
    *,
    lat_key: str = "la",
    lon_key: str = "lo",
) -> list[dict[str, Any]]:
    out = []
    for p in pontos:
        try:
            la, lo = float(p[lat_key]), float(p[lon_key])
        except (KeyError, TypeError, ValueError):
            continue
        if ponto_no_corredor(la, lo, polyline, semi_largura_km):
            out.append(p)
    return out


def predicate_corredor(
    polyline: list[list[float]], semi_largura_km: float
) -> Callable[[float, float], bool]:
    return lambda la, lo: ponto_no_corredor(la, lo, polyline, semi_largura_km)


def predicate_circular(lat0: float, lon0: float, raio_km: float) -> Callable[[float, float], bool]:
    r = float(raio_km)
    return lambda la, lo: haversine_km(lat0, lon0, la, lo) <= r


def predicate_uniao(*preds: Callable[[float, float], bool]) -> Callable[[float, float], bool]:
    return lambda la, lo: any(p(la, lo) for p in preds)
