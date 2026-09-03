"""MDE/HAND proxy no eixo Manso–Cuiabá (piloto).

Amostra elevações SRTM 30 m via OpenTopoData (gratuito), calcula HAND
(Height Above Nearest Drainage) em relação ao eixo hidrográfico, e grava
grade + polígonos por limiar para a simulação com relevo.

NÃO é mancha PAE nem dam break. Rótulo obrigatório de proxy geomorfológico.

Uso:
  python scripts/35_mde_hand_piloto.py
  python executar.py 35
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import comum

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

EIXO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"
SAIDA_GRADE = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba_grade.csv"
SAIDA_GEO = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba.geojson"
SAIDA_META = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba_meta.json"

# Primeiros km do eixo a partir de Manso (manso_capital) — piloto operacional.
MAX_S_KM = 80.0
PASSO_EIXO_KM = 2.0
OFFSETS_KM = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
LIMIARES_M = (2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0)
DATASET = "srtm30m"
OPENTOPO = f"https://api.opentopodata.org/v1/{DATASET}"
LOTE = 90  # < 100 (limite da API)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def destino_offset(
    lat: float, lon: float, bearing_rad: float, dist_km: float
) -> tuple[float, float]:
    """Destino a `dist_km` no azimute `bearing_rad` (radianos)."""
    r = 6371.0
    ang = dist_km / r
    la1 = math.radians(lat)
    lo1 = math.radians(lon)
    la2 = math.asin(
        math.sin(la1) * math.cos(ang)
        + math.cos(la1) * math.sin(ang) * math.cos(bearing_rad)
    )
    lo2 = lo1 + math.atan2(
        math.sin(bearing_rad) * math.sin(ang) * math.cos(la1),
        math.cos(ang) - math.sin(la1) * math.sin(la2),
    )
    return math.degrees(la2), math.degrees(lo2)


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.atan2(y, x)


def eixo_polyline() -> list[tuple[float, float]]:
    if not EIXO.exists():
        raise SystemExit(f"ausente: {EIXO.name} — rode a etapa 12 antes.")
    geo = json.loads(EIXO.read_text(encoding="utf-8"))
    feats = [
        f
        for f in geo.get("features") or []
        if (f.get("properties") or {}).get("segmento") == "manso_capital"
    ]
    feats.sort(key=lambda f: int((f.get("properties") or {}).get("ordem") or 0))
    poly: list[tuple[float, float]] = []
    for f in feats:
        for c in (f.get("geometry") or {}).get("coordinates") or []:
            if len(c) < 2:
                continue
            la, lo = float(c[1]), float(c[0])
            if poly and abs(poly[-1][0] - la) < 1e-9 and abs(poly[-1][1] - lo) < 1e-9:
                continue
            poly.append((la, lo))
    if len(poly) < 2:
        raise SystemExit("eixo manso_capital sem geometria suficiente")
    return poly


def amostrar_eixo(
    poly: list[tuple[float, float]], passo_km: float, max_s: float
) -> list[dict[str, float]]:
    """Pontos ao longo do eixo com s_km e azimute local."""
    pts: list[dict[str, float]] = []
    acum = 0.0
    az0 = bearing(poly[0][0], poly[0][1], poly[1][0], poly[1][1])
    pts.append({"la": poly[0][0], "lo": poly[0][1], "s_km": 0.0, "az": az0})

    for i in range(1, len(poly)):
        a_la, a_lo = poly[i - 1]
        b_la, b_lo = poly[i]
        seg = haversine_km(a_la, a_lo, b_la, b_lo)
        if seg <= 1e-6:
            continue
        az = bearing(a_la, a_lo, b_la, b_lo)
        s0 = acum
        alvo = (math.floor(s0 / passo_km) + 1) * passo_km
        while alvo <= s0 + seg + 1e-9 and alvo <= max_s + 1e-9:
            t = (alvo - s0) / seg
            la = a_la + t * (b_la - a_la)
            lo = a_lo + t * (b_lo - a_lo)
            pts.append({"la": la, "lo": lo, "s_km": alvo, "az": az})
            alvo += passo_km
        acum += seg
        if acum > max_s:
            break
    return pts


def grade_lateral(eixo_pts: list[dict[str, float]]) -> list[dict[str, Any]]:
    grade: list[dict[str, Any]] = []
    for p in eixo_pts:
        az = float(p["az"])
        for off in OFFSETS_KM:
            sinais = (0.0,) if off == 0 else (-1.0, 1.0)
            for sinal in sinais:
                if off == 0:
                    la, lo = p["la"], p["lo"]
                    offset_assinado = 0.0
                else:
                    az_perp = az + (math.pi / 2 if sinal >= 0 else -math.pi / 2)
                    la, lo = destino_offset(p["la"], p["lo"], az_perp, off)
                    offset_assinado = off * sinal
                grade.append(
                    {
                        "latitude": round(la, 5),
                        "longitude": round(lo, 5),
                        "s_km": round(p["s_km"], 2),
                        "offset_km": round(offset_assinado, 2),
                        "elev_talvegue_ref": None,
                        "elevacao_m": None,
                        "hand_m": None,
                    }
                )
    vistos: set[tuple[float, float]] = set()
    limpo: list[dict[str, Any]] = []
    for g in grade:
        chave = (g["latitude"], g["longitude"])
        if chave in vistos:
            continue
        vistos.add(chave)
        limpo.append(g)
    return limpo


def buscar_elevacoes(pontos: list[tuple[float, float]]) -> list[float | None]:
    """Consulta OpenTopoData em lotes."""
    out: list[float | None] = [None] * len(pontos)
    headers = {
        "User-Agent": "VIGIBARRAGENS-MT/1.0 (hand-piloto; SES-MT)",
        "Accept": "application/json",
    }
    for i in range(0, len(pontos), LOTE):
        lote = pontos[i : i + LOTE]
        locs = "|".join(f"{la},{lo}" for la, lo in lote)
        url = f"{OPENTOPO}?{urllib.parse.urlencode({'locations': locs})}"
        tentativas = 0
        while tentativas < 4:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                results = payload.get("results") or []
                for j, r in enumerate(results):
                    elev = r.get("elevation")
                    out[i + j] = float(elev) if elev is not None else None
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                tentativas += 1
                time.sleep(1.5 * tentativas)
                if tentativas >= 4:
                    print(f"aviso: falha no lote {i}: {exc}", flush=True)
        time.sleep(1.05)
        print(f"  elevações {min(i + LOTE, len(pontos))}/{len(pontos)}", flush=True)
    return out


def celula_quad(lat: float, lon: float, meio_km: float = 0.55) -> list[list[float]]:
    """Anel exterior lon/lat de um quadrado ~meio_km (GeoJSON)."""
    n = destino_offset(lat, lon, 0.0, meio_km)
    s = destino_offset(lat, lon, math.pi, meio_km)
    e = destino_offset(lat, lon, math.pi / 2, meio_km)
    w = destino_offset(lat, lon, -math.pi / 2, meio_km)
    ne = (n[0], e[1])
    nw = (n[0], w[1])
    se = (s[0], e[1])
    sw = (s[0], w[1])
    return [
        [nw[1], nw[0]],
        [ne[1], ne[0]],
        [se[1], se[0]],
        [sw[1], sw[0]],
        [nw[1], nw[0]],
    ]


def main() -> None:
    comum.preparar_diretorios()
    print("Lendo eixo Manso–Cuiabá…", flush=True)
    poly = eixo_polyline()
    eixo_pts = amostrar_eixo(poly, PASSO_EIXO_KM, MAX_S_KM)
    print(f"  {len(eixo_pts)} estações no eixo (≤ {MAX_S_KM} km)", flush=True)

    coords_eixo = [(p["la"], p["lo"]) for p in eixo_pts]
    print("Consultando SRTM (OpenTopoData) no talvegue…", flush=True)
    elev_eixo = buscar_elevacoes(coords_eixo)
    for p, e in zip(eixo_pts, elev_eixo):
        p["elev"] = e

    grade = grade_lateral(eixo_pts)
    elev_por_s = {round(p["s_km"], 2): p.get("elev") for p in eixo_pts}
    for g in grade:
        g["elev_talvegue_ref"] = elev_por_s.get(g["s_km"])

    print(f"Consultando SRTM na grade ({len(grade)} pontos)…", flush=True)
    coords_g = [(g["latitude"], g["longitude"]) for g in grade]
    elev_g = buscar_elevacoes(coords_g)
    n_ok = 0
    for g, e in zip(grade, elev_g):
        g["elevacao_m"] = e
        et = g["elev_talvegue_ref"]
        if e is not None and et is not None:
            g["hand_m"] = round(max(0.0, float(e) - float(et)), 1)
            n_ok += 1
        else:
            g["hand_m"] = None

    print(f"  HAND válido em {n_ok}/{len(grade)} células", flush=True)

    campos = [
        "latitude",
        "longitude",
        "s_km",
        "offset_km",
        "elevacao_m",
        "elev_talvegue_ref",
        "hand_m",
    ]
    with SAIDA_GRADE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for g in grade:
            w.writerow({k: g.get(k) if g.get(k) is not None else "" for k in campos})

    features: list[dict[str, Any]] = []
    for lim in LIMIARES_M:
        rings = []
        for g in grade:
            h = g.get("hand_m")
            if h is None or h > lim:
                continue
            rings.append([celula_quad(g["latitude"], g["longitude"])])
        if not rings:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "hand_max_m": lim,
                    "n_celulas": len(rings),
                    "rotulo": f"HAND ≤ {lim:.0f} m (proxy SRTM)",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": rings},
            }
        )

    SAIDA_GEO.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )

    meta = {
        "dataset": DATASET,
        "fonte_api": OPENTOPO,
        "eixo": "manso_capital",
        "max_s_km": MAX_S_KM,
        "passo_eixo_km": PASSO_EIXO_KM,
        "offsets_km": list(OFFSETS_KM),
        "limiares_m": list(LIMIARES_M),
        "n_celulas": len(grade),
        "n_hand_valido": n_ok,
        "arquivo_grade": SAIDA_GRADE.name,
        "arquivo_geojson": SAIDA_GEO.name,
        "aviso": (
            "Proxy geomorfológico SRTM/HAND — não é mancha PAE nem dam break. "
            "Não estima tempo de chegada da onda."
        ),
    }
    SAIDA_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    rel = comum.RELATORIOS / "hand_piloto_manso_cuiaba.md"
    por_limiar = []
    for lim in LIMIARES_M:
        n = sum(1 for g in grade if g.get("hand_m") is not None and g["hand_m"] <= lim)
        por_limiar.append(f"| ≤ {lim:.0f} m | {n} |")
    rel.write_text(
        "\n".join(
            [
                "# HAND piloto — eixo Manso–Cuiabá",
                "",
                f"- Dataset: **{DATASET}** (`{OPENTOPO}`)",
                f"- Células na grade: **{len(grade)}** (HAND válido: **{n_ok}**)",
                f"- Eixo amostrado: até **{MAX_S_KM:.0f} km** a jusante (passo {PASSO_EIXO_KM} km)",
                f"- Arquivos: `{SAIDA_GRADE.name}`, `{SAIDA_GEO.name}`, `{SAIDA_META.name}`",
                "",
                "| Limiar HAND | Células |",
                "| --- | ---: |",
                *por_limiar,
                "",
                f"> {meta['aviso']}",
                "",
                "UI: Simulação → geometria **Relevo (HAND)** (`st_app/relevo_hand.py`).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Gravado: {SAIDA_GRADE.name}, {SAIDA_GEO.name}, {SAIDA_META.name}, {rel.name}", flush=True)


if __name__ == "__main__":
    main()
