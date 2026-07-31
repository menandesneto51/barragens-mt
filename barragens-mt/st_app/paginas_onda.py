"""Páginas e blocos da Onda 1–3 (sanitário, vulneráveis, despacho, RAG)."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from st_app.data import (
    CORES_NIVEL,
    TIPOLOGIA_CORES,
    TRATADOS,
    card_kpi,
    com_tipologia,
    projecao_semana,
    severidade_pct,
    tendencia_climatica_texto,
)
from st_app.indicadores import (
    carregar_alertabilidade,
    carregar_contatos,
    carregar_exposicao_vulneraveis,
    carregar_impacto_extraterritorial,
    indicadores_sanitarios,
    metricas_alertabilidade,
    quase_atencao,
    solo_chuva_composta,
    tendencia_7d_score,
    tendencia_idap_48h,
)
from st_app.sitrep import montar_sitrep_docx, montar_sitrep_md, montar_sitrep_pdf

_SEV_RANK = {
    "sev-critico": 5,
    "sev-alto": 4,
    "sev-elevado": 3,
    "sev-atencao": 2,
    "sev-ok": 1,
    "sev-neutro": 0,
}


def faixa_titulo(numero: str, titulo: str, subtitulo: str) -> None:
    st.markdown(
        f'<div class="faixa-titulo"><span>Faixa {numero}</span>{titulo}'
        f'<div style="font-family:Source Sans 3,sans-serif;font-size:0.85rem;'
        f'font-weight:400;color:#4a5d73;margin-top:2px">{subtitulo}</div></div>',
        unsafe_allow_html=True,
    )


def frescor_chips_html() -> str:
    arquivos = [
        "idap_estadual_mt.csv",
        "hidro_barragens_mt.csv",
        "piloto_manso_cuiaba.csv",
        "alertabilidade_piloto.csv",
        "cnes_estabelecimentos_mt.csv",
    ]
    chips = []
    agora = dt.datetime.now()
    for nome in arquivos:
        caminho = TRATADOS / nome
        if not caminho.exists():
            chips.append(f'<div class="chip morto">{nome.replace(".csv","")}: ausente</div>')
            continue
        mtime = dt.datetime.fromtimestamp(caminho.stat().st_mtime)
        idade_h = (agora - mtime).total_seconds() / 3600
        cls = "ok" if idade_h <= 24 else ("velho" if idade_h <= 72 else "morto")
        chips.append(
            f'<div class="chip {cls}">{nome.replace(".csv","")}: '
            f"{idade_h:.0f} h ({mtime.strftime('%d/%m %H:%M')})</div>"
        )
    return '<div class="frescor-chips">' + "".join(chips) + "</div>"


def _negrito_html(texto: str) -> str:
    """`**x**` → `<b>x</b>`: a caixa de tendência é renderizada como HTML."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)


def tendencia_unificada(df: pd.DataFrame) -> tuple[str, str]:
    """Escolhe a tendência mais grave entre clima e histórico IDAP."""
    proj = projecao_semana(df)
    sev_c, msg_c = tendencia_climatica_texto(proj, df)
    msg_c = _negrito_html(msg_c)
    hist = tendencia_idap_48h()
    if hist.get("ok"):
        sev_h = hist["classe"]
        msg_h = _negrito_html(hist["msg"])
        if _SEV_RANK.get(sev_h, 0) >= _SEV_RANK.get(sev_c, 0):
            return sev_h, f"<b>Tendência do índice (últimas rodadas)</b><br>{msg_h}<br><br><b>Clima:</b> {msg_c}"
        return sev_c, f"<b>Tendência climática</b><br>{msg_c}<br><br><b>Índice:</b> {msg_h}"
    return sev_c, f"<b>Tendência climática</b><br>{msg_c}"


