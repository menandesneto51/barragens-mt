"""Registra um evento operacional governado em log append-only.

Exemplo:
  python scripts/39_registrar_sinal_operacional.py \
    --id-snisb 123 \
    --signal rompimento_confirmado \
    --action confirm \
    --value sim \
    --observed-at 2026-09-27T10:30:00-04:00 \
    --source-type defesa_civil \
    --source-name "Defesa Civil Municipal" \
    --document-reference "SITREP 001/2026" \
    --confirmed-by "Nome do responsável" \
    --confirmer-role "Coordenador"

Revogação/correção gera novo evento; o histórico nunca é reescrito.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import comum

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vigibarragens.intelligence.operational_signal_registry import (  # noqa: E402
    ACTIONS,
    SIGNALS,
    SOURCE_TYPES,
    create_event,
    ledger_hash,
)
from vigibarragens.lineage_runtime import current_run_id  # noqa: E402

EVENTS = comum.RAIZ / "dados" / "metadata" / "sinais_operacionais_eventos.jsonl"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"


def inventory_ids() -> set[str]:
    import csv

    if not INVENTARIO.exists():
        return set()
    with INVENTARIO.open(encoding="utf-8-sig", newline="") as fh:
        return {
            str(r.get("id_snisb") or "").strip()
            for r in csv.DictReader(fh, delimiter=";")
            if str(r.get("id_snisb") or "").strip()
        }


def append_event(payload: dict) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    previous_anchor = ""
    if EVENTS.exists():
        last = None
        with EVENTS.open(encoding="utf-8") as existing:
            for line in existing:
                text = line.strip()
                if text:
                    last = json.loads(text)
        if last:
            previous_anchor = str(
                last.get("ledger_sha256") or last.get("event_sha256") or ""
            )
    payload = dict(payload)
    payload["previous_ledger_sha256"] = previous_anchor
    payload["ledger_sha256"] = ledger_hash(payload, previous_anchor)
    with EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Registro governado de sinal operacional")
    parser.add_argument("--id-snisb", required=True)
    parser.add_argument("--signal", required=True, choices=sorted(SIGNALS))
    parser.add_argument("--action", required=True, choices=sorted(ACTIONS))
    parser.add_argument("--value", default="")
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--source-type", required=True, choices=sorted(SOURCE_TYPES))
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--document-reference", default="")
    parser.add_argument("--confirmed-by", required=True)
    parser.add_argument("--confirmer-role", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--parent-event-id", default="")
    args = parser.parse_args()

    ids = inventory_ids()
    if not ids:
        raise SystemExit("inventário ausente; execute a etapa 05.")
    if args.id_snisb not in ids:
        raise SystemExit(f"id_snisb não encontrado no inventário: {args.id_snisb}")

    event = create_event(
        id_snisb=args.id_snisb,
        signal=args.signal,
        action=args.action,
        value=args.value,
        observed_at=args.observed_at,
        source_type=args.source_type,
        source_name=args.source_name,
        document_reference=args.document_reference,
        confirmed_by=args.confirmed_by,
        confirmer_role=args.confirmer_role,
        note=args.note,
        run_id=current_run_id(),
        parent_event_id=args.parent_event_id,
    )
    append_event(event.to_dict())
    print(
        f"evento registrado: {event.event_id} | {event.id_snisb} | "
        f"{event.signal} | {event.action} | sha256={event.event_sha256}"
    )
    print("reexecute a etapa 38 e depois a 16 para materializar o estado operacional.")


if __name__ == "__main__":
    main()
