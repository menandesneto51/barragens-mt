"""Navegação institucional do painel Streamlit (5 áreas + aliases).

Primeira entrega da revisão de UX: áreas nomeadas para gestores, sem jargão
técnico no primeiro contato. Páginas HTML gêmeas ficam fora do menu principal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

# Área → páginas (rótulos públicos)
AREAS: dict[str, list[str]] = {
    "Visão geral": [
        "Visão geral estadual",
    ],
    "Territórios e barragens": [
        "Análise por município",
        "Análise por região de saúde",
        "Detalhe da barragem",
        "Populações vulneráveis",
        "Impacto fora do município-sede",
        "Tipos e usos das barragens",
    ],
    "Alertas e resposta": [
        "Fila de alertas",
        "Preparar e enviar alerta",
        "Confirmação de recebimento",
        "Notificações e impactos",
        "Registro rápido pós-evento",
        "VIGIPÓS O/E",
    ],
    "Cenários e simulações": [
        "Chuva e condições hidrológicas",
        "Área prioritária Manso–Cuiabá",
        "Simular área potencialmente afetada",
    ],
    "Dados, metodologia e documentos": [
        "Cadastro de barragens",
        "Como interpretar os indicadores",
        "Biblioteca e documentos",
    ],
}

# Páginas só para desenvolvimento / offline (fora do menu principal)
PAGINAS_DEV: list[str] = [
    "Comando (HTML)",
    "Confirmação (HTML)",
]

# Nome canônico da simulação
TELA_SIMULACAO = "Simular área potencialmente afetada"

# Migração de rótulos antigos → novos
ALIAS_PAGINA: dict[str, str] = {
    "Comando estadual": "Visão geral estadual",
    "Visão territorial": "Análise por município",
    "Hidro municipal": "Chuva e condições hidrológicas",
    "Eixo Manso–Cuiabá": "Área prioritária Manso–Cuiabá",
    "Impacto extraterritorial": "Mapa de impacto em outras localidades (jusante)",
    "Mapa por tipologia": "Tipos e usos das barragens",
    "Barragem 360°": "Detalhe da barragem",
    "Alertabilidade / despacho": "Preparar e enviar alerta",
    "Confirmação persistente": "Confirmação de recebimento",
    "Ficha rápida": "Registro rápido pós-evento",
    "Simulação de cenário": TELA_SIMULACAO,
    "Simulação volume/área": TELA_SIMULACAO,
    "Interpretação / KPIs": "Como interpretar os indicadores",
    "Região de saúde": "Análise por região de saúde",
    "Documentos (RAG leve)": "Biblioteca e documentos",
    "Inventário": "Cadastro de barragens",
}

ALIAS_AREA: dict[str, str] = {
    "Território": "Territórios e barragens",
    "Situação": "Visão geral",
    "Ação": "Alertas e resposta",
    "Dados e apoio": "Dados, metodologia e documentos",
}

VERSAO_INSTITUCIONAL = "1.0 institucional"
FONTES_PRINCIPAIS = "SNISB, SIGBM, ANA, Cemaden, INMET, CNES e bases SES-MT"

# Perfis de visualização — restringem áreas padrão (técnico vê tudo).
PERFIS: dict[str, dict[str, Any]] = {
    "Gestor municipal": {
        "areas": [
            "Visão geral",
            "Territórios e barragens",
            "Alertas e resposta",
            "Cenários e simulações",
        ],
        "ajuda": "Foco em recorte local, pessoas expostas e alertas a confirmar.",
    },
    "CIEVS / vigilância": {
        "areas": [
            "Visão geral",
            "Territórios e barragens",
            "Alertas e resposta",
            "Cenários e simulações",
            "Dados, metodologia e documentos",
        ],
        "ajuda": "Monitoramento estadual, despacho e interpretação dos indicadores.",
    },
    "Técnico / analista": {
        "areas": list(AREAS.keys()),
        "ajuda": "Acesso completo, inclusive cadastro, metodologia e HTML offline.",
    },
}


def areas_visiveis(perfil: str | None = None) -> list[str]:
    p = perfil or st.session_state.get("perfil_ui") or "CIEVS / vigilância"
    cfg = PERFIS.get(p) or PERFIS["CIEVS / vigilância"]
    return [a for a in AREAS if a in cfg["areas"]]


def normalizar_pagina(nome: str | None) -> str:
    if not nome:
        return "Visão geral estadual"
    return ALIAS_PAGINA.get(nome, nome)


def normalizar_area(nome: str | None) -> str:
    if not nome:
        return "Visão geral"
    return ALIAS_AREA.get(nome, nome)


def area_da_pagina(pagina: str) -> str | None:
    p = normalizar_pagina(pagina)
    for area, telas in AREAS.items():
        if p in telas:
            return area
    if p in PAGINAS_DEV:
        return "Dados, metodologia e documentos"
    return None


def migrar_estado_navegacao() -> None:
    """Converte chaves legadas (jornada/tela antigas) para a estrutura atual."""
    if "jornada" in st.session_state:
        st.session_state["jornada"] = normalizar_area(st.session_state.get("jornada"))
    if "pagina" in st.session_state:
        st.session_state["pagina"] = normalizar_pagina(st.session_state.get("pagina"))


def cabecalho_institucional(
    *,
    situacao: str = "—",
    atualizado_em: str | None = None,
) -> None:
    """Faixa superior: assinatura GOV/SES + produto + ações."""
    agora = atualizado_em or datetime.now().strftime("%d/%m/%Y, %Hh%M")
    cor_sit = {
        "Verde": "#1e8449",
        "Amarelo": "#b7950b",
        "Laranja": "#d35400",
        "Vermelho": "#c0392b",
        "Roxo": "#5b2c6f",
    }.get(situacao, "#5b6b80")
    st.markdown(
        f"""
