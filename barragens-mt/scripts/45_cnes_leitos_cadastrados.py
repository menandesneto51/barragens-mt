"""CNES LT — leitos cadastrados (SAU-01), fallback quando IndicaSUS não cobre.

Fontes (ordem):
  1. CSV dump `dados/brutos/cnes_leitos_lt_mt.csv` (ou VIGIBARRAGENS_CNES_LT_CSV)
  2. Extrato catálogo `cnes_leitos_cadastrados` via dw_saude (CSV/SQLite/DW)
  3. Arquivo .dbc local LTMT*.dbc se `pysus` estiver instalado

FTP DATASUS costuma falhar neste ambiente; o caminho operacional é dump/DW.

Saídas:
  dados/tratados/cnes_leitos_cadastrados_mt.csv
  dados/tratados/cnes_leitos_cadastrados_municipio.csv
  dados/tratados/cnes_leitos_cadastrados_status.json
  relatorios/cnes_leitos_cadastrados.md

Uso:
  python scripts/45_cnes_leitos_cadastrados.py
  python executar.py 45
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum
import dw_saude

SAIDA = comum.DADOS_TRATADOS / "cnes_leitos_cadastrados_mt.csv"
SAIDA_MUN = comum.DADOS_TRATADOS / "cnes_leitos_cadastrados_municipio.csv"
STATUS = comum.DADOS_TRATADOS / "cnes_leitos_cadastrados_status.json"
REL = comum.RELATORIOS / "cnes_leitos_cadastrados.md"

CAMPOS = [
    "codigo_cnes",
    "codigo_municipio_ibge",
    "tipo_leito",
    "leitos_cadastrados",
    "leitos_sus",
    "competencia",
    "fonte",
    "banco_dw",
]
CAMPOS_MUN = [
    "codigo_municipio_ibge",
    "leitos_cadastrados",
    "leitos_sus",
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


def _int(valor: Any) -> int | None:
    if valor is None or valor == "":
        return None
    try:
        return int(round(float(str(valor).replace(",", "."))))
    except ValueError:
        return None


def _ler_dbc_local() -> tuple[list[dict[str, Any]], str] | None:
    env = os.environ.get("VIGIBARRAGENS_CNES_LT_DBC")
    candidatos: list[Path] = []
    if env:
        candidatos.append(Path(env))
    candidatos.extend(sorted(comum.DADOS_BRUTOS.glob("LTMT*.dbc")))
    candidatos.extend(sorted(comum.DADOS_BRUTOS.glob("**/LTMT*.dbc")))
    path = next((p for p in candidatos if p.is_file()), None)
    if path is None:
        return None
    try:
        from pysus import FTP_DATASUS  # noqa: F401
    except ImportError:
        pass
    try:
        import pandas as pd
        from pysus.utilities.readdbc import read_dbc  # type: ignore
    except Exception:
        return None
    try:
        df = read_dbc(str(path))
    except Exception as exc:  # noqa: BLE001
        print(f"  falha ao ler DBC {path.name}: {exc}")
        return None
    if hasattr(df, "to_dict"):
        rows = df.to_dict(orient="records")
    else:
        rows = [dict(r) for r in df]
    return rows, f"dbc:{path}"


def coletar() -> tuple[list[dict[str, Any]], str]:
    env_csv = os.environ.get("VIGIBARRAGENS_CNES_LT_CSV")
    if env_csv and Path(env_csv).is_file():
        rows = dw_saude.aplicar_aliases(
            dw_saude.ler_csv(Path(env_csv)),
            dw_saude.extrato("cnes_leitos_cadastrados").get("aliases") or {},
        )
        return rows, f"csv:{env_csv}"

    rows, fonte = dw_saude.extrair("cnes_leitos_cadastrados")
    if rows:
        return rows, fonte

    dbc = _ler_dbc_local()
    if dbc:
        raw, fonte = dbc
        rows = dw_saude.aplicar_aliases(
            raw,
            dw_saude.extrato("cnes_leitos_cadastrados").get("aliases") or {},
        )
        return rows, fonte
    return [], "nenhuma fonte (CSV LT / DW / DBC local)"


def normalizar(rows: list[dict[str, Any]], fonte: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        cnes = _digitos(r.get("codigo_cnes"), 7)
        if not cnes:
            continue
        cad = _int(r.get("leitos_cadastrados"))
        if cad is None:
            continue
        sus = _int(r.get("leitos_sus"))
        ibge = _digitos(r.get("codigo_municipio_ibge"), 7)
        if len(ibge) == 6:
            ibge = ibge  # IBGE6 do LT — ok
        out.append(
            {
                "codigo_cnes": cnes,
                "codigo_municipio_ibge": ibge,
                "tipo_leito": str(r.get("tipo_leito") or "total").strip() or "total",
                "leitos_cadastrados": str(cad),
                "leitos_sus": "" if sus is None else str(sus),
                "competencia": str(r.get("competencia") or ""),
                "fonte": "CNES LT (cadastrado)",
                "banco_dw": fonte,
            }
        )
    return out


def agregar_cnes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Soma tipos de leito por CNES → uma linha `total`."""
    acc: dict[str, dict[str, Any]] = {}
    for r in rows:
        cnes = r["codigo_cnes"]
        slot = acc.setdefault(
            cnes,
            {
                "codigo_cnes": cnes,
                "codigo_municipio_ibge": r.get("codigo_municipio_ibge") or "",
                "tipo_leito": "total",
                "leitos_cadastrados": 0,
                "leitos_sus": 0,
                "competencia": r.get("competencia") or "",
                "fonte": r.get("fonte") or "",
                "banco_dw": r.get("banco_dw") or "",
            },
        )
        slot["leitos_cadastrados"] += _int(r.get("leitos_cadastrados")) or 0
        slot["leitos_sus"] += _int(r.get("leitos_sus")) or 0
        if not slot["codigo_municipio_ibge"]:
            slot["codigo_municipio_ibge"] = r.get("codigo_municipio_ibge") or ""
    out = []
    for s in acc.values():
        out.append(
            {
                **s,
                "leitos_cadastrados": str(s["leitos_cadastrados"]),
                "leitos_sus": str(s["leitos_sus"]),
            }
        )
    return sorted(out, key=lambda x: x["codigo_cnes"])


