"""Valida a integridade do log append-only de sinais operacionais.

Falha o pipeline quando encontra:
- JSON inválido;
- event_id duplicado;
- vocabulário inválido;
- campos obrigatórios ausentes;
- SHA-256 divergente do conteúdo canônico;
- evento para barragem inexistente no inventário.

Saída:
  dados/tratados/sinais_operacionais_auditoria.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import comum

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vigibarragens.intelligence.operational_signal_registry import (  # noqa: E402
    validate_event_log,
    validate_governance_chain,
    validate_ledger_chain,
)

EVENTS = comum.RAIZ / "dados" / "metadata" / "sinais_operacionais_eventos.jsonl"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
OUT = comum.DADOS_TRATADOS / "sinais_operacionais_auditoria.json"


def read_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    rows = []
    with EVENTS.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"JSON inválido na linha {line_no}: {exc}") from exc
    return rows


def inventory_ids() -> set[str]:
    if not INVENTARIO.exists():
        return set()
    with INVENTARIO.open(encoding="utf-8-sig", newline="") as fh:
        return {
            str(r.get("id_snisb") or "").strip()
            for r in csv.DictReader(fh, delimiter=";")
            if str(r.get("id_snisb") or "").strip()
        }


def main() -> None:
    comum.preparar_diretorios()
    events = read_events()
    problems = validate_event_log(events)
    problems.extend(validate_governance_chain(events))
    problems.extend(validate_ledger_chain(events))
    ids = inventory_ids()

    for index, event in enumerate(events, start=1):
        bid = str(event.get("id_snisb") or "").strip()
        if bid and bid not in ids:
            problems.append({
                "line": index,
                "event_id": event.get("event_id") or "",
                "error": f"id_snisb fora do inventário corrente: {bid}",
            })

    result = {
        "status": "ok" if not problems else "failure",
        "eventos": len(events),
        "problemas": len(problems),
        "detalhes": problems,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"auditoria sinais operacionais: {len(events)} evento(s), "
        f"{len(problems)} problema(s)"
    )
    if problems:
        for p in problems[:20]:
            print(f"  linha {p['line']} | {p.get('event_id','')} | {p['error']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
