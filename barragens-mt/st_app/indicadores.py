"""Indicadores sanitários e operacionais do comando (Onda 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from st_app.data import TRATADOS, _num, carregar_cnes_pontos, cnes_no_buffer, estimar_pop_cenario


NIVEIS_ATENCAO = {"Amarelo", "Laranja", "Vermelho", "Roxo"}


def _atencao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "nivel" not in df.columns:
        return df.iloc[0:0]
    return df[df["nivel"].isin(NIVEIS_ATENCAO)].copy()


def pop_estimada_barragem(row: pd.Series, fracao: float = 0.5) -> dict[str, Any]:
    """Proxy alinhado à simulação (fração 50% / profundidade 2 m se houver volume)."""
    vol = row.get("capacidade_hm3")
    try:
        vol_f = float(vol) if pd.notna(vol) else None
    except (TypeError, ValueError):
        vol_f = None
    area = (vol_f * fracao / 2.0) if vol_f and vol_f > 0 else 0.0
    afet = [
        p.strip()
        for p in str(row.get("municipios_potencialmente_afetados") or "").split("|")
        if p.strip()
    ]
    sede = str(row.get("municipio_sede") or row.get("municipio") or "") or None
    return estimar_pop_cenario(
        area_km2=area,
        fracao=fracao,
        municipio_sede=sede,
        municipios_afetados=afet or None,
        pop_afetadas=row.get("sigbm_pessoas_afetadas"),
        pop_jusante=row.get("sigbm_populacao_jusante"),
    )


def indicadores_sanitarios(df: pd.DataFrame) -> dict[str, Any]:
    """Agrega KPIs sanitários do recorte (estado ou município)."""
    aten = _atencao(df)
    cnes = carregar_cnes_pontos(so_prioritarios=False)

    pops: list[int] = []
    us_total = 0
    us_prio = 0
    munis_jusante: set[str] = set()
    rejeito = 0
    dpa_sem_alerta = 0
    extra_ativo = 0

    for _, r in aten.iterrows():
        est = pop_estimada_barragem(r)
        pops.append(int(est.get("populacao_estimada") or 0))
        afet = str(r.get("municipios_potencialmente_afetados") or "")
        for p in afet.split("|"):
            if p.strip():
                munis_jusante.add(p.strip())
        uso = str(r.get("uso_principal") or "").lower()
        if "rejeito" in uso or "miner" in uso:
            rejeito += 1
        dpa = str(r.get("dano_potencial_associado") or "").lower()
        al = str(r.get("alertavel") or "").lower()
        if dpa == "alto" and al != "sim":
            dpa_sem_alerta += 1
        try:
            if float(r.get("n_municipios_extraterritoriais") or 0) > 0:
                extra_ativo += 1
        except (TypeError, ValueError):
            pass

        if (
            pd.notna(r.get("latitude"))
            and pd.notna(r.get("longitude"))
            and pd.notna(r.get("capacidade_hm3"))
            and float(r.get("capacidade_hm3") or 0) > 0
            and not cnes.empty
        ):
            area = float(r["capacidade_hm3"]) * 0.5 / 2.0
            raio = (area / 3.14159265) ** 0.5 if area > 0 else 0
            buf = cnes_no_buffer(cnes, float(r["latitude"]), float(r["longitude"]), raio)
            us_total += len(buf)
            if not buf.empty and "prioritario" in buf.columns:
                us_prio += int(buf["prioritario"].sum())
            elif not buf.empty:
                us_prio += int(
                    buf.get("hospitalar", False).sum()
                    + buf.get("upa_ps", False).sum()
                    + buf.get("ubs_esf", False).sum()
                )

    pop_total = sum(pops)
    razao = (pop_total / us_prio) if us_prio > 0 else None
    completude = None
    if "completude" in df.columns and len(df):
        # completude pode ser "72%", "0,72" ou número 0–100 / 0–1
        serie = (
            df["completude"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        nums = pd.to_numeric(serie, errors="coerce")
        if nums.notna().any():
            med = float(nums.mean())
            if med <= 1.5:
                med *= 100.0
            completude = med

    return {
        "n_atencao": len(aten),
        "pop_sob_pressao": pop_total,
        "us_sob_risco": us_total,
        "us_prioritarias": us_prio,
        "razao_pop_us": round(razao, 1) if razao is not None else None,
        "municipios_jusante": len(munis_jusante),
        "completude_media": round(completude, 1) if completude is not None else None,
        "rejeito_atencao": rejeito,
        "dpa_alto_sem_alerta": dpa_sem_alerta,
        "extraterritorial_ativo": extra_ativo,
    }


def tendencia_7d_score(df: pd.DataFrame) -> dict[str, Any]:
    """Score único 0–100 e classe estável / atenção / piora (clima + projeção)."""
    from st_app.data import projecao_semana

    if df.empty:
        return {"score": 0, "classe": "estável", "sev": "sev-ok", "detalhe": "sem dados"}
    proj = projecao_semana(df)
    chuva72 = float(pd.to_numeric(df.get("chuva_72h_mm"), errors="coerce").max() or 0)
    prev = float(proj.get("prevista_max") or 0)
    pct = float(pd.to_numeric(df.get("percentil_climatologico"), errors="coerce").max() or 0)
    cem = 0
    if "alerta_cemaden_nivel" in df.columns:
        cem = int(
            df["alerta_cemaden_nivel"]
            .fillna("")
            .astype(str)
            .str.lower()
            .isin(["laranja", "vermelha", "vermelho", "roxa", "roxo", "moderado", "alto"])
            .sum()
        )
    score = 0.0
    score += min(35.0, chuva72 * 0.35)
    score += min(40.0, prev * 0.4) if prev < 140 else 45.0
    score += min(15.0, max(0.0, pct - 50) * 0.3)
    score += min(20.0, cem * 5.0)
    score += min(15.0, max(0, int(proj.get("delta") or 0)) * 3.0)
    score = round(min(100.0, score), 1)
    if score >= 60 or prev >= 140:
        classe, sev = "piora", "sev-alto"
    elif score >= 30 or prev >= 40 or int(proj.get("delta") or 0) > 0:
        classe, sev = "atenção", "sev-atencao"
    else:
        classe, sev = "estável", "sev-ok"
    return {
        "score": score,
        "classe": classe,
        "sev": sev,
        "detalhe": f"chuva72={chuva72:.0f} · prev={prev:.0f} · Cemaden={cem}",
    }


def solo_chuva_composta(df: pd.DataFrame) -> dict[str, Any]:
    """Proxy saturação × chuva recente/prevista — antecipa pressão A."""
    if df.empty:
        return {"indice": 0.0, "n_alto": 0, "sev": "sev-ok"}
    sat = pd.to_numeric(df.get("saturacao_antecedente"), errors="coerce")
    if sat.isna().all() and "saturacao_antecedente" not in df.columns:
        # fallback textual
        sat_txt = df.get("saturacao_antecedente", pd.Series(dtype=str)).fillna("").astype(str).str.lower()
        sat = sat_txt.map(
            lambda s: 0.8 if "alta" in s or "elevad" in s else (0.5 if "média" in s or "media" in s else 0.2)
        )
    sat = sat.fillna(0).clip(0, 1)
    if sat.max() > 1.5:
        sat = (sat / 100.0).clip(0, 1)
    chuva = pd.to_numeric(df.get("chuva_72h_mm"), errors="coerce").fillna(0)
    prev = pd.to_numeric(df.get("chuva_prevista_24_72h_mm"), errors="coerce").fillna(0)
    comp = sat * (chuva * 0.6 + prev * 0.4)
    indice = float(comp.max()) if len(comp) else 0.0
    n_alto = int((comp >= 25).sum())
    sev = severidade_from_composta(indice)
    return {"indice": round(indice, 1), "n_alto": n_alto, "sev": sev, "media": round(float(comp.mean()), 1)}


def severidade_from_composta(indice: float) -> str:
    if indice >= 60:
        return "sev-critico"
    if indice >= 40:
        return "sev-alto"
    if indice >= 25:
        return "sev-elevado"
    if indice >= 10:
        return "sev-atencao"
    return "sev-ok"


def quase_atencao(df: pd.DataFrame, limiar_a: float = 8.0, limiar_prev: float = 40.0) -> pd.DataFrame:
    """Verdes sob pressão climática ou previsão elevada — lista de vigília."""
    if df.empty:
        return df
    base = df[df["nivel"] == "Verde"].copy()
    if base.empty:
        return base
    a = pd.to_numeric(base.get("pontos_a"), errors="coerce").fillna(0)
    prev = pd.to_numeric(base.get("chuva_prevista_24_72h_mm"), errors="coerce").fillna(0)
    mask = (a >= limiar_a) | (prev >= limiar_prev)
    out = base.loc[mask].sort_values(
        ["pontos_a", "chuva_prevista_24_72h_mm"], ascending=False, na_position="last"
    )
    return out


def tendencia_idap_48h() -> dict[str, Any]:
    """Compara as duas últimas rodadas do histórico (piora/melhora Em atenção+)."""
    from st_app.data import carregar_historico_indice

    ind = carregar_historico_indice()
    if len(ind) < 2:
        return {"ok": False, "msg": "Histórico insuficiente (rode a etapa 16 mais de uma vez)."}
    ant, atu = ind.iloc[-2], ind.iloc[-1]
    ama_ant = int(ant["amarelo"] + ant["laranja"] + ant["vermelho"] + ant["roxo"])
    ama_atu = int(atu["amarelo"] + atu["laranja"] + atu["vermelho"] + atu["roxo"])
    delta = ama_atu - ama_ant
    if delta > 0:
        classe, rotulo = "sev-elevado", "piora"
    elif delta < 0:
        classe, rotulo = "sev-ok", "melhora"
    else:
        classe, rotulo = "sev-neutro", "estável"
    return {
        "ok": True,
        "classe": classe,
        "rotulo": rotulo,
        "delta": delta,
        "atual": ama_atu,
        "anterior": ama_ant,
        "instante_atual": str(atu.get("instante", "")),
        "instante_anterior": str(ant.get("instante", "")),
        "msg": (
            f"Em atenção+ passou de {ama_ant} para {ama_atu} ({delta:+d}) "
            f"entre as duas últimas rodadas do índice."
        ),
    }


def carregar_exposicao_vulneraveis() -> pd.DataFrame:
    caminho = TRATADOS / "exposicao_populacoes_eixo_cuiaba.csv"
    if not caminho.exists():
        return pd.DataFrame()
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)
    if "distancia_eixo_km" in df.columns:
        df["distancia_eixo_km"] = _num(df["distancia_eixo_km"])
    if "latitude" in df.columns:
        df["latitude"] = _num(df["latitude"])
    if "longitude" in df.columns:
        df["longitude"] = _num(df["longitude"])
    if "familias" in df.columns:
        df["familias"] = _num(df["familias"])
    return df


def carregar_impacto_extraterritorial() -> pd.DataFrame:
    caminho = TRATADOS / "impacto_extraterritorial_mt.csv"
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


def carregar_alertabilidade() -> pd.DataFrame:
    caminho = TRATADOS / "alertabilidade_piloto.csv"
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


def carregar_contatos() -> pd.DataFrame:
    caminho = TRATADOS / "contatos_institucionais_piloto.csv"
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


def metricas_alertabilidade() -> dict[str, Any]:
    al = carregar_alertabilidade()
    ct = carregar_contatos()
    if al.empty:
        return {"n": 0, "alertaveis": 0, "pct": 0.0, "contatos_com_email": 0, "contatos_com_fone": 0}
    alertaveis = int((al.get("alertavel", "") == "sim").sum()) if "alertavel" in al.columns else 0
    email_ok = 0
    fone_ok = 0
    if not ct.empty:
        email_ok = int(ct["email"].fillna("").astype(str).str.contains("@").sum()) if "email" in ct.columns else 0
        fone = (ct.get("telefone", pd.Series(dtype=str)).fillna("") + ct.get("celular", pd.Series(dtype=str)).fillna(""))
        fone_ok = int(fone.astype(str).str.replace(r"\D", "", regex=True).str.len().ge(8).sum())
    return {
        "n": len(al),
        "alertaveis": alertaveis,
        "pct": round(100.0 * alertaveis / max(len(al), 1), 1),
        "contatos_com_email": email_ok,
        "contatos_com_fone": fone_ok,
        "n_contatos": len(ct),
        "regioes": sorted(ct["regiao_saude"].dropna().unique().tolist()) if "regiao_saude" in ct.columns else [],
    }
