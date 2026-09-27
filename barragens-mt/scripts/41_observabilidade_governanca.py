"""Materializa observabilidade da governança operacional.

Não altera IDAP, regras nem nível. Resume:
- eventos do ledger;
- propostas pendentes e suas idades;
- sinais ativos/revogados;
- estado de integridade;
- SLA somente se configurado explicitamente em VIGIBARRAGENS_CONFIRMATION_SLA_HOURS.

Saídas:
  dados/tratados/governanca_operacional_resumo.csv
  dados/tratados/governanca_operacional_pendencias.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vigibarragens.intelligence.operational_observability import (  # noqa: E402
    enrich_pending,
    governance_summary,
)
from vigibarragens.intelligence.operational_signal_registry import (  # noqa: E402
    materialize_latest,
    pending_proposals,
)

EVENTS = comum.RAIZ / "dados" / "metadata" / "sinais_operacionais_eventos.jsonl"
AUDIT = comum.DADOS_TRATADOS / "sinais_operacionais_auditoria.json"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
OUT_SUMMARY = comum.DADOS_TRATADOS / "governanca_operacional_resumo.csv"
OUT_PENDING = comum.DADOS_TRATADOS / "governanca_operacional_pendencias.csv"


def read_events() -> list[dict[str, Any]]:
    if not EVENTS.exists():
        return []
    rows: list[dict[str, Any]] = []
    with EVENTS.open(encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def read_inventory() -> dict[str, dict[str, str]]:
    if not INVENTARIO.exists():
        return {}
    with INVENTARIO.open(encoding="utf-8-sig", newline="") as fh:
        return {
            str(r.get("id_snisb") or "").strip(): r
            for r in csv.DictReader(fh, delimiter=";")
            if str(r.get("id_snisb") or "").strip()
        }


def read_audit() -> tuple[str, int]:
    if not AUDIT.exists():
        return "desconhecido", 0
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    return str(data.get("status") or "desconhecido"), int(data.get("problemas") or 0)


def configured_sla_hours() -> float | None:
    raw = os.environ.get("VIGIBARRAGENS_CONFIRMATION_SLA_HOURS", "").strip()
    if not raw:
        return None
    try:
        value = float(raw.replace(",", "."))
    except ValueError as exc:
        raise SystemExit("VIGIBARRAGENS_CONFIRMATION_SLA_HOURS inválido") from exc
    if value <= 0:
        raise SystemExit("VIGIBARRAGENS_CONFIRMATION_SLA_HOURS deve ser > 0")
    return value


def main() -> None:
    comum.preparar_diretorios()
    now = datetime.now(timezone.utc)
    events = read_events()
    pending = pending_proposals(events)
    latest = materialize_latest(events)
    inventory = read_inventory()
    integrity_status, integrity_problems = read_audit()
    sla_hours = configured_sla_hours()

    summary = governance_summary(
        events=events,
        pending=pending,
        latest_state=latest,
        integrity_status=integrity_status,
        integrity_problems=integrity_problems,
        now=now,
        sla_hours=sla_hours,
    )

    pending_rows = enrich_pending(pending, now=now, sla_hours=sla_hours)
    for row in pending_rows:
        bid = str(row.get("id_snisb") or "")
        inv = inventory.get(bid, {})
        row["nome"] = inv.get("nome") or ""
        row["municipio_sede"] = inv.get("municipio") or ""

    summary_fields = list(summary.keys())
    comum.salvar_csv(OUT_SUMMARY, [summary], summary_fields)

    pending_fields = [
        "id_snisb",
        "nome",
        "municipio_sede",
        "signal",
        "value",
        "event_id",
        "observed_at",
        "recorded_at",
        "source_type",
        "source_name",
        "document_reference",
        "confirmed_by",
        "confirmer_role",
        "idade_aguardando_h",
        "sla_horas",
        "sla_status",
    ]
    comum.salvar_csv(OUT_PENDING, pending_rows, pending_fields)
    print(
        "Governança operacional: "
        f"{summary['propostas_pendentes']} pendência(s) · "
        f"{summary['sinais_ativos']} ativo(s) · "
        f"integridade={summary['integridade_status']} · "
        f"SLA={summary['sla_politica']}"
    )


if __name__ == "__main__":
    main()
