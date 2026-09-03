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


def proxy_ribeirinhos_municipio(municipio: str) -> dict[str, Any]:
    """Proxy operacional no eixo Manso–Cuiabá — não é cadastro ribeirinho.

    Sem camada estadual oficial, o produto oferece população em setores
    censitários do eixo hidrográfico (IBGE 2022) e elementos vulneráveis
    a ≤5 km do eixo. Setores rurais são o sinal mais próximo de comunidades
    de margem; a vigilância municipal deve cruzar com microáreas da APS.
    """
    mun = (municipio or "").strip()
    vazio = {
        "disponivel": False,
        "tipo": "lacuna",
        "n_setores_eixo": 0,
        "populacao_eixo": 0,
        "n_setores_rural_eixo": 0,
        "populacao_rural_eixo": 0,
        "n_elementos_proximos_5km": 0,
        "elementos_proximos": pd.DataFrame(),
        "mensagem": (
            "Não há base estadual consolidada de comunidades ribeirinhas. "
            "Este município também não entra no recorte de setores do eixo "
            "Manso–Cuiabá — sem proxy quantitativo in-repo."
        ),
        "aviso": (
            "Qualquer número apresentado como «população ribeirinha» sem "
            "cadastro APS/Defesa Civil seria estimativa sem fonte."
        ),
        "fonte": "Lacuna — sem camada estadual; setores do eixo ausentes para o município",
    }
    if not mun:
        return vazio

    from st_app.setores_ibge import carregar_setores_eixo

    setores = carregar_setores_eixo()
    sub = pd.DataFrame()
    if not setores.empty and "municipio" in setores.columns:
        sub = setores[
            setores["municipio"].apply(lambda m: nomes_equivalentes(mun, m))
        ].copy()

    eixo = vulneraveis_eixo_no_municipio(mun)
    prox = pd.DataFrame()
    if not eixo.empty:
        cats = (
            eixo["categoria"].fillna("").astype(str).str.lower()
            if "categoria" in eixo.columns
            else pd.Series([""] * len(eixo))
        )
        trad = eixo[~cats.str.contains("saúde|saude|estabelecimento")].copy()
        if "distancia_eixo_km" in trad.columns:
            dist = pd.to_numeric(trad["distancia_eixo_km"], errors="coerce")
            prox = trad[dist.notna() & (dist <= 5.0)].copy()
        elif "faixa" in trad.columns:
            faixa = trad["faixa"].fillna("").astype(str).str.lower()
            prox = trad[faixa.str.contains("2 km|5 km|até 2|ate 2|até 5|ate 5")].copy()
        else:
            prox = trad

    if sub.empty and prox.empty:
        return vazio

    n_set = int(len(sub))
    pop_eixo = int(sub["populacao"].sum()) if n_set and "populacao" in sub.columns else 0
    rural = pd.DataFrame()
    if n_set and "situacao" in sub.columns:
        sit = sub["situacao"].fillna("").astype(str).str.lower()
        rural = sub[sit.str.contains("rural")].copy()
    n_rural = int(len(rural))
    pop_rural = int(rural["populacao"].sum()) if n_rural and "populacao" in rural.columns else 0
    n_prox = int(len(prox))

    partes_msg: list[str] = []
    if n_set:
        partes_msg.append(
            f"{n_set} setores do eixo Manso–Cuiabá "
            f"({pop_eixo:,} hab.; {n_rural} rurais / {pop_rural:,} hab.)".replace(",", ".")
        )
    if n_prox:
        partes_msg.append(
            f"{n_prox} elemento(s) vulnerável(is) a ≤5 km do eixo "
            "(aldeias, assentamentos, quilombos — não saúde)"
        )
    msg = (
        "Proxy operacional (não cadastro ribeirinho): "
        + "; ".join(partes_msg)
        + ". Cruzar com microáreas da APS / Defesa Civil local."
    )

    return {
        "disponivel": True,
        "tipo": "proxy_setores_eixo",
        "n_setores_eixo": n_set,
        "populacao_eixo": pop_eixo,
        "n_setores_rural_eixo": n_rural,
        "populacao_rural_eixo": pop_rural,
        "n_elementos_proximos_5km": n_prox,
        "elementos_proximos": prox,
        "mensagem": msg,
        "aviso": (
            "Não há delimitação oficial de população ribeirinha comparável a "
            "FUNAI/INCRA. Os números abaixo são população em setores do eixo "
            "hidrográfico e exposição próxima — alvo para busca ativa, não contagem "
            "de comunidade ribeirinha."
        ),
        "fonte": (
            "IBGE Censo 2022 (setores_censitarios_eixo_cuiaba.csv) + "
            "exposicao_populacoes_eixo_cuiaba.csv (≤5 km)"
        ),
    }


