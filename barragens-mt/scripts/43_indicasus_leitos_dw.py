"""IndicaSUS / DW — leitos e ocupação operacional (D6 / SAU-07).

Consome extrato institucional (não inventa ocupação). Fontes:
  - CSV dump (`dados/brutos/indicasus_leitos.csv` ou `VIGIBARRAGENS_INDICASUS_CSV`)
  - SQLite `VIGIBARRAGENS_DW_SQLITE`
  - SQLAlchemy `VIGIBARRAGENS_DW_URL` + tabela (`VIGIBARRAGENS_INDICASUS_TABELA`)

Saídas:
  dados/tratados/indicasus_leitos_mt.csv
  dados/tratados/indicasus_leitos_municipio.csv
  dados/tratados/indicasus_leitos_status.json
  relatorios/indicasus_leitos_dw.md

Uso:
  python scripts/43_indicasus_leitos_dw.py
  python executar.py 43
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum
import dw_saude

SAIDA = comum.DADOS_TRATADOS / "indicasus_leitos_mt.csv"
SAIDA_MUN = comum.DADOS_TRATADOS / "indicasus_leitos_municipio.csv"
STATUS = comum.DADOS_TRATADOS / "indicasus_leitos_status.json"
REL = comum.RELATORIOS / "indicasus_leitos_dw.md"

CAMPOS = [
    "codigo_cnes",
    "nome_estabelecimento",
    "codigo_municipio_ibge",
    "municipio",
    "tipo_leito",
    "leitos_cadastrados",
    "leitos_operacionais",
    "leitos_ocupados",
    "leitos_disponiveis",
    "taxa_ocupacao",
    "atualizado_em",
    "fonte",
    "banco_dw",
]

CAMPOS_MUN = [
    "codigo_municipio_ibge",
    "municipio",
    "leitos_operacionais",
    "leitos_ocupados",
    "leitos_disponiveis",
    "taxa_ocupacao",
    "n_estabelecimentos",
    "fonte",
]


def _digitos(valor: Any, n: int | None = None) -> str:
    texto = str(valor or "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    d = re.sub(r"\D", "", texto)
    if n and len(d) >= n:
        return d[:n]
    return d


def _num(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("%", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _int(valor: Any) -> int | None:
    n = _num(valor)
    if n is None:
        return None
    return int(round(n))


def normalizar(rows: list[dict[str, Any]], fonte: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        cnes = _digitos(r.get("codigo_cnes"), 7)
        if not cnes:
            continue
        op = _int(r.get("leitos_operacionais"))
        oc = _int(r.get("leitos_ocupados"))
        disp = _int(r.get("leitos_disponiveis"))
        cad = _int(r.get("leitos_cadastrados"))
        if disp is None and op is not None and oc is not None:
            disp = max(0, op - oc)
        if op is None and disp is not None and oc is not None:
            op = disp + oc
        taxa = _num(r.get("taxa_ocupacao"))
        if taxa is not None and taxa <= 1.5:
            taxa = taxa * 100.0  # aceita fração 0–1
        if taxa is None and op and op > 0 and oc is not None:
            taxa = 100.0 * oc / op
        ibge = _digitos(r.get("codigo_municipio_ibge"), 7)
        tipo = (str(r.get("tipo_leito") or "total").strip() or "total").lower()
        out.append(
            {
                "codigo_cnes": cnes,
                "nome_estabelecimento": str(r.get("nome_estabelecimento") or "")[:120],
                "codigo_municipio_ibge": ibge,
                "municipio": str(r.get("municipio") or "")[:80],
                "tipo_leito": tipo,
                "leitos_cadastrados": "" if cad is None else str(cad),
                "leitos_operacionais": "" if op is None else str(op),
                "leitos_ocupados": "" if oc is None else str(oc),
                "leitos_disponiveis": "" if disp is None else str(disp),
                "taxa_ocupacao": "" if taxa is None else f"{taxa:.1f}",
                "atualizado_em": str(r.get("atualizado_em") or ""),
                "fonte": "IndicaSUS/DW",
                "banco_dw": fonte,
            }
        )
    return out


def agregar_municipio(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Prefere linhas tipo_leito=total; senão soma tipos.
    por_cnes: dict[str, dict[str, Any]] = {}
    for r in rows:
        cnes = r["codigo_cnes"]
        tipo = r.get("tipo_leito") or "total"
        if cnes in por_cnes and por_cnes[cnes].get("tipo_leito") == "total":
            continue
        if tipo == "total" or cnes not in por_cnes:
            por_cnes[cnes] = r
        elif por_cnes[cnes].get("tipo_leito") != "total":
            # soma tipos distintos
            a = por_cnes[cnes]
            for k in (
                "leitos_operacionais",
                "leitos_ocupados",
                "leitos_disponiveis",
                "leitos_cadastrados",
            ):
                va = _int(a.get(k)) or 0
                vb = _int(r.get(k)) or 0
                a[k] = str(va + vb)
            a["tipo_leito"] = "soma_tipos"

    acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "municipio": "",
            "op": 0,
            "oc": 0,
            "disp": 0,
            "n": 0,
        }
    )
    for r in por_cnes.values():
        ibge = r.get("codigo_municipio_ibge") or "0000000"
        slot = acc[ibge]
        slot["municipio"] = r.get("municipio") or slot["municipio"]
        slot["op"] += _int(r.get("leitos_operacionais")) or 0
        slot["oc"] += _int(r.get("leitos_ocupados")) or 0
        slot["disp"] += _int(r.get("leitos_disponiveis")) or 0
        slot["n"] += 1

    saida: list[dict[str, Any]] = []
    for ibge, s in sorted(acc.items()):
        taxa = (100.0 * s["oc"] / s["op"]) if s["op"] else None
        saida.append(
            {
                "codigo_municipio_ibge": ibge,
                "municipio": s["municipio"],
                "leitos_operacionais": str(s["op"]),
                "leitos_ocupados": str(s["oc"]),
                "leitos_disponiveis": str(s["disp"]),
                "taxa_ocupacao": "" if taxa is None else f"{taxa:.1f}",
                "n_estabelecimentos": str(s["n"]),
                "fonte": "IndicaSUS/DW",
            }
        )
    return saida


def gravar_status(payload: dict[str, Any]) -> None:
    payload = {
        **payload,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "catalogo": "indicasus_leitos",
    }
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    comum.preparar_diretorios()
    print("Extraindo IndicaSUS leitos/ocupação (DW)…", flush=True)
    rows_raw, fonte = dw_saude.extrair("indicasus_leitos")
    if not rows_raw:
        comum.salvar_csv(SAIDA, [], CAMPOS)
        comum.salvar_csv(SAIDA_MUN, [], CAMPOS_MUN)
        gravar_status(
            {
                "ok": False,
                "motivo": fonte,
                "n_linhas": 0,
                "orientacao": (
                    "Disponibilize dump CSV em dados/brutos/indicasus_leitos.csv, "
                    "ou defina VIGIBARRAGENS_INDICASUS_CSV / VIGIBARRAGENS_DW_SQLITE / "
                    "VIGIBARRAGENS_DW_URL. Ver docs/15-integracao-indicasus-dw.md."
                ),
            }
        )
        REL.write_text(
            "\n".join(
                [
                    "# IndicaSUS — leitos e ocupação",
                    "",
                    f"- Status: **aguardando fonte** (`{fonte}`)",
                    "- Contrato e variáveis: `docs/15-integracao-indicasus-dw.md`",
                    "- Catálogo DW: `dados/config/dw_catalogo.json`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"  sem fonte — status em {STATUS.relative_to(comum.RAIZ)}")
        return

    rows = normalizar(rows_raw, fonte)
    mun = agregar_municipio(rows)
    comum.salvar_csv(SAIDA, rows, CAMPOS)
    comum.salvar_csv(SAIDA_MUN, mun, CAMPOS_MUN)
    op = sum(_int(r.get("leitos_operacionais")) or 0 for r in mun)
    disp = sum(_int(r.get("leitos_disponiveis")) or 0 for r in mun)
    gravar_status(
        {
            "ok": True,
            "fonte": fonte,
            "n_linhas": len(rows),
            "n_municipios": len(mun),
            "leitos_operacionais": op,
            "leitos_disponiveis": disp,
        }
    )
    REL.write_text(
        "\n".join(
            [
                "# IndicaSUS — leitos e ocupação",
                "",
                f"- Fonte: `{fonte}`",
                f"- Linhas (CNES × tipo): **{len(rows)}**",
                f"- Municípios: **{len(mun)}**",
                f"- Leitos operacionais (agg): **{op}**",
                f"- Leitos disponíveis (agg): **{disp}**",
                f"- Arquivos: `{SAIDA.relative_to(comum.RAIZ)}`, `{SAIDA_MUN.relative_to(comum.RAIZ)}`",
                "",
                "Alimenta D6 (razão leitos/demanda) e o painel de capacidade na Simulação.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  {len(rows)} linhas · {len(mun)} municípios · fonte={fonte}")
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
