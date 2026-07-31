"""VIGIBARRAGENS–MT — painel operacional em Streamlit.

Executar local:
  streamlit run streamlit_app.py

Cloud: apontar o arquivo principal para barragens-mt/streamlit_app.py
(ou usar o atalho na raiz do repositório).
"""

from __future__ import annotations

import math
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from st_app.data import (
    CORES_NIVEL,
    TIPOLOGIA_CORES,
    card_kpi,
    carregar_cnes_pontos,
    com_tipologia,
    carregar_hidro_mun,
    carregar_idap,
    carregar_piloto,
    carregar_populacao,
    cnes_no_buffer,
    estimar_pop_cenario,
    filtrar_municipio,
    municipios_catalogo,
    projecao_semana,
    severidade_pct,
    tendencia_climatica_texto,
    tendencias_estado,
)
from st_app.mapa_sim import html_mapa_simulacao
from st_app.vias_isolamento import analisar_isolamento_json
from st_app.paginas_onda import (
    aplicar_navegacao_pendente,
    bloco_atalhos_comando,
    bloco_frescor,
    bloco_quase_atencao,
    bloco_sanitario_compacto,
    bloco_sitrep_downloads,
    bloco_tipologia,
    faixa_titulo,
    pagina_alertabilidade_despacho,
    pagina_confirmacao_persistente,
    pagina_extraterritorial,
    pagina_municipio_360,
    pagina_rag_docs,
    pagina_regiao_saude,
    pagina_vulneraveis,
    tendencia_unificada,
)
from st_app.style import CSS

JORNADAS: dict[str, list[str]] = {
    "Situação": [
        "Comando estadual",
        "Simulação de cenário",
        "Hidro municipal",
        "Eixo Manso–Cuiabá",
    ],
    "Território": [
        "Populações vulneráveis",
        "Impacto extraterritorial",
        "Mapa por tipologia",
        "Barragem 360°",
    ],
    "Ação": [
        "Simulação de cenário",
        "Alertabilidade / despacho",
        "Fila de alertas",
        "Confirmação persistente",
        "Ficha rápida",
    ],
    "Dados e apoio": [
        "Interpretação / KPIs",
        "Região de saúde",
        "Documentos (RAG leve)",
        "Inventário",
        "Confirmação (HTML)",
        "Comando (HTML)",
    ],
}

# Nome canônico da tela (aparece em Situação e Ação).
TELA_SIMULACAO = "Simulação de cenário"