def agregar_municipio(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"cad": 0, "sus": 0, "cnes": set()}
    )
    for r in rows:
        ibge = r.get("codigo_municipio_ibge") or "000000"
        slot = acc[ibge]
        slot["cad"] += _int(r.get("leitos_cadastrados")) or 0
        slot["sus"] += _int(r.get("leitos_sus")) or 0
        slot["cnes"].add(r["codigo_cnes"])
    return [
        {
            "codigo_municipio_ibge": ibge,
            "leitos_cadastrados": str(s["cad"]),
            "leitos_sus": str(s["sus"]),
            "n_estabelecimentos": str(len(s["cnes"])),
            "fonte": "CNES LT (cadastrado)",
        }
        for ibge, s in sorted(acc.items())
    ]


def main() -> None:
    comum.preparar_diretorios()
    print("CNES LT — leitos cadastrados (SAU-01)…", flush=True)
    raw, fonte = coletar()
    if not raw:
        comum.salvar_csv(SAIDA, [], CAMPOS)
        comum.salvar_csv(SAIDA_MUN, [], CAMPOS_MUN)
        payload = {
            "ok": False,
            "motivo": fonte,
            "n_linhas": 0,
            "orientacao": (
                "Exporte LT MT (DATASUS) para CSV em dados/brutos/cnes_leitos_lt_mt.csv "
                "ou defina VIGIBARRAGENS_CNES_LT_CSV. Layout em "
                "dados/config/exemplos/cnes_leitos_lt_mt.exemplo.csv. "
                "FTP DATASUS costuma falhar aqui; IndicaSUS (43) cobre ocupação."
            ),
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        }
        STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        REL.write_text(
            "\n".join(
                [
                    "# CNES LT — leitos cadastrados",
                    "",
                    f"- Status: **aguardando fonte** (`{fonte}`)",
                    "- Ver `docs/15-integracao-indicasus-dw.md` §15.7",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"  sem fonte — {STATUS.relative_to(comum.RAIZ)}")
        return

    detalhe = normalizar(raw, fonte)
    por_cnes = agregar_cnes(detalhe)
    mun = agregar_municipio(por_cnes)
    comum.salvar_csv(SAIDA, por_cnes, CAMPOS)
    comum.salvar_csv(SAIDA_MUN, mun, CAMPOS_MUN)
    total = sum(_int(r.get("leitos_cadastrados")) or 0 for r in por_cnes)
    STATUS.write_text(
        json.dumps(
            {
                "ok": True,
                "fonte": fonte,
                "n_estabelecimentos": len(por_cnes),
                "n_municipios": len(mun),
                "leitos_cadastrados": total,
                "gerado_em": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    REL.write_text(
        "\n".join(
            [
                "# CNES LT — leitos cadastrados",
                "",
                f"- Fonte: `{fonte}`",
                f"- Estabelecimentos: **{len(por_cnes)}**",
                f"- Municípios: **{len(mun)}**",
                f"- Leitos cadastrados: **{total}**",
                "",
                "SAU-01 — capacidade cadastrada. Ocupação operacional: IndicaSUS (43).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  {len(por_cnes)} CNES · {total} leitos cadastrados · {fonte}")


if __name__ == "__main__":
    main()
