"""Fontes ANA via SisClima (SQLite) ou CSV de fallback — sem reimplementar a API.

Ordem de resolução:
  1. VIGIBARRAGENS_SISCLIMA_DB / candidatos locais (tabelas ana_estacoes, ana_telemetria)
  2. ANA_ESTACOES_CSV / ANA_TELEMETRIA_CSV (env)
  3. CSVs em dados/brutos/ (amostra SisClima)
  4. Clone irmão ../sisclima-repo/data/sample/
"""

from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import comum

CANDIDATOS_DB = [
    Path(os.environ["VIGIBARRAGENS_SISCLIMA_DB"])
    if os.environ.get("VIGIBARRAGENS_SISCLIMA_DB")
    else None,
    comum.RAIZ.parent / "sisclima-repo" / "data" / "cloud" / "sis_cloud_seed.db",
    comum.RAIZ.parent / "sisclima-repo" / "data" / "output" / "sis_integrado.db",
    Path(
        r"C:\Users\Menandesneto\OneDrive\CIEVS MT"
        r"\SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO\data\cloud\sis_cloud_seed.db"
    ),
]


def resolver_db() -> Path | None:
    for caminho in CANDIDATOS_DB:
        if caminho is not None and caminho.exists() and caminho.stat().st_size > 0:
            return caminho
    return None


