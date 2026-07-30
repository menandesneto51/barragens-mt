"""Carrega CSVs tratados do VIGIBARRAGENS–MT para o app Streamlit."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
TRATADOS = RAIZ / "dados" / "tratados"
SCRIPTS = RAIZ / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CORES_NIVEL = {
    "Roxo": "#5b2c6f",
    "Vermelho": "#c0392b",
    "Laranja": "#d35400",
    "Amarelo": "#b7950b",
    "Verde": "#1e8449",
}


def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype(str).str.replace(",", ".", regex=False),
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
        cols_inv = [
            c
            for c in (
                "id_snisb",
                "latitude",
                "longitude",
                "capacidade_hm3",
                "altura_m",
                "municipio",
                "uso_principal",
                "orgao_fiscalizador",
                "sigbm_populacao_jusante",
                "sigbm_pessoas_afetadas",
            )
            if c in inv.columns
        ]
        coords = inv[cols_inv].copy()
        for c in (
            "latitude",
            "longitude",
            "capacidade_hm3",
            "altura_m",
            "sigbm_populacao_jusante",
            "sigbm_pessoas_afetadas",
        ):
            if c in coords.columns:
                coords[c] = _num(coords[c])
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
    if not df.empty and "densidade_hab_km2" in df.columns:
        df["densidade_hab_km2"] = _num(df["densidade_hab_km2"])
    if not df.empty and "area_km2" in df.columns:
        df["area_km2"] = _num(df["area_km2"])
    return df


@st.cache_data(show_spinner=False)
def carregar_densidades() -> dict[str, float]:
    """Densidades municipais (IBGE quando disponível; fallback do módulo sanitário)."""
    from idap.impacto_sanitario import _carregar_densidades_ibge

    return dict(_carregar_densidades_ibge())


@st.cache_data(show_spinner=False)
def carregar_cnes_pontos() -> pd.DataFrame:
    """Pontos CNES prioritários (UBS/ESF/UPA/hospital) com coordenada — eixo Cuiabá."""
    from cnes_tipos import classificar_estabelecimento

    caminho = TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.geojson"
    if not caminho.exists():
        return pd.DataFrame()
    geo = json.loads(caminho.read_text(encoding="utf-8"))
    linhas: list[dict] = []
    for feicao in geo.get("features") or []:
        geom = feicao.get("geometry") or {}
        props = feicao.get("properties") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        nome = (props.get("nome_fantasia") or props.get("nome_razao_social") or "").strip()
        cls = classificar_estabelecimento(
            codigo_tipo=props.get("codigo_tipo_unidade"),
            nome=nome,
            atendimento_hospitalar=props.get("atendimento_hospitalar"),
        )
        if not cls["prioritario"]:
            continue
        linhas.append(
            {
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "nome": nome[:80],
                "municipio": (props.get("municipio") or "").strip(),
                "tipo": cls["tipo"],
                "prioridade": cls["prioridade"],
                "hospitalar": bool(cls["hospitalar"]),
                "upa_ps": bool(cls["upa_ps"]),
                "ubs_esf": bool(cls["ubs_esf"]),
            }
        )
    if not linhas:
        return pd.DataFrame()
    return pd.DataFrame(linhas).sort_values(["prioridade", "nome"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def carregar_piloto() -> pd.DataFrame:
    df = ler_csv("piloto_manso_cuiaba.csv")
    if not df.empty and "idap" in df.columns:
        df["idap_n"] = _num(df["idap"])
    return df


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cnes_no_buffer(
    cnes: pd.DataFrame,
    lat: float,
    lon: float,
    raio_km: float,
) -> pd.DataFrame:
    if cnes.empty or raio_km <= 0 or pd.isna(lat) or pd.isna(lon):
        return pd.DataFrame()
    dists = [
        haversine_km(lat, lon, float(r.latitude), float(r.longitude))
        for r in cnes.itertuples()
    ]
    out = cnes.copy()
    out["dist_km"] = dists
    out = out[out["dist_km"] <= raio_km].sort_values(["prioridade", "dist_km"])
    return out.reset_index(drop=True)


def estimar_pop_cenario(
    *,
    area_km2: float,
    fracao: float,
    municipio_sede: str | None,
    municipios_afetados: list[str] | None,
    pop_afetadas: float | None,
    pop_jusante: float | None,
) -> dict:
    from idap.impacto_sanitario import estimar_populacao

    return estimar_populacao(
        area_km2=area_km2,
        municipio_sede=municipio_sede,
        municipios_afetados=municipios_afetados,
        pop_sigbm_afetadas=pop_afetadas if pd.notna(pop_afetadas) else None,
        pop_sigbm_jusante=pop_jusante if pd.notna(pop_jusante) else None,
        fracao_volume=fracao,
    )
