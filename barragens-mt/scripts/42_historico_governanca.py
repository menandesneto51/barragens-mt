"""Materializa o histórico da governança operacional a partir do ledger append-only.

Não altera IDAP, regras ou nível operacional.

Saídas:
  dados/tratados/governanca_operacional_ciclo_vida.csv
  dados/tratados/governanca_operacional_historico_diario.csv
  dados/tratados/governanca_operacional_historico_dimensoes.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import comum

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vigibarragens.intelligence.operational_governance_history import (  # noqa: E402
    daily_dimensions,
    daily_history,
    proposal_lifecycle,
)

EVENTS = comum.RAIZ / "dados" / "metadata" / "sinais_operacionais_eventos.jsonl"
OUT_LIFECYCLE = comum.DADOS_TRATADOS / "governanca_operacional_ciclo_vida.csv"
OUT_DAILY = comum.DADOS_TRATADOS / "governanca_operacional_historico_diario.csv"
OUT_DIMS = comum.DADOS_TRATADOS / "governanca_operacional_historico_dimensoes.csv"


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


def main() -> None:
    comum.preparar_diretorios()
    events = read_events()
    lifecycle = proposal_lifecycle(events)
    daily = daily_history(lifecycle)
    dims = daily_dimensions(lifecycle)

    lifecycle_fields = [
        "proposal_event_id",
        "id_snisb",
        "signal",
        "value",
        "source_type",
        "source_name",
        "proposed_by",
        "proposed_at",
        "observed_at",
        "status",
        "resolution_event_id",
        "resolved_by",
        "resolved_at",
        "resolution_action",
        "tempo_resolucao_h",
    ]
    daily_fields = [
        "data",
        "propostas_registradas",
        "propostas_resolvidas",
        "propostas_confirmadas",
        "propostas_revogadas",
        "taxa_confirmacao_resolvidas_pct",
        "taxa_revogacao_resolvidas_pct",
        "tempo_resolucao_mediana_h",
        "tempo_resolucao_p95_h",
        "backlog_fim_dia",
    ]
    dim_fields = [
        "data",
        "signal",
        "source_type",
        "propostas_registradas",
        "propostas_confirmadas",
        "propostas_revogadas",
        "backlog_fim_dia",
    ]

    comum.salvar_csv(OUT_LIFECYCLE, lifecycle, lifecycle_fields)
    comum.salvar_csv(OUT_DAILY, daily, daily_fields)
    comum.salvar_csv(OUT_DIMS, dims, dim_fields)
    print(
        "Histórico da governança: "
        f"{len(lifecycle)} proposta(s) · {len(daily)} dia(s) · "
        f"{len(dims)} linha(s) por sinal/fonte."
    )


if __name__ == "__main__":
    main()