# Papéis mínimos para despacho institucional (SES / CIEVS / Vigidesastres / DC).
PAPEIS_ALERTA_CRITICOS = (
    "gestor_municipal_saude",
    "vigilancia_saude",
    "defesa_civil_municipal",
    "cievs",
)


def resumo_contatos_municipio(municipio: str) -> dict[str, Any]:
    """Cobertura de contatos SES/CIEVS/Defesa Civil no município (piloto)."""
    from datetime import date, datetime

    from st_app.indicadores import carregar_contatos

    mun = (municipio or "").strip()
    ct = carregar_contatos()
    vazio = {
        "disponivel": False,
        "n_total": 0,
        "n_com_telefone": 0,
        "n_com_email": 0,
        "n_validados_90d": 0,
        "n_criticos": len(PAPEIS_ALERTA_CRITICOS),
        "n_criticos_com_fone": 0,
        "papeis_criticos_faltando": list(PAPEIS_ALERTA_CRITICOS),
        "alertavel": False,
        "tabela": pd.DataFrame(),
        "fonte": "contatos_institucionais_piloto.csv",
    }
    if not mun or ct.empty or "municipio" not in ct.columns:
        return vazio

    hit = ct[ct["municipio"].apply(lambda m: nomes_equivalentes(mun, m))].copy()
    if hit.empty:
        return vazio

    def _tem_fone(row: pd.Series) -> bool:
        dig = "".join(
            c
            for c in f"{row.get('telefone') or ''}{row.get('celular') or ''}"
            if c.isdigit()
        )
        return len(dig) >= 8

    def _tem_email(row: pd.Series) -> bool:
        return "@" in str(row.get("email") or "")

    def _validado_90d(raw: object) -> bool:
        s = str(raw or "").strip()[:10]
        if len(s) < 10:
            return False
        try:
            dt = datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return False
        return (date.today() - dt).days <= 90

    hit["_fone"] = hit.apply(_tem_fone, axis=1)
    hit["_email"] = hit.apply(_tem_email, axis=1)
    hit["_val90"] = hit["data_validacao"].apply(_validado_90d) if "data_validacao" in hit.columns else False

    crit = hit[hit["papel"].isin(PAPEIS_ALERTA_CRITICOS)] if "papel" in hit.columns else hit.iloc[0:0]
    papeis_ok = set(crit.loc[crit["_fone"], "papel"].astype(str)) if not crit.empty else set()
    faltando = [p for p in PAPEIS_ALERTA_CRITICOS if p not in papeis_ok]

    cols_show = [
        c
        for c in (
            "papel_rotulo",
            "papel",
            "nome",
            "telefone",
            "celular",
            "email",
            "data_validacao",
            "fonte",
        )
        if c in hit.columns
    ]
    tab = hit[cols_show].copy() if cols_show else hit.copy()
    if "papel" in tab.columns:
        ordem = {p: i for i, p in enumerate(PAPEIS_ALERTA_CRITICOS)}
        tab["_ord"] = tab["papel"].map(lambda p: ordem.get(str(p), 99))
        tab = tab.sort_values("_ord").drop(columns=["_ord"])

    return {
        "disponivel": True,
        "n_total": len(hit),
        "n_com_telefone": int(hit["_fone"].sum()),
        "n_com_email": int(hit["_email"].sum()),
        "n_validados_90d": int(hit["_val90"].sum()),
        "n_criticos": len(PAPEIS_ALERTA_CRITICOS),
        "n_criticos_com_fone": len(papeis_ok),
        "papeis_criticos_faltando": faltando,
        "alertavel": len(faltando) == 0 and int(hit["_val90"].sum()) > 0,
        "tabela": tab.reset_index(drop=True),
        "fonte": "contatos_institucionais_piloto.csv",
    }


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
        "ribeirinhos": proxy_ribeirinhos_municipio(mun),
        "contatos": resumo_contatos_municipio(mun),
        "fontes": {
            "barragens": "SNISB/IDAP + Otto (sede ou jusante)",
            "populacao": "IBGE (ibge_populacao_municipios_mt.csv)",
            "indigenas": "FUNAI terras indígenas e aldeias",
            "assentamentos": "INCRA assentamentos",
            "quilombolas": "Fundação Palmares + INCRA (quando houver)",
            "saude": "CNES estabelecimentos",
            "ribeirinhos": (
                "Proxy setores do eixo Manso–Cuiabá (IBGE 2022) + exposição ≤5 km; "
                "sem cadastro estadual de comunidade ribeirinha"
            ),
            "contatos": (
                "Papéis SES/CIEVS/Vigilância/Defesa Civil em "
                "contatos_institucionais_piloto.csv (validação ≤90 dias)"
            ),
            "acao": (
                "Fila gerada a partir de IDAP, PAE checklist, vulneráveis, "
                "ficha rápida e contatos"
            ),
        },
    }


