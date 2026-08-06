"""Páginas e blocos da Onda 1–3 (sanitário, vulneráveis, despacho, RAG)."""

from __future__ import annotations

import datetime as dt
import json
import math
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
        f'<div class="faixa-titulo"><span class="kicker">Faixa {numero}</span>'
        f'<span class="titulo">{titulo}</span>'
        f'<span class="sub">{subtitulo}</span></div>',
        unsafe_allow_html=True,
    )


def pagina_vigipos_oe() -> None:
    """Tela VIGIPÓS — O/E e canal endêmico (§5.6)."""
    import json as _json

    from st_app.vigipos import exemplo_leptospirose_564

    st.markdown("# VIGIPÓS — observado / esperado")
    st.markdown(
        '<p class="nota">Detecção de excesso por canal endêmico (média + k·dp). '
        "A IA pode explicar o sinal; <strong>não</strong> o produz. "
        "Método e parâmetros ficam registrados (§5.6).</p>",
        unsafe_allow_html=True,
    )
    tratados = Path(__file__).resolve().parents[1] / "dados" / "tratados"
    status_p = tratados / "vigipos_status.json"
    sinais_p = tratados / "vigipos_sinais.csv"
    base_p = tratados / "vigipos_linha_base.csv"

    if status_p.is_file():
        st_json = _json.loads(status_p.read_text(encoding="utf-8"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Sinais", str(st_json.get("n_sinais") or "—"))
        c2.metric(
            "Exemplo §5.6.4",
            "OK" if st_json.get("exemplo_564_ok") else "falhou",
        )
        c3.metric("Fonte", str(st_json.get("fonte") or "—")[:40])
        st.caption(st_json.get("nota") or "")
    else:
        st.warning(
            "Rode `python scripts/50_vigipos_linha_base.py` para gerar a linha de base."
        )

    ex = exemplo_leptospirose_564()
    with st.expander("Exemplo normativo leptospirose (§5.6.4)", expanded=True):
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Observado", f"{ex.observado:g}")
        e2.metric("Esperado", f"{ex.esperado:g}".replace(".", ","))
        e3.metric("Limite superior", f"{ex.limite_superior:g}")
        e4.metric("O/E", f"{ex.razao_oe:.1f}".replace(".", ","))
        st.info(f"Classificação: **{ex.classificacao}** · excesso {ex.excesso:g}")

    if sinais_p.is_file():
        st.markdown("##### Sinais avaliados")
        df_s = pd.read_csv(sinais_p, sep=";")
        st.dataframe(df_s, width="stretch", hide_index=True, height=280)
        st.download_button(
            "Baixar sinais (CSV)",
            data=sinais_p.read_text(encoding="utf-8-sig"),
            file_name="vigipos_sinais.csv",
            mime="text/csv",
            key="vigipos_sinais_dl",
        )
    if base_p.is_file():
        with st.expander("Linha de base", expanded=False):
            st.dataframe(
                pd.read_csv(base_p, sep=";"),
                width="stretch",
                hide_index=True,
                height=260,
            )


_FONTES_FRESCOR = (
    "idap_estadual_mt.csv",
    "hidro_barragens_mt.csv",
    "piloto_manso_cuiaba.csv",
    "alertabilidade_piloto.csv",
    "cnes_estabelecimentos_mt.csv",
)


def _idades_fontes() -> list[tuple[str, float | None, str, str]]:
    """(rótulo, idade_h, classe, quando) por fonte — None quando ausente."""
    agora = dt.datetime.now()
    saida = []
    for nome in _FONTES_FRESCOR:
        rotulo = nome.replace(".csv", "")
        caminho = TRATADOS / nome
        if not caminho.exists():
            saida.append((rotulo, None, "morto", "ausente"))
            continue
        mtime = dt.datetime.fromtimestamp(caminho.stat().st_mtime)
        idade_h = (agora - mtime).total_seconds() / 3600
        cls = "ok" if idade_h <= 24 else ("velho" if idade_h <= 72 else "morto")
        saida.append((rotulo, idade_h, cls, mtime.strftime("%d/%m %H:%M")))
    return saida


def frescor_chips_html() -> str:
    chips = []
    for rotulo, idade_h, cls, quando in _idades_fontes():
        texto = "ausente" if idade_h is None else f"{idade_h:.0f} h ({quando})"
        chips.append(f'<div class="chip {cls}">{rotulo}: {texto}</div>')
    return '<div class="frescor-chips">' + "".join(chips) + "</div>"


def bloco_frescor() -> None:
    """Uma linha de status das fontes; o detalhe por fonte fica no expander."""
    fontes = _idades_fontes()
    ausentes = [f[0] for f in fontes if f[1] is None]
    velhas = [f[0] for f in fontes if f[1] is not None and f[1] > 24]
    idades = [f[1] for f in fontes if f[1] is not None]
    pior = max(idades) if idades else None
    if ausentes:
        resumo = f"Fontes: {len(ausentes)} ausente(s) — {', '.join(ausentes)}."
    elif velhas:
        resumo = f"Fontes: mais antiga com {pior:.0f} h ({len(velhas)} acima de 24 h)."
    else:
        resumo = f"Fontes atualizadas — mais antiga com {pior:.0f} h." if pior else "Fontes: —"
    with st.expander(resumo, expanded=False):
        st.markdown(frescor_chips_html(), unsafe_allow_html=True)
        st.caption("Verde ≤24 h · laranja ≤72 h · vermelho acima disso ou ausente.")


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
            f"{san['us_sob_risco']:,}".replace(",", "."),
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
    # PAE (SNISB) — cobertura estadual da etapa 47
    try:
        from pathlib import Path
        import json as _json

        st_pae = Path(__file__).resolve().parents[1] / "dados" / "tratados" / "pae_cobertura_status.json"
        if st_pae.is_file():
            pj = _json.loads(st_pae.read_text(encoding="utf-8"))
            n_sim = int(pj.get("tem_pae_sim") or 0)
            n_tot = int(pj.get("n_barragens") or 0)
            pct = (100.0 * n_sim / n_tot) if n_tot else 0.0
            extras.append(
                card_kpi(
                    "PAE declarado (SNISB)",
                    f"{n_sim}/{n_tot} ({pct:.0f}%)",
                    sev="sev-atencao" if pct < 30 else ("sev-ok" if pct >= 50 else "sev-atencao"),
                    nota="Mancha ZAS oficial ainda não ingerida — etapa 47",
                )
            )
    except (OSError, ValueError, TypeError):
        pass
    with st.expander("Cadastro e tipológico (detalhe)", expanded=False):
        st.markdown('<div class="grade-kpis">' + "".join(extras) + "</div>", unsafe_allow_html=True)

    lac_pae = Path(__file__).resolve().parents[1] / "dados" / "tratados" / "pae_checklist_lacunas.csv"
    if lac_pae.is_file():
        try:
            df_lac = pd.read_csv(lac_pae, sep=";")
            with st.expander("Ranking lacunas PAE (etapa 48)", expanded=False):
                st.caption(
                    "Checklist proxy SNISB+SIGBM — não substitui auditoria do PAE oficial. "
                    "CSV: `dados/tratados/pae_checklist_lacunas.csv`."
                )
                cols = [
                    c
                    for c in (
                        "id_snisb",
                        "nome",
                        "municipio",
                        "n_lacunas_criticas",
                        "n_atencao",
                        "pae_01",
                        "pae_04_zas",
                    )
                    if c in df_lac.columns
                ]
                st.dataframe(
                    df_lac[cols].head(40),
                    width="stretch",
                    hide_index=True,
                    height=320,
                )
        except (OSError, ValueError, TypeError):
            pass


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
        width="stretch",
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
        width="stretch",
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
        st.altair_chart(grafico + marca, width="stretch")
        with st.expander("Contagem por tipologia (estado × recorte)", expanded=False):
            st.dataframe(tabela, width="stretch", hide_index=True, height=300)


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
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Simular área afetada", width="stretch", type="primary"):
            ir_para("Cenários e simulações", "Simular área potencialmente afetada")
    with c2:
        if st.button("Análise por município", width="stretch"):
            ir_para("Territórios e barragens", "Análise por município")
    with c3:
        if st.button("Notificações / impactos", width="stretch"):
            ir_para("Alertas e resposta", "Notificações e impactos")
    with c4:
        if st.button(f"Preparar alerta ({m.get('pct', 0)}%)", width="stretch"):
            ir_para("Alertas e resposta", "Preparar e enviar alerta")


_CORES_VULN = {
    "aldeia indígena": "#166534",
    "terra indígena": "#14532d",
    "assentamento rural": "#a16207",
    "assentamento": "#a16207",
    "território quilombola": "#7c3aed",
    "quilombo": "#7c3aed",
    "estabelecimento de saúde": "#1d4ed8",
}


def _cor_categoria(cat: str) -> str:
    c = (cat or "").strip().lower()
    if c in _CORES_VULN:
        return _CORES_VULN[c]
    for k, v in _CORES_VULN.items():
        if k in c:
            return v
    return "#1b3281"


def pagina_visao_territorial(df_barragens: pd.DataFrame) -> None:
    """Mapa estadual integrado — análise territorial por município."""
    st.markdown("# Análise por município")
    st.markdown(
        '<p class="nota">Mapa de <b>todas as barragens</b> do inventário com camadas de '
        "populações vulneráveis (área prioritária Manso–Cuiabá) e unidades de saúde (CNES). "
        "Clique nos pontos para detalhes.</p>",
        unsafe_allow_html=True,
    )
    from st_app.data import carregar_cnes_pontos, ordenar_por_severidade

    bars = df_barragens.dropna(subset=["latitude", "longitude"]).copy() if not df_barragens.empty else pd.DataFrame()
    vul = carregar_exposicao_vulneraveis()
    cnes = carregar_cnes_pontos(so_prioritarios=True)
    if cnes.empty:
        cnes = carregar_cnes_pontos(so_prioritarios=False)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Barragens no mapa", len(bars))
    n_trad = 0
    n_us_eixo = 0
    if not vul.empty and "categoria" in vul.columns:
        cats = vul["categoria"].fillna("").astype(str).str.lower()
        n_us_eixo = int(cats.str.contains("saúde|saude|estabelecimento").sum())
        n_trad = int((~cats.str.contains("saúde|saude|estabelecimento")).sum())
    c2.metric("Povos/comunidades (eixo)", n_trad)
    c3.metric("US no arquivo de exposição", n_us_eixo)
    c4.metric("US CNES prioritárias", len(cnes) if not cnes.empty else 0)

    camadas = st.multiselect(
        "Camadas",
        ["Barragens", "Populações vulneráveis", "Unidades de saúde (CNES)"],
        default=["Barragens", "Populações vulneráveis", "Unidades de saúde (CNES)"],
    )
    niveis = st.multiselect(
        "Níveis das barragens",
        ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"],
        default=["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"],
    )
    if niveis and not bars.empty and "nivel" in bars.columns:
        bars = bars[bars["nivel"].isin(niveis)]

    cats_vul = []
    if not vul.empty and "categoria" in vul.columns:
        cats_vul = sorted(vul["categoria"].dropna().astype(str).unique().tolist())
    filtro_cat = st.multiselect(
        "Categorias vulneráveis",
        cats_vul,
        default=[c for c in cats_vul if "saúde" not in c.lower() and "saude" not in c.lower()]
        or cats_vul,
    )

    m = folium.Map(location=[-13.0, -55.8], zoom_start=6, tiles="CartoDB positron")
    if "Barragens" in camadas and not bars.empty:
        for r in ordenar_por_severidade(bars).itertuples():
            cor = CORES_NIVEL.get(str(getattr(r, "nivel", "") or ""), "#888")
            pop = (
                f"<b>{r.nome}</b><br>SNISB {r.id_snisb}<br>"
                f"{getattr(r, 'municipio_sede', '') or '—'} · "
                f"{getattr(r, 'nivel', '—')} · IDAP {getattr(r, 'idap', '—')}<br>"
                f"Uso: {getattr(r, 'uso_principal', '') or '—'}<br>"
                f"CRI/DPA: {getattr(r, 'categoria_risco', '—')} / "
                f"{getattr(r, 'dano_potencial_associado', '—')}<br>"
                f"Vol. {getattr(r, 'capacidade_hm3', '—')} hm³ · "
                f"alt. {getattr(r, 'altura_m', '—')} m"
            )
            folium.CircleMarker(
                [r.latitude, r.longitude],
                radius=6,
                color="#111",
                weight=1,
                fill=True,
                fill_color=cor,
                fill_opacity=0.9,
                popup=folium.Popup(pop, max_width=320),
                tooltip=str(r.nome),
            ).add_to(m)

    if "Populações vulneráveis" in camadas and not vul.empty:
        pts = vul.dropna(subset=["latitude", "longitude"])
        if filtro_cat:
            pts = pts[pts["categoria"].astype(str).isin(filtro_cat)]
        for _, r in pts.head(1200).iterrows():
            cat = str(r.get("categoria") or "")
            pop = (
                f"<b>{r.get('nome') or '—'}</b><br>{cat}<br>"
                f"{r.get('municipio') or '—'} · {r.get('faixa') or '—'}<br>"
                f"Dist. eixo: {r.get('distancia_eixo_km') or '—'} km"
            )
            try:
                fam = r.get("familias")
                if fam is not None and str(fam).strip() not in ("", "nan", "None"):
                    pop += f"<br>Famílias: {int(float(fam))}"
            except (TypeError, ValueError):
                pass
            folium.CircleMarker(
                [float(r["latitude"]), float(r["longitude"])],
                radius=4,
                color="#fff",
                weight=1,
                fill=True,
                fill_color=_cor_categoria(cat),
                fill_opacity=0.85,
                popup=folium.Popup(pop, max_width=280),
                tooltip=f"{r.get('nome')} ({cat})",
            ).add_to(m)

    if "Unidades de saúde (CNES)" in camadas and not cnes.empty:
        amostra = cnes
        if len(amostra) > 1500:
            # prioriza hospitalar / UPA / UBS
            pri = amostra
            for col in ("hospitalar", "upa_ps", "ubs_esf", "prioritario"):
                if col in pri.columns:
                    pri = amostra.sort_values(col, ascending=False)
                    break
            amostra = pri.head(1500)
        for row in amostra.itertuples():
            tip = getattr(row, "tipo", "US") or "US"
            pop = (
                f"<b>{getattr(row, 'nome', '')}</b><br>{tip}<br>"
                f"{getattr(row, 'municipio', '') or '—'}"
            )
            cor = (
                "#b91c1c"
                if getattr(row, "hospitalar", False)
                else ("#ea580c" if getattr(row, "upa_ps", False) else "#2563eb")
            )
            folium.CircleMarker(
                [float(row.latitude), float(row.longitude)],
                radius=3,
                color="#fff",
                weight=0.5,
                fill=True,
                fill_color=cor,
                fill_opacity=0.8,
                popup=folium.Popup(pop, max_width=260),
            ).add_to(m)

    st_folium(m, height=560, use_container_width=True, returned_objects=[])
    st.caption(
        "Verde escuro = aldeia/TI · âmbar = assentamento · violeta = quilombo · "
        "azul = US. Barragens coloridas pelo nível IDAP. "
        "Exposição vulnerável hoje cobre o eixo Manso–Cuiabá (não o estado inteiro)."
    )


def pagina_vulneraveis() -> None:
    st.markdown("# Populações vulneráveis (eixo)")
    st.markdown(
        '<p class="nota">Aldeias, terras indígenas, assentamentos e quilombos próximos ao '
        "eixo Manso–Cuiabá. Ribeirinhos: sem base espacial contínua no repositório ainda.</p>",
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
    cats = (
        sorted(df["categoria"].dropna().astype(str).unique().tolist())
        if "categoria" in df.columns
        else []
    )
    filtro_cat = st.multiselect("Categoria", cats, default=cats)
    view = df[df["faixa"].isin(faixa)] if faixa else df
    if filtro_cat:
        view = view[view["categoria"].astype(str).isin(filtro_cat)]
    pts = view.dropna(subset=["latitude", "longitude"])
    if not pts.empty:
        m = folium.Map(location=[-15.5, -56.0], zoom_start=8, tiles="CartoDB positron")
        for _, r in pts.head(800).iterrows():
            cat = str(r.get("categoria") or "")
            popup = (
                f"<b>{r.get('nome') or '—'}</b><br>{cat}<br>"
                f"{r.get('municipio') or '—'} · {r.get('faixa') or '—'}<br>"
                f"Dist. eixo {r.get('distancia_eixo_km') or '—'} km"
            )
            folium.CircleMarker(
                [r["latitude"], r["longitude"]],
                radius=5,
                color="#fff",
                weight=1,
                fill=True,
                fill_color=_cor_categoria(cat),
                fill_opacity=0.85,
                popup=folium.Popup(popup, max_width=280),
                tooltip=str(r.get("nome") or cat),
            ).add_to(m)
        st_folium(m, height=480, use_container_width=True, returned_objects=[])
    st.dataframe(view.head(200), width="stretch", hide_index=True, height=360)


def pagina_extraterritorial() -> None:
    st.markdown("# Impacto fora do município-sede")
    st.markdown(
        '<p class="nota">Mapa das <b>outras localidades</b> que uma barragem pode pressionar '
        "a jusante (topologia Otto). Cor do município = nº de barragens a montante. "
        "Linhas = ligação esquemática sede → afetado. "
        "<b>Não é mancha PAE</b> nem trajeto hidrodinâmico da onda.</p>",
        unsafe_allow_html=True,
    )
    df = carregar_impacto_extraterritorial()
    if df.empty:
        st.error("impacto_extraterritorial_mt.csv ausente — rode `python executar.py 16`.")
        return

    from st_app.mapa_impacto import agregar_pressao_destino, montar_mapa_impacto

    so_atencao = st.checkbox("Só Em atenção+ (origem)", value=False, key="extra_so_atencao")
    base = df.copy()
    if so_atencao and "nivel" in base.columns:
        base = base[base["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"])]

    pressao_all = agregar_pressao_destino(base)
    destinos = sorted(pressao_all["municipio"].dropna().unique().tolist()) if not pressao_all.empty else []
    origens = (
        base[["id_snisb", "nome_barragem", "municipio_sede"]]
        .drop_duplicates("id_snisb")
        .sort_values("nome_barragem")
        if not base.empty
        else pd.DataFrame()
    )

    c_a, c_b = st.columns(2)
    with c_a:
        mun = st.selectbox(
            "Município afetado (destaque)",
            ["(todos)"] + destinos,
            help="Pinta e filtra localidades sob pressão a jusante.",
        )
    with c_b:
        rotulos_bar = ["(todas)"]
        mapa_bar: dict[str, str] = {}
        if not origens.empty:
            for _, r in origens.iterrows():
                bid = str(r.get("id_snisb") or "")
                lab = f"{r.get('nome_barragem') or bid} — {r.get('municipio_sede') or ''}"
                rotulos_bar.append(lab)
                mapa_bar[lab] = bid
        bar_sel = st.selectbox(
            "Barragem de origem",
            rotulos_bar,
            help="Mostra só o leque jusante dessa estrutura.",
        )

    mun_f = None if mun == "(todos)" else mun
    bid_f = None if bar_sel == "(todas)" else mapa_bar.get(bar_sel)

    mapa, meta = montar_mapa_impacto(
        base,
        municipio_destino=mun_f,
        id_snisb=bid_f,
        so_atencao=False,  # já filtrado em `base`
        max_ligacoes=220 if bid_f or mun_f else 160,
    )
    pressao = meta.get("pressao") if isinstance(meta.get("pressao"), pd.DataFrame) else pressao_all

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Localidades sob pressão", int(meta.get("n_destinos") or 0))
    k2.metric("Barragens de origem", int(meta.get("n_origens") or 0))
    k3.metric("Ligações no mapa", int(meta.get("n_ligacoes") or 0))
    n_aten = int(pressao["n_atencao"].sum()) if not pressao.empty and "n_atencao" in pressao.columns else 0
    k4.metric("Pares Em atenção+", n_aten)

    if mapa is not None:
        st_folium(mapa, height=560, use_container_width=True, returned_objects=[])
        st.caption(
            "Camadas: municípios sob pressão · ligações sede→afetado · barragens de origem · satélite. "
            "Clique no polígono ou na linha para o detalhe."
        )
    else:
        st.info("Sem geometria suficiente para o mapa neste filtro.")

    st.markdown("##### Ranking — localidades mais pressionadas a jusante")
    if pressao is not None and not pressao.empty:
        rank = pressao.rename(
            columns={
                "municipio": "Município afetado",
                "n_barragens_montante": "Barragens a montante",
                "n_atencao": "Em atenção+",
                "idap_max": "IDAP máx.",
                "populacao": "População IBGE",
                "n_pares": "Pares Otto",
            }
        )
        cols = [
            c
            for c in (
                "Município afetado",
                "Barragens a montante",
                "Em atenção+",
                "IDAP máx.",
                "População IBGE",
                "Pares Otto",
            )
            if c in rank.columns
        ]
        st.dataframe(rank[cols].head(40), width="stretch", hide_index=True, height=320)
    with st.expander("Tabela de pares sede → afetado", expanded=False):
        st.dataframe(base.head(500), width="stretch", hide_index=True, height=360)


def pagina_alertabilidade_despacho() -> None:
    st.markdown("# Preparar e enviar alerta")
    st.markdown(
        '<p class="nota">Onda 2 — cobertura de contatos do eixo e despacho (Telegram/e-mail). '
        "Destinatários = e-mails validados em `contatos_institucionais_piloto.csv`. "
        "Envio real só com credenciais SMTP/Telegram.</p>",
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

    ct = carregar_contatos()
    if not ct.empty:
        st.subheader("Matriz de destinatários (e-mail)")
        st.caption(
            "Papéis previstos: gestor municipal, vigilância, Defesa Civil, CIEVS, SAMU, "
            "hospital, Vigiagua, concessionária. Preencha e-mails institucionais da SES/SMS — "
            "hoje o cadastro ainda está em exercício técnico (telefones CNES, sem e-mail)."
        )
        cols_m = [
            c
            for c in (
                "municipio",
                "papel_rotulo",
                "papel",
                "nome",
                "email",
                "telefone",
                "data_validacao",
                "fonte",
            )
            if c in ct.columns
        ]
        st.dataframe(
            ct[cols_m].sort_values(["municipio", "papel"] if "papel" in cols_m else cols_m[:1]),
            width="stretch",
            hide_index=True,
            height=280,
        )
        emails_ok = sorted(
            {
                str(e).strip()
                for e in ct.get("email", pd.Series(dtype=str)).fillna("").tolist()
                if "@" in str(e)
            }
        )
        if emails_ok:
            st.success(f"{len(emails_ok)} e-mail(s) pronto(s) para despacho: {', '.join(emails_ok[:12])}")
        else:
            st.warning(
                "Nenhum e-mail cadastrado. Preencha o modelo "
                "`dados/tratados/contatos_emails_modelo.csv` e importe abaixo, "
                "ou valide contato a contato."
            )

    st.subheader("Importar cadastro / e-mails (quando o arquivo completo chegar)")
    st.caption(
        "Não é necessário preencher nada agora. Quando a SES enviar o arquivo completo, "
        "envie abaixo em modo **replace** (schema do cadastro) ou **merge**. "
        "Enquanto isso, telefone/exercício já destravam o D8 no eixo."
    )
    modelo_path = TRATADOS / "contatos_emails_modelo.csv"
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        if modelo_path.exists():
            st.download_button(
                "Baixar modelo (88 linhas do eixo)",
                data=modelo_path.read_text(encoding="utf-8-sig"),
                file_name="contatos_emails_modelo.csv",
                mime="text/csv",
            )
    with c_dl2:
        cad_path = TRATADOS / "contatos_institucionais_piloto.csv"
        if cad_path.exists():
            st.download_button(
                "Baixar cadastro atual completo",
                data=cad_path.read_text(encoding="utf-8-sig"),
                file_name="contatos_institucionais_piloto.csv",
                mime="text/csv",
            )
    modo_imp = st.radio(
        "Modo de importação",
        ["auto", "replace", "merge", "patch"],
        horizontal=True,
        help="replace = arquivo completo SES substitui campos; "
        "merge = atualiza e pode criar linhas; "
        "patch = só linhas com e-mail; auto detecta schema.",
    )
    up = st.file_uploader(
        "Enviar CSV (completo ou só e-mails)",
        type=["csv"],
        key="upload_contatos_completo",
    )
    if up is not None and st.button("Aplicar importação"):
        import importlib.util
        import sys
        import tempfile

        raiz = Path(__file__).resolve().parent.parent
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        spec = importlib.util.spec_from_file_location(
            "imp36", raiz / "scripts" / "36_contatos_importar_emails.py"
        )
        if spec and spec.loader:
            mod36 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod36)
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as tmp:
                tmp.write(up.getvalue())
                tmp_path = Path(tmp.name)
            try:
                stats = mod36.aplicar(tmp_path, modo=modo_imp, dry_run=False)
                st.success(
                    f"Modo `{stats.get('modo')}` · e-mails: {stats.get('emails_aplicados', 0)} · "
                    f"campos: {stats.get('campos_atualizados', 0)} · "
                    f"novas: {stats.get('linhas_novas', 0)} · "
                    f"ignoradas: {stats.get('linhas_ignoradas', 0)}. "
                    "Depois: `python executar.py 19 16 18`."
                )
                st.json(stats)
                st.cache_data.clear()
            finally:
                tmp_path.unlink(missing_ok=True)

    al = carregar_alertabilidade()
    if not al.empty:
        st.subheader("Pendências de alertabilidade")
        st.dataframe(al, width="stretch", hide_index=True, height=280)

    st.subheader("Validar contato (rápido)")
    ct = carregar_contatos()
    if not ct.empty:
        mun_opt = sorted(ct["municipio"].dropna().unique().tolist())
        papel_opt = sorted(ct["papel"].dropna().unique().tolist()) if "papel" in ct.columns else []
        with st.form("validar_contato"):
            mun_v = st.selectbox("Município", mun_opt)
            papel_v = st.selectbox("Papel", papel_opt)
            tel_v = st.text_input("Telefone / celular")
            email_v = st.text_input("E-mail institucional")
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
                st.cache_data.clear()
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
        n_em = len(mod.emails_piloto()) if hasattr(mod, "emails_piloto") else 0
        st.caption(
            f"Credenciais: Telegram={'ok' if st_cred['telegram'] else 'ausente'} · "
            f"SMTP={'ok' if st_cred['smtp'] else 'ausente'} · "
            f"destinatários e-mail={n_em}. "
            "Configure `dados/tratados/despacho_secrets.env` "
            "(veja `.example`) ou secrets `[vigi]` no Cloud."
        )
    if fila_dir.exists():
        textos = sorted(fila_dir.glob("*.txt"))
        st.write(f"Textos de alerta prontos: **{len(textos)}** em `alertas/piloto/`")
        b1, b2 = st.columns(2)
        if b1.button("Gerar log de despacho (dry-run)") and mod:
            n = mod.despachar(dry_run=True)
            st.success(f"Dry-run: {n} registros em {log_path.name}")
        if b2.button("Enviar agora (requer credenciais)") and mod:
            if not mod.emails_piloto() and not mod.credenciais_status().get("telegram"):
                st.error("Sem e-mails cadastrados e sem Telegram — nada a enviar.")
            else:
                n = mod.despachar(dry_run=False)
                st.warning(f"Tentativa de envio: {n} registros no log — confira status.")
    else:
        st.info("Pasta alertas/piloto ausente — rode a etapa 18.")

    if log_path.exists():
        st.subheader("Últimos despachos")
        st.dataframe(
            pd.read_csv(log_path, sep=";", encoding="utf-8-sig").tail(30),
            width="stretch",
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
    st.markdown("# Confirmação de recebimento")
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
            width="stretch",
            hide_index=True,
        )
    st.info("O painel HTML com timer permanece em Desenvolvimento / HTML offline.")


def pagina_rag_docs() -> None:
    st.markdown("# Biblioteca e documentos")
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
    st.markdown("# Análise por região de saúde")
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
    st.dataframe(view, width="stretch", hide_index=True, height=400)


def pagina_notificacoes_impactos(df_barragens: pd.DataFrame) -> None:
    """Registro de possíveis rompimentos / impactos + autofill da barragem."""
    st.markdown("# Notificações e impactos")
    st.markdown(
        '<p class="nota">Registro operacional de <b>possível rompimento / impacto</b> '
        "com dados do sistema (população, IDAP, US no buffer) + campos preenchidos pela equipe. "
        "Não substitui SIM/SINAN nem ordem da Defesa Civil.</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Quem recebe e onde fica registrado")
    ct = carregar_contatos()
    emails = []
    if not ct.empty and "email" in ct.columns:
        emails = sorted(
            {
                str(e).strip()
                for e in ct["email"].fillna("").tolist()
                if isinstance(e, str) and "@" in e
            }
        )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            "**Destinatários previstos (despacho)**\n\n"
            "- Papéis do cadastro `contatos_institucionais_piloto.csv`: "
            "gestor municipal de saúde, vigilância, CIEVS/SES, Defesa Civil (quando houver e-mail).\n"
            "- Envio real via etapa 29 (SMTP/`secrets [vigi]` ou Telegram).\n"
            f"- E-mails preenchidos hoje: **{len(emails)}** "
            + (f"({', '.join(emails[:8])}{'…' if len(emails) > 8 else ''})" if emails else "(nenhum — cadastro ainda em exercício técnico sem e-mail).")
        )
    with c2:
        st.markdown(
            "**Onde os dados ficam**\n\n"
            "- Esta tela → `dados/tratados/notificacoes_impactos.csv`\n"
            "- Ficha rápida HTML → só `localStorage` do navegador (+ JSON exportado)\n"
            "- Confirmações → `dados/tratados/confirmacoes/confirmacoes.csv`\n"
            "- Log de despacho → `despacho_alertas_log.csv`"
        )

    from st_app.data import (
        carregar_cnes_pontos,
        cnes_no_buffer,
        estimar_pop_cenario,
        ordenar_por_severidade,
        rotulo_regulada,
        rotulo_sim_nao,
    )
    from st_app.data import haversine_km

    if df_barragens.empty:
        st.error("Base de barragens ausente.")
        return

    ordenado = ordenar_por_severidade(df_barragens)
    labels = [
        f"{r.nome} — {r.id_snisb} ({getattr(r, 'nivel', '—')})"
        for r in ordenado.itertuples()
    ]
    # Prefill se veio de outra tela (simulação / visão territorial)
    pre_id = str(st.session_state.pop("barragem_notif_id", "") or "")
    idx0 = 0
    if pre_id:
        for i, lab in enumerate(labels):
            if f" — {pre_id} " in lab or lab.endswith(f" — {pre_id}"):
                idx0 = i
                break
    escolha = st.selectbox("Barragem do evento", labels, index=idx0)
    bid = escolha.split(" — ")[1].split(" ")[0]
    st.session_state["barragem_selecionada_id"] = bid
    r = df_barragens[df_barragens["id_snisb"] == bid].iloc[0]
    a1, a2 = st.columns(2)
    if a1.button("Abrir simulação com esta barragem"):
        st.session_state["barragem_sim_id"] = bid
        ir_para("Cenários e simulações", "Simular área potencialmente afetada")
    if a2.button("Abrir detalhe da barragem"):
        st.session_state["barragem_360_id"] = bid
        ir_para("Territórios e barragens", "Detalhe da barragem")

    afetados_txt = str(r.get("municipios_potencialmente_afetados") or "")
    afetados = [p.strip() for p in afetados_txt.split("|") if p.strip()]
    sede = str(r.get("municipio_sede") or r.get("municipio") or "") or None
    vol = float(r["capacidade_hm3"]) if pd.notna(r.get("capacidade_hm3")) else 0.0
    # Cenário-base 50% / 2 m para pré-preencher magnitude
    area = (vol * 0.5 / 2.0) if vol > 0 else 0.0
    raio = math.sqrt(area / math.pi) if area > 0 else 0.0
    est = estimar_pop_cenario(
        area_km2=area or 1.0,
        fracao=0.5,
        municipio_sede=sede,
        municipios_afetados=afetados or None,
        pop_afetadas=r.get("sigbm_pessoas_afetadas"),
        pop_jusante=r.get("sigbm_populacao_jusante"),
    )
    n_us = 0
    if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")) and raio > 0:
        us = cnes_no_buffer(
            carregar_cnes_pontos(),
            float(r["latitude"]),
            float(r["longitude"]),
            max(3.0, min(raio, 40.0)),
        )
        n_us = len(us)

    vul = carregar_exposicao_vulneraveis()
    n_vuln = 0
    if (
        not vul.empty
        and pd.notna(r.get("latitude"))
        and pd.notna(r.get("longitude"))
        and raio > 0
    ):
        lat0, lon0 = float(r["latitude"]), float(r["longitude"])
        for row in vul.dropna(subset=["latitude", "longitude"]).itertuples():
            cat = str(getattr(row, "categoria", "") or "").lower()
            if "saúde" in cat or "saude" in cat or "estabelecimento" in cat:
                continue
            if haversine_km(lat0, lon0, float(row.latitude), float(row.longitude)) <= raio:
                n_vuln += 1

    st.markdown("##### Dados do sistema (pré-preenchidos)")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("IDAP / nível", f"{r.get('idap', '—')} / {r.get('nivel', '—')}")
    k2.metric("Pop. estimada (proxy 50%)", f"{int(est.get('populacao_estimada') or 0):,}".replace(",", "."))
    k3.metric("US no raio proxy", n_us)
    k4.metric("Comunidades no raio", n_vuln)
    k5.metric("Mun. afetados (Otto)", int(r.get("n_municipios_afetados") or len(afetados) or 0))
    st.caption(
        f"Sede {sede or '—'} · CRI/DPA {r.get('categoria_risco') or '—'}/"
        f"{r.get('dano_potencial_associado') or '—'} · "
        f"vol. {r.get('capacidade_hm3') or '—'} hm³ · "
        f"PAE {rotulo_sim_nao(r.get('possui_pae'))} · "
        f"regulada {rotulo_regulada(r.get('indicador_regulada'), r.get('regulada_pelo_pnsb'))} · "
        f"raio proxy ~{raio:.1f} km (50% volume / 2 m). "
        f"Método pop.: `{est.get('metodo')}`."
    )

    with st.form("form_notif_impacto"):
        st.markdown("##### Complemento da equipe")
        t1, t2 = st.columns(2)
        with t1:
            tipo = st.selectbox(
                "Tipo de registro",
                [
                    "possível_rompimento",
                    "rompimento_confirmado",
                    "galgamento",
                    "incidente_estrutural",
                    "exercicio_simulado",
                    "outro",
                ],
            )
            magnitude = st.selectbox(
                "Magnitude percebida",
                ["baixa", "moderada", "alta", "extrema"],
                index=1,
            )
            data_ref = st.text_input(
                "Data/hora referência",
                value=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
        with t2:
            informante = st.text_input("Informante (nome/cargo)")
            canal = st.selectbox(
                "Canal de entrada",
                ["telefone", "whatsapp", "email", "radio", "presencial", "sistema"],
            )
            pop_informada = st.number_input(
                "População atingida (informada)",
                min_value=0,
                value=int(est.get("populacao_estimada") or 0),
                step=10,
            )
        obs = st.text_area("Descrição / impactos observados", height=100)
        desalojados = st.number_input("Desalojados", min_value=0, value=0)
        desabrigados = st.number_input("Desabrigados", min_value=0, value=0)
        us_afetadas_inf = st.number_input(
            "US afetadas (informadas)", min_value=0, value=int(n_us), step=1
        )
        gravar = st.form_submit_button("Registrar notificação")

    pasta = TRATADOS / "notificacoes"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / "notificacoes_impactos.csv"
    if gravar and informante:
        registro = {
            "instante": dt.datetime.now().isoformat(timespec="seconds"),
            "data_referencia": data_ref,
            "tipo": tipo,
            "magnitude": magnitude,
            "id_snisb": bid,
            "nome_barragem": r.get("nome"),
            "municipio_sede": sede,
            "nivel_idap": r.get("nivel"),
            "idap": r.get("idap"),
            "cri": r.get("categoria_risco"),
            "dpa": r.get("dano_potencial_associado"),
            "capacidade_hm3": r.get("capacidade_hm3"),
            "municipios_afetados_otto": afetados_txt,
            "pop_estimada_sistema": int(est.get("populacao_estimada") or 0),
            "metodo_pop": est.get("metodo"),
            "us_raio_sistema": n_us,
            "comunidades_raio_sistema": n_vuln,
            "pop_informada": pop_informada,
            "us_afetadas_informadas": us_afetadas_inf,
            "desalojados": desalojados,
            "desabrigados": desabrigados,
            "informante": informante,
            "canal": canal,
            "descricao": obs,
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
        }
        pd.DataFrame([registro]).to_csv(
            arq,
            mode="a",
            header=not arq.exists(),
            sep=";",
            index=False,
            encoding="utf-8-sig",
        )
        st.success(f"Registrado em `dados/tratados/notificacoes/{arq.name}`.")
        # Gera texto territorializado na fila para despacho
        fila = Path(__file__).resolve().parent.parent / "alertas" / "piloto"
        fila.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arq = f"notif_{tipo}_{bid}_{stamp}.txt"
        texto = (
            f"ALERTA-NOTIF-{stamp}-{bid}\n"
            f"Sistema: VIGIBARRAGENS-MT\n"
            f"Tipo: {tipo} · Magnitude: {magnitude}\n"
            f"Barragem: {r.get('nome')} (SNISB {bid})\n"
            f"Sede: {sede or '—'} · Nível IDAP: {r.get('nivel')} ({r.get('idap')})\n"
            f"CRI/DPA: {r.get('categoria_risco') or '—'} / {r.get('dano_potencial_associado') or '—'}\n"
            f"Municípios afetados (Otto): {afetados_txt or '—'}\n"
            f"Pop. estimada (sistema): {int(est.get('populacao_estimada') or 0)}\n"
            f"Pop. informada: {pop_informada}\n"
            f"US no raio (sistema): {n_us} · informadas: {us_afetadas_inf}\n"
            f"Comunidades vulneráveis no raio: {n_vuln}\n"
            f"Desalojados/desabrigados: {desalojados}/{desabrigados}\n"
            f"Informante: {informante} · canal: {canal}\n"
            f"Data ref.: {data_ref}\n"
            f"Descrição: {obs or '—'}\n"
            "\n"
            "RESSALVA: prontidão sanitária / registro operacional. "
            "NÃO é ordem de evacuação. Evacuação é exclusividade da Defesa Civil.\n"
        )
        (fila / nome_arq).write_text(texto, encoding="utf-8")
        st.info(
            f"Texto gerado na fila: `alertas/piloto/{nome_arq}`. "
            "Abra **Preparar e enviar alerta** para dry-run ou envio "
            "(requer e-mails validados + SMTP/Telegram)."
        )
        if st.button("Ir para Preparar e enviar alerta"):
            ir_para("Alertas e resposta", "Preparar e enviar alerta")
    elif gravar:
        st.warning("Informe o nome do informante para gravar.")

    st.subheader("Histórico de notificações / impactos")
    if arq.exists():
        hist = pd.read_csv(arq, sep=";", encoding="utf-8-sig")
        st.dataframe(hist.iloc[::-1], width="stretch", hide_index=True, height=320)
        st.download_button(
            "Baixar CSV",
            data=arq.read_text(encoding="utf-8-sig"),
            file_name="notificacoes_impactos.csv",
            mime="text/csv",
        )
    else:
        st.caption("Nenhum registro ainda.")
