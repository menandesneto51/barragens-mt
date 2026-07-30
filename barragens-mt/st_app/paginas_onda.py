"""Páginas e blocos da Onda 1–3 (sanitário, vulneráveis, despacho, RAG)."""

from __future__ import annotations

import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from st_app.data import (
    CORES_NIVEL,
    TRATADOS,
    card_kpi,
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
from st_app.sitrep import montar_sitrep_docx, montar_sitrep_md


def bloco_sanitario_e_historico(df: pd.DataFrame, *, mun_ativo: str | None) -> None:
    san = indicadores_sanitarios(df)
    hist = tendencia_idap_48h()
    t7 = tendencia_7d_score(df)
    solo = solo_chuva_composta(df)
    st.subheader("Indicadores sanitários")
    razao = san["razao_pop_us"]
    cards = [
        card_kpi(
            "População sob pressão sanitária",
            f"{san['pop_sob_pressao']:,}".replace(",", "."),
            sev=severidade_pct(min(100, san["pop_sob_pressao"] / 5000) if san["pop_sob_pressao"] else 0),
            nota="Estimativa nas Em atenção+ (SIGBM ou área×densidade)",
        ),
        card_kpi(
            "US na trajetória (proxy)",
            str(san["us_sob_risco"]),
            sev=severidade_pct(min(100, san["us_sob_risco"] / 5) if san["us_sob_risco"] else 0),
            nota=f"Prioritárias: {san['us_prioritarias']}",
        ),
        card_kpi(
            "Razão pop. / US prioritária",
            "—" if razao is None else f"{razao:,.0f}".replace(",", "."),
            sev=severidade_pct(None if razao is None else min(100, razao / 50)),
            nota="Quanto maior, maior sobrecarga potencial",
        ),
        card_kpi(
            "Municípios a jusante em atenção",
            str(san["municipios_jusante"]),
            sev=severidade_pct(min(100, san["municipios_jusante"] * 5)),
        ),
        card_kpi(
            "Completude média do índice",
            "—" if san["completude_media"] is None else f"{san['completude_media']:.0f}%",
            sev="sev-ok"
            if (san["completude_media"] or 0) >= 70
            else ("sev-atencao" if (san["completude_media"] or 0) >= 40 else "sev-alto"),
        ),
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
    st.markdown('<div class="grade-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    if hist.get("ok"):
        st.markdown(
            f'<div class="tend-box {hist["classe"]}"><b>Tendência do índice (24–48 h / últimas rodadas)</b><br>'
            f'{hist["msg"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(hist.get("msg", ""))

    proj = projecao_semana(df)
    sev_t, msg_t = tendencia_climatica_texto(proj, df)
    sitrep = montar_sitrep_md(
        df,
        municipio=mun_ativo,
        proj=proj,
        tend_clima=msg_t,
    )
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        st.download_button(
            "Baixar SITREP (Markdown)",
            data=sitrep.encode("utf-8"),
            file_name=f"sitrep_vigibarragens_{(mun_ativo or 'MT').replace(' ', '_')}.md",
            mime="text/markdown",
            help="Relatório de situação de 1 página para o recorte atual.",
        )
    with c_dl2:
        try:
            docx_bytes = montar_sitrep_docx(
                df, municipio=mun_ativo, proj=proj, tend_clima=msg_t
            )
            st.download_button(
                "Baixar SITREP (DOCX)",
                data=docx_bytes,
                file_name=f"sitrep_vigibarragens_{(mun_ativo or 'MT').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as exc:  # noqa: BLE001
            st.caption(f"DOCX indisponível ({exc})")


def bloco_quase_atencao(df: pd.DataFrame) -> None:
    q = quase_atencao(df)
    st.subheader("Quase atenção — vigília")
    st.caption(
        "Barragens ainda verdes, mas com pressão climática alta ou chuva prevista ≥40 mm."
    )
    if q.empty:
        st.success("Nenhuma barragem verde sob pressão climática relevante no recorte.")
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
        height=280,
    )


def pagina_municipio_360(df: pd.DataFrame, municipio: str) -> None:
    st.markdown(f"## Município 360° — {municipio}")
    st.markdown(
        '<p class="nota">Visão sanitária do município como <b>sede</b> e/ou '
        "<b>potencialmente afetado a jusante</b> (a barragem pode estar em outro município).</p>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.warning("Sem barragens vinculadas a este município.")
        return
    bloco_sanitario_e_historico(df, mun_ativo=municipio)
    sede = df[df.get("papel_municipio", pd.Series(dtype=str)).astype(str).str.contains("Sede", na=False)]
    jus = df[df.get("papel_municipio", pd.Series(dtype=str)).astype(str).str.contains("jusante|Afetado", case=False, na=False)]
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
        st_folium(m, height=420, use_container_width=True, returned_objects=[])
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
        height=360,
    )


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

    # Coordenadas: barragem do IDAP + centroide municipal (média de barragens na sede)
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

    st.subheader("Despacho (fila)")
    fila_dir = Path(__file__).resolve().parent.parent / "alertas" / "piloto"
    log_path = TRATADOS / "despacho_alertas_log.csv"
    if fila_dir.exists():
        textos = sorted(fila_dir.glob("*.txt"))
        st.write(f"Textos de alerta prontos: **{len(textos)}** em `alertas/piloto/`")
        if st.button("Gerar log de despacho (dry-run)"):
            import importlib.util
            import sys

            raiz = Path(__file__).resolve().parent.parent
            if str(raiz) not in sys.path:
                sys.path.insert(0, str(raiz))
            spec = importlib.util.spec_from_file_location(
                "despacho29",
                raiz / "scripts" / "29_despacho_alertas.py",
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                n = mod.despachar(dry_run=True)
                st.success(f"Dry-run: {n} registros em {log_path.name}")
            else:
                st.error("Não foi possível carregar scripts/29_despacho_alertas.py")
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
        import datetime as dt

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
    st.info("O painel HTML com timer permanece em «Confirmação (HTML)».")


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
        # trecho: primeira ocorrência
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