def _taxa_ocupacao_municipio(municipio: str) -> float | None:
    """Taxa de ocupação IndicaSUS municipal (0–100), se existir."""
    from st_app.leitos_indicasus import carregar_leitos_municipio

    df = carregar_leitos_municipio()
    if df.empty or "municipio" not in df.columns or "taxa_ocupacao" not in df.columns:
        return None
    hit = df[df["municipio"].apply(lambda m: nomes_equivalentes(municipio, m))]
    if hit.empty:
        return None
    try:
        v = float(hit.iloc[0]["taxa_ocupacao"])
        # DW às vezes grava 0–1
        return v * 100.0 if v <= 1.5 else v
    except (TypeError, ValueError):
        return None


def pressao_assistencial_localidade(municipio: str, dossie: dict[str, Any] | None = None) -> dict[str, Any]:
    """IPAPD proxy no recorte municipal — A/P/C via ficha do município quando houver."""
    from st_app.ficha_rapida import carregar_ficha_municipio, termos_ipapd_da_ficha
    from st_app.ipapd import calcular_ipapd_proxy

    dossie = dossie or {}
    ficha = carregar_ficha_municipio(municipio)
    termos = termos_ipapd_da_ficha(ficha)
    taxa = _taxa_ocupacao_municipio(municipio)
    rib = dossie.get("ribeirinhos") or {}
    pop_proxy = rib.get("populacao_eixo") if rib.get("disponivel") else None
    if pop_proxy is None:
        pop_proxy = (dossie.get("populacao") or {}).get("populacao")

    ipapd = calcular_ipapd_proxy(
        taxa_ocupacao_pct=taxa,
        n_us_atingidas=int(dossie.get("n_cnes") or 0),
        n_us_isoladas=0,
        pessoas_isoladas=0,
        pop_exposta=pop_proxy,
        n_servicos_essenciais_mancha=0,
        n_servicos_essenciais_eixo=0,
        ficha_termos=termos or None,
    )
    ipapd["ficha"] = {
        "encontrada": ficha is not None,
        "arquivo": (ficha or {}).get("_arquivo"),
        "municipio_ficha": (ficha or {}).get("municipio"),
        "tipo": (ficha or {}).get("tipo"),
        "status": (ficha or {}).get("status"),
    }
    return ipapd