<div class="cab-inst">
  <div class="cab-inst-topo">
    Governo de Mato Grosso · Secretaria de Estado de Saúde · CIEVS-MT
  </div>
  <div class="cab-inst-linha">
    <div class="cab-inst-marca">
      <div class="cab-inst-nome">VIGIBARRAGENS–MT</div>
      <div class="cab-inst-tag">
        Monitoramento de riscos e apoio à preparação e resposta do setor saúde
      </div>
    </div>
    <div class="cab-inst-meta">
      <div>Atualização: <b>{agora}</b></div>
      <div>Situação geral:
        <span class="cab-inst-sit" style="background:{cor_sit}">{situacao}</span>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("? Como usar", key="btn_como_usar", help="Tutorial de primeiro acesso"):
            st.session_state["mostrar_tutorial"] = True
            st.rerun()
    with c2:
        st.session_state.setdefault("gerar_sitrep_pedido", False)
        if st.button("Gerar SITREP", key="btn_gerar_sitrep"):
            st.session_state["gerar_sitrep_pedido"] = True
            st.session_state["jornada"] = "Visão geral"
            st.session_state["pagina"] = "Visão geral estadual"
            st.rerun()


def barra_contexto(
    *,
    estado: str = "Mato Grosso",
    regiao: str | None = None,
    municipio: str | None = None,
    atualizado_em: str | None = None,
) -> None:
    reg = regiao or "Todas as regiões"
    mun = municipio or "Todos os municípios"
    agora = atualizado_em or datetime.now().strftime("%d/%m/%Y, %Hh%M")
    st.markdown(
        f'<div class="barra-ctx">Recorte atual: <b>{estado}</b> · {reg} · {mun}'
        f" · Atualização: {agora}</div>",
        unsafe_allow_html=True,
    )


