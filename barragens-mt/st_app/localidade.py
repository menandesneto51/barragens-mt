"""Dossiê por localidade (município): barragens, população e vulneráveis.

Responde perguntas do tipo «Cuiabá — quais barragens? população? indígenas?
ribeirinhos?» com as bases já tratadas no sistema e lacunas explícitas.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import pandas as pd
import streamlit as st

from st_app.data import carregar_cnes_pontos, carregar_populacao, filtrar_municipio, ler_csv


def normalizar_nome(texto: object) -> str:
    s = str(texto or "").strip().casefold()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(s.split())


def nomes_equivalentes(a: object, b: object) -> bool:
    na, nb = normalizar_nome(a), normalizar_nome(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def _lista_municipios_campo(valor: object) -> list[str]:
    raw = str(valor or "").strip()
    if not raw or raw.lower() in ("nan", "none"):
        return []
    partes: list[str] = []
    for sep in ("|", ";", "/", ","):
        if sep in raw:
            partes = [p.strip() for p in raw.split(sep) if p.strip()]
            break
    return partes or [raw]


def _filtra_por_municipio(df: pd.DataFrame, col: str, municipio: str) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return pd.DataFrame()
    return df[df[col].apply(lambda v: any(nomes_equivalentes(municipio, p) for p in _lista_municipios_campo(v)))].copy()


@st.cache_data(show_spinner=False)
def carregar_funai_tis() -> pd.DataFrame:
    return ler_csv("funai_terras_indigenas_mt.csv")


@st.cache_data(show_spinner=False)
def carregar_funai_aldeias() -> pd.DataFrame:
    return ler_csv("funai_aldeias_mt.csv")


@st.cache_data(show_spinner=False)
def carregar_incra_assentamentos() -> pd.DataFrame:
    return ler_csv("incra_assentamentos_mt.csv")


@st.cache_data(show_spinner=False)
def carregar_palmares() -> pd.DataFrame:
    return ler_csv("palmares_quilombolas_mt.csv")


@st.cache_data(show_spinner=False)
def carregar_incra_quilombolas() -> pd.DataFrame:
    return ler_csv("incra_quilombolas_mt.csv")


def populacao_municipio(municipio: str) -> dict[str, Any]:
    pop = carregar_populacao()
    if pop.empty or "municipio" not in pop.columns:
        return {"populacao": None, "ano": None, "fonte": None, "codigo_ibge": None}
    hit = pop[pop["municipio"].apply(lambda m: nomes_equivalentes(municipio, m))]
    if hit.empty:
        return {"populacao": None, "ano": None, "fonte": None, "codigo_ibge": None}
    r = hit.iloc[0]
    try:
        n = int(float(r.get("populacao"))) if pd.notna(r.get("populacao")) else None
    except (TypeError, ValueError):
        n = None
    return {
        "populacao": n,
        "ano": r.get("ano_referencia"),
        "fonte": r.get("fonte"),
        "codigo_ibge": r.get("codigo_ibge"),
        "area_km2": r.get("area_km2"),
        "densidade_hab_km2": r.get("densidade_hab_km2"),
    }


def cnes_no_municipio(municipio: str) -> pd.DataFrame:
    from st_app.indicadores import us_nos_municipios

    cnes = carregar_cnes_pontos(so_prioritarios=False)
    if cnes.empty:
        return cnes
    return us_nos_municipios(cnes, {municipio})


def vulneraveis_eixo_no_municipio(municipio: str) -> pd.DataFrame:
    from st_app.indicadores import carregar_exposicao_vulneraveis

    vul = carregar_exposicao_vulneraveis()
    if vul.empty or "municipio" not in vul.columns:
        return pd.DataFrame()
    return _filtra_por_municipio(vul, "municipio", municipio)


def montar_dossie_localidade(
    municipio: str,
    df_barragens: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Agrega barragens (sede/jusante), pop IBGE, FUNAI, INCRA, Palmares, CNES."""
    mun = (municipio or "").strip()
    base = df_barragens if df_barragens is not None else pd.DataFrame()
    bars = filtrar_municipio(base, mun) if mun and not base.empty else base.copy()

    sede = pd.DataFrame()
    jus = pd.DataFrame()
    if not bars.empty and "papel_municipio" in bars.columns:
        papel = bars["papel_municipio"].astype(str)
        sede = bars[papel.str.contains("Sede", na=False)]
        jus = bars[papel.str.contains("jusante|Afetado", case=False, na=False)]

    niveis: dict[str, int] = {}
    if not bars.empty and "nivel" in bars.columns:
        niveis = {str(k): int(v) for k, v in bars["nivel"].value_counts().items()}

    pop = populacao_municipio(mun)
    tis = _filtra_por_municipio(carregar_funai_tis(), "municipio_nome", mun)
    aldeias = _filtra_por_municipio(carregar_funai_aldeias(), "nommunic", mun)
    assent = _filtra_por_municipio(carregar_incra_assentamentos(), "municipio", mun)
    palmares = _filtra_por_municipio(carregar_palmares(), "MUNICÍPIO", mun)
    quil_incra = pd.DataFrame()
    iq = carregar_incra_quilombolas()
    for col in ("municipio", "nome_municipio", "nm_municip", "municipio_nome"):
        if col in iq.columns:
            quil_incra = _filtra_por_municipio(iq, col, mun)
            break

    eixo = vulneraveis_eixo_no_municipio(mun)
    eixo_trad = pd.DataFrame()
    if not eixo.empty and "categoria" in eixo.columns:
        cats = eixo["categoria"].fillna("").astype(str).str.lower()
        eixo_trad = eixo[~cats.str.contains("saúde|saude|estabelecimento")].copy()

    cnes = cnes_no_municipio(mun)
    us_prio = 0
    if not cnes.empty and "prioritario" in cnes.columns:
        us_prio = int(cnes["prioritario"].sum())

    familias_assent = None
    if not assent.empty and "num_familias" in assent.columns:
        familias_assent = int(pd.to_numeric(assent["num_familias"], errors="coerce").fillna(0).sum())

    moradores_palmares = None
    if not palmares.empty and "Nº DE MORADORES" in palmares.columns:
        moradores_palmares = int(
            pd.to_numeric(palmares["Nº DE MORADORES"], errors="coerce").fillna(0).sum()
        )

    # Municípios sede das barragens que só afetam a localidade a jusante (contexto).
    sedes_montante: list[str] = []
    if not jus.empty and "municipio_sede" in jus.columns:
        sedes_montante = sorted(
            {
                str(s).strip()
                for s in jus["municipio_sede"].dropna()
                if str(s).strip() and not nomes_equivalentes(s, mun)
            }
        )

    return {
        "municipio": mun,
        "barragens": bars,
        "n_barragens": len(bars) if bars is not None else 0,
        "n_sede": len(sede),
        "n_jusante": len(jus),
        "sede": sede,
        "jusante": jus,
        "niveis": niveis,
        "populacao": pop,
        "terras_indigenas": tis,
        "aldeias": aldeias,
        "assentamentos": assent,
        "familias_assentamentos": familias_assent,
        "quilombolas_palmares": palmares,
        "moradores_palmares": moradores_palmares,
        "quilombolas_incra": quil_incra,
        "exposicao_eixo": eixo_trad,
        "cnes": cnes,
        "n_cnes": len(cnes),
        "n_cnes_prioritarios": us_prio,
        "sedes_montante": sedes_montante,
        "ribeirinhos": {
            "disponivel": False,
            "mensagem": (
                "Não há base estadual consolidada de comunidades ribeirinhas no inventário. "
                "Use FUNAI/INCRA/Palmares + exposição do eixo como proxy parcial; "
                "complementar com SES/Defesa Civil local."
            ),
        },
        "fontes": {
            "barragens": "SNISB/IDAP + Otto (sede ou jusante)",
            "populacao": "IBGE (ibge_populacao_municipios_mt.csv)",
            "indigenas": "FUNAI terras indígenas e aldeias",
            "assentamentos": "INCRA assentamentos",
            "quilombolas": "Fundação Palmares + INCRA (quando houver)",
            "saude": "CNES estabelecimentos",
            "ribeirinhos": "Lacuna — sem camada estadual",
        },
    }


