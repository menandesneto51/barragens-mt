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
            if c in inv.columns and (c == "id_snisb" or c not in idap.columns)
        ]
        # Sempre trazer coordenadas e SIGBM do inventário.
        for obrig in (
            "id_snisb",
            "latitude",
            "longitude",
            "capacidade_hm3",
            "altura_m",
            "sigbm_populacao_jusante",
            "sigbm_pessoas_afetadas",
        ):
            if obrig in inv.columns and obrig not in cols_inv:
                cols_inv.append(obrig)
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
        idap = idap.merge(coords, on="id_snisb", how="left", suffixes=("", "_inv"))
        for c in list(idap.columns):
            if c.endswith("_inv"):
                base = c[:-4]
                if base in idap.columns:
                    idap[base] = idap[base].fillna(idap[c])
                else:
                    idap.rename(columns={c: base}, inplace=True)
                idap.drop(columns=[c], inplace=True, errors="ignore")
        if "uso_principal" not in idap.columns and "uso_principal" in inv.columns:
            idap = idap.merge(inv[["id_snisb", "uso_principal"]], on="id_snisb", how="left")
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
def carregar_cnes_pontos(so_prioritarios: bool = False) -> pd.DataFrame:
    """Pontos CNES com coordenada — estadual se existir; senão eixo Cuiabá."""
    from cnes_tipos import classificar_estabelecimento

    estadual = TRATADOS / "cnes_estabelecimentos_mt.geojson"
    eixo = TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.geojson"
    caminho = estadual if estadual.exists() else eixo
    if not caminho.exists():
        return pd.DataFrame()
    geo = json.loads(caminho.read_text(encoding="utf-8"))
    linhas: list[dict] = []
    vistos: set[tuple[float, float, str]] = set()
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
        if so_prioritarios and not cls["prioritario"]:
            continue
        chave = (round(lat, 5), round(lon, 5), nome[:40])
        if chave in vistos:
            continue
        vistos.add(chave)
        linhas.append(
            {
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "nome": nome[:80],
                "municipio": (props.get("municipio") or "").strip(),
                "tipo": cls["tipo"],
                "prioridade": cls["prioridade"],
                "prioritario": bool(cls["prioritario"]),
                "hospitalar": bool(cls["hospitalar"]),
                "upa_ps": bool(cls["upa_ps"]),
                "ubs_esf": bool(cls["ubs_esf"]),
            }
        )
    if not linhas:
        return pd.DataFrame()
    return pd.DataFrame(linhas).sort_values(["prioridade", "nome"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def carregar_historico_indice() -> pd.DataFrame:
    caminho = TRATADOS / "historico_idap" / "indice.csv"
    if not caminho.exists():
        return pd.DataFrame()
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
    for c in ("roxo", "vermelho", "laranja", "amarelo", "verde", "n_barragens"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def tendencias_estado() -> dict[str, int | None]:
    """Delta Amarelo+/Amarelo/Verde entre as duas últimas rodadas do histórico."""
    ind = carregar_historico_indice()
    if len(ind) < 2:
        return {"amarelo_mais": None, "amarelo": None, "verde": None}
    ant, atu = ind.iloc[-2], ind.iloc[-1]
    ama_ant = int(ant["amarelo"] + ant["laranja"] + ant["vermelho"] + ant["roxo"])
    ama_atu = int(atu["amarelo"] + atu["laranja"] + atu["vermelho"] + atu["roxo"])
    return {
        "amarelo_mais": ama_atu - ama_ant,
        "amarelo": int(atu["amarelo"] - ant["amarelo"]),
        "verde": int(atu["verde"] - ant["verde"]),
    }


def projecao_semana(df: pd.DataFrame) -> dict:
    """Proxy hidro próximos dias a partir da chuva prevista 24–72h."""
    amarelo_mais = int(
        df["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"]).sum()
    )
    prev = (
        pd.to_numeric(df.get("chuva_prevista_24_72h_mm"), errors="coerce")
        if "chuva_prevista_24_72h_mm" in df.columns
        else pd.Series(dtype=float)
    )
    n_atencao = int((prev >= 40).sum()) if len(prev) else 0
    n_r12 = int((prev >= 140).sum()) if len(prev) else 0
    verde_risco = 0
    if "nivel" in df.columns and len(prev):
        verde_risco = int(((df["nivel"] == "Verde") & (prev >= 40)).sum())
    proj = amarelo_mais + verde_risco
    if n_r12 and "nivel" in df.columns:
        mask_r12 = prev >= 140
        ids = set(df.loc[mask_r12, "id_snisb"].astype(str))
        ids_ja = set(
            df.loc[df["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"]), "id_snisb"].astype(str)
        )
        proj = max(proj, len(ids | ids_ja))
    return {
        "amarelo_mais_atual": amarelo_mais,
        "amarelo_mais_projetado": proj,
        "delta": proj - amarelo_mais,
        "prevista_max": float(prev.max()) if len(prev) and prev.notna().any() else None,
        "n_atencao": n_atencao,
        "n_r12": n_r12,
    }


@st.cache_data(show_spinner=False)
def carregar_piloto() -> pd.DataFrame:
    df = ler_csv("piloto_manso_cuiaba.csv")
    if not df.empty and "idap" in df.columns:
        df["idap_n"] = _num(df["idap"])
    return df


def severidade_pct(pct: float | None) -> str:
    """Classe visual por percentual 0–100 (pressão, índice etc.)."""
    if pct is None:
        return "sev-neutro"
    if pct >= 80:
        return "sev-critico"
    if pct >= 60:
        return "sev-alto"
    if pct >= 40:
        return "sev-elevado"
    if pct >= 20:
        return "sev-atencao"
    return "sev-ok"


def severidade_nivel(nivel: str) -> str:
    return {
        "Roxo": "sev-critico",
        "Vermelho": "sev-alto",
        "Laranja": "sev-elevado",
        "Amarelo": "sev-atencao",
        "Verde": "sev-ok",
    }.get(nivel, "sev-neutro")


def card_kpi(
    titulo: str,
    valor: str,
    *,
    sev: str = "sev-neutro",
    delta: str | None = None,
    nota: str | None = None,
) -> str:
    dlt = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    nt = f'<div class="kpi-nota">{nota}</div>' if nota else ""
    return (
        f'<div class="kpi-card {sev}">'
        f'<div class="kpi-val">{valor}</div>'
        f'<div class="kpi-tit">{titulo}</div>'
        f"{dlt}{nt}</div>"
    )


def municipios_catalogo(df: pd.DataFrame) -> list[str]:
    nomes: set[str] = set()
    if "municipio_sede" in df.columns:
        nomes.update(df["municipio_sede"].dropna().astype(str).str.strip())
    if "municipios_potencialmente_afetados" in df.columns:
        for txt in df["municipios_potencialmente_afetados"].fillna(""):
            for p in str(txt).split("|"):
                p = p.strip()
                if p:
                    nomes.add(p)
    return sorted(n for n in nomes if n and n.lower() != "nan")


def filtrar_municipio(df: pd.DataFrame, municipio: str) -> pd.DataFrame:
    """Sede OU potencialmente afetado a jusante (rompimento)."""
    if not municipio or df.empty:
        return df
    alvo = municipio.strip().casefold()

    def _bate(row: pd.Series) -> bool:
        sede = str(row.get("municipio_sede") or "").strip().casefold()
        if alvo in sede or sede == alvo:
            return True
        af = str(row.get("municipios_potencialmente_afetados") or "")
        return any(alvo == p.strip().casefold() or alvo in p.strip().casefold() for p in af.split("|") if p.strip())

    mask = df.apply(_bate, axis=1)
    out = df.loc[mask].copy()
    if out.empty:
        return out

    def _papel(row: pd.Series) -> str:
        sede = str(row.get("municipio_sede") or "").strip().casefold()
        if alvo in sede or sede == alvo:
            af = str(row.get("municipios_potencialmente_afetados") or "")
            if any(alvo == p.strip().casefold() for p in af.split("|") if p.strip()) and alvo != sede:
                return "Sede e também na mancha potencial"
            return "Sede da barragem"
        return "Potencialmente afetado (jusante) — barragem pode estar em outro município"

    out["papel_municipio"] = out.apply(_papel, axis=1)
    return out


def tendencia_climatica_texto(proj: dict, df: pd.DataFrame) -> tuple[str, str]:
    """Retorna (classe_sev, mensagem) para a tendência dos próximos dias."""
    prev = proj.get("prevista_max")
    chuva72 = (
        float(pd.to_numeric(df["chuva_72h_mm"], errors="coerce").max())
        if "chuva_72h_mm" in df.columns and len(df)
        else None
    )
    delta = int(proj.get("delta") or 0)
    atual = int(proj.get("amarelo_mais_atual") or 0)
    futuro = int(proj.get("amarelo_mais_projetado") or atual)

    if (prev or 0) >= 140 or (proj.get("n_r12") or 0) > 0:
        sev = "sev-critico"
        msg = (
            f"Tendência de **piora**: previsão extrema (≥140 mm) em "
            f"{proj.get('n_r12', 0)} sede(s). Em atenção+ pode ir de {atual} para {futuro}."
        )
    elif (prev or 0) >= 40 or delta > 0:
        sev = "sev-elevado" if delta > 5 or (prev or 0) >= 80 else "sev-atencao"
        msg = (
            f"Tendência de **atenção climática**: chuva prevista máx. "
            f"{(prev or 0):.1f} mm".replace(".", ",")
            + f" · em atenção+ projetado {futuro} ({delta:+d} vs hoje)."
        )
    elif (chuva72 or 0) >= 50:
        sev = "sev-atencao"
        msg = (
            f"Tendência **estável com solo carregado**: chuva 72h recente até "
            f"{chuva72:.1f} mm".replace(".", ",")
            + f", mas previsão próxima ainda baixa. Em atenção+ permanece ~{atual}."
        )
    else:
        sev = "sev-ok"
        msg = (
            f"Tendência **estável / favorável** para os próximos dias: previsão máx. "
            f"{(prev if prev is not None else 0):.1f} mm".replace(".", ",")
            + f" · em atenção+ projetado {futuro} (sem alta climática relevante)."
        )
    return sev, msg



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
    # Pré-filtro por bounding box (~1° ≈ 111 km) para não varrer 12k pontos à toa.
    grau = raio_km / 111.0 + 0.02
    cand = cnes[
        (cnes["latitude"] >= lat - grau)
        & (cnes["latitude"] <= lat + grau)
        & (cnes["longitude"] >= lon - grau)
        & (cnes["longitude"] <= lon + grau)
    ]
    if cand.empty:
        return cand
    dists = [
        haversine_km(lat, lon, float(r.latitude), float(r.longitude))
        for r in cand.itertuples()
    ]
    out = cand.copy()
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
