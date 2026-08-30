"""Status honesto dos coletores (A8): silêncio ≠ sem risco.

Lê artefatos já produzidos pelas etapas (auditoria ANA, IndicaSUS, hidro)
e monta avisos para Comando / Detalhe — sem zerar o IDAP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TRATADOS = RAIZ / "dados" / "tratados"

AUDITORIA_ANA = TRATADOS / "auditoria_ana_sisclima.json"
INDICASUS_STATUS = TRATADOS / "indicasus_leitos_status.json"
HIDRO_BARRAGENS = TRATADOS / "hidro_barragens_mt.csv"
HIDRO_MUNICIPIOS = TRATADOS / "hidro_municipios_mt.csv"


def _ler_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def status_coletores(*, id_snisb: str | None = None) -> dict[str, Any]:
    """Resumo de lacunas/indisponibilidade de fontes (não altera IDAP)."""
    lacunas: list[dict[str, str]] = []

    ana = _ler_json(AUDITORIA_ANA)
    if not ana:
        lacunas.append(
            {
                "fonte": "ANA / SisClima",
                "severidade": "alto",
                "mensagem": "auditoria_ana_sisclima.json ausente — rode a etapa 52",
            }
        )
    else:
        series_ok = bool(ana.get("series_fluviometricas_disponiveis"))
        sqlite_ok = bool(ana.get("sqlite_tem_tabelas_ana"))
        fonte = str(ana.get("fonte_telemetria") or ana.get("fonte_estacoes") or "")
        sample = "sample" in fonte.casefold() or "csv:" in fonte.casefold()
        if not series_ok:
            lacunas.append(
                {
                    "fonte": "ANA / SisClima",
                    "severidade": "alto",
                    "mensagem": "séries fluviométricas indisponíveis — completude A6 reduzida",
                }
            )
        elif not sqlite_ok or sample:
            lacunas.append(
                {
                    "fonte": "ANA / SisClima",
                    "severidade": "atencao",
                    "mensagem": (
                        "usando fallback CSV/sample (SisClima sem tabelas ANA ou "
                        "ANA_FETCH_SERIES/token ausente) — não é telemetria operacional plena"
                    ),
                }
            )

    ind = _ler_json(INDICASUS_STATUS)
    if not ind:
        lacunas.append(
            {
                "fonte": "IndicaSUS",
                "severidade": "atencao",
                "mensagem": "status IndicaSUS ausente — leitos/ocupação (D6/IPAPD) incompletos",
            }
        )
    elif not ind.get("ok"):
        lacunas.append(
            {
                "fonte": "IndicaSUS",
                "severidade": "alto",
                "mensagem": str(ind.get("motivo") or "IndicaSUS indisponível"),
            }
        )
    else:
        fonte_i = str(ind.get("fonte") or "")
        motivo = str(ind.get("motivo") or "")
        if "seed" in fonte_i.casefold() or "seed" in motivo.casefold() or "exemplo" in fonte_i.casefold():
            lacunas.append(
                {
                    "fonte": "IndicaSUS",
                    "severidade": "atencao",
                    "mensagem": "fonte seed/exemplo — substituir por extrato IndicaSUS/DW oficial",
                }
            )

    hidro_ok = HIDRO_BARRAGENS.is_file() or HIDRO_MUNICIPIOS.is_file()
    if not hidro_ok:
        lacunas.append(
            {
                "fonte": "Hidro SisClima/TITAN",
                "severidade": "alto",
                "mensagem": "hidro_barragens_mt.csv ausente — rode a etapa 17",
            }
        )
    elif id_snisb and HIDRO_BARRAGENS.is_file():
        try:
            df = pd.read_csv(HIDRO_BARRAGENS, sep=";", dtype=str, nrows=50000)
            hit = df[df["id_snisb"].astype(str) == str(id_snisb)] if "id_snisb" in df.columns else df.iloc[0:0]
            if hit.empty:
                lacunas.append(
                    {
                        "fonte": "Hidro SisClima/TITAN",
                        "severidade": "atencao",
                        "mensagem": f"barragem {id_snisb} sem linha hidro — completude A reduzida",
                    }
                )
            else:
                row = hit.iloc[0]
                fontes = " ".join(
                    str(row.get(c) or "")
                    for c in ("fonte_precip", "fonte_hidro", "fonte_solo", "a6_fonte")
                ).casefold()
                if "sample" in fontes or (not str(row.get("fonte_precip") or "").strip()):
                    lacunas.append(
                        {
                            "fonte": "Hidro SisClima/TITAN",
                            "severidade": "atencao",
                            "mensagem": "precipitação/fonte hidro frágil ou vazia nesta barragem",
                        }
                    )
        except (OSError, ValueError, pd.errors.ParserError):
            lacunas.append(
                {
                    "fonte": "Hidro SisClima/TITAN",
                    "severidade": "atencao",
                    "mensagem": "falha ao ler hidro_barragens_mt.csv",
                }
            )

    n_alto = sum(1 for x in lacunas if x["severidade"] == "alto")
    return {
        "ok": n_alto == 0 and len(lacunas) == 0,
        "n_lacunas": len(lacunas),
        "n_alto": n_alto,
        "lacunas": lacunas,
        "nota": "Lacunas baixam a confiança na leitura — o IDAP não é zerado.",
    }


def faixa_html(status: dict[str, Any] | None = None) -> str:
    """HTML compacto para banner no Streamlit (unsafe_allow_html)."""
    st = status if status is not None else status_coletores()
    if not st.get("lacunas"):
        return (
            '<div style="padding:.55rem .85rem;margin:.4rem 0 .8rem;'
            "border-left:4px solid #15803d;background:#f0fdf4;color:#14532d;"
            'font-size:.92rem">'
            "<b>Coletores:</b> fontes hidro/ANA/IndicaSUS sem lacuna crítica sinalizada."
            "</div>"
        )
    itens = "".join(
        f"<li><b>{x['fonte']}</b> indisponível ou incompleto — {x['mensagem']}</li>"
        for x in st["lacunas"]
    )
    cor = "#b91c1c" if st.get("n_alto") else "#b45309"
    bg = "#fef2f2" if st.get("n_alto") else "#fffbeb"
    return (
        f'<div style="padding:.55rem .85rem;margin:.4rem 0 .8rem;'
        f"border-left:4px solid {cor};background:{bg};color:#1c1917;"
        f'font-size:.92rem">'
        f"<b>Completude reduzida (A8):</b> silêncio de coletor ≠ sem risco. "
        f"IDAP mantido; use com cautela.<ul style='margin:.35rem 0 0 1.1rem'>{itens}</ul>"
        f"<span style='opacity:.85'>{st.get('nota') or ''}</span>"
        f"</div>"
    )


def render_faixa_streamlit(*, id_snisb: str | None = None) -> None:
    import streamlit as st

    st.markdown(faixa_html(status_coletores(id_snisb=id_snisb)), unsafe_allow_html=True)
