"""Contexto fluvial ANA (estações próximas) — não altera geometria da mancha."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"


def _num_br(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def carregar_estacoes_barragem() -> pd.DataFrame:
    path = TRATADOS / "ana_estacoes_barragem.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty:
        return df
    for col in (
        "dist_barragem_km",
        "dist_eixo_km",
        "cota_cm",
        "vazao_m3s",
        "cota_alerta_cm",
        "razao_nivel_cota_alerta",
        "lat",
        "lon",
        "rank",
    ):
        if col in df.columns:
            df[col] = df[col].map(_num_br)
    return df


def contexto_fluvial_barragem(id_snisb: str, *, max_itens: int = 5) -> dict[str, Any]:
    """Resumo para a Simulação / ficha: estações ANA da barragem."""
    vazio = {
        "disponivel": False,
        "n_estacoes": 0,
        "n_com_cota": 0,
        "n_acima_alerta": 0,
        "itens": [],
        "fonte": "",
        "nota": (
            "Contexto fluvial (ANA/SisClima) — não dimensiona a mancha proxy. "
            "Rode `python executar.py 52 53`."
        ),
    }
    df = carregar_estacoes_barragem()
    if df.empty:
        return vazio
    bid = str(id_snisb or "").strip()
    sub = df[df["id_snisb"].astype(str).str.strip() == bid].copy()
    if sub.empty:
        return {**vazio, "nota": "Nenhuma estação ANA vinculada a esta barragem (≤80 km)."}

    sub = sub.sort_values(["rank", "dist_barragem_km"], na_position="last")
    itens: list[dict[str, Any]] = []
    n_cota = 0
    n_acima = 0
    for _, r in sub.head(max_itens).iterrows():
        cota = r.get("cota_cm")
        alerta = r.get("cota_alerta_cm")
        razao = r.get("razao_nivel_cota_alerta")
        if cota is not None and not (isinstance(cota, float) and pd.isna(cota)):
            n_cota += 1
        if razao is not None and not (isinstance(razao, float) and pd.isna(razao)) and razao >= 1.0:
            n_acima += 1
        elif (
            cota is not None
            and alerta is not None
            and not pd.isna(cota)
            and not pd.isna(alerta)
            and float(alerta) > 0
            and float(cota) / float(alerta) >= 1.0
        ):
            n_acima += 1
        itens.append(
            {
                "codigo": str(r.get("codigo_estacao") or ""),
                "nome": str(r.get("nome_estacao") or ""),
                "rio": str(r.get("nome_rio") or ""),
                "relacao": str(r.get("relacao") or ""),
                "dist_km": r.get("dist_barragem_km"),
                "cota_cm": cota,
                "vazao_m3s": r.get("vazao_m3s"),
                "cota_alerta_cm": alerta,
                "razao": razao,
                "data": str(r.get("data_ultima") or ""),
                "a6_fonte": str(r.get("a6_fonte") or ""),
                "lat": r.get("lat"),
                "lon": r.get("lon"),
            }
        )

    fonte = ""
    if "fonte_telemetria" in sub.columns and len(sub):
        fonte = str(sub.iloc[0].get("fonte_telemetria") or "")
    return {
        "disponivel": True,
        "n_estacoes": int(len(sub)),
        "n_com_cota": n_cota,
        "n_acima_alerta": n_acima,
        "itens": itens,
        "fonte": fonte or "ana_estacoes_barragem.csv",
        "nota": (
            "Contexto fluvial ANA/SisClima (cota/vazão observadas). "
            "Não altera Circular / Trajeto / HAND — não é mancha PAE nem dam break."
        ),
    }