def fila_acao_localidade(dossie: dict[str, Any]) -> list[dict[str, str]]:
    """Prioriza o que o gestor municipal deve olhar agora (máx. ~8 itens)."""
    mun = str(dossie.get("municipio") or "")
    bars = dossie.get("barragens")
    if not isinstance(bars, pd.DataFrame):
        bars = pd.DataFrame()
    acoes: list[dict[str, str]] = []

    niveis_aten = {"Amarelo", "Laranja", "Vermelho", "Roxo"}
    n_aten = 0
    if not bars.empty and "nivel" in bars.columns:
        n_aten = int(bars["nivel"].isin(niveis_aten).sum())
    if n_aten > 0:
        acoes.append(
            {
                "prioridade": "1",
                "tema": "Prontidão IDAP",
                "acao": (
                    f"Revisar {n_aten} barragem(ns) Em atenção+ vinculadas a {mun} "
                    "(sede ou jusante) — abrir Detalhe da barragem / Simulação."
                ),
            }
        )

    # PAE lacunas no recorte
    pae = ler_csv("pae_checklist_lacunas.csv")
    n_pae_crit = 0
    if not pae.empty and not bars.empty and "id_snisb" in bars.columns:
        ids = set(bars["id_snisb"].astype(str).str.strip())
        sub = pae[pae["id_snisb"].astype(str).str.strip().isin(ids)]
        if "n_lacunas_criticas" in sub.columns:
            n_pae_crit = int(pd.to_numeric(sub["n_lacunas_criticas"], errors="coerce").fillna(0).sum())
        elif "n_lacuna" in sub.columns:
            n_pae_crit = int(pd.to_numeric(sub["n_lacuna"], errors="coerce").fillna(0).gt(0).sum())
    if n_pae_crit > 0:
        acoes.append(
            {
                "prioridade": "2",
                "tema": "PAE / documentação",
                "acao": (
                    f"Há lacunas críticas de PAE/PAEBM no recorte (soma={n_pae_crit}). "
                    "Cobrar empreendedor/SEMA e registrar checklist na Simulação."
                ),
            }
        )

    if dossie.get("n_jusante", 0) > 0:
        sedes = dossie.get("sedes_montante") or []
        extra = f" Sedes a montante: {', '.join(sedes[:5])}." if sedes else ""
        acoes.append(
            {
                "prioridade": "2",
                "tema": "Impacto a jusante",
                "acao": (
                    f"{dossie['n_jusante']} estrutura(s) fora da sede podem atingir {mun} (Otto)."
                    f"{extra} Usar mapa de impacto em outras localidades."
                ),
            }
        )

    n_vuln = 0
    for key in ("terras_indigenas", "aldeias", "assentamentos", "quilombolas_palmares"):
        bloco = dossie.get(key)
        if isinstance(bloco, pd.DataFrame):
            n_vuln += len(bloco)
        elif isinstance(bloco, (list, tuple)):
            n_vuln += len(bloco)
    if n_vuln > 0:
        acoes.append(
            {
                "prioridade": "3",
                "tema": "Povos e comunidades",
                "acao": (
                    f"{n_vuln} registro(s) FUNAI/INCRA/Palmares no município — "
                    "incluir na comunicação de risco e na ficha rápida."
                ),
            }
        )

    rib = dossie.get("ribeirinhos") or {}
    if rib.get("disponivel") and int(rib.get("populacao_rural_eixo") or 0) > 0:
        acoes.append(
            {
                "prioridade": "3",
                "tema": "Ribeirinhos (proxy)",
                "acao": (
                    f"Proxy: ~{int(rib['populacao_rural_eixo']):,} hab. em setores rurais do eixo "
                    f"({rib.get('n_setores_rural_eixo') or 0} setores). "
                    "Priorizar APS de beira d’água — não é cadastro oficial."
                ).replace(",", "."),
            }
        )
    elif not rib.get("disponivel"):
        acoes.append(
            {
                "prioridade": "4",
                "tema": "Ribeirinhos",
                "acao": (
                    "Sem proxy de eixo neste município. Solicitar cadastro SES/Defesa Civil "
                    "de comunidades ribeirinhas."
                ),
            }
        )

    from st_app.ficha_rapida import carregar_ficha_municipio

    ficha = carregar_ficha_municipio(mun)
    if ficha is None:
        acoes.append(
            {
                "prioridade": "3",
                "tema": "Ficha rápida / IPAPD",
                "acao": (
                    "Sem ficha rápida para este município — A/P/C do IPAPD ficam lacuna. "
                    "Preencher `painel/ficha_rapida.html` e salvar em "
                    "`dados/tratados/fichas_rapidas/`."
                ),
            }
        )
    else:
        acoes.append(
            {
                "prioridade": "3",
                "tema": "Ficha rápida / IPAPD",
                "acao": (
                    f"Ficha `{ficha.get('_arquivo')}` encontrada "
                    f"({ficha.get('tipo') or '—'} / {ficha.get('status') or '—'}). "
                    "Conferir decomposição IPAPD abaixo."
                ),
            }
        )

    if dossie.get("n_cnes_prioritarios", 0) == 0 and dossie.get("n_cnes", 0) == 0:
        acoes.append(
            {
                "prioridade": "4",
                "tema": "Rede CNES",
                "acao": "Nenhuma US georreferenciada no recorte — validar município no CNES estadual.",
            }
        )

    cont = dossie.get("contatos") or {}
    if not cont.get("disponivel"):
        acoes.append(
            {
                "prioridade": "2",
                "tema": "Contatos / alertabilidade",
                "acao": (
                    f"Sem cadastro de contatos para {mun}. Incluir papéis SES, CIEVS, "
                    "Vigilância e Defesa Civil em contatos_institucionais_piloto.csv."
                ),
            }
        )
    else:
        faltam = cont.get("papeis_criticos_faltando") or []
        n_ok = int(cont.get("n_criticos_com_fone") or 0)
        n_crit = int(cont.get("n_criticos") or 4)
        if faltam:
            rotulos = {
                "gestor_municipal_saude": "gestor saúde",
                "vigilancia_saude": "vigilância",
                "defesa_civil_municipal": "Defesa Civil",
                "cievs": "CIEVS",
            }
            nomes = ", ".join(rotulos.get(p, p) for p in faltam)
            acoes.append(
                {
                    "prioridade": "2",
                    "tema": "Contatos / alertabilidade",
                    "acao": (
                        f"Papéis críticos com telefone: {n_ok}/{n_crit}. "
                        f"Completar e validar: {nomes}. "
                        "Abrir Alertabilidade / despacho."
                    ),
                }
            )
        elif int(cont.get("n_validados_90d") or 0) == 0:
            acoes.append(
                {
                    "prioridade": "3",
                    "tema": "Contatos / alertabilidade",
                    "acao": (
                        "Há telefones, mas nenhum contato validado nos últimos 90 dias. "
                        "Revalidar SES/CIEVS/Defesa Civil."
                    ),
                }
            )

    # Ordena por prioridade numérica
    acoes.sort(key=lambda a: int(a.get("prioridade") or 9))
    return acoes[:8]


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
