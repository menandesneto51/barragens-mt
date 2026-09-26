"""Contrato de sinais operacionais persistentes usados pelas regras R02–R09.

Ausência de linha/campo NÃO é evidência de normalidade. O motor mantém os defaults
históricos (False/0), enquanto o lineage registra se há ou não fonte materializada.
"""
from __future__ import annotations

from typing import Any

BOOL_FIELDS = (
    "rompimento_confirmado",
    "perda_subita_de_nivel",
    "evacuacao_determinada",
    "mancha_atinge_unidade_estrategica",
    "mancha_atinge_captacao",
)

SIGNAL_FIELDS = (
    *BOOL_FIELDS,
    "sensores_criticos_em_falha",
    "municipios_zas_sem_confirmacao",
)


def parse_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "sim", "s", "yes"}


def parse_int(value: Any) -> int:
    try:
        return max(0, int(float(str(value or "0").replace(",", "."))))
    except (TypeError, ValueError):
        return 0


def parse_municipalities(value: Any) -> tuple[str, ...]:
    parts = [p.strip() for p in str(value or "").replace(";", "|").split("|")]
    return tuple(p for p in parts if p)


def normalized_signal_values(row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    out: dict[str, Any] = {field: parse_bool(row.get(field)) for field in BOOL_FIELDS}
    out["sensores_criticos_em_falha"] = parse_int(row.get("sensores_criticos_em_falha"))
    out["municipios_zas_sem_confirmacao"] = parse_municipalities(
        row.get("municipios_zas_sem_confirmacao")
    )
    return out


def signal_source_metadata(row: dict[str, Any] | None) -> dict[str, str]:
    row = row or {}
    return {
        "fonte_observacional": str(row.get("fonte_observacional") or "").strip(),
        "referencia_temporal": str(row.get("referencia_temporal") or "").strip(),
        "documento_referencia": str(row.get("documento_referencia") or "").strip(),
        "observacao_sinal": str(row.get("observacao") or "").strip(),
    }
