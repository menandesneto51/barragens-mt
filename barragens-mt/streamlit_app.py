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
    card_kpi,
    carregar_cnes_pontos,
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
from st_app.paginas_onda import (
    bloco_quase_atencao,
    bloco_sanitario_e_historico,
    pagina_alertabilidade_despacho,
    pagina_confirmacao_persistente,
    pagina_extraterritorial,
    pagina_municipio_360,
    pagina_rag_docs,
    pagina_regiao_saude,
    pagina_vulneraveis,
)
from st_app.style import CSS

st.set_page_config(
    page_title="VIGIBARRAGENS–MT",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)


def _badge(nivel: str) -> str:
    cor = CORES_NIVEL.get(nivel, "#888")
    return f'<span class="badge" style="background:{cor}">{nivel}</span>'


def _semaforo(df: pd.DataFrame) -> str:
    ordem = ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"]
    for n in ordem:
        if (df["nivel"] == n).any():
            return n
    return "Verde"


def pagina_comando(df: pd.DataFrame) -> None:
    st.markdown("# VIGIBARRAGENS–MT")
    st.markdown(
        '<p class="nota">Comando estadual — prontidão sanitária diante de barragens, '
        "clima e previsão. Primeira leitura em linguagem operacional (sem siglas).</p>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.error("Base de alerta ausente. Rode `python executar.py 16 17` no projeto.")
        return

    munis = municipios_catalogo(df)
    from st_app.indicadores import carregar_contatos

    contatos = carregar_contatos()
    regioes = (
        sorted(contatos["regiao_saude"].dropna().unique().tolist())
        if not contatos.empty and "regiao_saude" in contatos.columns
        else []
    )
    munis_por_regiao: dict[str, set[str]] = {}
    if regioes and "municipio" in contatos.columns:
        for _, row in contatos.dropna(subset=["regiao_saude", "municipio"]).iterrows():
            munis_por_regiao.setdefault(str(row["regiao_saude"]), set()).add(str(row["municipio"]).strip())

    with st.sidebar:
        st.header("Filtros")
        mun_sel = st.selectbox(
            "Município",
            ["(estado todo)"] + munis,
            help="Inclui sede da barragem e municípios potencialmente afetados a jusante "
            "(a barragem pode estar em outro município).",
        )
        reg_sel = st.selectbox(
            "Região de saúde",
            ["(todas)"] + regioes,
            help="Filtra municípios do cadastro de contatos do eixo (expansão estadual pendente).",
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
            f'<p class="nota"><b>Recorte: {mun_ativo}</b> — lista barragens cuja sede é este '
            "município <b>ou</b> que o têm como potencialmente afetado a jusante em caso de "
            "rompimento (a estrutura pode estar em outro município).</p>",
            unsafe_allow_html=True,
        )
    elif reg_sel != "(todas)" and reg_sel in munis_por_regiao:
        alvos = munis_por_regiao[reg_sel]
        mask = view["municipio_sede"].isin(alvos) if "municipio_sede" in view.columns else pd.Series(False, index=view.index)
        if "municipios_potencialmente_afetados" in view.columns:
            mask = mask | view["municipios_potencialmente_afetados"].fillna("").apply(
                lambda t: any(m in str(t).split("|") for m in alvos)
            )
        view = view.loc[mask].copy()
        st.markdown(
            f'<p class="nota"><b>Região de saúde: {reg_sel}</b> — '
            f"{len(alvos)} município(s) no cadastro de contatos.</p>",
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
    st.markdown(
        f"**Prontidão no recorte:** {_badge(sem)} — {len(base_kpi)} barragens",
        unsafe_allow_html=True,
    )

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

    cards = [
        card_kpi("Barragens no recorte", str(len(base_kpi)), sev="sev-neutro"),
        card_kpi(
            "Em atenção ou pior",
            str(amarelo_mais),
            sev=severidade_pct(pct_atencao),
            delta=_delta(tend.get("amarelo_mais")),
            nota=f"{pct_atencao:.0f}% do recorte",
        ),
        card_kpi(
            "Só faixa amarela",
            str(int(cont.get("Amarelo", 0))),
            sev="sev-atencao" if cont.get("Amarelo", 0) else "sev-ok",
            delta=_delta(tend.get("amarelo")),
        ),
        card_kpi(
            "Situação estável (verde)",
            str(int(cont.get("Verde", 0))),
            sev="sev-ok",
            delta=_delta(tend.get("verde")),
        ),
        card_kpi(
            "Eixo Manso–Cuiabá",
            str(piloto_n),
            sev="sev-neutro",
            nota=f"{piloto_ama} em atenção+",
        ),
        card_kpi(
            "Com canal de alerta",
            str(int(alertaveis)),
            sev="sev-ok" if alertaveis else "sev-atencao",
        ),
    ]
    st.markdown('<div class="grade-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    proj = projecao_semana(base_kpi)
    sev_t, msg_t = tendencia_climatica_texto(proj, base_kpi)
    st.markdown(
        f'<div class="tend-box {sev_t}"><b>Tendência para os próximos dias</b><br>{msg_t}</div>',
        unsafe_allow_html=True,
    )

    if mun_ativo:
        pagina_municipio_360(base_kpi, mun_ativo)
        bloco_quase_atencao(base_kpi)
        st.divider()
    else:
        bloco_sanitario_e_historico(base_kpi, mun_ativo=None)
        bloco_quase_atencao(base_kpi)

    st.subheader("Painel de situação (cores = gravidade)")
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
    chuva24 = float(base_kpi["chuva_24h_mm"].max()) if "chuva_24h_mm" in base_kpi.columns else None
    chuva72 = float(base_kpi["chuva_72h_mm"].max()) if "chuva_72h_mm" in base_kpi.columns else None
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
    ext = (
        int(
            (
                pd.to_numeric(base_kpi.get("n_municipios_extraterritoriais"), errors="coerce").fillna(
                    0
                )
                > 0
            ).sum()
        )
        if "n_municipios_extraterritoriais" in base_kpi.columns
        else 0
    )

    def _mm(v):
        return "—" if v is None else f"{v:.1f} mm".replace(".", ",")

    risco_cards = [
        card_kpi(
            "Índice de alerta máximo",
            f"{idap_max:.0f}",
            sev=severidade_pct(idap_max),
            nota="0–100 · quanto maior, mais atenção",
        ),
        card_kpi(
            "Índice de alerta médio",
            f"{idap_med:.1f}".replace(".", ","),
            sev=severidade_pct(idap_med),
        ),
        card_kpi(
            "Pressão climática média",
            f"{a_pct:.0f}%",
            sev=severidade_pct(a_pct),
            nota=f"{a_med:.1f} de 30 pontos".replace(".", ","),
        ),
        card_kpi(
            "Condição da estrutura (média)",
            f"{b_pct:.0f}%",
            sev=severidade_pct(b_pct),
            nota=f"{b_med:.1f} de 30 pontos".replace(".", ","),
        ),
        card_kpi(
            "Impacto sanitário potencial",
            f"{c_pct:.0f}%",
            sev=severidade_pct(c_pct),
            nota=f"{c_med:.1f} de 25 pontos".replace(".", ","),
        ),
        card_kpi(
            "Déficit de capacidade de resposta",
            f"{d_pct:.0f}%",
            sev=severidade_pct(d_pct),
            nota=f"{d_med:.1f} de 15 pontos".replace(".", ","),
        ),
        card_kpi(
            "Barragens com pressão climática",
            str(pressao_a),
            sev=severidade_pct(100.0 * pressao_a / max(len(base_kpi), 1)),
        ),
        card_kpi(
            "Chuva nas últimas 24 h (máx.)",
            _mm(chuva24),
            sev=severidade_pct(None if chuva24 is None else min(100, chuva24)),
        ),
        card_kpi(
            "Chuva nas últimas 72 h (máx.)",
            _mm(chuva72),
            sev=severidade_pct(None if chuva72 is None else min(100, chuva72 * 0.5)),
        ),
        card_kpi(
            "Chuva prevista (próximos dias)",
            _mm(prev),
            sev=severidade_pct(
                None
                if prev is None
                else (100 if prev >= 140 else 70 if prev >= 80 else 40 if prev >= 40 else 10)
            ),
        ),
        card_kpi(
            "Alertas oficiais de chuva/hidro",
            str(cem),
            sev="sev-alto" if cem else "sev-ok",
        ),
        card_kpi(
            "Alertas externos / previsão extrema",
            str(n_regras),
            sev="sev-elevado" if n_regras else "sev-ok",
        ),
        card_kpi(
            "Cadastro: risco estrutural alto",
            str(cri_alto),
            sev="sev-alto" if cri_alto else "sev-ok",
        ),
        card_kpi(
            "Cadastro: dano potencial alto",
            str(dpa_alto),
            sev="sev-alto" if dpa_alto else "sev-ok",
        ),
        card_kpi(
            "Impacto possível fora da sede",
            str(ext),
            sev="sev-atencao" if ext else "sev-ok",
        ),
    ]
    st.markdown(
        '<div class="grade-kpis">' + "".join(risco_cards) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Verde = confortável · amarelo = atenção · laranja/vermelho/roxo = gravidade crescente. "
        "Pressão climática em % do teto (ex.: 90% = cenário alto, borda vermelha)."
    )

    view = view.sort_values("idap_n", ascending=False)
    esquerda, direita = st.columns([1.35, 1])
    with esquerda:
        st.subheader("Mapa por faixa de prontidão")
        pts = view.dropna(subset=["latitude", "longitude"])
        if pts.empty:
            st.info("Sem coordenadas no recorte filtrado.")
        else:
            m = folium.Map(location=[-13.0, -55.8], zoom_start=5, tiles="OpenStreetMap")
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
            st_folium(m, width=None, height=520, returned_objects=[])

    with direita:
        st.subheader("Top 15 — olhar primeiro")
        cols_top = [
            c
            for c in (
                "idap",
                "nivel",
                "nome",
                "municipio_sede",
                "papel_municipio",
                "pontos_a",
                "chuva_24h_mm",
                "chuva_prevista_24_72h_mm",
                "alertavel",
            )
            if c in view.columns
        ]
        if "completude" in view.columns and "completude" not in cols_top:
            cols_top.append("completude")
        top = view.head(15)[cols_top].rename(
            columns={
                "idap": "Índice",
                "nivel": "Prontidão",
                "nome": "Barragem",
                "municipio_sede": "Sede",
                "papel_municipio": "Papel no município",
                "pontos_a": "Pressão clima",
                "chuva_24h_mm": "Chuva 24h",
                "chuva_prevista_24_72h_mm": "Chuva prevista",
                "alertavel": "Alertável",
                "completude": "Completude",
            }
        )
        st.caption("Completude baixa no Top 15 = risco de falso verde / índice frágil.")
        st.dataframe(top, use_container_width=True, hide_index=True, height=520)

    st.subheader(f"Fila operacional ({len(view)})")
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
        use_container_width=True,
        hide_index=True,
        height=420,
    )


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
    st.dataframe(mostrar, use_container_width=True, hide_index=True, height=400)


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
        use_container_width=True,
        hide_index=True,
        height=480,
    )


def _fmt_br(valor: float, casas: int = 1, sufixo: str = "") -> str:
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto}{sufixo}"


