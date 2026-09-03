"""Ativos essenciais OSM (ETA/ETE/energia/abrigos) — KPI C5 na mancha."""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from st_app.relevo_hand import ponto_na_mancha_hand
from st_app.trajeto_hidraulico import ponto_no_corredor

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"

ROTULOS = {
    "eta_agua": "ETA / água",
    "ete_esgoto": "ETE / esgoto",
    "subestacao_energia": "Subestação",
    "abrigo": "Abrigo",
    "base_ambulancia": "Base ambulância",
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


@lru_cache(maxsize=1)
def carregar_ativos() -> pd.DataFrame:
    path = TRATADOS / "ativos_essenciais_osm_eixo.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    return df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def cruzar_ativos_mancha(
    *,
    lat0: float,
    lon0: float,
    raio_km: float,
    mostrar_circular: bool = True,
    trajeto: dict[str, Any] | None = None,
    mostrar_trajeto: bool = False,
    hand_limiar: float | None = None,
    usar_hand: bool = False,
) -> dict[str, Any]:
    df = carregar_ativos()
    vazio = {
        "disponivel": False,
        "n_total": 0,
        "n_na_mancha": 0,
        "por_categoria": {},
        "itens": [],
        "fonte": "",
    }
    if df.empty:
        return vazio

    itens: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        la, lo = float(r["latitude"]), float(r["longitude"])
        ok = False
        if mostrar_circular and _haversine_km(lat0, lon0, la, lo) <= raio_km:
            ok = True
        if mostrar_trajeto and trajeto and trajeto.get("ok") and trajeto.get("polyline"):
            ok = ok or ponto_no_corredor(
                la,
                lo,
                trajeto["polyline"],
                float(trajeto.get("largura_km") or 2.0),
            )
        if usar_hand and hand_limiar is not None:
            ok = ok or ponto_na_mancha_hand(la, lo, float(hand_limiar))
        if not ok:
            continue
        cat = str(r.get("categoria") or "")
        itens.append(
            {
                "categoria": cat,
                "rotulo": ROTULOS.get(cat, cat),
                "nome": str(r.get("nome") or ""),
                "municipio": str(r.get("municipio") or ""),
                "lat": la,
                "lon": lo,
            }
        )

    por: dict[str, int] = {}
    for it in itens:
        por[it["categoria"]] = por.get(it["categoria"], 0) + 1

    return {
        "disponivel": True,
        "n_total": int(len(df)),
        "n_na_mancha": len(itens),
        "por_categoria": por,
        "n_eta": por.get("eta_agua", 0),
        "n_ete": por.get("ete_esgoto", 0),
        "n_energia": por.get("subestacao_energia", 0),
        "n_abrigo": por.get("abrigo", 0),
        "n_ambulancia": por.get("base_ambulancia", 0),
        "itens": itens[:60],
        "fonte": "OSM ativos essenciais (proxy C5)",
    }
