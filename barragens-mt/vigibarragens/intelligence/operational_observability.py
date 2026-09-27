"""Observabilidade da governança de sinais operacionais.

Não altera IDAP, regras ou nível operacional. Apenas resume o ledger governado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_hours(value: Any, *, now: datetime | None = None) -> float | None:
    dt = parse_dt(value)
    if dt is None:
        return None
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    hours = (ref.astimezone(timezone.utc) - dt).total_seconds() / 3600.0
    return max(0.0, hours)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def enrich_pending(
    pending: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
    sla_hours: float | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in pending:
        row = dict(event)
        age = age_hours(event.get("recorded_at"), now=now)
        row["idade_aguardando_h"] = round(age, 2) if age is not None else ""
        row["sla_horas"] = sla_hours if sla_hours is not None else ""
        if sla_hours is None:
            row["sla_status"] = "sem_politica"
        elif age is None:
            row["sla_status"] = "sem_data"
        elif age > sla_hours:
            row["sla_status"] = "fora_sla"
        else:
            row["sla_status"] = "dentro_sla"
        out.append(row)
    return out


def governance_summary(
    *,
    events: Iterable[dict[str, Any]],
    pending: Iterable[dict[str, Any]],
    latest_state: dict[str, dict[str, dict[str, Any]]],
    integrity_status: str,
    integrity_problems: int,
    now: datetime | None = None,
    sla_hours: float | None = None,
) -> dict[str, Any]:
    events_list = [dict(e) for e in events]
    pending_rows = enrich_pending(pending, now=now, sla_hours=sla_hours)
    ages = [
        float(r["idade_aguardando_h"])
        for r in pending_rows
        if r.get("idade_aguardando_h") not in {"", None}
    ]

    current = [
        event
        for by_signal in latest_state.values()
        for event in by_signal.values()
    ]
    active = sum(1 for e in current if str(e.get("action") or "") == "confirm")
    revoked = sum(1 for e in current if str(e.get("action") or "") == "revoke")
    actions = {
        action: sum(1 for e in events_list if str(e.get("action") or "") == action)
        for action in ("propose", "confirm", "revoke")
    }

    if sla_hours is None:
        breaches: int | str = ""
        sla_policy = "nao_configurada"
    else:
        breaches = sum(1 for r in pending_rows if r.get("sla_status") == "fora_sla")
        sla_policy = "configurada"

    return {
        "instante_observabilidade": (now or datetime.now(timezone.utc)).isoformat(),
        "eventos_total": len(events_list),
        "eventos_propose": actions["propose"],
        "eventos_confirm": actions["confirm"],
        "eventos_revoke": actions["revoke"],
        "sinais_ativos": active,
        "sinais_revogados": revoked,
        "propostas_pendentes": len(pending_rows),
        "idade_pendente_mediana_h": round(median(ages), 2) if ages else "",
        "idade_pendente_p95_h": round(percentile(ages, 0.95), 2) if ages else "",
        "idade_pendente_max_h": round(max(ages), 2) if ages else "",
        "sla_politica": sla_policy,
        "sla_horas": sla_hours if sla_hours is not None else "",
        "pendencias_fora_sla": breaches,
        "integridade_status": integrity_status or "desconhecido",
        "integridade_problemas": int(integrity_problems or 0),
    }


def governance_actions(
    *,
    pending_rows: Iterable[dict[str, Any]],
    integrity_status: str,
    integrity_problems: int,
) -> list[dict[str, Any]]:
    """Gera fila de trabalho de governança sem classificar risco de barragem."""
    actions: list[dict[str, Any]] = []

    if str(integrity_status or "") != "ok" or int(integrity_problems or 0) > 0:
        actions.append({
            "tipo_acao": "tratar_integridade_ledger",
            "id_snisb": "",
            "signal": "",
            "event_id": "",
            "idade_aguardando_h": "",
            "sla_status": "",
            "acao_requerida": (
                "Interromper materialização operacional e investigar os problemas "
                "de integridade reportados pela etapa 40."
            ),
        })

    for row in pending_rows:
        sla_status = str(row.get("sla_status") or "sem_politica")
        action = (
            "Revisar pendência fora do SLA configurado e obter segunda confirmação."
            if sla_status == "fora_sla"
            else "Obter segunda confirmação ou rejeitar/revogar a proposta de forma auditável."
        )
        actions.append({
            "tipo_acao": "confirmacao_pendente",
            "id_snisb": row.get("id_snisb", ""),
            "signal": row.get("signal", ""),
            "event_id": row.get("event_id", ""),
            "idade_aguardando_h": row.get("idade_aguardando_h", ""),
            "sla_status": sla_status,
            "acao_requerida": action,
        })
    return actions
