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
    carregar_cnes_pontos,
    carregar_hidro_mun,
    carregar_idap,
    carregar_piloto,
    carregar_populacao,
    cnes_no_buffer,
    estimar_pop_cenario,
)
from st_app.mapa_sim import html_mapa_simulacao
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
        '<p class="nota">Comando estadual — IDAP + hidro SisClima/TITAN + previsão '
        "ECMWF/GloFAS. Dados do pipeline local (CSVs tratados).</p>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.error("Base IDAP ausente. Rode `python executar.py 16 17` no projeto.")
        return

    sem = _semaforo(df)
    st.markdown(
        f"**Prontidão estadual:** {_badge(sem)} — {len(df)} barragens monitoradas",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    cont = df["nivel"].value_counts()
    amarelo_mais = int(
        cont.get("Amarelo", 0)
        + cont.get("Laranja", 0)
        + cont.get("Vermelho", 0)
        + cont.get("Roxo", 0)
    )
    c1.metric("Monitoradas", len(df))
    c2.metric("Amarelo+", amarelo_mais)
    c3.metric("Amarelo", int(cont.get("Amarelo", 0)))
    c4.metric("Verde", int(cont.get("Verde", 0)))
    c5.metric("Piloto", int(df["piloto"].sum()) if "piloto" in df.columns else 0)
    alertaveis = (df.get("alertavel") == "sim").sum() if "alertavel" in df.columns else 0
    c6.metric("Alertáveis", int(alertaveis))

    st.subheader("Indicadores de risco")
    idap_max = float(df["idap_n"].max()) if "idap_n" in df.columns else 0
    idap_med = float(df["idap_n"].mean()) if "idap_n" in df.columns else 0
    pressao_a = int((df.get("pontos_a", 0) > 0).sum()) if "pontos_a" in df.columns else 0
    r1 = st.columns(5)
    r1[0].metric("IDAP máximo", f"{idap_max:.0f}")
    r1[1].metric("IDAP médio", f"{idap_med:.1f}")
    r1[2].metric("Com pressão A", pressao_a)
    r1[3].metric(
        "A médio",
        f"{df['pontos_a'].mean():.1f}" if "pontos_a" in df.columns else "—",
    )
    r1[4].metric(
        "B médio",
        f"{df['pontos_b'].mean():.1f}" if "pontos_b" in df.columns else "—",
    )
    r2 = st.columns(5)
    r2[0].metric(
        "Chuva 24h máx.",
        f"{df['chuva_24h_mm'].max():.1f} mm" if "chuva_24h_mm" in df.columns else "—",
    )
    r2[1].metric(
        "Chuva 72h máx.",
        f"{df['chuva_72h_mm'].max():.1f} mm" if "chuva_72h_mm" in df.columns else "—",
    )
    r2[2].metric(
        "Prevista 24–72h máx.",
        f"{df['chuva_prevista_24_72h_mm'].max():.1f} mm"
        if "chuva_prevista_24_72h_mm" in df.columns
        else "—",
    )
    cem = 0
    if "alerta_cemaden_nivel" in df.columns:
        cem = int(
            df["alerta_cemaden_nivel"]
            .fillna("")
            .str.lower()
            .isin(["laranja", "vermelha", "vermelho", "roxa", "roxo", "moderado", "alto"])
            .sum()
        )
    r2[3].metric("Cemaden ativos", cem)
    regras = df.get("regras_disparadas", pd.Series(dtype=str)).fillna("")
    r2[4].metric("Com R10–R12", int(regras.str.contains(r"R1[012]").sum()))
    r3 = st.columns(5)
    r3[0].metric(
        "C médio",
        f"{df['pontos_c'].mean():.1f}" if "pontos_c" in df.columns else "—",
    )
    r3[1].metric(
        "D médio",
        f"{df['pontos_d'].mean():.1f}" if "pontos_d" in df.columns else "—",
    )
    cri_alto = (
        int(df["categoria_risco"].fillna("").str.lower().eq("alto").sum())
        if "categoria_risco" in df.columns
        else 0
    )
    dpa_alto = (
        int(df["dano_potencial_associado"].fillna("").str.lower().eq("alto").sum())
        if "dano_potencial_associado" in df.columns
        else 0
    )
    r3[2].metric("CRI Alto", cri_alto)
    r3[3].metric("DPA Alto", dpa_alto)
    ext = (
        int((pd.to_numeric(df.get("n_municipios_extraterritoriais"), errors="coerce").fillna(0) > 0).sum())
        if "n_municipios_extraterritoriais" in df.columns
        else 0
    )
    r3[4].metric("Impacto fora da sede", ext)
    st.caption(
        "Indicadores agregados do estado. Chuva/previsão = máximo entre barragens. "
        "Cemaden conta sedes com alerta hidrológico/chuva acima de verde."
    )

    with st.sidebar:
        st.header("Filtros")
        niveis = st.multiselect(
            "Nível IDAP",
            ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"],
            default=["Roxo", "Vermelho", "Laranja", "Amarelo"],
        )
        so_piloto = st.checkbox("Só piloto Manso–Cuiabá", value=False)
        busca = st.text_input("Busca (nome ou SNISB)", "")
        orgao = st.text_input("Órgão", "")

    view = df.copy()
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

    view = view.sort_values("idap_n", ascending=False)

    esquerda, direita = st.columns([1.35, 1])
    with esquerda:
        st.subheader("Mapa por faixa IDAP")
        pts = view.dropna(subset=["latitude", "longitude"])
        if pts.empty:
            st.info("Sem coordenadas no recorte filtrado.")
        else:
            m = folium.Map(location=[-13.0, -55.8], zoom_start=5, tiles="OpenStreetMap")
            for _, r in pts.iterrows():
                cor = CORES_NIVEL.get(r["nivel"], "#888")
                critico = r["nivel"] != "Verde"
                folium.CircleMarker(
                    location=[r["latitude"], r["longitude"]],
                    radius=9 if critico else 4,
                    color="#111" if critico else "#555",
                    weight=2 if critico else 0.5,
                    fill=True,
                    fill_color=cor,
                    fill_opacity=0.9 if critico else 0.55,
                    popup=folium.Popup(
                        f"<b>{r['nome']}</b><br>IDAP {r.get('idap','—')} — {r['nivel']}<br>"
                        f"Sede: {r.get('municipio_sede','—')}<br>"
                        f"Chuva 24/72h: {r.get('chuva_24h_mm','—')} / {r.get('chuva_72h_mm','—')} mm<br>"
                        f"Prevista 24–72h: {r.get('chuva_prevista_24_72h_mm','—')} mm",
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
        top = view.head(15)[
            [
                c
                for c in (
                    "idap",
                    "nivel",
                    "nome",
                    "municipio_sede",
                    "pontos_a",
                    "chuva_24h_mm",
                    "chuva_prevista_24_72h_mm",
                    "alertavel",
                )
                if c in view.columns
            ]
        ]
        st.dataframe(top, use_container_width=True, hide_index=True, height=520)

    st.subheader(f"Fila operacional ({len(view)})")
    cols = [
        c
        for c in (
            "idap",
            "nivel",
            "nome",
            "municipio_sede",
            "orgao_fiscalizador",
            "pontos_a",
            "pontos_b",
            "pontos_c",
            "pontos_d",
            "chuva_72h_mm",
            "chuva_prevista_24_72h_mm",
            "alerta_cemaden_nivel",
            "nivel_alerta_integrado",
            "regras_disparadas",
            "alertavel",
        )
        if c in view.columns
    ]
    st.dataframe(view[cols], use_container_width=True, hide_index=True, height=360)
    st.caption(
        "Completude baixa ≠ verde seguro. Hidro = máximo sede+montante (Otto). "
        "Alertas Cemaden/INMET no município-sede. A3 = Open-Meteo ECMWF."
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
    st.markdown("# Piloto Manso–Cuiabá")
    st.markdown(
        '<p class="nota">Ciclo dado → IDAP → alerta no eixo que pode afetar Cuiabá / VG.</p>',
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
    recorte = st.radio("Recorte", ["Piloto", "Top 40 volumes", "Todas com volume"], horizontal=True)
    if recorte == "Piloto":
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
    p1.metric("População estimada", f"{pop_n:,}".replace(",", "."))
    p2.metric("US no buffer", n_us)
    p3.metric("Hospital / UPA", f"{n_hosp} / {n_upa}")
    p4.metric("UBS / ESF", n_ubs)
    st.caption(
        f"Método da população: `{metodo}` — {est.get('detalhe', '')} "
        "CNES: estabelecimentos prioritários com coordenada no raio "
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
            "Amarelo+ / semáforo estadual",
            "Contagem de barragens em Amarelo ou acima. Define a prontidão agregada do estado "
            "no comando (pior nível presente na base).",
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
                "Piloto Manso–Cuiabá",
                "Simulação volume/área",
                "Barragem 360°",
                "Interpretação / KPIs",
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
    elif pagina == "Piloto Manso–Cuiabá":
        pagina_piloto(carregar_piloto())
    elif pagina == "Simulação volume/área":
        pagina_simulacao(df)
    elif pagina == "Interpretação / KPIs":
        pagina_interpretacao()
    else:
        pagina_ficha(df)


if __name__ == "__main__":
    main()
