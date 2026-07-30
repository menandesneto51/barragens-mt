"""Sonda o SQLite do SIS Clima / TITAN e lista tabelas uteis ao IDAP."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DBS = [
    Path(
        r"C:\Users\Menandesneto\OneDrive\CIEVS MT"
        r"\SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO\data\output\sis_integrado.db"
    ),
    Path(
        r"C:\Users\Menandesneto\OneDrive\CIEVS MT"
        r"\SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO\data\cloud\sis_cloud_seed.db"
    ),
]

ALVO = [
    "met_biometeo",
    "ana_risco_municipal",
    "hidro_risco_municipal",
    "solo_saturacao_municipal",
    "cemaden_alertas",
    "inmet_alertas",
    "alerta_integrado_sis_titan",
    "resumo_municipal",
]


def main() -> None:
    for db in DBS:
        if not db.exists():
            print(f"ausente: {db}")
            continue
        print(f"==== {db.name} size={db.stat().st_size}")
        con = sqlite3.connect(db)
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
            )
        ]
        print(f"tables ({len(tables)}): {tables}")
        for t in ALVO:
            if t not in tables:
                continue
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: n={n} cols={cols}")
            if n:
                row = con.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
                print("   sample:", dict(zip(cols, row)))
        if "met_biometeo" in tables:
            print(
                "  met range:",
                con.execute(
                    "SELECT min(data), max(data), count(DISTINCT data), "
                    "count(DISTINCT cod_ibge) FROM met_biometeo"
                ).fetchone(),
            )
            print(
                "  met por data:",
                con.execute(
                    "SELECT data, COUNT(*) AS n FROM met_biometeo "
                    "GROUP BY data ORDER BY data DESC LIMIT 8"
                ).fetchall(),
            )
        con.close()


if __name__ == "__main__":
    main()
