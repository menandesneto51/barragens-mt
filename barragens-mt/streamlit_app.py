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
from streamlit_folium import st_folium

from st_app.data import (
    CORES_NIVEL,
    carregar_hidro_mun,
    carregar_idap,
    carregar_piloto,
    carregar_populacao,
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
    c1.metric("Monitoradas", len(df))
    c2.metric("Amarelo+", int(cont.get("Amarelo", 0) + cont.get("Laranja", 0) + cont.get("Vermelho", 0) + cont.get("Roxo", 0)))
    c3.metric("Amarelo", int(cont.get("Amarelo", 0)))
    c4.metric("Verde", int(cont.get("Verde", 0)))
    c5.metric("Piloto", int(df["piloto"].sum()) if "piloto" in df.columns else 0)
    alertaveis = (df.get("alertavel") == "sim").sum() if "alertavel" in df.columns else 0
    c6.metric("Alertáveis", int(alertaveis))

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


def pagina_simulacao(df: pd.DataFrame) -> None:
    st.markdown("# Simulação volume → área")
    st.markdown(
        '<p class="nota">Proxy geométrico — <b>não</b> é mancha oficial nem ordem de evacuação.</p>',
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
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Volume liberado", f"{liberado:,.1f} hm³".replace(",", "X").replace(".", ",").replace("X", "."))
    k2.metric("Área equivalente", f"{area:,.1f} km²".replace(",", "X").replace(".", ",").replace("X", "."))
    k3.metric("Raio equivalente", f"{raio:,.2f} km".replace(",", "X").replace(".", ",").replace("X", "."))
    k4.metric("IDAP", f"{r.get('idap','—')} ({r.get('nivel','—')})")
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")):
        m = folium.Map(
            location=[r["latitude"], r["longitude"]],
            zoom_start=9,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
        )
        folium.Circle(
            location=[r["latitude"], r["longitude"]],
            radius=raio * 1000,
            color="#c2410c",
            fill=True,
            fill_color="#fb923c",
            fill_opacity=0.35,
            popup=f"Área proxy {area:.1f} km²",
        ).add_to(m)
        folium.CircleMarker(
            [r["latitude"], r["longitude"]],
            radius=8,
            color="#fff",
            fill=True,
            fill_color="#ea580c",
            fill_opacity=1,
            popup=r["nome"],
        ).add_to(m)
        st_folium(m, width=None, height=480, returned_objects=[])
    st.caption("Fórmula: área_km² = (hm³ × fração) / profundidade_m. Não substitui PAE/dam break.")


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
        st.markdown("### VIGIBARRAGENS–MT")
        st.caption("Saúde 360 · SES-MT / CIEVS")
        pagina = st.radio(
            "Telas",
            [
                "Comando estadual",
                "Hidro municipal",
                "Piloto Manso–Cuiabá",
                "Simulação volume/área",
                "Barragem 360°",
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
    else:
        pagina_ficha(df)


if __name__ == "__main__":
    main()
