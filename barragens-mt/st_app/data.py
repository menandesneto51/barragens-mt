"""Carrega CSVs tratados do VIGIBARRAGENS–MT para o app Streamlit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
TRATADOS = RAIZ / "dados" / "tratados"

CORES_NIVEL = {
    "Roxo": "#5b2c6f",
    "Vermelho": "#c0392b",
    "Laranja": "#d35400",
    "Amarelo": "#b7950b",
    "Verde": "#1e8449",
}


def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype(str).str.replace(",", ".", regex=False).str.replace("", "", regex=False),
        errors="coerce",
    )


@st.cache_data(show_spinner=False)
def ler_csv(nome: str) -> pd.DataFrame:
    caminho = TRATADOS / nome
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


@st.cache_data(show_spinner=False)
def carregar_idap() -> pd.DataFrame:
    idap = ler_csv("idap_estadual_mt.csv")
    inv = ler_csv("inventario_barragens_mt.csv")
    hidro = ler_csv("hidro_barragens_mt.csv")
    if idap.empty:
        return idap
    idap["idap_n"] = _num(idap["idap"])
    for col in ("pontos_a", "pontos_b", "pontos_c", "pontos_d"):
        if col in idap.columns:
            idap[col] = _num(idap[col]).fillna(0)
    if not inv.empty:
        coords = inv[["id_snisb", "latitude", "longitude", "capacidade_hm3", "altura_m"]].copy()
        coords["latitude"] = _num(coords["latitude"])
        coords["longitude"] = _num(coords["longitude"])
        coords["capacidade_hm3"] = _num(coords["capacidade_hm3"])
        idap = idap.merge(coords, on="id_snisb", how="left")
    if not hidro.empty:
        cols = [
            c
            for c in (
                "id_snisb",
                "chuva_24h_mm",
                "chuva_72h_mm",
                "chuva_prevista_24_72h_mm",
                "percentil_climatologico",
                "saturacao_antecedente",
                "nivel_alerta_hidro",
                "alerta_cemaden",
                "alerta_cemaden_nivel",
                "alerta_inmet",
                "nivel_alerta_integrado",
                "fonte_previsao",
                "vazao_prevista_glofas_m3s",
            )
            if c in hidro.columns
        ]
        h = hidro[cols].copy()
        for c in cols:
            if c.endswith("_mm") or c in {
                "percentil_climatologico",
                "saturacao_antecedente",
                "vazao_prevista_glofas_m3s",
            }:
                h[c] = _num(h[c])
        idap = idap.merge(h, on="id_snisb", how="left")
    piloto = ler_csv("piloto_manso_cuiaba.csv")
    if not piloto.empty:
        idap["piloto"] = idap["id_snisb"].isin(set(piloto["id_snisb"]))
    else:
        idap["piloto"] = False
    return idap


@st.cache_data(show_spinner=False)
def carregar_hidro_mun() -> pd.DataFrame:
    df = ler_csv("hidro_municipios_mt.csv")
    if df.empty:
        return df
    for c in (
        "chuva_24h_mm",
        "chuva_72h_mm",
        "chuva_prevista_24_72h_mm",
        "percentil_climatologico",
        "indice_saturacao_solo",
    ):
        if c in df.columns:
            df[c] = _num(df[c])
    return df


@st.cache_data(show_spinner=False)
def carregar_populacao() -> pd.DataFrame:
    df = ler_csv("ibge_populacao_municipios_mt.csv")
    if not df.empty and "populacao" in df.columns:
        df["populacao"] = _num(df["populacao"])
    return df


@st.cache_data(show_spinner=False)
def carregar_piloto() -> pd.DataFrame:
    df = ler_csv("piloto_manso_cuiaba.csv")
    if not df.empty and "idap" in df.columns:
        df["idap_n"] = _num(df["idap"])
    return df