def rodape_lateral(*, atualizado_em: str | None = None) -> None:
    agora = atualizado_em or datetime.now().strftime("%d/%m/%Y")
    st.caption(f"Dados atualizados em: **{agora}**")
    st.caption(f"Fontes principais: {FONTES_PRINCIPAIS}")
    st.caption(f"Versão: {VERSAO_INSTITUCIONAL}")


def bloco_guia_60s() -> None:
    with st.expander("Leia nesta ordem (guia de 60 segundos)", expanded=False):
        st.markdown(
            """
1. **Recorte** — Qual território está selecionado?
2. **Nível de prontidão** — Qual é a pior situação presente no recorte?
3. **Motivo** — Chuva, condição cadastral/estrutural, exposição sanitária ou dificuldade de resposta?
4. **Pessoas e serviços** — Quantas pessoas, municípios e unidades de saúde podem ser afetados?
5. **Prioridades** — Quais barragens ou territórios devem ser verificados primeiro?
6. **Ação** — Há alerta para preparar, enviar ou confirmar?
"""
        )


def bloco_idap_na_home() -> None:
    with st.expander("Como ler o IDAP nesta tela", expanded=True):
        st.markdown(
            """
**O que significa:** nível integrado de **alerta e prontidão** para o setor saúde.

**Não significa:** probabilidade de rompimento ou estabilidade estrutural isolada.

**Interpretação:** valores maiores → maior necessidade de verificação, preparação e articulação.

**Componentes:** pressão hidroclimática · condição da barragem · impacto sanitário · capacidade de resposta.

**Faixas:** Verde 0–19 · Amarelo 20–39 · Laranja 40–59 · Vermelho 60–79 · Roxo 80–100.
"""
        )


def aviso_simulacao_permanente() -> None:
    st.warning(
        "**Cenário estimado para planejamento sanitário.** "
        "Não representa mancha oficial de inundação, probabilidade de rompimento "
        "nem ordem de evacuação."
    )


def tutorial_primeiro_acesso() -> None:
    """Diálogo em 4 etapas (nível 1 do tutorial integrado)."""
    if not st.session_state.get("mostrar_tutorial"):
        return
    passo = int(st.session_state.get("tutorial_passo", 1))
    textos = {
        1: (
            "Etapa 1 — Escolha o território",
            "Use os filtros para analisar o estado, uma região de saúde, um município "
            "ou uma barragem específica. Confira sempre o **recorte** no alto da página.",
        ),
        2: (
            "Etapa 2 — Leia a prontidão",
            "A cor indica o nível de atenção e prontidão para o setor saúde. "
            "O **IDAP não informa a probabilidade de rompimento**.",
        ),
        3: (
            "Etapa 3 — Verifique pessoas e serviços",
            "Observe população potencialmente exposta, grupos vulneráveis, "
            "municípios a jusante e unidades de saúde que podem ser afetadas ou pressionadas.",
        ),
        4: (
            "Etapa 4 — Identifique a ação",
            "Abra as barragens prioritárias, verifique os fatores que elevaram o nível "
            "e consulte as ações recomendadas, contatos e alertas pendentes.",
        ),
    }
    titulo, corpo = textos.get(passo, textos[1])
    st.markdown(
        f'<div class="tut-box"><div class="tut-passo">Como usar · {passo}/4</div>'
        f"<h3>{titulo}</h3><p>{corpo}</p></div>",
        unsafe_allow_html=True,
    )
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Voltar", disabled=passo <= 1, key="tut_voltar"):
            st.session_state["tutorial_passo"] = max(1, passo - 1)
            st.rerun()
    with b2:
        if passo < 4:
            if st.button("Próximo", type="primary", key="tut_prox"):
                st.session_state["tutorial_passo"] = passo + 1
                st.rerun()
        else:
            if st.button("Começar a usar", type="primary", key="tut_fim"):
                st.session_state["mostrar_tutorial"] = False
                st.session_state["tutorial_passo"] = 1
                st.session_state["tutorial_visto"] = True
                st.rerun()
    with b3:
        if st.button("Pular", key="tut_pular"):
            st.session_state["mostrar_tutorial"] = False
            st.session_state["tutorial_passo"] = 1
            st.session_state["tutorial_visto"] = True
            st.rerun()


