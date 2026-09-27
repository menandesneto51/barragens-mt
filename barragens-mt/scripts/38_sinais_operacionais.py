"""Materializa o estado corrente dos sinais operacionais a partir de eventos append-only.

A fonte de verdade é `dados/metadata/sinais_operacionais_eventos.jsonl`.
Este script:
- adiciona barragens novas ao estado materializado;
- preserva compatibilidade com valores legados já existentes no CSV largo;
- aplica o último evento válido por barragem/sinal;
- gera estado largo para o motor IDAP;
- gera estado longo por barragem × sinal para auditoria;
- nunca transforma ausência de evento em confirmação de segurança.

Saídas:
  dados/tratados/sinais_operacionais_mt.csv
  dados/tratados/sinais_operacionais_estado_mt.csv
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import comum

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vigibarragens.intelligence.operational_signal_registry import (  # noqa: E402
    SIGNALS,
    materialize_latest,
    pending_proposals,
)

OUT = comum.DADOS_TRATADOS / "sinais_operacionais_mt.csv"
OUT_LONG = comum.DADOS_TRATADOS / "sinais_operacionais_estado_mt.csv"
OUT_PENDING = comum.DADOS_TRATADOS / "sinais_operacionais_pendentes_mt.csv"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
EVENTS = comum.RAIZ / "dados" / "metadata" / "sinais_operacionais_eventos.jsonl"

BASE_FIELDS = [
    "id_snisb",
    "nome",
    "municipio_sede",
    *SIGNALS.keys(),
    "fonte_observacional",
    "referencia_temporal",
    "documento_referencia",
    "observacao",
]

PENDING_FIELDS = [
    "id_snisb",
    "nome",
    "municipio_sede",
    "signal",
    "value",
    "event_id",
    "event_sha256",
    "observed_at",
    "recorded_at",
    "source_type",
    "source_name",
    "document_reference",
    "confirmed_by",
    "confirmer_role",
    "note",
    "run_id",
]

LONG_FIELDS = [
    "id_snisb",
    "nome",
    "municipio_sede",
    "signal",
    "value",
    "action",
    "event_id",
    "event_sha256",
    "observed_at",
    "recorded_at",
    "source_type",
    "source_name",
    "document_reference",
    "confirmed_by",
    "confirmer_role",
    "note",
    "run_id",
    "status_corrente",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def read_events() -> list[dict[str, Any]]:
    if not EVENTS.exists():
        return []
    rows: list[dict[str, Any]] = []
    with EVENTS.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"evento JSON inválido na linha {line_no}: {exc}") from exc
            rows.append(item)
    return rows


def _most_recent_active(events_by_signal: dict[str, dict[str, Any]]) -> dict[str, Any]:
    active = [
        e for e in events_by_signal.values()
        if str(e.get("action") or "") == "confirm"
    ]
    if not active:
        return {}
    return max(
        active,
        key=lambda e: (str(e.get("observed_at") or ""), str(e.get("event_id") or "")),
    )


def main() -> None:
    comum.preparar_diretorios()
    inventario = read_csv(INVENTARIO)
    if not inventario:
        raise SystemExit("inventário ausente; execute a etapa 05.")

    existentes = {
        str(r.get("id_snisb") or "").strip(): r
        for r in read_csv(OUT)
        if str(r.get("id_snisb") or "").strip()
    }
    eventos = read_events()
    latest = materialize_latest(eventos)
    pendentes = pending_proposals(eventos)

    wide_rows: list[dict[str, Any]] = []
    long_rows: list[dict[str, Any]] = []
    novos = 0
    barragens_por_id = {
        str(b.get("id_snisb") or "").strip(): b
        for b in inventario
        if str(b.get("id_snisb") or "").strip()
    }

    for bid, b in barragens_por_id.items():
        anterior = existentes.get(bid, {})
        row = {field: anterior.get(field, "") for field in BASE_FIELDS}
        row["id_snisb"] = bid
        row["nome"] = b.get("nome") or row.get("nome") or ""
        row["municipio_sede"] = b.get("municipio") or row.get("municipio_sede") or ""
        if bid not in existentes:
            novos += 1

        by_signal = latest.get(bid, {})
        for signal in SIGNALS:
            event = by_signal.get(signal)
            if not event:
                continue
            if str(event.get("action") or "") == "revoke":
                row[signal] = ""
            else:
                row[signal] = event.get("value", "")

            long_rows.append({
                "id_snisb": bid,
                "nome": row["nome"],
                "municipio_sede": row["municipio_sede"],
                "signal": signal,
                "value": event.get("value", ""),
                "action": event.get("action", ""),
                "event_id": event.get("event_id", ""),
                "event_sha256": event.get("event_sha256", ""),
                "observed_at": event.get("observed_at", ""),
                "recorded_at": event.get("recorded_at", ""),
                "source_type": event.get("source_type", ""),
                "source_name": event.get("source_name", ""),
                "document_reference": event.get("document_reference", ""),
                "confirmed_by": event.get("confirmed_by", ""),
                "confirmer_role": event.get("confirmer_role", ""),
                "note": event.get("note", ""),
                "run_id": event.get("run_id", ""),
                "status_corrente": (
                    "ativo" if str(event.get("action") or "") == "confirm" else "revogado"
                ),
            })

        latest_active = _most_recent_active(by_signal)
        if latest_active:
            row["fonte_observacional"] = latest_active.get("source_name", "")
            row["referencia_temporal"] = latest_active.get("observed_at", "")
            row["documento_referencia"] = latest_active.get("document_reference", "")
            row["observacao"] = latest_active.get("note", "")

        wide_rows.append(row)

    pending_rows: list[dict[str, Any]] = []
    for event in pendentes:
        bid = str(event.get("id_snisb") or "").strip()
        b = barragens_por_id.get(bid, {})
        pending_rows.append({
            "id_snisb": bid,
            "nome": b.get("nome") or "",
            "municipio_sede": b.get("municipio") or "",
            "signal": event.get("signal", ""),
            "value": event.get("value", ""),
            "event_id": event.get("event_id", ""),
            "event_sha256": event.get("event_sha256", ""),
            "observed_at": event.get("observed_at", ""),
            "recorded_at": event.get("recorded_at", ""),
            "source_type": event.get("source_type", ""),
            "source_name": event.get("source_name", ""),
            "document_reference": event.get("document_reference", ""),
            "confirmed_by": event.get("confirmed_by", ""),
            "confirmer_role": event.get("confirmer_role", ""),
            "note": event.get("note", ""),
            "run_id": event.get("run_id", ""),
        })

    # Eventos para IDs fora do inventário são preservados no log, mas não entram no estado.
    orphan_ids = sorted(set(latest) - set(barragens_por_id))

    wide_rows.sort(key=lambda r: (str(r.get("municipio_sede") or ""), str(r.get("nome") or "")))
    long_rows.sort(key=lambda r: (str(r.get("id_snisb") or ""), str(r.get("signal") or "")))
    comum.salvar_csv(OUT, wide_rows, BASE_FIELDS)
    comum.salvar_csv(OUT_LONG, long_rows, LONG_FIELDS)
    comum.salvar_csv(OUT_PENDING, pending_rows, PENDING_FIELDS)
    print(
        f"Sinais operacionais: {len(wide_rows)} barragens · {len(long_rows)} "
        f"estado(s) com evento · {len(pending_rows)} proposta(s) pendente(s) · {novos} nova(s)."
    )
    if orphan_ids:
        print(
            "AVISO: eventos append-only sem barragem no inventário corrente: "
            + ", ".join(orphan_ids)
        )
    print(
        "Ausência de evento permanece lacuna; fatos só entram no estado por confirmação explícita."
    )


if __name__ == "__main__":
    main()
