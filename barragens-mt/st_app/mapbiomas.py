"""Pressão de ocupação MapBiomas (módulo urbano) no eixo Manso–Cuiabá."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
ARQUIVO = TRATADOS / "mapbiomas_pressao_eixo_cuiaba.csv"


def _norm(s: str) -> str:
    return (
        str(s or "")
        .strip()
        .casefold()
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


@lru_cache(maxsize=1)
def carregar_mapbiomas() -> pd.DataFrame:
    if not ARQUIVO.is_file():
        return pd.DataFrame()
    df = pd.read_csv(ARQUIVO, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    for c in (
        "area_urbana_2024_ha",
        "area_urbana_2014_ha",
        "delta_urbana_10a_ha",
        "area_urbana_drenagem_ate_3m_2024_ha",
        "pct_urbana_em_drenagem_baixa",
    ):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def pressao_municipio(municipio: str) -> dict[str, Any]:
    """KPI municipal de pressão urbana (contexto — não é mancha PAE)."""
    df = carregar_mapbiomas()
    vazio: dict[str, Any] = {
        "disponivel": False,
        "municipio": municipio or "",
        "ha_urbana": None,
        "ha_urbana_drenagem_baixa": None,
        "pct_urbana_drenagem_baixa": None,
        "delta_10a_ha": None,
        "fonte": "",
    }
    if df.empty or not municipio or "municipio" not in df.columns:
        return vazio
    alvo = _norm(municipio)
    hit = df[df["municipio"].map(_norm) == alvo]
    if hit.empty:
        hit = df[df["municipio"].map(_norm).str.contains(alvo, na=False)]
    if hit.empty:
        return {**vazio, "fonte": ARQUIVO.name}
    r = hit.iloc[0]

    def _f(col: str) -> float | None:
        v = r.get(col)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "disponivel": True,
        "municipio": str(r.get("municipio") or municipio),
        "ha_urbana": _f("area_urbana_2024_ha"),
        "ha_urbana_drenagem_baixa": _f("area_urbana_drenagem_ate_3m_2024_ha"),
        "pct_urbana_drenagem_baixa": _f("pct_urbana_em_drenagem_baixa"),
        "delta_10a_ha": _f("delta_urbana_10a_ha"),
        "fonte": "MapBiomas Col.10 módulo urbano (eixo)",
    }


def resumo_eixo() -> dict[str, Any]:
    df = carregar_mapbiomas()
    if df.empty:
        return {"disponivel": False, "n_municipios": 0}
    return {
        "disponivel": True,
        "n_municipios": int(len(df)),
        "ha_urbana_total": float(
            pd.to_numeric(df.get("area_urbana_2024_ha"), errors="coerce").fillna(0).sum()
        ),
        "ha_drenagem_baixa_total": float(
            pd.to_numeric(
                df.get("area_urbana_drenagem_ate_3m_2024_ha"), errors="coerce"
            )
            .fillna(0)
            .sum()
        ),
        "fonte": "MapBiomas Col.10 módulo urbano (eixo)",
    }