def motivo_nivel_texto(df: pd.DataFrame) -> str:
    """Frase objetiva sobre o principal fator da atualização (proxy)."""
    if df is None or df.empty:
        return "Sem base de alerta carregada nesta execução."
    view = df.copy()
    if "idap_n" not in view.columns and "idap" in view.columns:
        view["idap_n"] = pd.to_numeric(view["idap"], errors="coerce")
    top = view.sort_values("idap_n", ascending=False).head(20) if "idap_n" in view.columns else view.head(20)
    # Heurística: maior contribuição relativa entre eixos A/B/C/D nas top
    eixos = []
    for col, rotulo in (
        ("pontos_a", "previsão/pressão hidroclimática"),
        ("pontos_b", "condição cadastral ou estrutural da barragem"),
        ("pontos_c", "exposição sanitária (pessoas e serviços)"),
        ("pontos_d", "capacidade de resposta / alertabilidade"),
    ):
        if col in top.columns:
            eixos.append((float(pd.to_numeric(top[col], errors="coerce").fillna(0).mean()), rotulo))
    if not eixos:
        return (
            "Revise as barragens em atenção na lista prioritária e confira chuva, "
            "cadastro e exposição sanitária."
        )
    eixos.sort(reverse=True)
    fator = eixos[0][1]
    n_at = int(view["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"]).sum()) if "nivel" in view.columns else 0
    return (
        f"Principal fator desta atualização (proxy nas prioritárias): **{fator}**. "
        f"Há **{n_at}** barragem(ns) em atenção ou pior no recorte."
    )


def acoes_recomendadas(df: pd.DataFrame) -> list[str]:
    """Recomendações objetivas; prioriza ações conforme o pior nível do recorte."""
    ordem = ["Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"]
    sem = "Verde"
    if df is not None and not df.empty and "nivel" in df.columns:
        for n in ordem:
            if (df["nivel"] == n).any():
                sem = n
                break

    por_nivel: dict[str, list[str]] = {
        "Roxo": [
            "Acionar sala de situação CIEVS-MT e articular Defesa Civil imediatamente.",
            "Confirmar recebimento do alerta com todos os pontos focais do recorte.",
            "Revisar unidades de saúde e abrigos sob pressão agora.",
        ],
        "Vermelho": [
            "Preparar e enviar alerta aos municípios potencialmente afetados.",
            "Confirmar situação da barragem com o órgão fiscalizador responsável.",
            "Revisar unidades de saúde potencialmente afetadas no cenário.",
        ],
        "Laranja": [
            "Verificar contato do ponto focal municipal nas barragens prioritárias.",
            "Acompanhar previsão de chuva e alertas Cemaden/INMET/ANA.",
            "Preparar comunicado preventivo para a rede de atenção.",
        ],
        "Amarelo": [
            "Verificar contato do ponto focal municipal nas barragens prioritárias.",
            "Acompanhar previsão de chuva nas próximas 72 h.",
            "Revisar unidades de saúde potencialmente afetadas no cenário.",
        ],
        "Verde": [
            "Manter rotina de monitoramento e atualização de contatos.",
            "Acompanhar previsão de chuva e alertas Cemaden/INMET/ANA.",
            "Revisar cadastro e lacunas de dados nas barragens do recorte.",
        ],
    }
    acoes = list(por_nivel.get(sem, por_nivel["Amarelo"]))
    if df is not None and not df.empty and "alertavel" in df.columns:
        s = df["alertavel"].astype(str).str.lower()
        n_nao = int((~s.isin(["sim", "true", "1", "yes"])).sum())
        if n_nao > 0 and sem != "Verde":
            acoes.insert(
                0,
                f"Completar canal de alerta — {n_nao} barragens sem contato confirmado no recorte.",
            )
    return acoes[:5]


