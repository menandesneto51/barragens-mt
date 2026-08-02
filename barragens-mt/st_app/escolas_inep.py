"""Escolas (INEP / OSM) no eixo — KPI C5 na mancha de simulação."""

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
def carregar_escolas() -> pd.DataFrame:
    path = TRATADOS / "escolas_eixo_cuiaba.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty or "latitude" not in df.columns:
        return pd.DataFrame()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def cruzar_escolas_mancha(
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
    df = carregar_escolas()
    vazio = {
        "disponivel": False,
        "n_total": 0,
        "n_na_mancha": 0,
        "itens": [],
        "fonte": "",
        "por_dependencia": {},
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
                "nome": str(r.get("nome") or "Escola"),
                "municipio": str(r.get("municipio") or ""),
                "dependencia": str(r.get("dependencia") or ""),
                "codigo_inep": str(r.get("codigo_inep") or ""),
                "fonte": str(r.get("fonte") or ""),
                "lat": la,
                "lon": lo,
            }
        )

    por_dep: dict[str, int] = {}
    for it in itens:
        d = it["dependencia"] or "nao_informada"
        por_dep[d] = por_dep.get(d, 0) + 1

    fontes = sorted({str(x) for x in df.get("fonte", pd.Series(dtype=str)).dropna().unique()})
    return {
        "disponivel": True,
        "n_total": int(len(df)),
        "n_na_mancha": len(itens),
        "itens": itens[:60],
        "fonte": " · ".join(fontes) or "escolas_eixo_cuiaba.csv",
        "por_dependencia": por_dep,
    }
