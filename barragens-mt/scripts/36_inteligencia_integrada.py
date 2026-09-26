"""Materializa a camada de inteligência v2.2 a partir do IDAP e seu histórico.

Não coleta fontes externas e não cria novo score. Consome exclusivamente produtos já
materializados pelo pipeline, preservando o IDAP como fonte única do nível operacional.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from vigibarragens.intelligence import build_intelligence_state  # noqa: E402

TRATADOS = RAIZ / "dados" / "tratados"
IDAP = TRATADOS / "idap_estadual_mt.csv"
HIST = TRATADOS / "historico_idap"
OUT_CSV = TRATADOS / "inteligencia_estadual_mt.csv"
OUT_JSON = TRATADOS / "inteligencia_estadual_resumo.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def previous_by_id() -> dict[str, dict[str, str]]:
    snapshots = sorted(HIST.glob("idap_*.csv"))
    if len(snapshots) < 2:
        return {}
    rows = read_rows(snapshots[-2])
    return {str(r.get("id_snisb") or "").strip(): r for r in rows if str(r.get("id_snisb") or "").strip()}


def main() -> None:
    if not IDAP.exists():
        raise SystemExit("idap_estadual_mt.csv ausente; execute a etapa 16 primeiro.")
    current = read_rows(IDAP)
    previous = previous_by_id()
    states = [build_intelligence_state(r, previous.get(str(r.get("id_snisb") or "").strip())) for r in current]
    fields = list(states[0].keys()) if states else []
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(states)

    levels = Counter(str(r.get("nivel_operacional") or "Sem nível") for r in states)
    trends = Counter(str(r.get("tendencia") or "sem_historico") for r in states)
    proxies = sum(bool(r.get("proxy_flags")) for r in states)
    summary = {
        "contrato": "vigibarragens-inteligencia-v2.2",
        "fonte_nivel": "IDAP + regras deterministicas de sobreposicao",
        "n_barragens": len(states),
        "por_nivel": dict(levels),
        "por_tendencia": dict(trends),
        "com_proxy": proxies,
        "observacao": "Esta camada nao recalcula nem substitui o nivel operacional.",
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Inteligencia v2.2: {len(states)} barragens")
    print(f"  {OUT_CSV.relative_to(RAIZ)}")
    print(f"  {OUT_JSON.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