def aplicar_query_params(df: pd.DataFrame | None = None) -> None:
    """Deep-links: ?municipio=...&barragem=...&area=...&pagina=..."""
    try:
        params = st.query_params
    except Exception:  # noqa: BLE001
        return
    if not params:
        return
    if "perfil" in params:
        p = str(params.get("perfil") or "")
        if p in PERFIS:
            st.session_state["perfil_ui"] = p
    if "municipio" in params:
        mun = str(params.get("municipio") or "").strip()
        if mun:
            st.session_state["filtro_municipio"] = mun
            st.session_state["ctx_municipio"] = mun
    if "barragem" in params:
        bid = str(params.get("barragem") or "").strip()
        if bid:
            st.session_state["barragem_destaque_id"] = bid
            st.session_state["barragem_360_id"] = bid
            st.session_state["jornada"] = "Territórios e barragens"
            st.session_state["pagina"] = "Detalhe da barragem"
    if "area" in params:
        area = normalizar_area(str(params.get("area") or ""))
        if area in AREAS:
            st.session_state["jornada"] = area
    if "pagina" in params:
        pag = normalizar_pagina(str(params.get("pagina") or ""))
        st.session_state["pagina"] = pag
        a = area_da_pagina(pag)
        if a:
            st.session_state["jornada"] = a


def render_filtros_persistentes(df: pd.DataFrame) -> None:
    """Filtros de recorte na sidebar — persistem entre páginas."""
    from st_app.data import municipios_catalogo
    from st_app.indicadores import carregar_contatos

    st.markdown("##### Filtros do recorte")
    munis = municipios_catalogo(df) if df is not None and not df.empty else []
    contatos = carregar_contatos()
    regioes = (
        sorted(contatos["regiao_saude"].dropna().unique().tolist())
        if not contatos.empty and "regiao_saude" in contatos.columns
        else []
    )
    munis_por_regiao: dict[str, set[str]] = {}
    if regioes and not contatos.empty and "municipio" in contatos.columns:
        for _, row in contatos.dropna(subset=["regiao_saude", "municipio"]).iterrows():
            munis_por_regiao.setdefault(str(row["regiao_saude"]), set()).add(
                str(row["municipio"]).strip()
            )
    st.session_state["_munis_por_regiao"] = munis_por_regiao

    op_mun = ["(estado todo)"] + munis
    atual_mun = st.session_state.get("filtro_municipio") or "(estado todo)"
    if atual_mun not in op_mun:
        atual_mun = "(estado todo)"
    idx_m = op_mun.index(atual_mun)
    mun_sel = st.selectbox("Município", op_mun, index=idx_m, key="filtro_municipio_ui")
    st.session_state["filtro_municipio"] = None if mun_sel == "(estado todo)" else mun_sel
    st.session_state["ctx_municipio"] = st.session_state["filtro_municipio"]

    op_reg = ["(todas)"] + regioes
    atual_reg = st.session_state.get("filtro_regiao") or "(todas)"
    if atual_reg not in op_reg:
        atual_reg = "(todas)"
    reg_sel = st.selectbox(
        "Região de saúde",
        op_reg,
        index=op_reg.index(atual_reg),
        key="filtro_regiao_ui",
        disabled=not regioes,
    )
    st.session_state["filtro_regiao"] = None if reg_sel == "(todas)" else reg_sel
    st.session_state["ctx_regiao"] = st.session_state["filtro_regiao"]

    niveis_default = [
        "Roxo",
        "Vermelho",
        "Laranja",
        "Amarelo",
        "Verde",
    ]
    if "filtro_niveis_ui" not in st.session_state:
        st.session_state["filtro_niveis_ui"] = st.session_state.get("filtro_niveis") or niveis_default
    niveis = st.multiselect(
        "Nível de prontidão",
        niveis_default,
        key="filtro_niveis_ui",
    )
    st.session_state["filtro_niveis"] = niveis or niveis_default
    if "filtro_piloto_ui" not in st.session_state:
        st.session_state["filtro_piloto_ui"] = bool(st.session_state.get("filtro_piloto"))
    so_piloto = st.checkbox(
        "Só área prioritária Manso–Cuiabá",
        key="filtro_piloto_ui",
    )
    st.session_state["filtro_piloto"] = so_piloto

    if st.session_state.get("filtro_municipio"):
        if st.button("Abrir análise deste município", width="stretch"):
            st.session_state["jornada"] = "Territórios e barragens"
            st.session_state["pagina"] = "Análise por município"
            st.rerun()