def pagina_simulacao(df: pd.DataFrame) -> None:
    st.markdown("# Simulação volume → área")
    st.markdown(
        '<p class="nota">Proxy geométrico — <b>não</b> é mancha oficial nem ordem de evacuação. '
        "O rompimento afeta população e a <b>capacidade de resposta local</b> "
        "(unidades de saúde no buffer).</p>",
        unsafe_allow_html=True,
    )
    base = df.dropna(subset=["capacidade_hm3"]).copy()
    base = base[base["capacidade_hm3"] > 0]
    if base.empty:
        st.warning("Sem volumes no inventário.")
        return
    recorte = st.radio("Recorte", ["Eixo Manso–Cuiabá", "Top 40 volumes", "Todas com volume"], horizontal=True)
    if recorte == "Eixo Manso–Cuiabá":
        base = base[base.get("piloto", False) == True]  # noqa: E712
    elif recorte == "Top 40 volumes":
        base = base.sort_values("capacidade_hm3", ascending=False).head(40)
    opcoes = {
        f"{r['nome']} ({r['id_snisb']}) — {r['capacidade_hm3']:.1f} hm³": r["id_snisb"]
        for _, r in base.sort_values("capacidade_hm3", ascending=False).iterrows()
    }
    if not opcoes:
        st.info("Nenhuma barragem no recorte.")
        return
    escolha = st.selectbox("Barragem", list(opcoes.keys()))
    bid = opcoes[escolha]
    r = base[base["id_snisb"] == bid].iloc[0]
    frac = st.slider("Fração liberada (%)", 5, 100, 50, 5) / 100
    prof = st.slider("Profundidade média da lâmina (m)", 0.5, 8.0, 2.0, 0.5)
    liberado = float(r["capacidade_hm3"]) * frac
    area = liberado / prof
    raio = math.sqrt(area / math.pi)

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
            cnes, float(r["latitude"]), float(r["longitude"]), raio
        )
    n_us = len(us_buf)
    n_hosp = int(us_buf["hospitalar"].sum()) if n_us and "hospitalar" in us_buf.columns else 0
    n_upa = int(us_buf["upa_ps"].sum()) if n_us and "upa_ps" in us_buf.columns else 0
    n_ubs = int(us_buf["ubs_esf"].sum()) if n_us and "ubs_esf" in us_buf.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Volume liberado", _fmt_br(liberado, 1, " hm³"))
    k2.metric("Área equivalente", _fmt_br(area, 1, " km²"))
    k3.metric("Raio equivalente", _fmt_br(raio, 2, " km"))
    k4.metric("IDAP", f"{r.get('idap', '—')} ({r.get('nivel', '—')})")
    p1, p2, p3, p4 = st.columns(4)
    n_prio = (
        int(us_buf["prioritario"].sum())
        if n_us and "prioritario" in us_buf.columns
        else (n_hosp + n_upa + n_ubs)
    )
    p1.metric("População estimada", f"{pop_n:,}".replace(",", "."))
    p2.metric("US no buffer (todas)", n_us)
    p3.metric("Hospital / UPA", f"{n_hosp} / {n_upa}")
    p4.metric("Prioritárias (APS/urg.)", n_prio)
    st.caption(
        f"Método da população: `{metodo}` — {est.get('detalhe', '')} "
        "CNES: **todas** as unidades com coordenada no raio "
        "(rede do eixo Cuiabá; fora da região o contador pode ficar vazio)."
    )

    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        # Todos os CNES da região: a animação recalcula o buffer ao expandir o raio.
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
        html = html_mapa_simulacao(
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            nome=str(r["nome"]),
            volume_hm3=float(r["capacidade_hm3"]),
            fracao=frac,
            profundidade_m=float(prof),
            pop_est=pop_n,
            metodo_pop=metodo,
            cnes=cnes_todos,
            altura=480,
            autoplay=False,
        )
        components.html(html, height=500, scrolling=False)
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
        no_buf = vul[vul["dist_km"] <= raio].sort_values("dist_km")
        st.subheader("Populações vulneráveis no buffer (proxy)")
        if no_buf.empty:
            st.caption("Nenhuma aldeia/assentamento/quilombo do eixo dentro do raio equivalente.")
        else:
            st.dataframe(
                no_buf[
                    [c for c in ("nome", "categoria", "municipio", "faixa", "dist_km", "familias") if c in no_buf.columns]
                ].head(40),
                use_container_width=True,
                hide_index=True,
                height=220,
            )

    if n_us:
        st.markdown(
            f'<p class="lista-us-titulo">US prioritárias no buffer ({n_us})</p>',
            unsafe_allow_html=True,
        )
        mostrar = us_buf[
            ["nome", "tipo", "municipio", "dist_km", "hospitalar", "upa_ps", "ubs_esf"]
        ].copy()
        mostrar["dist_km"] = mostrar["dist_km"].round(2)
        st.dataframe(mostrar.head(60), use_container_width=True, hide_index=True, height=280)
    else:
        st.info(
            "Nenhuma US CNES prioritária com coordenada neste raio "
            "(cobertura atual: eixo Cuiabá)."
        )

    st.caption(
        "Fórmula: área_km² = (hm³ × fração) / profundidade_m. "
        "Use ▶ Animar no mapa para ver a expansão da mancha proxy e o ingresso de US. "
        "Não substitui PAE / dam break."
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

    def _tip(uso: object) -> str:
        u = str(uso or "").lower()
        regras = [
            ("Irrigação", ("irrig",)),
            ("Rejeito / mineração", ("rejeito", "sedimento", "miner")),
            ("Hidroelétrica", ("hidroel", "hidrel")),
            ("Aquicultura", ("aquicult",)),
            ("Abastecimento humano", ("abastec", "humano")),
            ("Dessedentação animal", ("dessedent",)),
            ("Recreação / paisagismo", ("recrea", "paisag")),
        ]
        for rotulo, chaves in regras:
            if any(c in u for c in chaves):
                return rotulo
        return "Industrial / outros"

    cores = {
        "Irrigação": "#2a4aad",
        "Rejeito / mineração": "#b91c1c",
        "Hidroelétrica": "#0e7490",
        "Aquicultura": "#0369a1",
        "Abastecimento humano": "#1b3281",
        "Dessedentação animal": "#854d0e",
        "Recreação / paisagismo": "#64748b",
        "Industrial / outros": "#475569",
    }
    uso_col = "uso_principal" if "uso_principal" in base.columns else None
    if uso_col is None:
        st.error("Coluna uso_principal ausente no inventário mesclado.")
        return
    base["tipologia"] = base[uso_col].map(_tip)
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
            popup=f"{r.nome}<br>{r.tipologia}<br>{getattr(r, uso_col, '')}",
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
    with st.sidebar:
        st.markdown('<p class="marca">VIGIBARRAGENS–MT</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="submarca">Saúde 360 · SES-MT / CIEVS</p>',
            unsafe_allow_html=True,
        )
        pagina = st.radio(
            "Telas",
            [
                "Comando estadual",
                "Hidro municipal",
                "Eixo Manso–Cuiabá",
                "Simulação volume/área",
                "Barragem 360°",
                "Populações vulneráveis",
                "Impacto extraterritorial",
                "Mapa por tipologia",
                "Interpretação / KPIs",
                "Alertabilidade / despacho",
                "Confirmação persistente",
                "Região de saúde",
                "Documentos (RAG leve)",
                "Fila de alertas",
                "Ficha rápida",
                "Confirmação (HTML)",
                "Inventário",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption(f"Dados: `{(Path(__file__).parent / 'dados' / 'tratados').as_posix()}`")

    df = carregar_idap()
    if pagina == "Comando estadual":
        pagina_comando(df)
    elif pagina == "Hidro municipal":
        pagina_hidro(carregar_hidro_mun(), carregar_populacao())
    elif pagina == "Eixo Manso–Cuiabá":
        pagina_piloto(carregar_piloto())
    elif pagina == "Simulação volume/área":
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
    else:
        pagina_ficha(df)


if __name__ == "__main__":
    main()
