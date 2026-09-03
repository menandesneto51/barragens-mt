"""Leitos e ocupação IndicaSUS/DW — join com CNES na mancha (D6)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"


@lru_cache(maxsize=1)
def carregar_leitos_indicasus() -> pd.DataFrame:
    path = TRATADOS / "indicasus_leitos_mt.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    df["codigo_cnes"] = df.get("codigo_cnes", "").astype(str).str.replace(r"\D", "", regex=True)
    for col in (
        "leitos_cadastrados",
        "leitos_operacionais",
        "leitos_ocupados",
        "leitos_disponiveis",
        "taxa_ocupacao",
    ):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@lru_cache(maxsize=1)
def carregar_leitos_municipio() -> pd.DataFrame:
    path = TRATADOS / "indicasus_leitos_municipio.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    df["codigo_municipio_ibge"] = (
        df.get("codigo_municipio_ibge", "").astype(str).str.replace(r"\D", "", regex=True)
    )
    for col in (
        "leitos_operacionais",
        "leitos_ocupados",
        "leitos_disponiveis",
        "taxa_ocupacao",
        "n_estabelecimentos",
    ):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def status_indicasus() -> dict[str, Any]:
    path = TRATADOS / "indicasus_leitos_status.json"
    if not path.is_file():
        return {"ok": False, "motivo": "status ausente — rode python executar.py 43"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "motivo": "status ilegível"}


def agregar_por_cnes(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por CNES (prefere tipo_leito=total; senão soma)."""
    df = carregar_leitos_indicasus() if df is None else df
    if df is None or df.empty:
        return pd.DataFrame()
    prefer = df[df.get("tipo_leito", pd.Series(dtype=str)).astype(str).str.lower() == "total"]
    if not prefer.empty:
        base = prefer
    else:
        base = df
    nums = ["leitos_operacionais", "leitos_ocupados", "leitos_disponiveis", "leitos_cadastrados"]
    ag = (
        base.groupby("codigo_cnes", as_index=False)[nums]
        .sum(min_count=1)
        if all(c in base.columns for c in nums[:3])
        else base.drop_duplicates("codigo_cnes")
    )
    meta = base.drop_duplicates("codigo_cnes")[
        [c for c in ("codigo_cnes", "nome_estabelecimento", "codigo_municipio_ibge", "municipio") if c in base.columns]
    ]
    return meta.merge(ag, on="codigo_cnes", how="left")


def leitos_por_municipio_ibge(ibge7: str) -> dict[str, Any] | None:
    mun = carregar_leitos_municipio()
    if mun.empty:
        return None
    dig = "".join(c for c in str(ibge7 or "") if c.isdigit())[:7]
    if not dig:
        return None
    hit = mun[mun["codigo_municipio_ibge"].astype(str).str.startswith(dig[:6])]
    if hit.empty:
        return None
    row = hit.iloc[0]
    return {
        "codigo_municipio_ibge": str(row.get("codigo_municipio_ibge") or ""),
        "municipio": str(row.get("municipio") or ""),
        "leitos_operacionais": float(row.get("leitos_operacionais") or 0),
        "leitos_ocupados": float(row.get("leitos_ocupados") or 0),
        "leitos_disponiveis": float(row.get("leitos_disponiveis") or 0),
        "taxa_ocupacao": float(row["taxa_ocupacao"]) if pd.notna(row.get("taxa_ocupacao")) else None,
    }