st.set_page_config(
    page_title="VIGIBARRAGENS–MT",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def _isolamento_cached(
    lat0: float,
    lon0: float,
    raio0: float,
    cnes_key: str,
    corredor_key: str = "",
    sedes_key: str = "",
    uniao_circular: bool = False,
) -> dict:
    return analisar_isolamento_json(
        lat0, lon0, raio0, cnes_key, corredor_key, sedes_key, uniao_circular
    )


def _badge(nivel: str) -> str:
    cor = CORES_NIVEL.get(nivel, "#888")
    claro = " claro" if nivel == "Amarelo" else ""
    return f'<span class="badge{claro}" style="background:{cor}">{nivel}</span>'


def _semaforo(df: pd.DataFrame) -> str:
    ordem = ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"]
    for n in ordem:
        if (df["nivel"] == n).any():
            return n
    return "Verde"


def pagina_comando(df: pd.DataFrame) -> None:
    st.markdown("# VIGIBARRAGENS–MT")
    st.markdown(
        '<p class="nota">Comando estadual — <b>como está Mato Grosso agora</b> e '
        "onde olhar primeiro. Linguagem operacional (sem siglas na 1ª leitura).</p>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.error("Base de alerta ausente. Rode `python executar.py 16 17` no projeto.")
        return

    munis = municipios_catalogo(df)
    from st_app.indicadores import carregar_contatos
    from st_app.data import carregar_historico_indice

    contatos = carregar_contatos()
    regioes = (
        sorted(contatos["regiao_saude"].dropna().unique().tolist())
        if not contatos.empty and "regiao_saude" in contatos.columns
        else []
    )
    munis_por_regiao: dict[str, set[str]] = {}
    if regioes and "municipio" in contatos.columns:
        for _, row in contatos.dropna(subset=["regiao_saude", "municipio"]).iterrows():
            munis_por_regiao.setdefault(str(row["regiao_saude"]), set()).add(
                str(row["municipio"]).strip()
            )

    with st.sidebar:
        st.header("Filtros do comando")
        mun_sel = st.selectbox(
            "Município",
            ["(estado todo)"] + munis,
            help="Sede ou potencialmente afetado a jusante.",
        )
        reg_sel = st.selectbox(
            "Região de saúde",
            ["(todas)"] + regioes,
            help="Cadastro de contatos do eixo (expansão estadual pendente).",
            disabled=not regioes,
        )
        niveis = st.multiselect(
            "Nível de prontidão",
            ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"],
            default=["Roxo", "Vermelho", "Laranja", "Amarelo"],
        )
        so_piloto = st.checkbox("Só eixo Manso–Cuiabá", value=False)
        busca = st.text_input("Busca (nome ou código)", "")
        orgao = st.text_input("Órgão fiscalizador", "")

    view = df.copy()
    mun_ativo = None if mun_sel == "(estado todo)" else mun_sel
    if mun_ativo:
        view = filtrar_municipio(view, mun_ativo)
        st.markdown(
            f'<p class="nota"><b>Recorte: {mun_ativo}</b> — sede <b>ou</b> jusante '
            "(a barragem pode estar em outro município).</p>",
            unsafe_allow_html=True,
        )
    elif reg_sel != "(todas)" and reg_sel in munis_por_regiao:
        alvos = munis_por_regiao[reg_sel]
        mask = (
            view["municipio_sede"].isin(alvos)
            if "municipio_sede" in view.columns
            else pd.Series(False, index=view.index)
        )
        if "municipios_potencialmente_afetados" in view.columns:
            mask = mask | view["municipios_potencialmente_afetados"].fillna("").apply(
                lambda t: any(m in str(t).split("|") for m in alvos)
            )
        view = view.loc[mask].copy()
        st.markdown(
            f'<p class="nota"><b>Região de saúde: {reg_sel}</b> — '
            f"{len(alvos)} município(s) no cadastro.</p>",
            unsafe_allow_html=True,
        )
    if niveis:
        view = view[view["nivel"].isin(niveis)]
    if so_piloto and "piloto" in view.columns:
        view = view[view["piloto"]]
    if busca:
        q = busca.lower()
        view = view[
            view["nome"].fillna("").str.lower().str.contains(q)
            | view["id_snisb"].fillna("").str.contains(q)
        ]
    if orgao and "orgao_fiscalizador" in view.columns:
        view = view[view["orgao_fiscalizador"].fillna("").str.contains(orgao, case=False)]

    if view.empty:
        st.warning("Nenhuma barragem no recorte. Amplie níveis ou limpe o município.")
        return

    base_kpi = view
    sem = _semaforo(base_kpi)
    cont = base_kpi["nivel"].value_counts()
    amarelo_mais = int(
        cont.get("Amarelo", 0)
        + cont.get("Laranja", 0)
        + cont.get("Vermelho", 0)
        + cont.get("Roxo", 0)
    )
    tend = (
        tendencias_estado()
        if not mun_ativo
        else {"amarelo_mais": None, "amarelo": None, "verde": None}
    )
    piloto_n = int(base_kpi["piloto"].sum()) if "piloto" in base_kpi.columns else 0
    piloto_ama = (
        int(
            base_kpi.loc[
                base_kpi["piloto"]
                & base_kpi["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"])
            ].shape[0]
        )
        if "piloto" in base_kpi.columns
        else 0
    )
    alertaveis = (
        (base_kpi.get("alertavel") == "sim").sum() if "alertavel" in base_kpi.columns else 0
    )
    pct_atencao = 100.0 * amarelo_mais / max(len(base_kpi), 1)

    def _delta(v):
        if v is None:
            return None
        seta = "▲" if v > 0 else "▼" if v < 0 else "→"
        return f"{seta} {v:+d} vs rodada anterior"

    # —— Faixa 1: Agora ——
    faixa_titulo("1", "Agora", "Prontidão do recorte e tendência que manda na decisão")
    st.markdown(
        f"**Prontidão:** {_badge(sem)} — {len(base_kpi)} barragens no recorte",
        unsafe_allow_html=True,
    )
    # O total do recorte já está na linha de prontidão — aqui só o que decide.
    cards = [
        card_kpi(
            "Em atenção ou pior",
            str(amarelo_mais),
            sev=severidade_pct(pct_atencao),
            delta=_delta(tend.get("amarelo_mais")),
            nota=f"{pct_atencao:.0f}% do recorte",
        ),
        card_kpi(
            "Situação estável (verde)",
            str(int(cont.get("Verde", 0))),
            sev="sev-ok",
            delta=_delta(tend.get("verde")),
        ),
        card_kpi(
            "Com canal de alerta",
            str(int(alertaveis)),
            sev="sev-ok" if alertaveis else "sev-atencao",
        ),
        card_kpi(
            "Eixo Manso–Cuiabá",
            str(piloto_n),
            sev="sev-neutro",
            nota=f"{piloto_ama} em atenção+",
        ),
    ]
    st.markdown('<div class="grade-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    # Distribuição por faixa em uma linha (evita 4 cards para o mesmo recorte).
    dist = [
        f'<span class="dist-item"><i style="background:{CORES_NIVEL[n]}"></i>{n} '
        f"<b>{int(cont.get(n, 0))}</b></span>"
        for n in ("Amarelo", "Laranja", "Vermelho", "Roxo")
    ]
    if "n_municipios_extraterritoriais" in base_kpi.columns:
        n_ext = int(
            (pd.to_numeric(base_kpi["n_municipios_extraterritoriais"], errors="coerce").fillna(0) > 0).sum()
        )
        dist.append(
            '<span class="dist-item"><i style="background:#1b3281"></i>'
            f"Impacto fora da sede <b>{n_ext}</b></span>"
        )
    st.markdown('<div class="dist">' + "".join(dist) + "</div>", unsafe_allow_html=True)

    sev_u, msg_u = tendencia_unificada(base_kpi)
    st.markdown(f'<div class="tend-box {sev_u}">{msg_u}</div>', unsafe_allow_html=True)
    bloco_frescor()
    bloco_sitrep_downloads(base_kpi, mun_ativo=mun_ativo)

    # —— Faixa 2: Pessoas e resposta ——
    faixa_titulo("2", "Pessoas e resposta", "Exposição sanitária e capacidade assistencial sob pressão")
    bloco_sanitario_compacto(base_kpi)

    # —— Faixa 3: Onde olhar ——
    faixa_titulo("3", "Onde olhar", "Mapa, Top 15, vigília (quase atenção) e tipologia")
    if mun_ativo:
        pagina_municipio_360(base_kpi, mun_ativo, incluir_sanitario=False)
    view = view.sort_values("idap_n", ascending=False)
    col_mapa, col_listas = st.columns([1.25, 1])
    with col_mapa:
        st.markdown("##### Mapa por faixa de prontidão")
        pts = view.dropna(subset=["latitude", "longitude"])
        if pts.empty:
            st.info("Sem coordenadas no recorte filtrado.")
        else:
            m = folium.Map(location=[-13.0, -55.8], zoom_start=5, tiles="CartoDB positron")
            for _, r in pts.iterrows():
                cor = CORES_NIVEL.get(r["nivel"], "#888")
                critico = r["nivel"] != "Verde"
                papel = r.get("papel_municipio") or ""
                folium.CircleMarker(
                    location=[r["latitude"], r["longitude"]],
                    radius=9 if critico else 4,
                    color="#111" if critico else "#555",
                    weight=2 if critico else 0.5,
                    fill=True,
                    fill_color=cor,
                    fill_opacity=0.9 if critico else 0.55,
                    popup=folium.Popup(
                        f"<b>{r['nome']}</b><br>Índice {r.get('idap','—')} — {r['nivel']}<br>"
                        f"Sede: {r.get('municipio_sede','—')}<br>"
                        + (f"{papel}<br>" if papel else "")
                        + f"Chuva 24/72h: {r.get('chuva_24h_mm','—')} / {r.get('chuva_72h_mm','—')} mm<br>"
                        f"Prevista: {r.get('chuva_prevista_24_72h_mm','—')} mm",
                        max_width=320,
                    ),
                ).add_to(m)
            if len(pts) <= 80:
                sw = [pts["latitude"].min(), pts["longitude"].min()]
                ne = [pts["latitude"].max(), pts["longitude"].max()]
                m.fit_bounds([sw, ne], padding=(30, 30))
            st_folium(m, width=None, height=480, returned_objects=[])

    with col_listas:
        st.markdown("##### Top 15 — olhar primeiro")
        cols_top = [
            c
            for c in (
                "idap",
                "nivel",
                "nome",
                "municipio_sede",
                "papel_municipio",
                "pontos_a",
                "chuva_prevista_24_72h_mm",
                "alertavel",
                "completude",
            )
            if c in view.columns
        ]
        top = view.head(15)[cols_top].rename(
            columns={
                "idap": "Índice",
                "nivel": "Prontidão",
                "nome": "Barragem",
                "municipio_sede": "Sede",
                "papel_municipio": "Papel",
                "pontos_a": "Pressão clima",
                "chuva_prevista_24_72h_mm": "Chuva prevista",
                "alertavel": "Alertável",
                "completude": "Completude",
            }
        )
        st.caption("Completude baixa = risco de falso verde.")
        st.dataframe(top, width="stretch", hide_index=True, height=240)
        bloco_quase_atencao(base_kpi, altura=200)

    bloco_tipologia(
        base_kpi,
        df,
        rotulo_recorte=mun_ativo or ("eixo Manso–Cuiabá" if so_piloto else "recorte atual"),
    )

    bloco_atalhos_comando(so_piloto=so_piloto)

    # —— Faixa 4: Fila e clima ——
    faixa_titulo("4", "Fila e clima", "Detalhe operacional — abrir só quando precisar aprofundar")

    with st.expander("Pressão climática e regras (dimensões A–D + hidro)", expanded=False):
        idap_max = float(base_kpi["idap_n"].max()) if "idap_n" in base_kpi.columns else 0
        idap_med = float(base_kpi["idap_n"].mean()) if "idap_n" in base_kpi.columns else 0
        a_med = float(base_kpi["pontos_a"].mean()) if "pontos_a" in base_kpi.columns else 0
        b_med = float(base_kpi["pontos_b"].mean()) if "pontos_b" in base_kpi.columns else 0
        c_med = float(base_kpi["pontos_c"].mean()) if "pontos_c" in base_kpi.columns else 0
        d_med = float(base_kpi["pontos_d"].mean()) if "pontos_d" in base_kpi.columns else 0
        a_pct = 100.0 * a_med / 30.0
        b_pct = 100.0 * b_med / 30.0
        c_pct = 100.0 * c_med / 25.0
        d_pct = 100.0 * d_med / 15.0
        pressao_a = (
            int((base_kpi.get("pontos_a", 0) > 0).sum()) if "pontos_a" in base_kpi.columns else 0
        )
        chuva24 = (
            float(base_kpi["chuva_24h_mm"].max()) if "chuva_24h_mm" in base_kpi.columns else None
        )
        chuva72 = (
            float(base_kpi["chuva_72h_mm"].max()) if "chuva_72h_mm" in base_kpi.columns else None
        )
        prev = (
            float(base_kpi["chuva_prevista_24_72h_mm"].max())
            if "chuva_prevista_24_72h_mm" in base_kpi.columns
            else None
        )
        cem = 0
        if "alerta_cemaden_nivel" in base_kpi.columns:
            cem = int(
                base_kpi["alerta_cemaden_nivel"]
                .fillna("")
                .str.lower()
                .isin(["laranja", "vermelha", "vermelho", "roxa", "roxo", "moderado", "alto"])
                .sum()
            )
        regras = base_kpi.get("regras_disparadas", pd.Series(dtype=str)).fillna("")
        n_regras = int(regras.str.contains(r"R1[012]").sum())
        cri_alto = (
            int(base_kpi["categoria_risco"].fillna("").str.lower().eq("alto").sum())
            if "categoria_risco" in base_kpi.columns
            else 0
        )
        dpa_alto = (
            int(base_kpi["dano_potencial_associado"].fillna("").str.lower().eq("alto").sum())
            if "dano_potencial_associado" in base_kpi.columns
            else 0
        )

        def _mm(v):
            return "—" if v is None else f"{v:.1f} mm".replace(".", ",")

        risco_cards = [
            card_kpi("Índice máximo", f"{idap_max:.0f}", sev=severidade_pct(idap_max)),
            card_kpi("Índice médio", f"{idap_med:.1f}".replace(".", ","), sev=severidade_pct(idap_med)),
            card_kpi("Pressão climática", f"{a_pct:.0f}%", sev=severidade_pct(a_pct)),
            card_kpi("Estrutura", f"{b_pct:.0f}%", sev=severidade_pct(b_pct)),
            card_kpi("Impacto sanitário", f"{c_pct:.0f}%", sev=severidade_pct(c_pct)),
            card_kpi("Déficit resposta", f"{d_pct:.0f}%", sev=severidade_pct(d_pct)),
            card_kpi("Com pressão A", str(pressao_a), sev=severidade_pct(100.0 * pressao_a / max(len(base_kpi), 1))),
            card_kpi("Chuva 24 h máx.", _mm(chuva24), sev=severidade_pct(None if chuva24 is None else min(100, chuva24))),
            card_kpi("Chuva 72 h máx.", _mm(chuva72), sev=severidade_pct(None if chuva72 is None else min(100, chuva72 * 0.5))),
            card_kpi(
                "Chuva prevista",
                _mm(prev),
                sev=severidade_pct(
                    None
                    if prev is None
                    else (100 if prev >= 140 else 70 if prev >= 80 else 40 if prev >= 40 else 10)
                ),
            ),
            card_kpi("Alertas oficiais", str(cem), sev="sev-alto" if cem else "sev-ok"),
            card_kpi("Regras R10–R12", str(n_regras), sev="sev-elevado" if n_regras else "sev-ok"),
            card_kpi("CRI alto", str(cri_alto), sev="sev-alto" if cri_alto else "sev-ok"),
            card_kpi("DPA alto", str(dpa_alto), sev="sev-alto" if dpa_alto else "sev-ok"),
        ]
        st.markdown('<div class="grade-kpis">' + "".join(risco_cards) + "</div>", unsafe_allow_html=True)

    st.markdown(f"##### Fila operacional ({len(view)})")
    cols = [
        c
        for c in (
            "idap",
            "nivel",
            "nome",
            "municipio_sede",
            "papel_municipio",
            "municipios_potencialmente_afetados",
            "orgao_fiscalizador",
            "pontos_a",
            "pontos_b",
            "pontos_c",
            "pontos_d",
            "chuva_72h_mm",
            "chuva_prevista_24_72h_mm",
            "alerta_cemaden_nivel",
            "alertavel",
        )
        if c in view.columns
    ]
    st.dataframe(
        view[cols].rename(
            columns={
                "idap": "Índice",
                "nivel": "Prontidão",
                "nome": "Barragem",
                "municipio_sede": "Sede",
                "papel_municipio": "Papel no município filtrado",
                "municipios_potencialmente_afetados": "Municípios potencialmente afetados",
                "orgao_fiscalizador": "Órgão",
                "pontos_a": "Pressão clima",
                "pontos_b": "Estrutura",
                "pontos_c": "Impacto sanitário",
                "pontos_d": "Déficit resposta",
                "chuva_72h_mm": "Chuva 72h",
                "chuva_prevista_24_72h_mm": "Chuva prevista",
                "alerta_cemaden_nivel": "Alerta oficial",
                "alertavel": "Alertável",
            }
        ),
        width="stretch",
        hide_index=True,
        height=360,
    )

    with st.expander("Histórico de snapshots do índice", expanded=False):
        hist = carregar_historico_indice()
        if hist.empty:
            st.caption("Sem snapshots — rode a etapa 16 mais de uma vez.")
        else:
            st.dataframe(hist.tail(12), width="stretch", hide_index=True)


def pagina_hidro(hidro: pd.DataFrame, pop: pd.DataFrame) -> None:
    st.markdown("# Hidrometeorologia municipal")
    st.markdown(
        '<p class="nota">SisClima/TITAN + previsão ECMWF (Copernicus/C3S) + amostra GloFAS.</p>',
        unsafe_allow_html=True,
    )
    if hidro.empty:
        st.error("Base hidro municipal ausente. Rode a etapa 17.")
        return
    metrica = st.selectbox(
        "Indicador no ranking",
        [
            "chuva_24h_mm",
            "chuva_72h_mm",
            "chuva_prevista_24_72h_mm",
            "percentil_climatologico",
            "indice_saturacao_solo",
        ],
        format_func=lambda x: {
            "chuva_24h_mm": "Chuva 24 h (mm)",
            "chuva_72h_mm": "Chuva 72 h (mm)",
            "chuva_prevista_24_72h_mm": "Chuva prevista 24–72 h (mm)",
            "percentil_climatologico": "Percentil espacial",
            "indice_saturacao_solo": "Saturação do solo",
        }[x],
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Municípios", len(hidro))
    c2.metric("Máx. chuva 24 h", f"{hidro['chuva_24h_mm'].max():.1f} mm" if "chuva_24h_mm" in hidro else "—")
    c3.metric(
        "Máx. prevista 72 h",
        f"{hidro['chuva_prevista_24_72h_mm'].max():.1f} mm"
        if "chuva_prevista_24_72h_mm" in hidro
        else "—",
    )
    ordenado = hidro.sort_values(metrica, ascending=False, na_position="last")
    st.bar_chart(ordenado.set_index("municipio")[metrica].head(25), height=360)
    mostrar = ordenado.copy()
    if not pop.empty:
        mostrar = mostrar.merge(pop[["municipio", "populacao"]], on="municipio", how="left")
    st.dataframe(mostrar, width="stretch", hide_index=True, height=400)


def pagina_piloto(piloto: pd.DataFrame) -> None:
    st.markdown("# Eixo Manso–Cuiabá")
    st.markdown(
        '<p class="nota">Recorte operacional do eixo que pode afetar Cuiabá / Várzea Grande '
        "(antes chamado «piloto»).</p>",
        unsafe_allow_html=True,
    )
    if piloto.empty:
        st.error("Piloto ausente. Rode a etapa 18.")
        return
    cont = piloto["nivel"].value_counts()
    cols = st.columns(5)
    for i, n in enumerate(["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"]):
        cols[i].metric(n, int(cont.get(n, 0)))
    st.dataframe(
        piloto.sort_values("idap_n", ascending=False),
        width="stretch",
        hide_index=True,
        height=480,
    )


def _fmt_br(valor: float, casas: int = 1, sufixo: str = "") -> str:
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto}{sufixo}"


def pagina_simulacao(df: pd.DataFrame) -> None:
    st.markdown("# Simulação de cenário")
    st.markdown(
        '<p class="nota">Proxy para <b>qualquer barragem</b> do inventário — '
        "<b>não</b> é mancha oficial nem ordem de evacuação. "
        "O <b>círculo</b> (volume→área) funciona em todo o MT; o "
        "<b>trajeto hidráulico</b> (corredor jusante) quando há calha BHO/eixo. "
        "No mapa: US CNES, rodovias e pontes OSM dentro da área.</p>",
        unsafe_allow_html=True,
    )
    base = df.dropna(subset=["capacidade_hm3"]).copy()
    base = base[base["capacidade_hm3"] > 0]
    if base.empty:
        st.warning("Sem volumes no inventário.")
        return
    recorte = st.radio(
        "Recorte",
        ["Todas com volume", "Top 40 volumes", "Eixo Manso–Cuiabá"],
        horizontal=True,
        help="Padrão: todas as barragens com volume no inventário estadual.",
    )
    if recorte == "Eixo Manso–Cuiabá":
        base = base[base.get("piloto", False) == True]  # noqa: E712
    elif recorte == "Top 40 volumes":
        base = base.sort_values("capacidade_hm3", ascending=False).head(40)
    filtro_mun = st.text_input(
        "Filtrar por município (opcional)",
        "",
        placeholder="ex.: Cuiabá, Rondonópolis, Sinop…",
    ).strip()
    if filtro_mun:
        col_sede = (
            base["municipio_sede"]
            if "municipio_sede" in base.columns
            else pd.Series("", index=base.index)
        )
        col_mun = (
            base["municipio"]
            if "municipio" in base.columns
            else pd.Series("", index=base.index)
        )
        mask = col_sede.fillna("").str.contains(filtro_mun, case=False, na=False) | col_mun.fillna(
            ""
        ).str.contains(filtro_mun, case=False, na=False)
        base = base[mask]
    opcoes = {
        f"{r['nome']} ({r['id_snisb']}) — {r.get('municipio_sede') or r.get('municipio') or '—'} — {r['capacidade_hm3']:.1f} hm³": r[
            "id_snisb"
        ]
        for _, r in base.sort_values("capacidade_hm3", ascending=False).iterrows()
    }
    if not opcoes:
        st.info("Nenhuma barragem no recorte/filtro.")
        return
    escolha = st.selectbox("Barragem", list(opcoes.keys()))
    bid = opcoes[escolha]
    r = base[base["id_snisb"] == bid].iloc[0]
    frac = st.slider("Fração liberada (%)", 5, 100, 50, 5) / 100
    prof = st.slider("Profundidade média da lâmina (m)", 0.5, 8.0, 2.0, 0.5)
    liberado = float(r["capacidade_hm3"]) * frac
    area = liberado / prof
    raio = math.sqrt(area / math.pi)
    # Raio operacional para CNES (piso evita buffer inútil; teto evita Overpass absurdo)
    raio_us = max(3.0, min(float(raio), 80.0))
    raio_osm = max(8.0, min(float(raio) * 1.35 + 6.0, 45.0))

    from st_app.trajeto_hidraulico import construir_trajeto, ponto_no_corredor

    # Pré-avalia trajeto para escolher geometria padrão
    trajeto_probe: dict = {"ok": False}
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        trajeto_probe = construir_trajeto(
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            area_km2=float(area),
            semi_largura_km=2.0,
            incluir_jusante_capital=True,
        )

    opcoes_geom = ["Só circular (todas as barragens)"]
    if trajeto_probe.get("ok"):
        opcoes_geom = [
            "Ambos (comparar)",
            "Só circular (todas as barragens)",
            "Só trajeto hidráulico",
        ]
    geom_modo = st.radio(
        "Geometria da mancha proxy",
        opcoes_geom,
        horizontal=True,
        help="Circular vale para qualquer barragem do MT. "
        "Trajeto = corredor jusante (eixo Manso–Cuiabá ou BHO da bacia) quando disponível.",
    )
    mostrar_circular = "circular" in geom_modo.lower() or geom_modo.startswith("Ambos")
    mostrar_trajeto = geom_modo.startswith("Ambos") or geom_modo.startswith("Só trajeto")
    semi_largura = 2.0
    if mostrar_trajeto:
        semi_largura = st.slider(
            "Semi-largura do corredor hidráulico (km)",
            0.5,
            6.0,
            2.0,
            0.5,
            help="Metade da faixa em cada margem do talvegue. "
            "Comprimento jusante ≈ área / (2 × semi-largura).",
        )

    trajeto: dict = {"ok": False, "polyline": [], "largura_km": semi_largura}
    if mostrar_trajeto and pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        trajeto = construir_trajeto(
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            area_km2=float(area),
            semi_largura_km=float(semi_largura),
            incluir_jusante_capital=True,
        )
        if not trajeto.get("ok"):
            st.info(
                trajeto.get("aviso")
                or "Trajeto hidráulico indisponível — usando apenas o círculo."
            )
            mostrar_circular = True
            mostrar_trajeto = False

    afetados_txt = str(r.get("municipios_potencialmente_afetados") or "")
    afetados = [p.strip() for p in afetados_txt.split("|") if p.strip()]
    sede = str(r.get("municipio_sede") or r.get("municipio") or "") or None
    est = estimar_pop_cenario(
        area_km2=area,
        fracao=frac,
        municipio_sede=sede,
        municipios_afetados=afetados or None,
        pop_afetadas=r.get("sigbm_pessoas_afetadas"),
        pop_jusante=r.get("sigbm_populacao_jusante"),
    )
    pop_n = int(est.get("populacao_estimada") or 0)
    metodo = str(est.get("metodo") or "—")

    cnes = carregar_cnes_pontos()
    us_buf = pd.DataFrame()
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        us_buf = cnes_no_buffer(
            cnes, float(r["latitude"]), float(r["longitude"]), raio_us
        )
    n_us = len(us_buf)
    n_hosp = int(us_buf["hospitalar"].sum()) if n_us and "hospitalar" in us_buf.columns else 0
    n_upa = int(us_buf["upa_ps"].sum()) if n_us and "upa_ps" in us_buf.columns else 0
    n_ubs = int(us_buf["ubs_esf"].sum()) if n_us and "ubs_esf" in us_buf.columns else 0

    # US no corredor (quando houver trajeto)
    n_us_tr = 0
    us_tr_ids: list[dict] = []
    if trajeto.get("ok") and not cnes.empty:
        for row in cnes.itertuples():
            if ponto_no_corredor(
                float(row.latitude),
                float(row.longitude),
                trajeto["polyline"],
                float(trajeto["largura_km"]),
            ):
                n_us_tr += 1
                if getattr(row, "prioritario", False) or row.hospitalar or row.upa_ps or row.ubs_esf:
                    us_tr_ids.append(
                        {
                            "nome": row.nome,
                            "tipo": row.tipo,
                            "municipio": row.municipio,
                        }
                    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Volume liberado", _fmt_br(liberado, 1, " hm³"))
    k2.metric("Área equivalente", _fmt_br(area, 1, " km²"))
    k3.metric("Raio circular", _fmt_br(raio, 2, " km"))
    k4.metric("IDAP", f"{r.get('idap', '—')} ({r.get('nivel', '—')})")

    if mostrar_circular and mostrar_trajeto and trajeto.get("ok"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown("##### Circular")
            p1, p2 = st.columns(2)
            p1.metric("Pop. estimada (ref.)", f"{pop_n:,}".replace(",", "."))
            p2.metric("US no círculo", n_us)
        with c_b:
            st.markdown("##### Trajeto hidráulico")
            t1, t2 = st.columns(2)
            t1.metric(
                "Comprimento na calha",
                _fmt_br(float(trajeto.get("comprimento_km") or 0), 1, " km"),
            )
            t2.metric("US no corredor", n_us_tr)
        st.caption(
            f"Corredor ±{trajeto.get('largura_km')} km · área faixa ~"
            f"{trajeto.get('area_corredor_km2')} km² · "
            f"dist. barragem→eixo {trajeto.get('dist_eixo_km')} km · "
            f"`{trajeto.get('fonte')}`. População continua estimada pela área equivalente "
            f"(`{metodo}`), não pelo polígono do corredor."
        )
    else:
        p1, p2, p3, p4 = st.columns(4)
        n_prio = (
            int(us_buf["prioritario"].sum())
            if n_us and "prioritario" in us_buf.columns
            else (n_hosp + n_upa + n_ubs)
        )
        p1.metric("População estimada", f"{pop_n:,}".replace(",", "."))
        p2.metric("US no círculo", n_us)
        if trajeto.get("ok") and mostrar_trajeto:
            p3.metric("US no corredor", n_us_tr)
            p4.metric(
                "Calha / faixa",
                f"{trajeto.get('comprimento_km')} km · ±{trajeto.get('largura_km')} km",
            )
        else:
            p3.metric("Hospital / UPA", f"{n_hosp} / {n_upa}")
            p4.metric("Prioritárias (APS/urg.)", n_prio)
        st.caption(
            f"Método da população: `{metodo}` — {est.get('detalhe', '')} "
            "CNES no círculo: unidades com coordenada no raio equivalente."
        )

    cnes_todos: list[dict] = []
    iso: dict = {}
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        cnes_todos = [
            {
                "la": float(row.latitude),
                "lo": float(row.longitude),
                "no": row.nome,
                "mu": row.municipio,
                "tp": row.tipo,
                "pr": int(row.prioridade),
                "h": 1 if row.hospitalar else 0,
                "upa": 1 if row.upa_ps else 0,
                "ubs": 1 if row.ubs_esf else 0,
                "prio": 1 if getattr(row, "prioritario", False) else 0,
            }
            for row in cnes.itertuples()
        ] if not cnes.empty else []

        st.markdown("#### Área de simulação — US, rodovias e pontes")
        import json as _json

        from st_app.sedes_municipais import sedes_candidatas

        # CNES no recorte da mancha — evita serializar 12k pontos no cache.
        from st_app.data import haversine_km as _hav

        lat0, lon0 = float(r["latitude"]), float(r["longitude"])
        raio_filtro = max(raio_us, raio_osm) + 5.0
        if mostrar_trajeto and trajeto.get("ok") and trajeto.get("polyline"):
            # Amplia para cobrir o corredor jusante inteiro
            plas = [float(p[0]) for p in trajeto["polyline"]]
            plos = [float(p[1]) for p in trajeto["polyline"]]
            dmax = max(_hav(lat0, lon0, a, b) for a, b in zip(plas, plos))
            raio_filtro = max(raio_filtro, dmax + float(trajeto.get("largura_km") or 2) + 5)
        cnes_perto = [
            p for p in cnes_todos if _hav(lat0, lon0, p["la"], p["lo"]) <= raio_filtro
        ]
        cnes_key = _json.dumps(cnes_perto, ensure_ascii=False)
        corredor_key = ""
        if mostrar_trajeto and trajeto.get("ok"):
            corredor_key = _json.dumps(
                {
                    "polyline": trajeto["polyline"],
                    "largura_km": trajeto["largura_km"],
                },
                ensure_ascii=False,
            )
        sedes = sedes_candidatas(
            municipios_afetados=afetados or None,
            so_eixo=False,
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            raio_km=raio_osm,
        )
        sedes_key = _json.dumps(sedes, ensure_ascii=False)
        uniao = bool(mostrar_circular and mostrar_trajeto and trajeto.get("ok"))
        with st.spinner(
            "Cruzando CNES, vias/pontes OSM e sedes municipais na área de simulação…"
        ):
            iso = _isolamento_cached(
                float(r["latitude"]),
                float(r["longitude"]),
                round(float(raio_us), 2),
                cnes_key,
                corredor_key,
                sedes_key,
                uniao,
            )

        i1, i2, i3, i4, i5 = st.columns(5)
        i1.metric("US na área (CNES)", iso.get("n_us_atingidas", 0))
        i2.metric(
            "Rodovias / pontes",
            f"{iso.get('n_vias_interrompidas', 0)} / {iso.get('n_pontes_comprometidas', 0)}",
        )
        i3.metric("US isoladas", iso.get("n_us_isoladas", 0))
        i4.metric(
            "Pessoas isoladas (proxy)",
            f"{int(iso.get('pessoas_isoladas_proxy') or 0):,}".replace(",", "."),
        )
        i5.metric(
            "C7 proxy",
            f"{iso.get('nivel_c7_proxy', 0)} · {iso.get('n_municipios_isolados', 0)} mun.",
        )
        geom_iso = iso.get("geom") or "circular"
        if iso.get("aviso"):
            st.warning(f"Malha viária / isolamento: {iso['aviso']}")
        else:
            st.caption(
                f"Área = geometria **{geom_iso}** · raio US {raio_us:.1f} km "
                f"(equiv. {raio:.1f} km) · busca OSM ~{raio_osm:.0f} km · "
                f"{iso.get('fonte')} · ~{iso.get('km_vias_no_buffer', 0)} km de vias. "
                "Contagens = elementos **dentro da área de simulação** (CNES + OSM)."
            )
        if (
            iso.get("n_us_atingidas", 0) == 0
            and iso.get("n_vias_interrompidas", 0) == 0
            and iso.get("n_pontes_comprometidas", 0) == 0
        ):
            st.info(
                "Nenhuma US, rodovia estruturante ou ponte OSM encontrada nesta área. "
                "Tente aumentar a fração liberada, reduzir a profundidade (raio maior) "
                "ou escolher uma barragem mais próxima de malha urbana/CNES."
            )

        html = html_mapa_simulacao(
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            nome=str(r["nome"]),
            volume_hm3=float(r["capacidade_hm3"]),
            fracao=frac,
            profundidade_m=float(prof),
            pop_est=pop_n,
            metodo_pop=metodo,
            cnes=cnes_perto,
            vias=iso.get("vias") or [],
            pontes=iso.get("pontes") or [],
            us_atingidas=iso.get("us_atingidas") or [],
            us_isoladas=iso.get("us_isoladas") or [],
            municipios_isolados=iso.get("municipios_isolados") or [],
            isolamento=iso,
            trajeto=trajeto if trajeto.get("ok") else None,
            mostrar_circular=mostrar_circular,
            mostrar_trajeto=mostrar_trajeto and bool(trajeto.get("ok")),
            altura=560,
            autoplay=False,
        )
        components.html(html, height=580, scrolling=False)
    else:
        st.warning("Barragem sem coordenada — mapa indisponível.")

    from st_app.indicadores import carregar_exposicao_vulneraveis
    from st_app.data import haversine_km

    vul = carregar_exposicao_vulneraveis()
    if (
        not vul.empty
        and pd.notna(r.get("latitude"))
        and pd.notna(r.get("longitude"))
    ):
        lat0, lon0 = float(r["latitude"]), float(r["longitude"])
        vul = vul.dropna(subset=["latitude", "longitude"]).copy()
        vul["dist_km"] = vul.apply(
            lambda row: haversine_km(lat0, lon0, float(row["latitude"]), float(row["longitude"])),
            axis=1,
        )
        if mostrar_circular:
            no_circ = vul[vul["dist_km"] <= raio].sort_values("dist_km")
            st.subheader("Populações vulneráveis — círculo")
            if no_circ.empty:
                st.caption("Nenhuma aldeia/assentamento/quilombo do eixo no raio.")
            else:
                st.dataframe(
                    no_circ[
                        [c for c in ("nome", "categoria", "municipio", "faixa", "dist_km", "familias") if c in no_circ.columns]
                    ].head(40),
                    width="stretch",
                    hide_index=True,
                    height=200,
                )
        if trajeto.get("ok") and mostrar_trajeto:
            mask = vul.apply(
                lambda row: ponto_no_corredor(
                    float(row["latitude"]),
                    float(row["longitude"]),
                    trajeto["polyline"],
                    float(trajeto["largura_km"]),
                ),
                axis=1,
            )
            no_tr = vul[mask].sort_values("dist_km")
            st.subheader("Populações vulneráveis — corredor hidráulico")
            if no_tr.empty:
                st.caption("Nenhuma população vulnerável do eixo no corredor.")
            else:
                st.dataframe(
                    no_tr[
                        [c for c in ("nome", "categoria", "municipio", "faixa", "dist_km", "familias") if c in no_tr.columns]
                    ].head(40),
                    width="stretch",
                    hide_index=True,
                    height=200,
                )

    us_at = list(iso.get("us_atingidas") or []) if iso else []
    if us_at:
        st.subheader(f"US reais atingidas — CNES na mancha ({len(us_at)})")
        st.dataframe(
            pd.DataFrame(us_at).rename(
                columns={"no": "nome", "mu": "municipio", "tp": "tipo", "dist": "dist_km"}
            )[["nome", "tipo", "municipio", "dist_km"]],
            width="stretch",
            hide_index=True,
            height=240,
        )

    mun_iso = list(iso.get("municipios_isolados") or []) if iso else []
    if mun_iso:
        st.subheader(
            f"Pessoas isoladas (proxy) — "
            f"{int(iso.get('pessoas_isoladas_proxy') or 0):,}".replace(",", ".")
            + f" hab. em {len(mun_iso)} município(s)"
        )
        st.dataframe(
            pd.DataFrame(mun_iso)[["municipio", "populacao", "dist", "codigo_ibge"]].rename(
                columns={"dist": "dist_km"}
            ),
            width="stretch",
            hide_index=True,
            height=220,
        )
        st.caption(
            "População = Censo IBGE 2022 do município cuja sede (centroide) perde "
            "caminho terrestre ao hub após corte de vias/pontes. Ordem de grandeza."
        )

    us_iso = list(iso.get("us_isoladas") or []) if iso else []
    if us_iso:
        st.subheader("US isoladas — fora da mancha, sem rota ao hub")
        st.dataframe(
            pd.DataFrame(us_iso).rename(
                columns={
                    "no": "nome",
                    "mu": "municipio",
                    "tp": "tipo",
                    "dist": "dist_km",
                }
            )[["nome", "tipo", "municipio", "dist_km"]],
            width="stretch",
            hide_index=True,
            height=200,
        )

    if us_tr_ids and mostrar_trajeto and trajeto.get("ok") and not us_at:
        st.markdown(
            f'<p class="lista-us-titulo">US prioritárias no corredor ({len(us_tr_ids)})</p>',
            unsafe_allow_html=True,
        )
        st.dataframe(pd.DataFrame(us_tr_ids).head(60), width="stretch", hide_index=True, height=220)

    if n_us and mostrar_circular and not us_at:
        st.markdown(
            f'<p class="lista-us-titulo">US prioritárias no círculo ({n_us})</p>',
            unsafe_allow_html=True,
        )
        mostrar = us_buf[
            ["nome", "tipo", "municipio", "dist_km", "hospitalar", "upa_ps", "ubs_esf"]
        ].copy()
        mostrar["dist_km"] = mostrar["dist_km"].round(2)
        st.dataframe(mostrar.head(60), width="stretch", hide_index=True, height=280)

    st.caption(
        "Circular: área_km² = (hm³ × fração) / profundidade_m → raio = √(área/π). "
        "Trajeto: L ≈ área / (2×semi-largura) ao longo do eixo BHO Manso–Cuiabá. "
        "Vias/C7 usam o corredor quando o trajeto está ativo. "
        "Mancha PAE oficial (quando houver) será uma terceira camada — não substitui estes proxies. "
        "Não é dam break nem tempo de chegada da onda."
    )


def pagina_interpretacao() -> None:
    st.markdown("# Interpretação dos indicadores")
    st.markdown(
        '<p class="nota">Leitura operacional dos KPIs usados no comando estadual, '
        "no IDAP e na simulação — para quem não é especialista em barragens.</p>",
        unsafe_allow_html=True,
    )

    blocos = [
        (
            "IDAP (0–100)",
            "Índice Dinâmico de Alerta e Prontidão para o setor saúde. "
            "Não estima probabilidade de rompimento: mede atenção e prontidão. "
            "Faixas: Verde 0–19, Amarelo 20–39, Laranja 40–59, Vermelho 60–79, Roxo 80–100.",
        ),
        (
            "Eixo A — Pressão hidroclimática",
            "Chuva observada (24h/72h), previsão ECMWF, percentil espacial, saturação do solo "
            "e alertas Cemaden/ANA/integrado na sede. Regras R10–R12 elevam o nível quando há "
            "alerta oficial ou chuva prevista extrema (≥140 mm).",
        ),
        (
            "Eixo B — Condição da barragem",
            "CRI, situação cadastral e sinais estruturais disponíveis no SNISB/SIGBM "
            "(emergência oficial, DCE etc.). Lacunas baixam a completude do IDAP.",
        ),
        (
            "Eixo C — Impacto sanitário potencial",
            "DPA, população a jusante, municípios Otto a jusante e exposição da rede de saúde. "
            "Quanto maior a exposição humana e assistencial, maior a pressão neste eixo.",
        ),
        (
            "Eixo D — Déficit de capacidade de resposta",
            "Contatos, alertabilidade e lacunas de articulação local. "
            "Sem canal confirmado, o território fica menos preparado mesmo com IDAP moderado.",
        ),
        (
            "Em atenção+ / semáforo estadual",
            "Contagem de barragens fora do Verde (Amarelo+Laranja+Vermelho+Roxo). "
            "Define a prontidão agregada do estado no comando (pior nível presente na base).",
        ),
        (
            "População estimada (simulação)",
            "Cascata: SIGBM pessoas afetadas → SIGBM pop. jusante → área × densidade municipal. "
            "É ordem de grandeza para planejamento sanitário, não censo da mancha oficial.",
        ),
        (
            "US no buffer (CNES)",
            "Estabelecimentos prioritários (hospital, UPA, UBS/ESF) com coordenada dentro do "
            "raio equivalente da simulação. Indicam capacidade de resposta local sob risco de "
            "interdição ou sobrecarga — não o município inteiro.",
        ),
        (
            "Vias, pontes e isolamento (C7 proxy)",
            "Malha OpenStreetMap (arteriais e pontes) cruzada com a geometria ativa "
            "(corredor hidráulico quando o trajeto está ligado; senão o círculo). "
            "Trecho na mancha = interrompido. US fora da mancha sem caminho terrestre até o "
            "hub de Cuiabá = potencialmente isolada. Escala 0–2 espelha o C7 do IDAP.",
        ),
        (
            "Trajeto hidráulico vs círculo",
            "Círculo: espalha a área equivalente em disco isótropo. "
            "Trajeto: percorre a calha BHO (eixo Manso–Cuiabá) jusante e forma um corredor "
            "com semi-largura ajustável — L ≈ área/(2×w). Ambos são proxies; a mancha PAE "
            "oficial (dam break) entra depois como camada própria, sem apagar estes modos.",
        ),
        (
            "US atingidas, vias/pontes e pessoas isoladas",
            "US atingidas = estabelecimentos CNES dentro da mancha proxy. "
            "Vias/pontes = arteriais OSM que cruzam a mancha. "
            "US isoladas = fora da mancha sem rota terrestre ao hub após o corte. "
            "Pessoas isoladas = soma da população IBGE 2022 dos municípios cuja sede "
            "(centroide) perde caminho ao hub — ordem de grandeza, não censo de desalojados. "
            "Relevo/MDE ainda não entra no cálculo.",
        ),
        (
            "CRI e DPA",
            "CRI = probabilidade relativa de acidente (estado da estrutura). "
            "DPA = consequência de um eventual rompimento (volume, população, ambiente). "
            "São classificações oficiais do cadastro, não o IDAP.",
        ),
        (
            "Completude e confiabilidade",
            "Completude: % dos pontos do IDAP com dado disponível. "
            "Baixa completude exige cautela na leitura do número — o IDAP projetado mostra o "
            "pior caso compatível com as lacunas.",
        ),
    ]
    for titulo, texto in blocos:
        st.markdown(
            f'<div class="bloco-interp"><h3>{titulo}</h3><p>{texto}</p></div>',
            unsafe_allow_html=True,
        )

    glossario = Path(__file__).parent / "docs" / "10-glossario.md"
    if glossario.exists():
        with st.expander("Glossário completo (documentação)"):
            st.markdown(glossario.read_text(encoding="utf-8"))


def pagina_ficha(df: pd.DataFrame) -> None:
    st.markdown("# Barragem 360°")
    if df.empty:
        st.error("Sem dados.")
        return
    ordenado = df.sort_values(["nivel", "idap_n"], ascending=[True, False])
    labels = [f"{r.nome} — {r.id_snisb}" for r in ordenado.itertuples()]
    escolha = st.selectbox("Barragem", labels)
    bid = escolha.split(" — ")[-1]
    r = df[df["id_snisb"] == bid].iloc[0]
    st.markdown(f"## {r['nome']}")
    st.markdown(
        f"{_badge(r['nivel'])} &nbsp; IDAP **{r.get('idap','—')}/100** · "
        f"completude {r.get('completude','—')} · {r.get('confiabilidade','—')}",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown("### Identificação")
        st.write(
            {
                "SNISB": r["id_snisb"],
                "Município": r.get("municipio_sede"),
                "Órgão": r.get("orgao_fiscalizador"),
                "Uso": r.get("uso_principal"),
                "CRI / DPA": f"{r.get('categoria_risco','—')} / {r.get('dano_potencial_associado','—')}",
                "Afetados (Otto)": r.get("municipios_potencialmente_afetados"),
            }
        )
        st.markdown("### Dimensões IDAP")
        st.bar_chart(
            pd.Series(
                {
                    "A": float(r.get("pontos_a") or 0),
                    "B": float(r.get("pontos_b") or 0),
                    "C": float(r.get("pontos_c") or 0),
                    "D": float(r.get("pontos_d") or 0),
                }
            )
        )
    with b:
        st.markdown("### Hidro / alertas")
        st.write(
            {
                "Chuva 24 h": r.get("chuva_24h_mm"),
                "Chuva 72 h": r.get("chuva_72h_mm"),
                "Prevista 24–72 h": r.get("chuva_prevista_24_72h_mm"),
                "Percentil": r.get("percentil_climatologico"),
                "Saturação": r.get("saturacao_antecedente"),
                "Cemaden": r.get("alerta_cemaden") or "—",
                "Integrado SIS": r.get("nivel_alerta_integrado") or "—",
                "GloFAS m³/s": r.get("vazao_prevista_glofas_m3s"),
                "Regras": r.get("regras_disparadas") or "—",
            }
        )
        if pd.notna(r.get("latitude")):
            m = folium.Map(location=[r["latitude"], r["longitude"]], zoom_start=10)
            folium.CircleMarker(
                [r["latitude"], r["longitude"]],
                radius=10,
                color="#111",
                fill=True,
                fill_color=CORES_NIVEL.get(r["nivel"], "#888"),
                fill_opacity=0.95,
                popup=r["nome"],
            ).add_to(m)
            st_folium(m, height=280, returned_objects=[])
    if r.get("lacunas"):
        st.warning(f"Lacunas: {r['lacunas']}")


def pagina_tipologia(df: pd.DataFrame) -> None:
    """Mapa estadual colorido por uso principal (tipologia)."""
    st.markdown("# Barragens por tipologia")
    st.markdown(
        '<p class="nota">Uso principal do cadastro SNISB — visão estadual. '
        "Cores institucionais SES-MT / agrupamento operacional.</p>",
        unsafe_allow_html=True,
    )
    base = df.dropna(subset=["latitude", "longitude"]).copy()
    if base.empty:
        st.warning("Sem coordenadas.")
        return
    if "uso_principal" not in base.columns:
        st.error("Coluna uso_principal ausente no inventário mesclado.")
        return
    cores = TIPOLOGIA_CORES
    base = com_tipologia(base)
    cont = base["tipologia"].value_counts()
    cols = st.columns(min(4, len(cont)))
    for i, (tip, n) in enumerate(cont.items()):
        cols[i % len(cols)].metric(str(tip), int(n))

    filtro = st.multiselect(
        "Tipologias no mapa",
        list(cont.index),
        default=list(cont.index),
    )
    view = base[base["tipologia"].isin(filtro)] if filtro else base
    m = folium.Map(location=[-13.0, -55.8], zoom_start=6, tiles="CartoDB positron")
    for r in view.itertuples():
        folium.CircleMarker(
            [r.latitude, r.longitude],
            radius=5,
            color="#fff",
            weight=1,
            fill=True,
            fill_color=cores.get(r.tipologia, "#888"),
            fill_opacity=0.9,
            popup=f"{r.nome}<br>{r.tipologia}<br>{getattr(r, 'uso_principal', '')}",
        ).add_to(m)
    st_folium(m, height=520, use_container_width=True, returned_objects=[])
    st.caption("Painel HTML equivalente: `painel/tipologia.html` (etapa 28).")


def pagina_html_painel(nome_arquivo: str, titulo: str, nota: str) -> None:
    """Abre telas HTML do painel operacional (mesmas do comando estadual)."""
    st.markdown(f"# {titulo}")
    st.markdown(f'<p class="nota">{nota}</p>', unsafe_allow_html=True)
    caminho = Path(__file__).parent / "painel" / nome_arquivo
    if not caminho.exists():
        st.error(
            f"Arquivo `{nome_arquivo}` ausente. Regenere com "
            "`python executar.py 07 20 21 22 23 25 27`."
        )
        return
    st.caption(f"Fonte: `painel/{nome_arquivo}` — mesma tela do painel HTML.")
    # Em Cloud o path file:// não abre; oferecemos o HTML embutido quando possível.
    try:
        html = caminho.read_text(encoding="utf-8")
        # Páginas muito grandes (barragem/inventário) — iframe altura maior.
        altura = 900 if caminho.stat().st_size > 400_000 else 720
        components.html(html, height=altura, scrolling=True)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Não foi possível embutir o HTML ({exc}). Abra o arquivo localmente.")
        st.code(str(caminho))


def main() -> None:
    aplicar_navegacao_pendente()
    jornadas_ordem = list(JORNADAS.keys())
    if "jornada" not in st.session_state:
        st.session_state["jornada"] = "Situação"
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Comando estadual"

    with st.sidebar:
        # Assinatura conforme o manual: marca do governo + nome da secretaria.
        st.markdown(
            '<div class="assinatura-gov">'
            '<span class="gov">Governo de Mato Grosso</span>'
            '<span class="secretaria">Secretaria de Estado de Saúde · CIEVS</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<p class="marca">VIGIBARRAGENS–MT</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="submarca">Saúde 360 · jornada '
            "Situação → Território → Ação → Dados</p>",
            unsafe_allow_html=True,
        )
        if st.session_state.get("jornada") not in JORNADAS:
            st.session_state["jornada"] = "Situação"
        jornada = st.selectbox("Jornada", jornadas_ordem, key="jornada")
        telas = JORNADAS[jornada]
        # Migra nome antigo da tela
        if st.session_state.get("pagina") == "Simulação volume/área":
            st.session_state["pagina"] = TELA_SIMULACAO
        if st.session_state.get("pagina") not in telas:
            st.session_state["pagina"] = telas[0]
        pagina = st.radio("Tela", telas, key="pagina")
        if st.button("Abrir simulação de cenário", width="stretch", type="primary"):
            from st_app.paginas_onda import ir_para

            ir_para("Situação", TELA_SIMULACAO)
        st.divider()
        st.caption(f"Dados: `{(Path(__file__).parent / 'dados' / 'tratados').as_posix()}`")

    df = carregar_idap()
    if pagina == "Comando estadual":
        pagina_comando(df)
    elif pagina == "Hidro municipal":
        pagina_hidro(carregar_hidro_mun(), carregar_populacao())
    elif pagina == "Eixo Manso–Cuiabá":
        pagina_piloto(carregar_piloto())
    elif pagina in (TELA_SIMULACAO, "Simulação volume/área"):
        pagina_simulacao(df)
    elif pagina == "Mapa por tipologia":
        pagina_tipologia(df)
    elif pagina == "Populações vulneráveis":
        pagina_vulneraveis()
    elif pagina == "Impacto extraterritorial":
        pagina_extraterritorial()
    elif pagina == "Interpretação / KPIs":
        pagina_interpretacao()
    elif pagina == "Barragem 360°":
        pagina_ficha(df)
    elif pagina == "Alertabilidade / despacho":
        pagina_alertabilidade_despacho()
    elif pagina == "Confirmação persistente":
        pagina_confirmacao_persistente()
    elif pagina == "Região de saúde":
        pagina_regiao_saude()
    elif pagina == "Documentos (RAG leve)":
        pagina_rag_docs()
    elif pagina == "Fila de alertas":
        pagina_html_painel(
            "alertas.html",
            "Fila de alertas",
            "Fila do piloto — textos territorializados. Escalonamento a canais reais ainda não ligado.",
        )
    elif pagina == "Ficha rápida":
        pagina_html_painel(
            "ficha_rapida.html",
            "Ficha rápida pós-desastre",
            "Captura operacional quando os sistemas oficiais ainda não refletem o evento.",
        )
    elif pagina == "Confirmação (HTML)":
        pagina_html_painel(
            "confirmacao_alerta.html",
            "Confirmação de alerta",
            "Prazos por nível e registro local de confirmação (protótipo).",
        )
    elif pagina == "Inventário":
        pagina_html_painel(
            "inventario.html",
            "Inventário de barragens",
            "Cadastro consolidado SNISB/SIGBM/SEMA — visão de fiscalização.",
        )
    elif pagina == "Comando (HTML)":
        pagina_html_painel(
            "comando.html",
            "Comando estadual (HTML)",
            "Gêmeo autocontido da 1ª tela (etapa 20) — serve para distribuir offline "
            "sem depender de um segundo servidor.",
        )
    else:
        pagina_ficha(df)


if __name__ == "__main__":
    main()