def bloco_sitrep_downloads(df: pd.DataFrame, *, mun_ativo: str | None) -> None:
    proj = projecao_semana(df)
    _, msg_t = tendencia_climatica_texto(proj, df)
    sitrep = montar_sitrep_md(df, municipio=mun_ativo, proj=proj, tend_clima=msg_t)
    stem = f"sitrep_vigibarragens_{(mun_ativo or 'MT').replace(' ', '_')}"
    # Espaçador à esquerda: os botões ficam alinhados à direita da faixa.
    _, c1, c2, c3 = st.columns([3.4, 1, 1, 1])
    with c1:
        st.download_button(
            "SITREP (Markdown)",
            data=sitrep.encode("utf-8"),
            file_name=f"{stem}.md",
            mime="text/markdown",
        )
    with c2:
        try:
            st.download_button(
                "SITREP (DOCX)",
                data=montar_sitrep_docx(df, municipio=mun_ativo, proj=proj, tend_clima=msg_t),
                file_name=f"{stem}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as exc:  # noqa: BLE001
            st.caption(f"DOCX indisponível ({exc})")
    with c3:
        try:
            st.download_button(
                "SITREP (PDF)",
                data=montar_sitrep_pdf(df, municipio=mun_ativo, proj=proj, tend_clima=msg_t),
                file_name=f"{stem}.pdf",
                mime="application/pdf",
            )
        except Exception as exc:  # noqa: BLE001
            st.caption(f"PDF indisponível ({exc})")


def bloco_sanitario_compacto(df: pd.DataFrame) -> None:
    """Faixa 2 — 5 cards SES + expander tipológico."""
    san = indicadores_sanitarios(df)
    t7 = tendencia_7d_score(df)
    solo = solo_chuva_composta(df)
    razao = san["razao_pop_us"]
    principais = [
        card_kpi(
            "População sob pressão sanitária",
            f"{san['pop_sob_pressao']:,}".replace(",", "."),
            sev=severidade_pct(min(100, san["pop_sob_pressao"] / 5000) if san["pop_sob_pressao"] else 0),
            nota="Estimativa nas Em atenção+ (SIGBM ou área×densidade)",
        ),
        card_kpi(
            "US nos municípios sob pressão",
            str(san["us_sob_risco"]),
            sev=severidade_pct(min(100, san["us_sob_risco"] / 50) if san["us_sob_risco"] else 0),
            nota=f"Prioritárias: {san['us_prioritarias']} · {san.get('metodo_us', '')}",
        ),
        card_kpi(
            "Razão pop. / US prioritária",
            "—" if razao is None else f"{razao:,.0f}".replace(",", "."),
            sev=severidade_pct(None if razao is None else min(100, razao / 50)),
            nota="Quanto maior, maior sobrecarga potencial",
        ),
        card_kpi(
            "Municípios sob pressão",
            str(san.get("municipios_sob_pressao") or san["municipios_jusante"]),
            sev=severidade_pct(
                min(100, (san.get("municipios_sob_pressao") or san["municipios_jusante"]) * 5)
            ),
            nota=f"Jusante distintos: {san['municipios_jusante']}",
        ),
        card_kpi(
            "Completude média do índice",
            "—" if san["completude_media"] is None else f"{san['completude_media']:.0f}%",
            sev="sev-ok"
            if (san["completude_media"] or 0) >= 70
            else ("sev-atencao" if (san["completude_media"] or 0) >= 40 else "sev-alto"),
        ),
    ]
    st.markdown('<div class="grade-kpis">' + "".join(principais) + "</div>", unsafe_allow_html=True)

    extras = [
        card_kpi(
            "Tendência 7 dias (score)",
            f"{t7['score']:.0f} · {t7['classe']}",
            sev=t7["sev"],
            nota=t7["detalhe"],
        ),
        card_kpi(
            "Solo + chuva composta",
            f"{solo['indice']:.0f}",
            sev=solo["sev"],
            nota=f"{solo['n_alto']} sede(s) com índice alto",
        ),
        card_kpi(
            "Rejeito em atenção+",
            str(san["rejeito_atencao"]),
            sev="sev-alto" if san["rejeito_atencao"] else "sev-ok",
        ),
        card_kpi(
            "Dano potencial alto sem canal",
            str(san["dpa_alto_sem_alerta"]),
            sev="sev-critico" if san["dpa_alto_sem_alerta"] else "sev-ok",
        ),
        card_kpi(
            "Impacto extraterritorial ativo",
            str(san["extraterritorial_ativo"]),
            sev="sev-atencao" if san["extraterritorial_ativo"] else "sev-ok",
        ),
    ]
    with st.expander("Cadastro e tipológico (detalhe)", expanded=False):
        st.markdown('<div class="grade-kpis">' + "".join(extras) + "</div>", unsafe_allow_html=True)


# Compat: Município 360° e chamadas antigas
def bloco_sanitario_e_historico(df: pd.DataFrame, *, mun_ativo: str | None) -> None:
    bloco_sanitario_compacto(df)
    bloco_sitrep_downloads(df, mun_ativo=mun_ativo)


def bloco_quase_atencao(df: pd.DataFrame, *, altura: int = 280) -> None:
    q = quase_atencao(df)
    st.markdown("##### Quase atenção — vigília")
    st.caption("Verdes com pressão climática alta ou chuva prevista ≥40 mm.")
    if q.empty:
        st.success("Nenhuma barragem verde sob pressão climática relevante.")
        return
    cols = [
        c
        for c in (
            "nome",
            "municipio_sede",
            "idap",
            "completude",
            "pontos_a",
            "chuva_72h_mm",
            "chuva_prevista_24_72h_mm",
            "nivel",
        )
        if c in q.columns
    ]
    st.dataframe(
        q[cols].head(20).rename(
            columns={
                "nome": "Barragem",
                "municipio_sede": "Sede",
                "idap": "Índice",
                "completude": "Completude",
                "pontos_a": "Pressão clima",
                "chuva_72h_mm": "Chuva 72h",
                "chuva_prevista_24_72h_mm": "Chuva prevista",
                "nivel": "Prontidão",
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=altura,
    )


def pagina_municipio_360(df: pd.DataFrame, municipio: str, *, incluir_sanitario: bool = False) -> None:
    st.markdown(f"### Município 360° — {municipio}")
    st.markdown(
        '<p class="nota">Visão do município como <b>sede</b> e/ou '
        "<b>potencialmente afetado a jusante</b>.</p>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.warning("Sem barragens vinculadas a este município.")
        return
    if incluir_sanitario:
        bloco_sanitario_e_historico(df, mun_ativo=municipio)
    sede = df[
        df.get("papel_municipio", pd.Series(dtype=str)).astype(str).str.contains("Sede", na=False)
    ]
    jus = df[
        df.get("papel_municipio", pd.Series(dtype=str))
        .astype(str)
        .str.contains("jusante|Afetado", case=False, na=False)
    ]
    c1, c2 = st.columns(2)
    c1.metric("Como sede", len(sede) if "papel_municipio" in df.columns else "—")
    c2.metric("Como afetado a jusante", len(jus) if "papel_municipio" in df.columns else "—")
    pts = df.dropna(subset=["latitude", "longitude"])
    if not pts.empty:
        m = folium.Map(
            location=[pts["latitude"].mean(), pts["longitude"].mean()],
            zoom_start=9,
            tiles="CartoDB positron",
        )
        for _, r in pts.iterrows():
            folium.CircleMarker(
                [r["latitude"], r["longitude"]],
                radius=8,
                color="#1b3281",
                fill=True,
                fill_color=CORES_NIVEL.get(r["nivel"], "#888"),
                fill_opacity=0.9,
                popup=f"{r['nome']}<br>{r.get('papel_municipio','')}<br>{r['nivel']}",
            ).add_to(m)
        st_folium(m, height=320, use_container_width=True, returned_objects=[])
    st.dataframe(
        df[
            [
                c
                for c in (
                    "nome",
                    "papel_municipio",
                    "municipio_sede",
                    "nivel",
                    "idap",
                    "completude",
                    "municipios_potencialmente_afetados",
                )
                if c in df.columns
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=220,
    )


NAV_DESTINO = "_nav_destino"


def bloco_tipologia(recorte: pd.DataFrame, estado: pd.DataFrame, *, rotulo_recorte: str) -> None:
    """Mapa por tipologia do recorte + tipologias presentes no estado."""
    st.markdown("##### Tipologia — para que serve cada barragem")
    st.caption(
        "Tipologia = agrupamento operacional do uso principal (SNISB). "
        "Rejeito/mineração e abastecimento humano puxam decisão sanitária diferente de irrigação."
    )
    est = com_tipologia(estado)
    rec = com_tipologia(recorte)
    if "tipologia" not in est.columns:
        st.info("Coluna `uso_principal` ausente no inventário mesclado — tipologia indisponível.")
        return

    cont_est = est["tipologia"].value_counts()
    cont_rec = rec["tipologia"].value_counts() if "tipologia" in rec.columns else pd.Series(dtype=int)
    tabela = pd.DataFrame(
        {
            "Tipologia": cont_est.index,
            "Estado": cont_est.to_numpy(),
            "No recorte": [int(cont_rec.get(t, 0)) for t in cont_est.index],
        }
    )

    col_mapa, col_graf = st.columns([1.25, 1])
    with col_mapa:
        pts = rec.dropna(subset=["latitude", "longitude"])
        if pts.empty:
            st.info("Sem coordenadas no recorte para o mapa de tipologia.")
        else:
            m = folium.Map(location=[-13.0, -55.8], zoom_start=5, tiles="CartoDB positron")
            for r in pts.itertuples():
                folium.CircleMarker(
                    [r.latitude, r.longitude],
                    radius=5,
                    color="#fff",
                    weight=1,
                    fill=True,
                    fill_color=TIPOLOGIA_CORES.get(r.tipologia, "#888"),
                    fill_opacity=0.9,
                    popup=(
                        f"<b>{r.nome}</b><br>{r.tipologia}<br>"
                        f"{getattr(r, 'uso_principal', '') or '—'}<br>"
                        f"Sede: {getattr(r, 'municipio_sede', '') or '—'} · {r.nivel}"
                    ),
                ).add_to(m)
            if len(pts) <= 120:
                sw = [pts["latitude"].min(), pts["longitude"].min()]
                ne = [pts["latitude"].max(), pts["longitude"].max()]
                m.fit_bounds([sw, ne], padding=(30, 30))
            st_folium(m, height=420, use_container_width=True, returned_objects=[])
            legenda = "".join(
                f'<div class="chip" style="border-left:3px solid {TIPOLOGIA_CORES.get(t, "#888")}">'
                f"{t}: {int(n)}</div>"
                for t, n in cont_rec.items()
            )
            if legenda:
                st.markdown(f'<div class="frescor-chips">{legenda}</div>', unsafe_allow_html=True)

    with col_graf:
        st.caption(f"Barras: estado inteiro (1.248). Marca: {rotulo_recorte}.")
        grafico = (
            alt.Chart(tabela)
            .mark_bar()
            .encode(
                x=alt.X("Estado:Q", title="Barragens no estado"),
                y=alt.Y("Tipologia:N", sort="-x", title=None),
                color=alt.Color(
                    "Tipologia:N",
                    scale=alt.Scale(
                        domain=list(TIPOLOGIA_CORES), range=list(TIPOLOGIA_CORES.values())
                    ),
                    legend=None,
                ),
                tooltip=["Tipologia", "Estado", "No recorte"],
            )
            .properties(height=260)
        )
        marca = (
            alt.Chart(tabela)
            .mark_tick(color="#15202b", thickness=2, size=18)
            .encode(x="No recorte:Q", y=alt.Y("Tipologia:N", sort="-x"))
        )
        st.altair_chart(grafico + marca, use_container_width=True)
        st.dataframe(tabela, use_container_width=True, hide_index=True, height=180)


def ir_para(jornada: str, pagina: str) -> None:
    """Agenda a navegação: as chaves dos widgets só podem mudar antes da sidebar."""
    st.session_state[NAV_DESTINO] = (jornada, pagina)
    st.rerun()


def aplicar_navegacao_pendente() -> None:
    destino = st.session_state.pop(NAV_DESTINO, None)
    if destino:
        st.session_state["jornada"], st.session_state["pagina"] = destino


def bloco_atalhos_comando(*, so_piloto: bool = False) -> None:
    st.markdown("##### Continuar a investigação")
    m = metricas_alertabilidade()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Impacto extraterritorial", use_container_width=True):
            ir_para("Território", "Impacto extraterritorial")
    with c2:
        if st.button(f"Cobertura de alerta ({m.get('pct', 0)}%)", use_container_width=True):
            ir_para("Ação", "Alertabilidade / despacho")
    with c3:
        rotulo = "Eixo Manso–Cuiabá" + (" (filtro ativo)" if so_piloto else "")
        if st.button(rotulo, use_container_width=True):
            ir_para("Situação", "Eixo Manso–Cuiabá")


def pagina_vulneraveis() -> None:
    st.markdown("# Populações vulneráveis (eixo)")
    st.markdown(
        '<p class="nota">Aldeias, assentamentos e quilombos próximos ao eixo Manso–Cuiabá '
        "(dado já tratado — exposição ao eixo).</p>",
        unsafe_allow_html=True,
    )
    df = carregar_exposicao_vulneraveis()
    if df.empty:
        st.error("Arquivo exposicao_populacoes_eixo_cuiaba.csv ausente.")
        return
    cont = df["categoria"].value_counts() if "categoria" in df.columns else pd.Series(dtype=int)
    cols = st.columns(min(4, max(1, len(cont))))
    for i, (cat, n) in enumerate(cont.items()):
        cols[i % len(cols)].metric(str(cat), int(n))
    faixa = st.multiselect(
        "Faixa de distância ao eixo",
        sorted(df["faixa"].dropna().unique().tolist()) if "faixa" in df.columns else [],
        default=None,
    )
    view = df[df["faixa"].isin(faixa)] if faixa else df
    pts = view.dropna(subset=["latitude", "longitude"])
    if not pts.empty:
        m = folium.Map(location=[-15.5, -56.0], zoom_start=8, tiles="CartoDB positron")
        cores = {
            "aldeia indígena": "#166534",
            "assentamento": "#a16207",
            "quilombo": "#7c3aed",
        }
        for _, r in pts.head(800).iterrows():
            cat = str(r.get("categoria") or "")
            folium.CircleMarker(
                [r["latitude"], r["longitude"]],
                radius=5,
                color="#fff",
                weight=1,
                fill=True,
                fill_color=cores.get(cat, "#1b3281"),
                fill_opacity=0.85,
                popup=f"{r.get('nome')}<br>{cat}<br>{r.get('municipio')} · {r.get('faixa')}",
            ).add_to(m)
        st_folium(m, height=480, use_container_width=True, returned_objects=[])
    st.dataframe(view.head(200), use_container_width=True, hide_index=True, height=360)


def pagina_extraterritorial() -> None:
    st.markdown("# Impacto extraterritorial")
    st.markdown(
        '<p class="nota">Barragem na sede A que pode afetar município B a jusante (Otto). '
        "Mapa: origem (barragem) → centroide do município afetado.</p>",
        unsafe_allow_html=True,
    )
    df = carregar_impacto_extraterritorial()
    if df.empty:
        st.error("impacto_extraterritorial_mt.csv ausente.")
        return
    so_atencao = st.checkbox("Só Em atenção+", value=True)
    view = df.copy()
    if so_atencao and "nivel" in view.columns:
        view = view[view["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"])]
    mun = st.selectbox(
        "Filtrar município afetado",
        ["(todos)"] + sorted(view["municipio_potencialmente_afetado"].dropna().unique().tolist()),
    )
    if mun != "(todos)":
        view = view[view["municipio_potencialmente_afetado"] == mun]
    st.metric("Pares sede → afetado", len(view))

    from st_app.data import carregar_idap

    idap = carregar_idap()
    coords_bar: dict[str, tuple[float, float]] = {}
    centroides: dict[str, tuple[float, float]] = {}
    if not idap.empty and "latitude" in idap.columns:
        for _, r in idap.dropna(subset=["latitude", "longitude"]).iterrows():
            bid = str(r.get("id_snisb") or "")
            if bid:
                coords_bar[bid] = (float(r["latitude"]), float(r["longitude"]))
        g = (
            idap.dropna(subset=["latitude", "longitude"])
            .assign(_sede=idap["municipio_sede"].fillna("").astype(str).str.strip())
            .groupby("_sede")
            .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        )
        centroides = {
            str(i): (float(row.latitude), float(row.longitude))
            for i, row in g.iterrows()
            if i
        }

    linhas_mapa = 0
    if coords_bar and centroides:
        m = folium.Map(location=[-13.0, -55.8], zoom_start=5, tiles="CartoDB positron")
        amostra = view.head(200)
        for _, r in amostra.iterrows():
            bid = str(r.get("id_snisb") or "")
            dest = str(r.get("municipio_potencialmente_afetado") or "").strip()
            origem = coords_bar.get(bid)
            destino = centroides.get(dest)
            if not origem or not destino:
                continue
            cor = CORES_NIVEL.get(str(r.get("nivel") or ""), "#1b3281")
            folium.PolyLine(
                [origem, destino],
                color=cor,
                weight=2,
                opacity=0.55,
                popup=(
                    f"{r.get('nome_barragem')}<br>{r.get('municipio_sede')} → {dest}<br>"
                    f"{r.get('nivel')} · índice {r.get('idap')}"
                ),
            ).add_to(m)
            folium.CircleMarker(
                origem, radius=4, color="#111", fill=True, fill_color=cor, fill_opacity=0.9
            ).add_to(m)
            folium.CircleMarker(
                destino, radius=3, color="#1b3281", fill=True, fill_color="#fff", fill_opacity=0.9
            ).add_to(m)
            linhas_mapa += 1
        if linhas_mapa:
            st_folium(m, height=480, use_container_width=True, returned_objects=[])
            st.caption(f"{linhas_mapa} ligação(ões) desenhadas (amostra até 200).")
        else:
            st.info("Sem pares com coordenadas suficientes para o mapa.")
    st.dataframe(view.head(500), use_container_width=True, hide_index=True, height=360)


def pagina_alertabilidade_despacho() -> None:
    st.markdown("# Alertabilidade e despacho")
    st.markdown(
        '<p class="nota">Onda 2 — cobertura de contatos do eixo e despacho (Telegram/e-mail). '
        "Envio real só com credenciais de ambiente.</p>",
        unsafe_allow_html=True,
    )
    m = metricas_alertabilidade()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Barragens eixo (alertabilidade)", m["n"])
    c2.metric("Alertáveis", m["alertaveis"], f"{m['pct']}%")
    c3.metric("Contatos com e-mail", m["contatos_com_email"])
    c4.metric("Contatos com telefone", m["contatos_com_fone"])
    if m.get("regioes"):
        st.caption("Regiões de saúde no cadastro de contatos: " + ", ".join(m["regioes"]))

    al = carregar_alertabilidade()
    if not al.empty:
        st.subheader("Pendências de alertabilidade")
        st.dataframe(al, use_container_width=True, hide_index=True, height=280)

    st.subheader("Validar contato (rápido)")
    ct = carregar_contatos()
    if not ct.empty:
        mun_opt = sorted(ct["municipio"].dropna().unique().tolist())
        papel_opt = sorted(ct["papel"].dropna().unique().tolist()) if "papel" in ct.columns else []
        with st.form("validar_contato"):
            mun_v = st.selectbox("Município", mun_opt)
            papel_v = st.selectbox("Papel", papel_opt)
            tel_v = st.text_input("Telefone / celular")
            email_v = st.text_input("E-mail")
            nome_v = st.text_input("Nome do responsável")
            ok_v = st.form_submit_button("Gravar validação (hoje)")
        if ok_v:
            caminho = TRATADOS / "contatos_institucionais_piloto.csv"
            df_ct = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
            mask = (df_ct["municipio"] == mun_v) & (df_ct["papel"] == papel_v)
            if mask.any():
                if nome_v:
                    df_ct.loc[mask, "nome"] = nome_v
                if tel_v:
                    df_ct.loc[mask, "telefone"] = tel_v
                if email_v:
                    df_ct.loc[mask, "email"] = email_v
                df_ct.loc[mask, "data_validacao"] = dt.date.today().isoformat()
                df_ct.loc[mask, "fonte"] = "validacao_ui"
                df_ct.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")
                st.success(
                    f"Contato {papel_v} em {mun_v} validado. "
                    "Rode `python executar.py 19 16 18` para propagar alertável/D8."
                )
            else:
                st.warning("Linha não encontrada no CSV de contatos.")

    st.subheader("Despacho (fila)")
    fila_dir = Path(__file__).resolve().parent.parent / "alertas" / "piloto"
    log_path = TRATADOS / "despacho_alertas_log.csv"
    import importlib.util
    import sys

    raiz = Path(__file__).resolve().parent.parent
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    spec = importlib.util.spec_from_file_location(
        "despacho29",
        raiz / "scripts" / "29_despacho_alertas.py",
    )
    mod = None
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        st_cred = mod.credenciais_status()
        st.caption(
            f"Credenciais: Telegram={'ok' if st_cred['telegram'] else 'ausente'} · "
            f"SMTP={'ok' if st_cred['smtp'] else 'ausente'} "
            "(secrets `[vigi]` no Cloud ou `despacho_secrets.env`)."
        )
    if fila_dir.exists():
        textos = sorted(fila_dir.glob("*.txt"))
        st.write(f"Textos de alerta prontos: **{len(textos)}** em `alertas/piloto/`")
        b1, b2 = st.columns(2)
        if b1.button("Gerar log de despacho (dry-run)") and mod:
            n = mod.despachar(dry_run=True)
            st.success(f"Dry-run: {n} registros em {log_path.name}")
        if b2.button("Enviar agora (requer credenciais)") and mod:
            n = mod.despachar(dry_run=False)
            st.warning(f"Tentativa de envio: {n} registros no log — confira status.")
    else:
        st.info("Pasta alertas/piloto ausente — rode a etapa 18.")

    if log_path.exists():
        st.subheader("Últimos despachos")
        st.dataframe(
            pd.read_csv(log_path, sep=";", encoding="utf-8-sig").tail(30),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Payload Defesa Civil (exemplo)")
    payload = {
        "sistema": "VIGIBARRAGENS-MT",
        "tipo": "alerta_prontidao_saude",
        "nivel": "Amarelo",
        "municipio": "Cuiabá",
        "papel": "potencialmente_afetado_jusante",
        "barragem_id_snisb": "EXEMPLO",
        "coordenadas": {"lat": -15.6, "lon": -56.1},
        "texto_resumo": "Prontidão sanitária — não é ordem de evacuação.",
        "contato_ses": "CIEVS-MT",
    }
    st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")
    st.caption("Especificação em docs/13-defesa-civil-gancho.md")


def pagina_confirmacao_persistente() -> None:
    st.markdown("# Confirmação de alerta (persistente)")
    st.markdown(
        '<p class="nota">Registros gravados em dados/tratados/confirmacoes/ — '
        "complementa o protótipo HTML (localStorage).</p>",
        unsafe_allow_html=True,
    )
    pasta = TRATADOS / "confirmacoes"
    pasta.mkdir(parents=True, exist_ok=True)
    with st.form("conf_form"):
        id_alerta = st.text_input("ID / SNISB ou nome do alerta")
        responsavel = st.text_input("Responsável que confirmou")
        canal = st.selectbox("Canal", ["telefone", "email", "telegram", "whatsapp", "presencial"])
        obs = st.text_area("Observação", "")
        ok = st.form_submit_button("Registrar confirmação")
    if ok and id_alerta and responsavel:
        registro = {
            "instante": dt.datetime.now().isoformat(timespec="seconds"),
            "id_alerta": id_alerta,
            "responsavel": responsavel,
            "canal": canal,
            "observacao": obs,
        }
        arq = pasta / "confirmacoes.csv"
        df = pd.DataFrame([registro])
        if arq.exists():
            df.to_csv(arq, mode="a", header=False, sep=";", index=False, encoding="utf-8-sig")
        else:
            df.to_csv(arq, sep=";", index=False, encoding="utf-8-sig")
        st.success("Confirmação gravada.")
    arq = pasta / "confirmacoes.csv"
    if arq.exists():
        st.dataframe(
            pd.read_csv(arq, sep=";", encoding="utf-8-sig"),
            use_container_width=True,
            hide_index=True,
        )
    st.info("O painel HTML com timer permanece em «Confirmação (HTML)» (Dados e apoio).")


def pagina_rag_docs() -> None:
    st.markdown("# Documentos e dúvidas (RAG leve)")
    st.markdown(
        '<p class="nota">Busca lexical nos docs/ do projeto — base para o RAG completo. '
        "Não inventa norma: só recupera trechos existentes.</p>",
        unsafe_allow_html=True,
    )
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    pergunta = st.text_input("Pergunta ou termos", placeholder="ex.: o que é ZAS / PAE / IDAP")
    if not pergunta.strip():
        st.caption("Digite termos para buscar em docs/*.md")
        return
    import re

    termos = [t for t in re.split(r"\W+", pergunta.lower()) if len(t) > 2]
    hits: list[tuple[int, Path, str]] = []
    for path in sorted(docs_dir.glob("*.md")):
        texto = path.read_text(encoding="utf-8", errors="ignore")
        low = texto.lower()
        score = sum(low.count(t) for t in termos)
        if score <= 0:
            continue
        idx = min((low.find(t) for t in termos if t in low), default=0)
        ini = max(0, idx - 80)
        trecho = texto[ini : ini + 420].replace("\n", " ")
        hits.append((score, path, trecho))
    hits.sort(key=lambda x: -x[0])
    if not hits:
        st.warning("Nenhum trecho encontrado. Tente outros termos.")
        return
    for score, path, trecho in hits[:8]:
        st.markdown(f"**{path.name}** (relevância {score})")
        st.write(trecho + "…")
        st.divider()


def pagina_regiao_saude() -> None:
    st.markdown("# Região de saúde")
    st.markdown(
        '<p class="nota">Vínculo município → região a partir do cadastro de contatos do eixo. '
        "Expansão estadual depende da tabela oficial da SES-MT.</p>",
        unsafe_allow_html=True,
    )
    ct = carregar_contatos()
    if ct.empty or "regiao_saude" not in ct.columns:
        st.warning("Sem regioes no cadastro de contatos.")
        return
    reg = st.selectbox("Região", sorted(ct["regiao_saude"].dropna().unique().tolist()))
    view = ct[ct["regiao_saude"] == reg]
    st.metric("Municípios/contatos na região", view["municipio"].nunique())
    st.dataframe(view, use_container_width=True, hide_index=True, height=400)
