"""Materializa provenance/freshness semântico por barragem para a v2.2."""
from __future__ import annotations
import csv
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path: sys.path.insert(0, str(RAIZ))
from vigibarragens.intelligence.provenance import build_lineage_record  # noqa: E402

TRATADOS = RAIZ / "dados" / "tratados"
IDAP = TRATADOS / "idap_estadual_mt.csv"
HIDRO = TRATADOS / "hidro_barragens_mt.csv"
OUT = TRATADOS / "proveniencia_freshness_mt.csv"
SUMMARY = TRATADOS / "proveniencia_freshness_resumo.json"


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))


def main() -> None:
    idap = read(IDAP)
    if not idap: raise SystemExit("IDAP ausente; execute a etapa 16.")
    hydro = {str(r.get("id_snisb") or "").strip(): r for r in read(HIDRO)}
    rows = [build_lineage_record(r, hydro.get(str(r.get("id_snisb") or "").strip())) for r in idap]
    fields = list(rows[0]) if rows else []
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, delimiter=";"); w.writeheader(); w.writerows(rows)
    freshness_count=Counter(r["freshness_hidro"] for r in rows)
    lineage_count=Counter(r["lineage_status"] for r in rows)
    summary={
        "contrato":"vigibarragens-proveniencia-v2.2",
        "n_barragens":len(rows),
        "freshness_hidro":dict(freshness_count),
        "lineage":dict(lineage_count),
        "politica":"<=24h atual; >24-72h atencao; >72h vencido; sem data desconhecido",
        "nota":"Freshness e lineage qualificam a evidência; não alteram o nível IDAP.",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Proveniência/freshness v2.2: {len(rows)} barragens")

if __name__ == "__main__": main()
