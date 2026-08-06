"""
Setores censitários IBGE 2022 no eixo Manso–Cuiabá — exposição/isolamento por setor.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from st_app.relevo_hand import ponto_na_mancha_hand
from st_app.trajeto_hidraulico import ponto_no_corredor

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


@lru_cache(maxsize=1)
def carregar_setores_eixo() -> pd.DataFrame:
    path = TRATADOS / "setores_censitarios_eixo_cuiaba.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    # Normaliza nomes (ETL 37)
    ren = {}
    if "codigo_setor" in df.columns and "cd_setor" not in df.columns:
        ren["codigo_setor"] = "cd_setor"
    if "codigo_ibge" in df.columns and "cd_mun" not in df.columns:
        ren["codigo_ibge"] = "cd_mun"
    if "latitude" in df.columns and "lat" not in df.columns:
        ren["latitude"] = "lat"
    if "longitude" in df.columns and "lon" not in df.columns:
        ren["longitude"] = "lon"
    if ren:
        df = df.rename(columns=ren)
    df["lat"] = pd.to_numeric(df.get("lat"), errors="coerce")
    df["lon"] = pd.to_numeric(df.get("lon"), errors="coerce")
    df["populacao"] = pd.to_numeric(df.get("populacao"), errors="coerce").fillna(0).astype(int)
    return df.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def _setor_na_mancha(
    lat: float,
    lon: float,
    *,
    lat0: float,
    lon0: float,
    raio_km: float,
    mostrar_circular: bool,
    trajeto: dict[str, Any] | None,
    mostrar_trajeto: bool,
    hand_limiar: float | None,
    usar_hand: bool,
) -> bool:
    ok = False
    if mostrar_circular and _haversine_km(lat0, lon0, lat, lon) <= raio_km:
        ok = True
    if mostrar_trajeto and trajeto and trajeto.get("ok") and trajeto.get("polyline"):
        ok = ok or ponto_no_corredor(
            lat,
            lon,
            trajeto["polyline"],
            float(trajeto.get("largura_km") or 2.0),
        )
    if usar_hand and hand_limiar is not None:
        ok = ok or ponto_na_mancha_hand(lat, lon, float(hand_limiar))
    return ok


def cruzar_setores_mancha(
    *,
    lat0: float,
    lon0: float,
    raio_km: float,
    mostrar_circular: bool = True,
    trajeto: dict[str, Any] | None = None,
    mostrar_trajeto: bool = False,
    hand_limiar: float | None = None,
    usar_hand: bool = False,
    munis_isolamento: list[str] | None = None,
) -> dict[str, Any]:
    """
    População exposta = setores com centróide na mancha (união das geometrias ativas).
    População isolada (proxy) = setores fora da mancha em municípios com vias cortadas.
    """
    df = carregar_setores_eixo()
    vazio = {
        "n_setores_eixo": 0,
        "n_setores_expostos": 0,
        "pop_exposta_setores": 0,
        "n_setores_isolados_proxy": 0,
        "pop_isolada_setores": 0,
        "por_municipio": [],
        "disponivel": False,
    }
    if df.empty:
        return vazio

    munis_iso = {str(m).strip() for m in (munis_isolamento or []) if str(m).strip()}
    rows_exp: list[dict[str, Any]] = []
    rows_iso: list[dict[str, Any]] = []

    for _, r in df.iterrows():
        lat, lon = float(r["lat"]), float(r["lon"])
        na = _setor_na_mancha(
            lat,
            lon,
            lat0=lat0,
            lon0=lon0,
            raio_km=raio_km,
            mostrar_circular=mostrar_circular,
            trajeto=trajeto,
            mostrar_trajeto=mostrar_trajeto,
            hand_limiar=hand_limiar,
            usar_hand=usar_hand,
        )
        item = {
            "cd_setor": str(r.get("cd_setor") or ""),
            "municipio": str(r.get("municipio") or ""),
            "cd_mun": str(r.get("cd_mun") or ""),
            "populacao": int(r["populacao"]),
            "lat": lat,
            "lon": lon,
        }
        if na:
            rows_exp.append(item)
        elif item["municipio"] in munis_iso:
            rows_iso.append(item)

    por_mun: dict[str, dict[str, int]] = {}
    for item in rows_exp:
        m = item["municipio"] or "?"
        por_mun.setdefault(m, {"exposta": 0, "isolada": 0, "setores_exp": 0, "setores_iso": 0})
        por_mun[m]["exposta"] += item["populacao"]
        por_mun[m]["setores_exp"] += 1
    for item in rows_iso:
        m = item["municipio"] or "?"
        por_mun.setdefault(m, {"exposta": 0, "isolada": 0, "setores_exp": 0, "setores_iso": 0})
        por_mun[m]["isolada"] += item["populacao"]
        por_mun[m]["setores_iso"] += 1

    return {
        "n_setores_eixo": int(len(df)),
        "n_setores_expostos": len(rows_exp),
        "pop_exposta_setores": int(sum(x["populacao"] for x in rows_exp)),
        "n_setores_isolados_proxy": len(rows_iso),
        "pop_isolada_setores": int(sum(x["populacao"] for x in rows_iso)),
        "por_municipio": [
            {"municipio": k, **v}
            for k, v in sorted(
                por_mun.items(), key=lambda kv: -(kv[1]["exposta"] + kv[1]["isolada"])
            )
        ],
        "disponivel": True,
        "fonte": "IBGE Censo 2022 (malha setores + agregados básico V0001) — centróide do setor",
    }
