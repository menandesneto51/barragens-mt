"""Malha BR/MT (proxy DNIT via OSM) — cruzamento com a mancha de simulação."""

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
def carregar_malha_dnit() -> pd.DataFrame:
    path = TRATADOS / "malha_dnit_osm_eixo.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df["km_aprox"] = pd.to_numeric(df.get("km_aprox"), errors="coerce").fillna(0)
    return df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def cruzar_malha_mancha(
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
    df = carregar_malha_dnit()
    vazio = {
        "disponivel": False,
        "n_total": 0,
        "n_na_mancha": 0,
        "n_federais_mancha": 0,
        "n_pontes_mancha": 0,
        "km_na_mancha": 0.0,
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
        itens.append(
            {
                "ref": str(r.get("ref") or ""),
                "nome": str(r.get("nome") or ""),
                "jurisdicao": str(r.get("jurisdicao") or ""),
                "bridge": str(r.get("bridge") or ""),
                "km_aprox": float(r.get("km_aprox") or 0),
                "highway": str(r.get("highway") or ""),
            }
        )

    return {
        "disponivel": True,
        "n_total": int(len(df)),
        "n_na_mancha": len(itens),
        "n_federais_mancha": sum(1 for x in itens if "federal" in x["jurisdicao"]),
        "n_pontes_mancha": sum(1 for x in itens if x["bridge"] == "sim"),
        "km_na_mancha": round(sum(x["km_aprox"] for x in itens), 1),
        "itens": sorted(itens, key=lambda x: -x["km_aprox"])[:40],
        "fonte": "OSM ref BR-/MT- (proxy DNIT/Sinfra)",
    }
