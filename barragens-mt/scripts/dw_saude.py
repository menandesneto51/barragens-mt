"""Conector genérico ao DW / dumps institucionais de saúde (SES-MT).

Fontes (na ordem):
  1. CSV dump em `VIGIBARRAGENS_DW_CSV_DIR` ou `dados/brutos/`
  2. SQLite `VIGIBARRAGENS_DW_SQLITE`
  3. SQLAlchemy URL `VIGIBARRAGENS_DW_URL` (Postgres/SQL Server/etc., se o driver estiver instalado)

Catálogo: `dados/config/dw_catalogo.json` — IndicaSUS e slots para SIH/SIA/SISREG/SINAN.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import comum

CATALOGO = comum.RAIZ / "dados" / "config" / "dw_catalogo.json"


def carregar_catalogo() -> dict[str, Any]:
    if not CATALOGO.is_file():
        raise FileNotFoundError(f"catálogo DW ausente: {CATALOGO}")
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def extrato(nome: str) -> dict[str, Any]:
    cat = carregar_catalogo()
    bloco = (cat.get("extratos") or {}).get(nome)
    if not bloco:
        raise KeyError(f"extrato DW desconhecido: {nome}")
    return bloco


def _csv_dirs() -> list[Path]:
    """Diretórios de dump. Exemplos em `dados/brutos/exemplos/` NÃO entram automaticamente."""
    dirs: list[Path] = []
    env = os.environ.get("VIGIBARRAGENS_DW_CSV_DIR")
    if env:
        dirs.append(Path(env))
    dirs.append(comum.DADOS_BRUTOS)
    return dirs


def localizar_csv(nome_arquivo: str) -> Path | None:
    for base in _csv_dirs():
        cand = base / nome_arquivo
        if cand.is_file() and cand.stat().st_size > 0:
            return cand
    # também aceita caminho absoluto via env específico
    for chave in (
        "VIGIBARRAGENS_INDICASUS_CSV",
        "VIGIBARRAGENS_DW_CSV",
    ):
        raw = os.environ.get(chave)
        if raw and Path(raw).is_file():
            return Path(raw)
    return None


def ler_csv(caminho: Path) -> list[dict[str, Any]]:
    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
    # detecta ; ou ,
    amostra = texto[:2048]
    delim = ";" if amostra.count(";") >= amostra.count(",") else ","
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delim))


def _norm_key(s: str) -> str:
    return (
        str(s or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def aplicar_aliases(
    linhas: list[dict[str, Any]],
    aliases: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Renomeia colunas do dump/DW para o contrato canônico do extrato."""
    if not linhas:
        return []
    mapa: dict[str, str] = {}
    origem = {_norm_key(k): k for k in linhas[0].keys()}
    for canonico, candidatos in aliases.items():
        for cand in candidatos:
            hit = origem.get(_norm_key(cand))
            if hit:
                mapa[hit] = canonico
                break
    out: list[dict[str, Any]] = []
    for row in linhas:
        novo: dict[str, Any] = {}
        for k, v in row.items():
            dest = mapa.get(k, _norm_key(k))
            novo[dest] = v
        out.append(novo)
    return out


def ler_sqlite(caminho: Path, sql: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description or []]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def ler_sqlalchemy(url: str, sql: str) -> list[dict[str, Any]]:
    try:
        from sqlalchemy import create_engine, text  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "VIGIBARRAGENS_DW_URL definido, mas sqlalchemy não está instalado. "
            "pip install sqlalchemy pyodbc|psycopg[binary] conforme o banco."
        ) from exc
    eng = create_engine(url)
    with eng.connect() as con:
        res = con.execute(text(sql))
        cols = list(res.keys())
        return [dict(zip(cols, row)) for row in res.fetchall()]


def montar_sql(cfg: dict[str, Any]) -> str:
    schema = os.environ.get(cfg.get("schema_env") or "", "") or cfg.get(
        "schema_default", "dbo"
    )
    tabela = os.environ.get(cfg.get("tabela_env") or "", "") or cfg.get(
        "tabela_default", "indicasus_leitos"
    )
    tpl = cfg.get("sql") or "SELECT * FROM {schema}.{tabela}"
    return tpl.format(schema=schema, tabela=tabela)


def extrair(nome: str) -> tuple[list[dict[str, Any]], str]:
    """
    Extrai linhas brutas + rótulo da fonte usada.

    Retorna ([], motivo) se nenhuma fonte estiver disponível.
    """
    cfg = extrato(nome)
    aliases = cfg.get("aliases") or {}

    csv_name = cfg.get("csv_dump") or f"{nome}.csv"
    caminho_csv = localizar_csv(csv_name)
    if caminho_csv is not None:
        rows = aplicar_aliases(ler_csv(caminho_csv), aliases)
        return rows, f"csv:{caminho_csv}"

    sqlite_path = os.environ.get("VIGIBARRAGENS_DW_SQLITE")
    if sqlite_path and Path(sqlite_path).is_file():
        sql = montar_sql(cfg)
        # SQLite ignora schema — usa só o nome da tabela
        tabela = os.environ.get(cfg.get("tabela_env") or "", "") or cfg.get(
            "tabela_default", nome
        )
        sql_lite = f"SELECT * FROM {tabela}"
        rows = aplicar_aliases(ler_sqlite(Path(sqlite_path), sql_lite), aliases)
        return rows, f"sqlite:{sqlite_path}:{tabela}"

    url = os.environ.get("VIGIBARRAGENS_DW_URL")
    if url:
        sql = montar_sql(cfg)
        rows = aplicar_aliases(ler_sqlalchemy(url, sql), aliases)
        return rows, f"dw_url:{sql}"

    return [], "nenhuma fonte (CSV/SQLite/DW_URL)"


def listar_extratos() -> list[str]:
    cat = carregar_catalogo()
    return sorted((cat.get("extratos") or {}).keys())
