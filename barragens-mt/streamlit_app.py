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
    ordenar_por_severidade,
    projecao_semana,
    rotulo_regulada,
    rotulo_sim_nao,
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
    pagina_notificacoes_impactos,
    pagina_rag_docs,
    pagina_regiao_saude,
    pagina_vigipos_oe,
    pagina_visao_territorial,
    pagina_vulneraveis,
    tendencia_unificada,
)
from st_app.style import CSS

JORNADAS: dict[str, list[str]] = {
    "Território": [
        "Visão territorial",
        "Populações vulneráveis",
        "Impacto extraterritorial",
        "Mapa por tipologia",
        "Barragem 360°",
    ],
    "Situação": [
        "Comando estadual",
        "Simulação de cenário",
        "VIGIPÓS O/E",
        "Hidro municipal",
        "Eixo Manso–Cuiabá",
    ],
    "Ação": [
        "Simulação de cenário",
        "VIGIPÓS O/E",
        "Notificações e impactos",
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
    hand_limiar: float | None = None,
) -> dict:
    return analisar_isolamento_json(
        lat0,
        lon0,
        raio0,
        cnes_key,
        corredor_key,
        sedes_key,
        uniao_circular,
        hand_limiar,
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
            default=["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"],
            help="Padrão: todos os cenários (inclui Verde). Remova níveis para filtrar.",
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
        '<p class="nota">SisClima/TITAN + previsão ECMWF (Copernicus/C3S) + amostra GloFAS. '
        "Nomes municipais completados via IBGE quando a fonte só traz o código.</p>",
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Municípios", len(hidro))
    c2.metric("Máx. chuva 24 h", f"{hidro['chuva_24h_mm'].max():.1f} mm" if "chuva_24h_mm" in hidro else "—")
    c3.metric(
        "Máx. prevista 72 h",
        f"{hidro['chuva_prevista_24_72h_mm'].max():.1f} mm"
        if "chuva_prevista_24_72h_mm" in hidro
        else "—",
    )
    n_nome = int((hidro["municipio"].fillna("").astype(str).str.strip() != "").sum()) if "municipio" in hidro.columns else 0
    c4.metric("Com nome IBGE", f"{n_nome}/{len(hidro)}")
    ordenado = hidro.sort_values(metrica, ascending=False, na_position="last")
    rotulos = ordenado["municipio"].fillna("").astype(str)
    rotulos = rotulos.where(rotulos.str.strip() != "", ordenado.get("codigo_ibge", pd.Series("", index=ordenado.index)).astype(str))
    chart = ordenado.assign(_rotulo=rotulos).set_index("_rotulo")[metrica].head(25)
    st.bar_chart(chart, height=360)
    cols_pref = [
        c
        for c in (
            "municipio",
            "codigo_ibge",
            "populacao",
            "chuva_24h_mm",
            "chuva_72h_mm",
            "chuva_prevista_24_72h_mm",
            "percentil_climatologico",
            "indice_saturacao_solo",
            "classe_saturacao_solo",
            "nivel_alerta_hidro",
            "dias_consecutivos_chuva_intensa",
            "fonte_precip",
            "fonte_previsao",
            "data_referencia",
        )
        if c in ordenado.columns
    ]
    mostrar = ordenado[cols_pref].copy() if cols_pref else ordenado.copy()
    if not pop.empty and "populacao" not in mostrar.columns and "municipio" in mostrar.columns:
        mostrar = mostrar.merge(
            pop[["municipio", "populacao"]].drop_duplicates("municipio"),
            on="municipio",
            how="left",
        )
    st.dataframe(mostrar, width="stretch", hide_index=True, height=420)
    st.caption(
        "Colunas principais: chuva observada/prevista, saturação, alerta hidro, população IBGE e fontes. "
        "Demais campos técnicos permanecem no CSV tratado."
    )


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
        "<b>trajeto hidráulico</b> (corredor jusante) quando há calha BHO/eixo; "
        "o <b>relevo (HAND)</b> no eixo Manso–Cuiabá quando a grade SRTM estiver gerada. "
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
    chaves = list(opcoes.keys())
    pre_sim = str(st.session_state.pop("barragem_sim_id", "") or "")
    idx_sim = 0
    if pre_sim:
        for i, k in enumerate(chaves):
            if opcoes[k] == pre_sim:
                idx_sim = i
                break
    escolha = st.selectbox("Barragem", chaves, index=idx_sim)
    bid = opcoes[escolha]
    st.session_state["barragem_selecionada_id"] = bid
    r = base[base["id_snisb"] == bid].iloc[0]
    frac = st.slider("Fração liberada (%)", 5, 100, 50, 5) / 100
    prof = st.slider("Profundidade média da lâmina (m)", 0.5, 8.0, 2.0, 0.5)
    liberado = float(r["capacidade_hm3"]) * frac
    area = liberado / prof
    raio = math.sqrt(area / math.pi)
    # Raio operacional para CNES (piso evita buffer inútil; teto evita Overpass absurdo)
    raio_us = max(3.0, min(float(raio), 80.0))
    raio_osm = max(8.0, min(float(raio) * 1.35 + 6.0, 45.0))

    from st_app.relevo_hand import (
        hand_arquivos_ok,
        hand_disponivel_para,
        limiar_para_lamina,
        resumo_hand,
    )
    from st_app.trajeto_hidraulico import construir_trajeto, ponto_no_corredor

    # Pré-avalia trajeto / HAND para escolher geometria padrão
    trajeto_probe: dict = {"ok": False}
    hand_ok = False
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        trajeto_probe = construir_trajeto(
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            area_km2=float(area),
            semi_largura_km=2.0,
            incluir_jusante_capital=True,
        )
        hand_ok = hand_arquivos_ok() and hand_disponivel_para(
            float(r["latitude"]), float(r["longitude"])
        )

    opcoes_geom = ["Só circular (todas as barragens)"]
    if trajeto_probe.get("ok") and hand_ok:
        opcoes_geom = [
            "Ambos (comparar)",
            "Só circular (todas as barragens)",
            "Só trajeto hidráulico",
            "Só relevo (HAND)",
            "Circular + relevo (HAND)",
        ]
    elif trajeto_probe.get("ok"):
        opcoes_geom = [
            "Ambos (comparar)",
            "Só circular (todas as barragens)",
            "Só trajeto hidráulico",
        ]
    elif hand_ok:
        opcoes_geom = [
            "Só circular (todas as barragens)",
            "Só relevo (HAND)",
            "Circular + relevo (HAND)",
        ]
    geom_modo = st.radio(
        "Geometria da mancha proxy",
        opcoes_geom,
        horizontal=True,
        help="Circular vale para qualquer barragem do MT. "
        "Trajeto = corredor jusante (eixo Manso–Cuiabá ou BHO) quando disponível. "
        "Relevo (HAND) = células SRTM ≤ lâmina no eixo Manso–Cuiabá (etapa 35).",
    )
    usar_hand = "relevo" in geom_modo.lower() or "HAND" in geom_modo
    mostrar_circular = (
        "circular" in geom_modo.lower()
        or geom_modo.startswith("Ambos")
        or geom_modo.startswith("Circular +")
    )
    mostrar_trajeto = (
        (geom_modo.startswith("Ambos") or geom_modo.startswith("Só trajeto"))
        and not usar_hand
    )
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

    hand_limiar = limiar_para_lamina(float(prof)) if usar_hand else None
    hand_info: dict = {"ok": False}
    if usar_hand and hand_limiar is not None:
        hand_info = resumo_hand(hand_limiar)
        st.caption(
            f"Relevo HAND ≤ **{hand_limiar:.0f} m** (lâmina {prof:.1f} m) · "
            f"{hand_info.get('n_celulas', 0)} células · área proxy ~"
            f"{hand_info.get('area_proxy_km2', 0)} km² · `{hand_info.get('fonte')}`. "
            f"{hand_info.get('aviso', '')}"
        )
        if not hand_info.get("ok"):
            st.info("Grade HAND sem células neste limiar — usando círculo.")
            usar_hand = False
            hand_limiar = None
            mostrar_circular = True

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
        if usar_hand and hand_info.get("ok"):
            from st_app.relevo_hand import bbox_hand as _bbox_hand

            bb = _bbox_hand(float(hand_limiar or 5.0))
            if bb:
                # canto mais distante da bbox → raio de filtro CNES
                cantos = [
                    (bb[0], bb[1]),
                    (bb[0], bb[3]),
                    (bb[2], bb[1]),
                    (bb[2], bb[3]),
                ]
                dmax_h = max(_hav(lat0, lon0, a, b) for a, b in cantos)
                raio_filtro = max(raio_filtro, dmax_h + 5)
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
            raio_km=max(raio_osm, raio_filtro),
        )
        sedes_key = _json.dumps(sedes, ensure_ascii=False)
        uniao = bool(
            mostrar_circular
            and (
                (mostrar_trajeto and trajeto.get("ok"))
                or (usar_hand and hand_info.get("ok"))
            )
        )
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
                float(hand_limiar) if usar_hand and hand_limiar is not None else None,
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
        d1, d2, d3 = st.columns(3)
        d1.metric("Sedes sem rota", iso.get("n_sedes_sem_rota", 0))
        d2.metric("Sedes com desvio", iso.get("n_sedes_com_desvio", 0))
        d3.metric(
            "Desvio médio (km)",
            f"{float(iso.get('delta_km_medio_desvio') or 0):.1f}".replace(".", ","),
        )
        st.caption(
            "Desvio = menor caminho OSM sede→hub depois do corte − antes "
            "(proxy C7/D7; não é tempo de viagem oficial)."
        )
        if iso.get("desvios_rota"):
            with st.expander("Desvios de rota por município", expanded=False):
                st.dataframe(
                    pd.DataFrame(iso["desvios_rota"]),
                    width="stretch",
                    hide_index=True,
                    height=240,
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

        from st_app.escolas_inep import cruzar_escolas_mancha
        from st_app.setores_ibge import cruzar_setores_mancha
        from st_app.sisagua_captacoes import cruzar_captacoes_mancha

        munis_iso_nomes = [
            str(m.get("municipio") or "")
            for m in (iso.get("municipios_isolados") or [])
            if m.get("municipio")
        ]
        _geom_mancha = dict(
            lat0=lat0,
            lon0=lon0,
            raio_km=float(raio),
            mostrar_circular=mostrar_circular,
            trajeto=trajeto if trajeto.get("ok") else None,
            mostrar_trajeto=mostrar_trajeto and bool(trajeto.get("ok")),
            hand_limiar=float(hand_limiar) if usar_hand and hand_limiar is not None else None,
            usar_hand=bool(usar_hand and hand_info.get("ok")),
        )
        set_kpi = cruzar_setores_mancha(
            **_geom_mancha,
            munis_isolamento=munis_iso_nomes,
        )
        cap_kpi = cruzar_captacoes_mancha(**_geom_mancha)
        esc_kpi = cruzar_escolas_mancha(**_geom_mancha)
        if set_kpi.get("disponivel"):
            s1, s2, s3, s4 = st.columns(4)
            s1.metric(
                "Pop. exposta (setores)",
                f"{int(set_kpi['pop_exposta_setores']):,}".replace(",", "."),
            )
            s2.metric("Setores na mancha", set_kpi["n_setores_expostos"])
            s3.metric(
                "Pop. isolada (setores)",
                f"{int(set_kpi['pop_isolada_setores']):,}".replace(",", "."),
            )
            s4.metric("Setores isolados (proxy)", set_kpi["n_setores_isolados_proxy"])
            st.caption(
                f"Censo IBGE 2022 por setor (eixo Manso–Cuiabá, n={set_kpi['n_setores_eixo']}). "
                "Exposta = centróide na mancha; isolada = fora da mancha em município com vias cortadas. "
                f"`{set_kpi.get('fonte')}`"
            )
            if set_kpi.get("por_municipio"):
                with st.expander("População por município (setores)", expanded=False):
                    st.dataframe(
                        pd.DataFrame(set_kpi["por_municipio"]).head(20),
                        width="stretch",
                        hide_index=True,
                        height=220,
                    )
        else:
            st.caption(
                "Setores censitários do eixo ainda não tratados — rode `python executar.py 37`."
            )

        if cap_kpi.get("disponivel"):
            c1, c2 = st.columns(2)
            c1.metric("Captações na mancha", cap_kpi["n_na_mancha"])
            c2.metric("Captações no eixo (cadastro)", cap_kpi["n_total"])
            label = "esqueleto Sisagua" if cap_kpi.get("esqueleto") else "Sisagua/OSM"
            st.caption(
                f"Captações ({label}) intersectando a mancha proxy — KPI C4. "
                f"`{cap_kpi.get('fonte')}`"
            )
            if cap_kpi.get("itens"):
                with st.expander("Captações atingidas", expanded=False):
                    st.dataframe(
                        pd.DataFrame(cap_kpi["itens"]),
                        width="stretch",
                        hide_index=True,
                        height=200,
                    )
        else:
            st.caption(
                "Captações Sisagua ausentes — rode `python executar.py 38` "
                "(portal oficial ou fallback OSM)."
            )

        if esc_kpi.get("disponivel"):
            e1, e2 = st.columns(2)
            e1.metric("Escolas na mancha", esc_kpi["n_na_mancha"])
            e2.metric("Escolas no eixo (espacial)", esc_kpi["n_total"])
            st.caption(
                f"Escolas na mancha proxy — KPI C5 (`{esc_kpi.get('fonte')}`). "
                "Microdados INEP 2024 sem lat/lon (LGPD); pontos = OSM. "
                "Contagem oficial por município em `escolas_inep_contagem_municipio.csv`."
            )
            if esc_kpi.get("itens"):
                with st.expander("Escolas atingidas", expanded=False):
                    st.dataframe(
                        pd.DataFrame(esc_kpi["itens"]).drop(
                            columns=["lat", "lon"], errors="ignore"
                        ),
                        width="stretch",
                        hide_index=True,
                        height=220,
                    )
            from st_app.data import TRATADOS as _TR

            cont_esc = _TR / "escolas_inep_contagem_municipio.csv"
            if cont_esc.is_file():
                with st.expander("Contagem INEP por município (eixo)", expanded=False):
                    st.dataframe(
                        pd.read_csv(cont_esc, sep=";"),
                        width="stretch",
                        hide_index=True,
                        height=260,
                    )
        else:
            st.caption(
                "Escolas do eixo ausentes — rode `python executar.py 40` "
                "(microdados INEP + camada OSM)."
            )

        from st_app.ativos_essenciais import cruzar_ativos_mancha
        from st_app.demanda_cenario import estimar_demanda

        ativos_kpi = cruzar_ativos_mancha(**_geom_mancha)

        # C5 — serviços essenciais não assistenciais na mancha
        n_pontes_c5 = int(iso.get("n_pontes_comprometidas") or 0)
        n_esc_c5 = int(esc_kpi.get("n_na_mancha") or 0) if esc_kpi.get("disponivel") else 0
        n_cap_c5 = int(cap_kpi.get("n_na_mancha") or 0) if cap_kpi.get("disponivel") else 0
        n_eta = int(ativos_kpi.get("n_eta") or 0) if ativos_kpi.get("disponivel") else 0
        n_ete = int(ativos_kpi.get("n_ete") or 0) if ativos_kpi.get("disponivel") else 0
        n_energia = int(ativos_kpi.get("n_energia") or 0) if ativos_kpi.get("disponivel") else 0
        n_abrigo = int(ativos_kpi.get("n_abrigo") or 0) if ativos_kpi.get("disponivel") else 0
        n_ativos_c5 = n_eta + n_ete + n_energia + n_abrigo
        st.markdown("##### Serviços essenciais na mancha (C5 proxy)")
        c5a, c5b, c5c, c5d = st.columns(4)
        c5a.metric("Escolas", n_esc_c5)
        c5b.metric("Captações", n_cap_c5)
        c5c.metric("Pontes OSM", n_pontes_c5)
        c5d.metric(
            "Total C5 proxy",
            n_esc_c5 + n_cap_c5 + n_pontes_c5 + n_ativos_c5,
        )
        if ativos_kpi.get("disponivel"):
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("ETA / água (OSM)", n_eta)
            a2.metric("ETE / esgoto (OSM)", n_ete)
            a3.metric("Subestações", n_energia)
            a4.metric("Abrigos OSM", n_abrigo)
            st.caption(
                f"C5 = escolas + captações + pontes + ativos OSM (`{ativos_kpi.get('fonte')}`). "
                "Proxy espacial — preferir cadastros oficiais de concessionárias/Defesa Civil. "
                "Rode `python executar.py 46` para atualizar."
            )
            if ativos_kpi.get("itens"):
                with st.expander("Ativos essenciais na mancha", expanded=False):
                    st.dataframe(
                        pd.DataFrame(ativos_kpi["itens"]).drop(
                            columns=["lat", "lon"], errors="ignore"
                        ),
                        width="stretch",
                        hide_index=True,
                        height=220,
                    )
        else:
            st.caption(
                "C5 = escolas + captações Sisagua + pontes OSM. "
                "Ativos ETA/ETE/energia/abrigos ausentes — rode `python executar.py 46`."
            )

        from st_app.malha_dnit import cruzar_malha_mancha
        from st_app.capacidade_cnes import cruzar_capacidade_mancha

        malha_kpi = cruzar_malha_mancha(**_geom_mancha)
        if malha_kpi.get("disponivel"):
            st.markdown("##### Malha federal/estadual na mancha (proxy DNIT)")
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Refs BR/MT na mancha", malha_kpi["n_na_mancha"])
            d2.metric("Federais (BR-)", malha_kpi["n_federais_mancha"])
            d3.metric("Pontes (ref)", malha_kpi["n_pontes_mancha"])
            d4.metric("Km aprox. na mancha", f"{malha_kpi['km_na_mancha']:.0f}")
            st.caption(
                f"`{malha_kpi.get('fonte')}` — rode `python executar.py 42` para atualizar. "
                "SNV/DNIT oficial permanece a fonte preferida quando o portal responder."
            )
            if malha_kpi.get("itens"):
                with st.expander("Trechos BR/MT atingidos", expanded=False):
                    st.dataframe(
                        pd.DataFrame(malha_kpi["itens"]),
                        width="stretch",
                        hide_index=True,
                        height=240,
                    )
        else:
            st.caption(
                "Malha BR/MT (proxy DNIT) ausente — rode `python executar.py 42`."
            )

        pop_exp_setores = None
        if set_kpi.get("disponivel"):
            try:
                pop_exp_setores = float(set_kpi.get("pop_exposta_setores") or 0) or None
            except (TypeError, ValueError):
                pop_exp_setores = None
        cap_assist = cruzar_capacidade_mancha(
            cnes,
            **_geom_mancha,
            us_isoladas=iso.get("us_isoladas") or [],
            pop_exposta=pop_exp_setores or (float(pop_n) if pop_n else None),
        )
        if cap_assist.get("disponivel"):
            st.markdown("##### Capacidade assistencial sob pressão (D6)")
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Hospitalar na mancha", cap_assist["n_hospitalar_mancha"])
            a2.metric("UPA/PS na mancha", cap_assist["n_upa_mancha"])
            a3.metric("UBS/ESF na mancha", cap_assist["n_ubs_mancha"])
            a4.metric("Pressão estrutural", cap_assist["pressao_estrutural"])
            b1, b2, b3 = st.columns(3)
            b1.metric("Hospitalar isolada", cap_assist["n_hospitalar_isolada"])
            b2.metric("UPA isolada", cap_assist["n_upa_isolada"])
            b3.metric("UBS isolada", cap_assist["n_ubs_isolada"])
            st.caption(
                f"{cap_assist['rotulo_pressao']}. `{cap_assist.get('fonte')}`. "
                "Score estrutural = 3×hospital + 2×UPA + 1×UBS (mancha + isoladas)."
            )
            if cap_assist.get("leitos_ok"):
                l1, l2, l3, l4 = st.columns(4)
                l1.metric(
                    "Leitos operacionais (mancha)",
                    cap_assist["leitos_operacionais_mancha"],
                )
                l2.metric(
                    "Leitos ocupados",
                    cap_assist["leitos_ocupados_mancha"],
                )
                l3.metric(
                    "Leitos disponíveis",
                    cap_assist["leitos_disponiveis_mancha"],
                )
                taxa = cap_assist.get("taxa_ocupacao_mancha")
                l4.metric(
                    "Taxa ocupação",
                    "—" if taxa is None else f"{taxa:.1f}%".replace(".", ","),
                )
                if cap_assist.get("razao_leitos_demanda") is not None:
                    st.caption(
                        f"D6 razão leitos disponíveis / demanda (2% pop. exposta) = "
                        f"**{cap_assist['razao_leitos_demanda']:.2f}** "
                        "(≥1,00 = 0 pts; 0,50–1 = 1 pt; <0,50 = 2 pts)."
                    )
            elif cap_assist.get("cadastrados_ok"):
                st.metric(
                    "Leitos cadastrados CNES na mancha (SAU-01)",
                    cap_assist["leitos_cadastrados_mancha"],
                )
                st.caption(
                    "Capacidade cadastrada (CNES LT) — **não** é ocupação operacional. "
                    "Para vagos/ocupação, aponte IndicaSUS e rode `python executar.py 43`."
                )
            else:
                st.caption(
                    "Leitos ainda não carregados — IndicaSUS: `python executar.py 43`; "
                    "CNES LT cadastrado: `python executar.py 45`. "
                    "Ver `docs/15-integracao-indicasus-dw.md`."
                )

            # Demanda sanitária do cenário (roadmap 4.3) — usa pop. setores ou proxy
            pop_demanda = pop_exp_setores
            if not pop_demanda:
                try:
                    pop_demanda = float(pop_n) if pop_n else None
                except (TypeError, ValueError):
                    pop_demanda = None
            leitos_disp_dem = None
            if cap_assist.get("leitos_ok"):
                leitos_disp_dem = cap_assist.get("leitos_disponiveis_mancha")
            dem = estimar_demanda(pop_demanda, leitos_disponiveis=leitos_disp_dem)
            if dem.get("ok"):
                st.markdown("##### Demanda estimada do cenário (proxy 4.3)")
                e1, e2, e3, e4 = st.columns(4)
                e1.metric(
                    "Pop. de referência",
                    f"{dem['pop_exposta']:,}".replace(",", "."),
                )
                e2.metric("Internações (2%)", dem["demanda_internacao"])
                e3.metric("Atendimentos 72 h (8%)", dem["demanda_atendimentos_72h"])
                e4.metric(
                    "Água L/dia (15 L/p)",
                    f"{dem['demanda_agua_L_dia']:,}".replace(",", "."),
                )
                e5, e6 = st.columns(2)
                e5.metric("Ambulâncias ref. (1/10 mil)", dem["ambulancias_ref"])
                if dem.get("razao_leitos_demanda") is not None:
                    e6.metric(
                        "Razão leitos/demanda",
                        f"{dem['razao_leitos_demanda']:.2f}".replace(".", ","),
                    )
                else:
                    e6.metric("Razão leitos/demanda", "—")
                st.caption(dem.get("nota") or "")

            from st_app.cenario_export import montar_csv_cenario
            from st_app.ficha_rapida import (
                carregar_ficha,
                listar_fichas,
                termos_ipapd_da_ficha,
                termos_irs_da_ficha,
            )
            from st_app.ipapd import calcular_ipapd_proxy
            from st_app.irs import ROTULOS as IRS_ROTULOS
            from st_app.irs import calcular_irs_proxy
            from st_app.pae_checklist import (
                checklist_para_dataframe,
                exportar_checklist_csv,
                montar_checklist_pae,
            )
            from st_app.sitrep import montar_sitrep_cenario_md

            chk_pae = montar_checklist_pae(r)
            with st.expander("Checklist PAE / PAEBM (lacunas)", expanded=False):
                res = chk_pae.get("resumo") or {}
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("OK", str(res.get("ok", 0)))
                c2.metric("Atenção", str(res.get("atencao", 0)))
                c3.metric("Não", str(res.get("nao", 0)))
                c4.metric("Lacuna", str(res.get("lacuna", 0)))
                st.dataframe(
                    checklist_para_dataframe(chk_pae),
                    width="stretch",
                    hide_index=True,
                    height=280,
                )
                st.download_button(
                    "Baixar checklist PAE (CSV)",
                    data=exportar_checklist_csv(chk_pae),
                    file_name=f"checklist_pae_{(r.get('id_snisb') or 'barragem')}.csv",
                    mime="text/csv",
                    key="checklist_pae_csv",
                )
                st.caption(chk_pae.get("fonte") or "")

            # S usa o mesmo universo no numerador/denominador (escolas+captações+ativos)
            n_ess_mancha = n_esc_c5 + n_cap_c5 + n_ativos_c5
            n_ess_eixo = 0
            if esc_kpi.get("disponivel"):
                n_ess_eixo += int(esc_kpi.get("n_total") or 0)
            if cap_kpi.get("disponivel"):
                n_ess_eixo += int(cap_kpi.get("n_total") or 0)
            if ativos_kpi.get("disponivel"):
                n_ess_eixo += int(ativos_kpi.get("n_total") or 0)
            if n_ess_eixo < n_ess_mancha:
                n_ess_eixo = n_ess_mancha

            ficha_termos: dict = {}
            ficha_irs: dict = {}
            with st.expander("Ficha rápida → IPAPD / IRS", expanded=False):
                st.caption(
                    "Exporte o JSON em `painel/ficha_rapida.html` para "
                    "`dados/tratados/fichas_rapidas/` ou envie abaixo."
                )
                up = st.file_uploader(
                    "JSON da ficha rápida",
                    type=["json"],
                    key="ficha_ipapd_up",
                )
                ficha_data = None
                if up is not None:
                    import json as _json_f

                    try:
                        ficha_data = _json_f.loads(up.getvalue().decode("utf-8"))
                        ficha_data["_arquivo"] = up.name
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"JSON inválido: {exc}")
                elif listar_fichas():
                    ficha_data = carregar_ficha()
                    if ficha_data:
                        st.caption(f"Usando `{ficha_data.get('_arquivo')}`")
                ficha_termos = termos_ipapd_da_ficha(ficha_data)
                ficha_irs = termos_irs_da_ficha(ficha_data)

            ipapd = calcular_ipapd_proxy(
                taxa_ocupacao_pct=cap_assist.get("taxa_ocupacao_mancha")
                if cap_assist.get("leitos_ok")
                else None,
                n_us_atingidas=int(iso.get("n_us_atingidas") or 0),
                n_us_isoladas=int(iso.get("n_us_isoladas") or 0),
                pessoas_isoladas=int(iso.get("pessoas_isoladas_proxy") or 0),
                pop_exposta=pop_demanda,
                n_servicos_essenciais_mancha=n_ess_mancha,
                n_servicos_essenciais_eixo=n_ess_eixo,
                ficha_termos=ficha_termos or None,
            )
            if ipapd.get("ok"):
                st.markdown("##### IPAPD proxy (pressão assistencial)")
                p1, p2, p3 = st.columns(3)
                p1.metric(
                    "IPAPD",
                    f"{ipapd['ipapd']:.2f}".replace(".", ",")
                    if ipapd.get("ipapd") is not None
                    else "—",
                )
                p2.metric("Situação", ipapd.get("rotulo") or "—")
                p3.metric(
                    "Completude dos termos",
                    f"{100 * float(ipapd.get('completude') or 0):.0f}%",
                )
                termos = ipapd.get("termos") or {}
                det = ipapd.get("detalhe") or {}
                with st.expander("Decomposição IPAPD (O/A/P/E/C/S)", expanded=False):
                    linhas_ip = []
                    nomes = {
                        "O": "Ocupação (0,25)",
                        "A": "Aumento atendimentos (0,20)",
                        "P": "Profissionais (0,15)",
                        "E": "Perda de acesso (0,15)",
                        "C": "Autonomia crítica (0,15)",
                        "S": "Interrupção serviços (0,10)",
                    }
                    for k in ("O", "A", "P", "E", "C", "S"):
                        v = termos.get(k)
                        linhas_ip.append(
                            {
                                "termo": nomes[k],
                                "valor": "lacuna" if v is None else f"{float(v):.2f}",
                                "detalhe": det.get(k) or "",
                            }
                        )
                    st.dataframe(
                        pd.DataFrame(linhas_ip),
                        width="stretch",
                        hide_index=True,
                        height=240,
                    )
                st.caption(ipapd.get("fonte") or "")

            irs = calcular_irs_proxy(
                ficha_irs=ficha_irs or None,
                n_us_atingidas=int(iso.get("n_us_atingidas") or 0),
                n_us_isoladas=int(iso.get("n_us_isoladas") or 0),
                n_vias=int(iso.get("n_vias_interrompidas") or 0),
                n_pontes=int(iso.get("n_pontes_comprometidas") or 0),
                taxa_ocupacao_pct=cap_assist.get("taxa_ocupacao_mancha")
                if cap_assist.get("leitos_ok")
                else None,
                leitos_disponiveis=cap_assist.get("leitos_disponiveis_mancha")
                if cap_assist.get("leitos_ok")
                else None,
                leitos_totais=cap_assist.get("leitos_totais_mancha")
                if cap_assist.get("leitos_ok")
                else None,
            )
            if irs.get("ok"):
                st.markdown("##### IRS proxy (recuperação sanitária)")
                r1, r2, r3 = st.columns(3)
                r1.metric(
                    "IRS",
                    f"{irs['irs']:.2f}".replace(".", ",")
                    if irs.get("irs") is not None
                    else "—",
                )
                r2.metric("Situação", irs.get("rotulo") or "—")
                r3.metric(
                    "Completude",
                    f"{100 * float(irs.get('completude') or 0):.0f}%",
                )
                with st.expander("Decomposição IRS (11 dimensões)", expanded=False):
                    linhas_irs = []
                    termos_i = irs.get("termos") or {}
                    det_i = irs.get("detalhe") or {}
                    for k, lab in IRS_ROTULOS.items():
                        v = termos_i.get(k)
                        linhas_irs.append(
                            {
                                "dimensão": lab,
                                "valor": "lacuna" if v is None else f"{float(v):.2f}",
                                "detalhe": det_i.get(k) or "",
                            }
                        )
                    st.dataframe(
                        pd.DataFrame(linhas_irs),
                        width="stretch",
                        hide_index=True,
                        height=340,
                    )
                st.caption(
                    (irs.get("fonte") or "")
                    + " · "
                    + (irs.get("criterio_encerramento") or "")
                )

            payload_cen = {
                "barragem": str(r.get("nome") or ""),
                "municipio": str(r.get("municipio") or ""),
                "id_snisb": str(r.get("id_snisb") or ""),
                "geometria": geom_iso,
                "pop_exposta": int(pop_demanda or 0),
                "n_setores": set_kpi.get("n_setores_expostos")
                if set_kpi.get("disponivel")
                else "—",
                "n_captacoes": n_cap_c5,
                "n_escolas": n_esc_c5,
                "n_ativos": n_ativos_c5,
                "n_us_atingidas": iso.get("n_us_atingidas", 0),
                "n_us_isoladas": iso.get("n_us_isoladas", 0),
                "n_vias": iso.get("n_vias_interrompidas", 0),
                "n_pontes": iso.get("n_pontes_comprometidas", 0),
                "pessoas_isoladas": iso.get("pessoas_isoladas_proxy", 0),
                "nivel_c7": iso.get("rotulo_c7") or iso.get("nivel_c7_proxy") or "—",
                "pressao_estrutural": cap_assist.get("pressao_estrutural"),
                "leitos_disponiveis": cap_assist.get("leitos_disponiveis_mancha")
                if cap_assist.get("leitos_ok")
                else "—",
                "demanda_internacao": dem.get("demanda_internacao")
                if dem.get("ok")
                else "—",
                "demanda_agua": dem.get("demanda_agua_L_dia") if dem.get("ok") else "—",
                "ipapd": ipapd.get("ipapd") if ipapd.get("ok") else "—",
                "ipapd_rotulo": ipapd.get("rotulo") if ipapd.get("ok") else "—",
                "ipapd_completude": (
                    f"{100*float(ipapd.get('completude') or 0):.0f}%"
                    if ipapd.get("ok")
                    else "—"
                ),
                "irs": irs.get("irs") if irs.get("ok") else "—",
                "irs_rotulo": irs.get("rotulo") if irs.get("ok") else "—",
                "irs_completude": (
                    f"{100*float(irs.get('completude') or 0):.0f}%"
                    if irs.get("ok")
                    else "—"
                ),
                "pae_status": next(
                    (
                        it["status"]
                        for it in (chk_pae.get("itens") or [])
                        if it.get("codigo") == "PAE-01"
                    ),
                    "",
                ),
                "pae_zas": next(
                    (
                        it["status"]
                        for it in (chk_pae.get("itens") or [])
                        if it.get("codigo") == "PAE-04"
                    ),
                    "",
                ),
                "pae_lacunas": chk_pae.get("n_lacunas", 0),
            }
            sitrep_cen = montar_sitrep_cenario_md(payload_cen)
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "Baixar SITREP do cenário (Markdown)",
                    data=sitrep_cen.encode("utf-8"),
                    file_name=f"sitrep_cenario_{(r.get('id_snisb') or 'barragem')}.md",
                    mime="text/markdown",
                    key="sitrep_cenario_md",
                )
            with d2:
                st.download_button(
                    "Baixar KPIs do cenário (CSV)",
                    data=montar_csv_cenario(payload_cen),
                    file_name=f"kpis_cenario_{(r.get('id_snisb') or 'barragem')}.csv",
                    mime="text/csv",
                    key="kpis_cenario_csv",
                )
            if cap_assist.get("itens_mancha"):
                with st.expander("US na mancha (tipologia + leitos)", expanded=False):
                    st.dataframe(
                        pd.DataFrame(cap_assist["itens_mancha"]),
                        width="stretch",
                        hide_index=True,
                        height=220,
                    )

            from st_app.dw_status import listar_status_dw

            dw_itens = listar_status_dw()
            if dw_itens:
                with st.expander("Fontes DW / saúde (status)", expanded=False):
                    st.dataframe(
                        pd.DataFrame(dw_itens)[
                            ["extrato", "titulo", "prioridade", "pipeline", "ok", "n_linhas", "fonte"]
                        ],
                        width="stretch",
                        hide_index=True,
                        height=260,
                    )
                    st.caption(
                        "Pipeline 43=IndicaSUS · 44=SIH/SIA/SISREG/SINAN · 45=CNES LT. "
                        "Catálogo: `dados/config/dw_catalogo.json`."
                    )

        from st_app.data import TRATADOS as _TR_MB

        mb_path = _TR_MB / "mapbiomas_pressao_eixo_cuiaba.csv"
        if mb_path.is_file():
            mb = pd.read_csv(mb_path, sep=";")
            st.markdown("##### Pressão de ocupação (MapBiomas — eixo)")
            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Área urbana 2024 (eixo)",
                f"{mb['area_urbana_2024_ha'].sum():,.0f} ha".replace(",", "."),
            )
            m2.metric(
                "Crescimento 10 anos",
                f"{mb['delta_urbana_10a_ha'].sum():,.0f} ha".replace(",", "."),
            )
            m3.metric(
                "Urbana em drenagem ≤3 m",
                f"{mb['area_urbana_drenagem_ate_3m_2024_ha'].sum():,.0f} ha".replace(
                    ",", "."
                ),
            )
            st.caption(
                "MapBiomas Col.10 módulo urbano — contexto de exposição municipal "
                "(não é mancha HAND). Rode `python executar.py 41` para atualizar."
            )
            with st.expander("MapBiomas por município", expanded=False):
                st.dataframe(mb, width="stretch", hide_index=True, height=280)
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

        from st_app.indicadores import carregar_exposicao_vulneraveis
        from st_app.data import haversine_km as _hav_v
        from st_app.relevo_hand import ponto_na_mancha_hand as _pnt_hand

        vul_mapa: list[dict] = []
        vul_df = carregar_exposicao_vulneraveis()
        no_circ = pd.DataFrame()
        no_tr = pd.DataFrame()
        if not vul_df.empty:
            lat0, lon0 = float(r["latitude"]), float(r["longitude"])
            vul_df = vul_df.dropna(subset=["latitude", "longitude"]).copy()
            vul_df["dist_km"] = vul_df.apply(
                lambda row: _hav_v(
                    lat0, lon0, float(row["latitude"]), float(row["longitude"])
                ),
                axis=1,
            )
            # Exclui estabelecimentos de saúde (já cobertos pelo CNES no mapa)
            if "categoria" in vul_df.columns:
                cats = vul_df["categoria"].fillna("").astype(str).str.lower()
                vul_df = vul_df[
                    ~cats.str.contains("saúde|saude|estabelecimento", regex=True)
                ].copy()

            def _na_mancha_vul(row) -> bool:
                la, lo = float(row["latitude"]), float(row["longitude"])
                ok = False
                if mostrar_circular and row["dist_km"] <= raio:
                    ok = True
                if mostrar_trajeto and trajeto.get("ok"):
                    ok = ok or ponto_no_corredor(
                        la, lo, trajeto["polyline"], float(trajeto["largura_km"])
                    )
                if usar_hand and hand_limiar is not None:
                    ok = ok or _pnt_hand(la, lo, float(hand_limiar))
                return ok

            na = vul_df[vul_df.apply(_na_mancha_vul, axis=1)].sort_values("dist_km")
            if mostrar_circular:
                no_circ = vul_df[vul_df["dist_km"] <= raio].sort_values("dist_km")
            if trajeto.get("ok") and mostrar_trajeto:
                mask = vul_df.apply(
                    lambda row: ponto_no_corredor(
                        float(row["latitude"]),
                        float(row["longitude"]),
                        trajeto["polyline"],
                        float(trajeto["largura_km"]),
                    ),
                    axis=1,
                )
                no_tr = vul_df[mask].sort_values("dist_km")
            for row in na.head(200).itertuples():
                fam = getattr(row, "familias", None)
                try:
                    fam_n = int(float(fam)) if fam not in (None, "") and not pd.isna(fam) else None
                except (TypeError, ValueError):
                    fam_n = None
                vul_mapa.append(
                    {
                        "la": float(row.latitude),
                        "lo": float(row.longitude),
                        "no": getattr(row, "nome", None),
                        "cat": getattr(row, "categoria", None),
                        "mu": getattr(row, "municipio", None),
                        "fam": fam_n,
                        "dist": float(row.dist_km),
                    }
                )
            st.metric("Comunidades vulneráveis na mancha", len(vul_mapa))

        escolas_mapa = [
            {
                "la": it["lat"],
                "lo": it["lon"],
                "no": it.get("nome") or "Escola",
                "mu": it.get("municipio") or "",
            }
            for it in (esc_kpi.get("itens") or [])
            if esc_kpi.get("disponivel") and it.get("lat") is not None
        ]
        ativos_mapa = [
            {
                "la": it["lat"],
                "lo": it["lon"],
                "no": it.get("nome") or "",
                "mu": it.get("municipio") or "",
                "cat": it.get("categoria") or "",
                "rotulo": it.get("rotulo") or "",
            }
            for it in (ativos_kpi.get("itens") or [])
            if ativos_kpi.get("disponivel") and it.get("lat") is not None
        ]
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
            hand_poligonos=hand_info.get("poligonos") if usar_hand else None,
            hand_limiar_m=float(hand_limiar) if usar_hand and hand_limiar is not None else None,
            mostrar_hand=bool(usar_hand and hand_info.get("ok")),
            vulneraveis=vul_mapa,
            escolas=escolas_mapa,
            ativos=ativos_mapa,
            altura=560,
            autoplay=False,
        )
        components.html(html, height=580, scrolling=False)

        if mostrar_circular:
            st.subheader("Populações vulneráveis — círculo")
            if no_circ.empty:
                st.caption(
                    "Nenhuma aldeia/TI/assentamento/quilombo do eixo no raio. "
                    "Ribeirinhos ainda sem base espacial contínua."
                )
            else:
                st.dataframe(
                    no_circ[
                        [
                            c
                            for c in (
                                "nome",
                                "categoria",
                                "municipio",
                                "faixa",
                                "dist_km",
                                "familias",
                            )
                            if c in no_circ.columns
                        ]
                    ].head(40),
                    width="stretch",
                    hide_index=True,
                    height=200,
                )
        if trajeto.get("ok") and mostrar_trajeto:
            st.subheader("Populações vulneráveis — corredor hidráulico")
            if no_tr.empty:
                st.caption("Nenhuma população vulnerável do eixo no corredor.")
            else:
                st.dataframe(
                    no_tr[
                        [
                            c
                            for c in (
                                "nome",
                                "categoria",
                                "municipio",
                                "faixa",
                                "dist_km",
                                "familias",
                            )
                            if c in no_tr.columns
                        ]
                    ].head(40),
                    width="stretch",
                    hide_index=True,
                    height=200,
                )
    else:
        st.warning("Barragem sem coordenada — mapa indisponível.")

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
        "Relevo HAND: células SRTM com elevação − talvegue ≤ lâmina (piloto Manso–Cuiabá). "
        "Vias/C7 usam a geometria ativa (círculo, corredor ou HAND). "
        "Não é mancha PAE, dam break nem tempo de chegada da onda."
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
            "(círculo, corredor hidráulico ou relevo HAND). "
            "Trecho na mancha = interrompido. US fora da mancha sem caminho terrestre até o "
            "hub de Cuiabá = potencialmente isolada. Escala 0–2 espelha o C7 do IDAP.",
        ),
        (
            "Trajeto hidráulico vs círculo vs relevo (HAND)",
            "Círculo: espalha a área equivalente em disco isótropo. "
            "Trajeto: percorre a calha BHO jusante e forma um corredor com semi-largura "
            "ajustável — L ≈ área/(2×w). "
            "Relevo HAND (piloto Manso–Cuiabá): células SRTM com elevação − talvegue ≤ "
            "lâmina proxy (etapa 35 / OpenTopoData). Todos são proxies; a mancha PAE "
            "oficial (dam break) entra depois como camada própria.",
        ),
        (
            "US atingidas, vias/pontes e pessoas isoladas",
            "US atingidas = estabelecimentos CNES dentro da mancha proxy. "
            "Vias/pontes = arteriais OSM que cruzam a mancha. "
            "US isoladas = fora da mancha sem rota terrestre ao hub após o corte. "
            "Pessoas isoladas = soma da população IBGE 2022 dos municípios cuja sede "
            "(centroide) perde caminho ao hub — ordem de grandeza, não censo de desalojados.",
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


def _txt(v: object, suf: str = "") -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return "—"
    if suf and isinstance(v, (int, float)):
        return f"{float(v):.2f}{suf}".replace(".", ",")
    return s


def pagina_ficha(df: pd.DataFrame) -> None:
    st.markdown("# Barragem 360°")
    if df.empty:
        st.error("Sem dados.")
        return
    ordenado = ordenar_por_severidade(df)
    labels = [
        f"{r.nome} — {r.id_snisb} ({getattr(r, 'nivel', '—')})"
        for r in ordenado.itertuples()
    ]
    pre_360 = str(st.session_state.pop("barragem_360_id", "") or "")
    idx360 = 0
    if pre_360:
        for i, lab in enumerate(labels):
            if f" — {pre_360} " in lab:
                idx360 = i
                break
    escolha = st.selectbox("Barragem", labels, index=idx360)
    bid = escolha.split(" — ")[1].split(" ")[0]
    st.session_state["barragem_selecionada_id"] = bid
    r = df[df["id_snisb"] == bid].iloc[0]
    st.markdown(f"## {r['nome']}")
    st.markdown(
        f"{_badge(r['nivel'])} &nbsp; IDAP **{_txt(r.get('idap'))}/100** · "
        f"completude {_txt(r.get('completude'))} · {_txt(r.get('confiabilidade'))}",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown("### Identificação e engenharia")
        st.write(
            {
                "SNISB": _txt(r.get("id_snisb")),
                "Município sede": _txt(r.get("municipio_sede") or r.get("municipio")),
                "Empreendedor": _txt(r.get("empreendedor")),
                "Tipo empreendedor": _txt(r.get("tipo_empreendedor")),
                "Órgão fiscalizador": _txt(r.get("orgao_fiscalizador")),
                "Uso principal": _txt(r.get("uso_principal")),
                "Fase de vida": _txt(r.get("fase_de_vida")),
                "Classe": _txt(r.get("classe")),
                "Material": _txt(r.get("tipo_material")),
                "Altura (m)": _txt(r.get("altura_m")),
                "Capacidade (hm³)": _txt(r.get("capacidade_hm3")),
                "PAE": rotulo_sim_nao(r.get("possui_pae")),
                "Regulada PNSB": rotulo_regulada(
                    r.get("indicador_regulada"), r.get("regulada_pelo_pnsb")
                ),
                "Última inspeção": _txt(r.get("data_ultima_inspecao")),
                "CRI / DPA": f"{_txt(r.get('categoria_risco'))} / {_txt(r.get('dano_potencial_associado'))}",
                "Pop. jusante (SIGBM)": _txt(r.get("sigbm_populacao_jusante")),
                "Pessoas afetadas (SIGBM)": _txt(r.get("sigbm_pessoas_afetadas")),
                "Status DCE (SIGBM)": _txt(r.get("sigbm_status_dce")),
                "Alteamento / minério": (
                    f"{_txt(r.get('sigbm_tipo_alteamento'))} / {_txt(r.get('sigbm_minerio'))}"
                ),
                "Afetados (Otto)": _txt(r.get("municipios_potencialmente_afetados")),
                "Nº mun. afetados / extraterr.": (
                    f"{_txt(r.get('n_municipios_afetados'))} / "
                    f"{_txt(r.get('n_municipios_extraterritoriais'))}"
                ),
            }
        )
        from st_app.pae_checklist import (
            checklist_para_dataframe,
            exportar_checklist_csv,
            montar_checklist_pae,
        )

        chk_det = montar_checklist_pae(r)
        with st.expander("Checklist PAE / PAEBM", expanded=False):
            st.dataframe(
                checklist_para_dataframe(chk_det),
                width="stretch",
                hide_index=True,
                height=260,
            )
            st.download_button(
                "Baixar checklist PAE (CSV)",
                data=exportar_checklist_csv(chk_det),
                file_name=f"checklist_pae_{(r.get('id_snisb') or 'barragem')}.csv",
                mime="text/csv",
                key="checklist_pae_detalhe_csv",
            )
        st.markdown("### Dimensões IDAP")
        st.bar_chart(
            pd.Series(
                {
                    "A hidro": float(r.get("pontos_a") or 0),
                    "B estrutural": float(r.get("pontos_b") or 0),
                    "C impacto": float(r.get("pontos_c") or 0),
                    "D articulação": float(r.get("pontos_d") or 0),
                }
            )
        )
    with b:
        st.markdown("### Hidro / alertas")
        st.write(
            {
                "Chuva 24 h (mm)": _txt(r.get("chuva_24h_mm")),
                "Chuva 72 h (mm)": _txt(r.get("chuva_72h_mm")),
                "Prevista 24–72 h (mm)": _txt(r.get("chuva_prevista_24_72h_mm")),
                "Percentil": _txt(r.get("percentil_climatologico")),
                "Saturação": _txt(r.get("saturacao_antecedente")),
                "Alerta hidro": _txt(r.get("nivel_alerta_hidro")),
                "Cemaden": _txt(r.get("alerta_cemaden")),
                "Integrado SIS": _txt(r.get("nivel_alerta_integrado")),
                "GloFAS m³/s": _txt(r.get("vazao_prevista_glofas_m3s")),
                "Alertável": rotulo_sim_nao(r.get("alertavel")),
                "Regras disparadas": _txt(r.get("regras_disparadas")),
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
                popup=folium.Popup(
                    f"<b>{r['nome']}</b><br>{r.get('municipio_sede')}<br>"
                    f"{r.get('nivel')} · IDAP {r.get('idap')}",
                    max_width=260,
                ),
            ).add_to(m)
            st_folium(m, height=300, returned_objects=[])
        st.caption(
            "Campos vazios no cadastro SNISB/SIGBM aparecem como «—». "
            "Valores 1/2/3 de regulada foram traduzidos para texto legível."
        )
    if r.get("lacunas"):
        st.warning(f"Lacunas: {r['lacunas']}")
    n1, n2 = st.columns(2)
    if n1.button("Simular esta barragem"):
        st.session_state["barragem_sim_id"] = bid
        from st_app.paginas_onda import ir_para

        ir_para("Situação", TELA_SIMULACAO)
    if n2.button("Registrar notificação / impacto"):
        st.session_state["barragem_notif_id"] = bid
        from st_app.paginas_onda import ir_para

        ir_para("Ação", "Notificações e impactos")


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
        st.session_state["jornada"] = "Território"
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Visão territorial"

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
            "Território → Situação → Ação → Dados</p>",
            unsafe_allow_html=True,
        )
        if st.session_state.get("jornada") not in JORNADAS:
            st.session_state["jornada"] = "Território"
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
    if pagina == "Visão territorial":
        pagina_visao_territorial(df)
    elif pagina == "Comando estadual":
        pagina_comando(df)
    elif pagina == "Hidro municipal":
        pagina_hidro(carregar_hidro_mun(), carregar_populacao())
    elif pagina == "Eixo Manso–Cuiabá":
        pagina_piloto(carregar_piloto())
    elif pagina == "VIGIPÓS O/E":
        pagina_vigipos_oe()
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
    elif pagina == "Notificações e impactos":
        pagina_notificacoes_impactos(df)
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
