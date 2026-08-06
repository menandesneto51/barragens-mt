"""Captações de água (Sisagua / OSM) no eixo — KPI na mancha de simulação."""

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
def carregar_captacoes() -> pd.DataFrame:
    """Prefere captações reais; cai no esqueleto se ainda não houver ETL."""
    for nome in (
        "sisagua_captacoes_eixo.csv",
        "sisagua_captacoes_eixo_esqueleto.csv",
    ):
        path = TRATADOS / nome
        if not path.is_file():
            continue
        df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
        if df.empty:
            continue
        if "latitude" not in df.columns or "longitude" not in df.columns:
            continue
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["latitude", "longitude"])
        if df.empty:
            continue
        df["_arquivo"] = nome
        return df.reset_index(drop=True)
    return pd.DataFrame()


def cruzar_captacoes_mancha(
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
    df = carregar_captacoes()
    vazio = {
        "disponivel": False,
        "n_total": 0,
        "n_na_mancha": 0,
        "itens": [],
        "fonte": "",
        "esqueleto": True,
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
                "nome": str(r.get("nome_sistema") or r.get("nome") or "Captação"),
                "municipio": str(r.get("municipio") or ""),
                "tipo": str(r.get("tipo_captacao") or r.get("tipo") or ""),
                "fonte": str(r.get("fonte") or ""),
                "lat": la,
                "lon": lo,
            }
        )

    arquivo = str(df["_arquivo"].iloc[0]) if "_arquivo" in df.columns else ""
    return {
        "disponivel": True,
        "n_total": int(len(df)),
        "n_na_mancha": len(itens),
        "itens": itens[:40],
        "fonte": f"{arquivo} · {(itens[0]['fonte'] if itens else df.iloc[0].get('fonte') or '')}",
        "esqueleto": "esqueleto" in arquivo,
    }
