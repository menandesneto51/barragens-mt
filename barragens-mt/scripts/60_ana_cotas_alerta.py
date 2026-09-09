"""Aplica cotas de alerta ANA (CSV oficial ou sample) ao seed/telemetria.

Ordem de leitura:
  1. dados/brutos/ana_cotas_alerta_mt.csv   (oficial, quando existir)
  2. dados/tratados/ana_cotas_alerta_mt_sample.csv  (demonstração)

Saídas:
  dados/tratados/ana_cotas_alerta_mt.csv       — cópia normalizada usada pelo 53
  dados/tratados/ana_cotas_alerta_status.json  — A8 (sample vs oficial)
  relatorios/ana_cotas_alerta.md

Se `sis_cloud_seed.db` tiver `ana_telemetria`, atualiza `cota_alerta_cm`.
A etapa 53 (logo após no ETL padrão) calcula A6 `cota_medida`.

Uso:
  python scripts/60_ana_cotas_alerta.py
  python executar.py 60
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum

BRUTO = comum.DADOS_BRUTOS / "ana_cotas_alerta_mt.csv"
SAMPLE = comum.DADOS_TRATADOS / "ana_cotas_alerta_mt_sample.csv"
SAIDA_CSV = comum.DADOS_TRATADOS / "ana_cotas_alerta_mt.csv"
STATUS = comum.DADOS_TRATADOS / "ana_cotas_alerta_status.json"
REL = comum.RELATORIOS / "ana_cotas_alerta.md"
SEED = comum.DADOS_BRUTOS / "sisclima" / "sis_cloud_seed.db"

CAMPOS = ["codigo_estacao", "cota_alerta_cm", "fonte", "nota"]


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _ler_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(2048)
        f.seek(0)
        delim = ";" if amostra.count(";") >= amostra.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def carregar_cotas() -> tuple[list[dict[str, Any]], str, Path]:
    for path, rotulo in ((BRUTO, "oficial_brutos"), (SAMPLE, "sample_tratados")):
        rows_in = _ler_csv(path)
        out: list[dict[str, Any]] = []
        for d in rows_in:
            cod = str(d.get("codigo_estacao") or d.get("codigo") or "").strip()
            cota = _num(d.get("cota_alerta_cm") or d.get("cota_alerta"))
            if not cod or cota is None or cota <= 0:
                continue
            fonte = str(d.get("fonte") or ("oficial" if rotulo.startswith("oficial") else "ANA_SAMPLE"))
            out.append(
                {
                    "codigo_estacao": cod,
                    "cota_alerta_cm": f"{cota:.1f}".replace(".", ","),
                    "fonte": fonte,
                    "nota": str(d.get("nota") or ""),
                }
            )
        if out:
            return out, rotulo, path
    return [], "indisponivel", Path()


def aplicar_no_seed(cotas: dict[str, float]) -> int:
    if not SEED.is_file() or not cotas:
        return 0
    con = sqlite3.connect(str(SEED))
    try:
        nomes = {
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "ana_telemetria" not in nomes:
            return 0
        n = 0
        for cod, alerta in cotas.items():
            cur = con.execute(
                "UPDATE ana_telemetria SET cota_alerta_cm = ? WHERE codigo_estacao = ?",
                (alerta, cod),
            )
            n += cur.rowcount
        con.commit()
        return n
    finally:
        con.close()


def main() -> None:
    comum.preparar_diretorios()
    linhas, origem, path = carregar_cotas()
    if not linhas:
        status = {
            "ok": False,
            "origem": origem,
            "n_estacoes": 0,
            "eh_sample": True,
            "mensagem": "nenhuma cota de alerta encontrada — rode com sample ou CSV oficial",
            "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        REL.write_text(
            "# Cotas de alerta ANA\n\nNenhuma cota disponível.\n",
            encoding="utf-8",
        )
        print("  cotas alerta: nenhuma fonte")
        return

    comum.salvar_csv(SAIDA_CSV, linhas, CAMPOS)
    mapa = {
        r["codigo_estacao"]: float(str(r["cota_alerta_cm"]).replace(",", "."))
        for r in linhas
    }
    n_seed = aplicar_no_seed(mapa)
    fontes = {r["fonte"] for r in linhas}
    eh_sample = any("sample" in f.casefold() or f.upper() == "ANA_SAMPLE" for f in fontes)
    if origem.startswith("sample"):
        eh_sample = True

    status = {
        "ok": True,
        "origem": origem,
        "path": str(path) if path else None,
        "n_estacoes": len(linhas),
        "n_linhas_seed_atualizadas": n_seed,
        "eh_sample": eh_sample,
        "fontes": sorted(fontes),
        "mensagem": (
            "cotas de demonstração (ANA_SAMPLE) — substituir por CSV oficial em "
            "dados/brutos/ana_cotas_alerta_mt.csv"
            if eh_sample
            else "cotas oficiais aplicadas a partir de dados/brutos/"
        ),
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REL.write_text(
        "\n".join(
            [
                "# Cotas de alerta ANA",
                "",
                f"- Origem: `{origem}` (`{path.name if path else '—'}`)",
                f"- Estações: **{len(linhas)}**",
                f"- Sample/demonstração: **{eh_sample}**",
                f"- Linhas atualizadas no seed: **{n_seed}**",
                "",
                status["mensagem"],
                "",
                "A etapa 53 consome estas cotas para `a6_fonte=cota_medida`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"  cotas alerta: {len(linhas)} estações ({origem}); "
        f"sample={eh_sample}; seed_upd={n_seed}"
    )


if __name__ == "__main__":
    main()