def municipios_vizinhos_vulneraveis(
    municipio: str,
    sedes_montante: list[str] | None = None,
    *,
    limite: int = 8,
) -> pd.DataFrame:
    """Resumo de vulneráveis em municípios ligados (sede montante / vizinhos Otto)."""
    alvos = list(sedes_montante or [])
    # Inclui pares Otto onde a localidade é afetada.
    impacto = ler_csv("impacto_extraterritorial_mt.csv")
    if not impacto.empty and "municipio_potencialmente_afetado" in impacto.columns:
        hit = impacto[
            impacto["municipio_potencialmente_afetado"].apply(
                lambda m: nomes_equivalentes(municipio, m)
            )
        ]
        if "municipio_sede" in hit.columns:
            for s in hit["municipio_sede"].dropna().astype(str):
                s = s.strip()
                if s and not nomes_equivalentes(s, municipio):
                    alvos.append(s)
    vistos: set[str] = set()
    linhas: list[dict[str, Any]] = []
    for m in alvos:
        chave = normalizar_nome(m)
        if not chave or chave in vistos or nomes_equivalentes(m, municipio):
            continue
        vistos.add(chave)
        tis = _filtra_por_municipio(carregar_funai_tis(), "municipio_nome", m)
        ald = _filtra_por_municipio(carregar_funai_aldeias(), "nommunic", m)
        ass = _filtra_por_municipio(carregar_incra_assentamentos(), "municipio", m)
        pal = _filtra_por_municipio(carregar_palmares(), "MUNICÍPIO", m)
        if tis.empty and ald.empty and ass.empty and pal.empty:
            continue
        linhas.append(
            {
                "Município ligado": m,
                "Terras indígenas": len(tis),
                "Aldeias": len(ald),
                "Assentamentos": len(ass),
                "Quilombos (Palmares)": len(pal),
            }
        )
        if len(linhas) >= limite:
            break
    return pd.DataFrame(linhas)
