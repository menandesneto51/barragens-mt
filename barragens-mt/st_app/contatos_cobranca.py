"""Lista de cobrança de contatos críticos (CIEVS / Vigilância / DC / gestor)."""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any

import pandas as pd

from st_app.localidade import PAPEIS_ALERTA_CRITICOS, nomes_equivalentes

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"

ROTULOS = {
    "gestor_municipal_saude": "Gestor saúde",
    "vigilancia_saude": "Vigilância",
    "defesa_civil_municipal": "Defesa Civil",
    "cievs": "CIEVS",
}


def _tem_fone(row: pd.Series) -> bool:
    dig = "".join(
        c for c in f"{row.get('telefone') or ''}{row.get('celular') or ''}" if c.isdigit()
    )
    return len(dig) >= 8


def _tem_email(row: pd.Series) -> bool:
    return "@" in str(row.get("email") or "")


def _validado_90d(raw: object, hoje: dt.date | None = None) -> bool:
    hoje = hoje or dt.date.today()
    s = str(raw or "").strip()[:10]
    if len(s) < 10:
        return False
    try:
        d = dt.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return False
    return (hoje - d).days <= 90


def lista_cobranca_contatos(
    contatos: pd.DataFrame | None = None,
    *,
    municipio: str | None = None,
    regiao: str | None = None,
) -> pd.DataFrame:
    """Linhas que precisam de telefone, e-mail ou revalidação (papéis críticos)."""
    from st_app.indicadores import carregar_contatos

    ct = contatos if contatos is not None else carregar_contatos()
    if ct.empty or "papel" not in ct.columns:
        return pd.DataFrame()
    sub = ct[ct["papel"].isin(PAPEIS_ALERTA_CRITICOS)].copy()
    if municipio and "municipio" in sub.columns:
        sub = sub[sub["municipio"].apply(lambda m: nomes_equivalentes(municipio, m))]
    if regiao and "regiao_saude" in sub.columns:
        sub = sub[sub["regiao_saude"].astype(str) == str(regiao)]
    if sub.empty:
        return pd.DataFrame()

    linhas: list[dict[str, Any]] = []
    for _, r in sub.iterrows():
        fone = _tem_fone(r)
        email = _tem_email(r)
        val90 = _validado_90d(r.get("data_validacao"))
        motivos: list[str] = []
        if not fone:
            motivos.append("sem_telefone")
        if not email:
            motivos.append("sem_email")
        if not val90:
            motivos.append("validacao_vencida_ou_ausente")
        if not motivos:
            continue
        linhas.append(
            {
                "municipio": r.get("municipio") or "",
                "regiao_saude": r.get("regiao_saude") or "",
                "papel": r.get("papel") or "",
                "papel_rotulo": r.get("papel_rotulo") or ROTULOS.get(str(r.get("papel")), ""),
                "nome": r.get("nome") or "",
                "telefone": r.get("telefone") or "",
                "email": r.get("email") or "",
                "data_validacao": r.get("data_validacao") or "",
                "motivos": "|".join(motivos),
                "prioridade": "1" if "sem_telefone" in motivos else ("2" if "sem_email" in motivos else "3"),
            }
        )
    if not linhas:
        return pd.DataFrame()
    out = pd.DataFrame(linhas)
    return out.sort_values(["prioridade", "municipio", "papel"]).reset_index(drop=True)


def kpis_contatos_criticos(
    contatos: pd.DataFrame | None = None,
    *,
    municipio: str | None = None,
    regiao: str | None = None,
) -> dict[str, Any]:
    from st_app.indicadores import carregar_contatos

    ct = contatos if contatos is not None else carregar_contatos()
    cob = lista_cobranca_contatos(ct, municipio=municipio, regiao=regiao)
    if ct.empty:
        return {
            "n_criticos": 0,
            "n_com_fone": 0,
            "n_com_email": 0,
            "n_validados_90d": 0,
            "n_cobranca": 0,
            "email_pronto_despacho": 0,
        }
    sub = ct[ct["papel"].isin(PAPEIS_ALERTA_CRITICOS)].copy() if "papel" in ct.columns else ct
    if municipio and "municipio" in sub.columns:
        sub = sub[sub["municipio"].apply(lambda m: nomes_equivalentes(municipio, m))]
    if regiao and "regiao_saude" in sub.columns:
        sub = sub[sub["regiao_saude"].astype(str) == str(regiao)]
    n_fone = int(sub.apply(_tem_fone, axis=1).sum()) if not sub.empty else 0
    n_email = int(sub.apply(_tem_email, axis=1).sum()) if not sub.empty else 0
    n_val = (
        int(sub["data_validacao"].apply(_validado_90d).sum())
        if not sub.empty and "data_validacao" in sub.columns
        else 0
    )
    return {
        "n_criticos": len(sub),
        "n_com_fone": n_fone,
        "n_com_email": n_email,
        "n_validados_90d": n_val,
        "n_cobranca": len(cob),
        "email_pronto_despacho": n_email,
    }


def exportar_cobranca_csv(df: pd.DataFrame | None = None) -> str:
    df = lista_cobranca_contatos() if df is None else df
    buf = io.StringIO()
    if df is None or df.empty:
        buf.write("municipio;papel;motivos\n")
        return buf.getvalue()
    df.to_csv(buf, sep=";", index=False, encoding="utf-8")
    return buf.getvalue()


def exportar_cobranca_md(df: pd.DataFrame | None = None) -> str:
    df = lista_cobranca_contatos() if df is None else df
    linhas = [
        "# Lista de cobrança — contatos críticos",
        "",
        f"Gerado em: {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Papéis: CIEVS, Vigilância, Defesa Civil municipal, Gestor de saúde.",
        "",
    ]
    if df is None or df.empty:
        linhas.append("Nenhuma lacuna nos papéis críticos do recorte.")
        return "\n".join(linhas) + "\n"
    linhas.append(f"Itens: **{len(df)}**")
    linhas.append("")
    for _, r in df.iterrows():
        linhas.append(
            f"- **{r.get('municipio')}** — {r.get('papel_rotulo') or r.get('papel')}: "
            f"{r.get('motivos')} "
            f"(tel: {r.get('telefone') or '—'}; e-mail: {r.get('email') or '—'})"
        )
    return "\n".join(linhas) + "\n"


def gravar_cobranca_tratados() -> Path:
    path = TRATADOS / "contatos_cobranca_criticos.csv"
    df = lista_cobranca_contatos()
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        path.write_text("municipio;papel;motivos\n", encoding="utf-8-sig")
    else:
        df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    md = TRATADOS / "contatos_cobranca_criticos.md"
    md.write_text(exportar_cobranca_md(df), encoding="utf-8")
    return path