def _ler_csv_qualquer(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(4096)
        f.seek(0)
        delim = ";" if amostra.count(";") > amostra.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def candidatos_estacoes_csv() -> list[Path]:
    env = os.environ.get("ANA_ESTACOES_CSV")
    out: list[Path] = []
    if env:
        out.append(Path(env))
    out.extend(
        [
            comum.DADOS_TRATADOS / "ana_estacoes_mt_sample.csv",
            comum.DADOS_BRUTOS / "ana_estacoes_mt.csv",
            comum.RAIZ.parent
            / "sisclima-repo"
            / "data"
            / "sample"
            / "ana_estacoes_mt.csv",
        ]
    )
    return out


def candidatos_telemetria_csv() -> list[Path]:
    env = os.environ.get("ANA_TELEMETRIA_CSV")
    out: list[Path] = []
    if env:
        out.append(Path(env))
    out.extend(
        [
            comum.DADOS_TRATADOS / "ana_telemetria_sample.csv",
            comum.DADOS_BRUTOS / "ana_telemetria.csv",
            comum.RAIZ.parent / "sisclima-repo" / "data" / "sample" / "ana_telemetria.csv",
        ]
    )
    return out


def candidatos_cotas_alerta_csv() -> list[Path]:
    env = os.environ.get("ANA_COTAS_ALERTA_CSV")
    out: list[Path] = []
    if env:
        out.append(Path(env))
    out.append(comum.DADOS_TRATADOS / "ana_cotas_alerta_mt_sample.csv")
    out.append(comum.DADOS_BRUTOS / "ana_cotas_alerta_mt.csv")
    return out


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _tabelas(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def carregar_estacoes() -> tuple[list[dict[str, Any]], str]:
    """Retorna (estações, fonte_descricao)."""
    db = resolver_db()
    if db is not None:
        con = sqlite3.connect(str(db))
        try:
            nomes = _tabelas(con)
            if "ana_estacoes" in nomes:
                cols = {r[1] for r in con.execute("PRAGMA table_info(ana_estacoes)")}
                if {"lat", "lon"} <= cols or {"latitude", "longitude"} <= cols:
                    lat_c = "lat" if "lat" in cols else "latitude"
                    lon_c = "lon" if "lon" in cols else "longitude"
                    cod = "codigo_estacao" if "codigo_estacao" in cols else "codigo"
                    rows = []
                    for r in con.execute(f"SELECT * FROM ana_estacoes"):
                        d = dict(zip([c[1] for c in con.execute("PRAGMA table_info(ana_estacoes)")], r))
                        la, lo = _num(d.get(lat_c)), _num(d.get(lon_c))
                        if la is None or lo is None:
                            continue
                        rows.append(
                            {
                                "codigo_estacao": str(d.get(cod) or "").strip(),
                                "nome_estacao": str(d.get("nome_estacao") or d.get("nome") or ""),
                                "municipio": str(d.get("municipio") or ""),
                                "uf": str(d.get("uf") or "MT"),
                                "cod_ibge": str(d.get("cod_ibge") or ""),
                                "lat": la,
                                "lon": lo,
                                "nome_rio": str(d.get("nome_rio") or d.get("rio") or ""),
                                "fonte": str(d.get("fonte") or "sisclima_sqlite"),
                            }
                        )
                    if rows:
                        return rows, f"sqlite:{db.name}:ana_estacoes"
        finally:
            con.close()

    for path in candidatos_estacoes_csv():
        brutos = _ler_csv_qualquer(path)
        rows = []
        for d in brutos:
            la, lo = _num(d.get("lat") or d.get("latitude")), _num(
                d.get("lon") or d.get("longitude")
            )
            if la is None or lo is None:
                continue
            rows.append(
                {
                    "codigo_estacao": str(d.get("codigo_estacao") or d.get("codigo") or "").strip(),
                    "nome_estacao": str(d.get("nome_estacao") or d.get("nome") or ""),
                    "municipio": str(d.get("municipio") or ""),
                    "uf": str(d.get("uf") or "MT"),
                    "cod_ibge": str(d.get("cod_ibge") or ""),
                    "lat": la,
                    "lon": lo,
                    "nome_rio": str(d.get("nome_rio") or ""),
                    "fonte": str(d.get("fonte") or path.name),
                }
            )
        if rows:
            return rows, f"csv:{path}"
    return [], "indisponivel"


def carregar_telemetria() -> tuple[list[dict[str, Any]], str]:
    db = resolver_db()
    if db is not None:
        con = sqlite3.connect(str(db))
        try:
            if "ana_telemetria" in _tabelas(con):
                cols = [r[1] for r in con.execute("PRAGMA table_info(ana_telemetria)")]
                rows_db = []
                for r in con.execute("SELECT * FROM ana_telemetria"):
                    d = dict(zip(cols, r))
                    rows_db.append(
                        {
                            "data": str(d.get("data") or "")[:10],
                            "data_hora": str(d.get("data_hora") or d.get("data") or ""),
                            "codigo_estacao": str(d.get("codigo_estacao") or "").strip(),
                            "municipio": str(d.get("municipio") or ""),
                            "cod_ibge": str(d.get("cod_ibge") or ""),
                            "chuva_mm": _num(d.get("chuva_mm")),
                            "cota_cm": _num(d.get("cota_cm")),
                            "vazao_m3s": _num(d.get("vazao_m3s")),
                            "cota_alerta_cm": _num(d.get("cota_alerta_cm")),
                            "fonte": str(d.get("fonte") or "sisclima_sqlite"),
                        }
                    )
                if rows_db:
                    return rows_db, f"sqlite:{db.name}:ana_telemetria"
        finally:
            con.close()

    for path in candidatos_telemetria_csv():
        brutos = _ler_csv_qualquer(path)
        rows = []
        for d in brutos:
            rows.append(
                {
                    "data": str(d.get("data") or "")[:10],
                    "data_hora": str(d.get("data_hora") or d.get("data") or ""),
                    "codigo_estacao": str(d.get("codigo_estacao") or "").strip(),
                    "municipio": str(d.get("municipio") or ""),
                    "cod_ibge": str(d.get("cod_ibge") or ""),
                    "chuva_mm": _num(d.get("chuva_mm")),
                    "cota_cm": _num(d.get("cota_cm")),
                    "vazao_m3s": _num(d.get("vazao_m3s")),
                    "cota_alerta_cm": _num(d.get("cota_alerta_cm")),
                    "fonte": str(d.get("fonte") or path.name),
                }
            )
        if rows:
            return rows, f"csv:{path}"
    return [], "indisponivel"


def carregar_cotas_alerta() -> dict[str, float]:
    out: dict[str, float] = {}
    for path in candidatos_cotas_alerta_csv():
        for d in _ler_csv_qualquer(path):
            cod = str(d.get("codigo_estacao") or "").strip()
            cota = _num(d.get("cota_alerta_cm"))
            if cod and cota is not None and cota > 0:
                out[cod] = cota
        if out:
            break
    return out


def ultima_leitura_por_estacao(
    telemetria: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Última observação por código (preferindo data_hora)."""
    best: dict[str, dict[str, Any]] = {}
    for row in telemetria:
        cod = row.get("codigo_estacao") or ""
        if not cod:
            continue
        chave = str(row.get("data_hora") or row.get("data") or "")
        prev = best.get(cod)
        if prev is None or chave >= str(prev.get("data_hora") or prev.get("data") or ""):
            best[cod] = row
    return best


def cobertura_dias(
    telemetria: list[dict[str, Any]], dias: int
) -> dict[str, int]:
    """Contagem de registros com cota ou vazão nos últimos N dias (relativo à data máx.)."""
    datas = []
    for row in telemetria:
        d = str(row.get("data") or "")[:10]
        if len(d) == 10:
            try:
                datas.append(datetime.strptime(d, "%Y-%m-%d").date())
            except ValueError:
                pass
    if not datas:
        return {}
    fim = max(datas)
    ini = fim - timedelta(days=dias)
    cont: dict[str, int] = {}
    for row in telemetria:
        d = str(row.get("data") or "")[:10]
        try:
            dia = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            continue
        if dia < ini or dia > fim:
            continue
        if row.get("cota_cm") is None and row.get("vazao_m3s") is None:
            continue
        cod = str(row.get("codigo_estacao") or "")
        if cod:
            cont[cod] = cont.get(cod, 0) + 1
    return cont