def aplicar_filtros_df(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Aplica filtros persistentes; retorna (view, municipio_ativo)."""
    if df is None or df.empty:
        return df, None
    view = df.copy()
    mun_ativo = st.session_state.get("filtro_municipio")
    reg = st.session_state.get("filtro_regiao")
    niveis = st.session_state.get("filtro_niveis") or [
        "Roxo",
        "Vermelho",
        "Laranja",
        "Amarelo",
        "Verde",
    ]
    if mun_ativo:
        from st_app.data import filtrar_municipio

        view = filtrar_municipio(view, mun_ativo)
    elif reg:
        alvos = st.session_state.get("_munis_por_regiao", {}).get(reg) or set()
        if alvos:
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
    if niveis and "nivel" in view.columns:
        view = view[view["nivel"].isin(niveis)]
    if st.session_state.get("filtro_piloto") and "piloto" in view.columns:
        pil = view["piloto"]
        if pil.dtype == bool:
            view = view[pil]
        else:
            view = view[pd.to_numeric(pil, errors="coerce").fillna(0).astype(int) > 0]
    return view, mun_ativo


def bloco_historico_niveis() -> None:
    """Série das últimas rodadas IDAP (contagens por nível)."""
    try:
        from st_app.data import carregar_historico_indice

        hist = carregar_historico_indice()
    except Exception:  # noqa: BLE001
        hist = pd.DataFrame()
    with st.expander("Histórico das mudanças de nível (estado)", expanded=False):
        if hist is None or hist.empty:
            st.caption("Histórico ainda sem snapshots suficientes.")
            return
        cols = [c for c in ("instante", "arquivo", "n_barragens", "roxo", "vermelho", "laranja", "amarelo", "verde") if c in hist.columns]
        mostra = hist[cols].tail(8).iloc[::-1]
        st.dataframe(mostra, width="stretch", hide_index=True, height=220)
        if len(hist) >= 2:
            ant, atu = hist.iloc[-2], hist.iloc[-1]
            def _n(row, k):
                try:
                    return int(row.get(k) or 0)
                except (TypeError, ValueError):
                    return 0
            ama_ant = _n(ant, "amarelo") + _n(ant, "laranja") + _n(ant, "vermelho") + _n(ant, "roxo")
            ama_atu = _n(atu, "amarelo") + _n(atu, "laranja") + _n(atu, "vermelho") + _n(atu, "roxo")
            delta = ama_atu - ama_ant
            st.caption(
                f"Atenção+ na última rodada: **{ama_atu}** "
                f"({delta:+d} vs rodada anterior)."
            )


def meta_atualizacao(df: pd.DataFrame | None = None) -> str:
    """Melhor esforço para data de atualização a partir do histórico ou agora."""
    try:
        from st_app.data import carregar_historico_indice

        hist = carregar_historico_indice()
        if hist is not None and not hist.empty:
            col = "data" if "data" in hist.columns else hist.columns[0]
            val = str(hist[col].iloc[-1])
            if val and val != "nan":
                return val[:16].replace("T", ", ")
    except Exception:  # noqa: BLE001
        pass
    return datetime.now().strftime("%d/%m/%Y, %Hh%M")
