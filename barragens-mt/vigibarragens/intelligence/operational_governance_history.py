"""Histórico da governança operacional derivado do ledger append-only.

Não altera risco. Reconstrói ciclo de vida das propostas e backlog ao fim de cada dia.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from statistics import median
from typing import Any, Iterable

from .operational_observability import parse_dt, percentile


def proposal_lifecycle(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(e) for e in events]
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in rows:
        parent = str(event.get("parent_event_id") or "").strip()
        if parent and str(event.get("action") or "") in {"confirm", "revoke"}:
            children[parent].append(event)

    out: list[dict[str, Any]] = []
    for proposal in rows:
        if str(proposal.get("action") or "") != "propose":
            continue
        event_id = str(proposal.get("event_id") or "")
        candidates = sorted(
            children.get(event_id, []),
            key=lambda e: (
                str(e.get("recorded_at") or ""),
                str(e.get("event_id") or ""),
            ),
        )
        resolution = candidates[0] if candidates else None
        proposed_at = parse_dt(proposal.get("recorded_at"))
        resolved_at = parse_dt(resolution.get("recorded_at")) if resolution else None
        latency = None
        if proposed_at and resolved_at:
            latency = max(0.0, (resolved_at - proposed_at).total_seconds() / 3600.0)

        status = (
            "pendente"
            if resolution is None
            else "confirmada"
            if str(resolution.get("action") or "") == "confirm"
            else "revogada"
        )
        out.append({
            "proposal_event_id": event_id,
            "id_snisb": proposal.get("id_snisb", ""),
            "signal": proposal.get("signal", ""),
            "value": proposal.get("value", ""),
            "source_type": proposal.get("source_type", ""),
            "source_name": proposal.get("source_name", ""),
            "proposed_by": proposal.get("confirmed_by", ""),
            "proposed_at": proposal.get("recorded_at", ""),
            "observed_at": proposal.get("observed_at", ""),
            "status": status,
            "resolution_event_id": resolution.get("event_id", "") if resolution else "",
            "resolved_by": resolution.get("confirmed_by", "") if resolution else "",
            "resolved_at": resolution.get("recorded_at", "") if resolution else "",
            "resolution_action": resolution.get("action", "") if resolution else "",
            "tempo_resolucao_h": round(latency, 2) if latency is not None else "",
        })
    return sorted(
        out,
        key=lambda r: (str(r.get("proposed_at") or ""), str(r.get("proposal_event_id") or "")),
    )


def _calendar_days(lifecycle: list[dict[str, Any]]) -> list[date]:
    dates: list[date] = []
    for row in lifecycle:
        for field in ("proposed_at", "resolved_at"):
            dt = parse_dt(row.get(field))
            if dt:
                dates.append(dt.date())
    if not dates:
        return []
    start, end = min(dates), max(dates)
    days: list[date] = []
    current = start
    from datetime import timedelta
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day, time.max, tzinfo=timezone.utc)


def daily_history(lifecycle: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(r) for r in lifecycle]
    out: list[dict[str, Any]] = []
    for day in _calendar_days(rows):
        eod = _end_of_day(day)
        proposed_today = [
            r for r in rows
            if (dt := parse_dt(r.get("proposed_at"))) and dt.date() == day
        ]
        resolved_today = [
            r for r in rows
            if (dt := parse_dt(r.get("resolved_at"))) and dt.date() == day
        ]
        confirmed_today = [r for r in resolved_today if r.get("status") == "confirmada"]
        revoked_today = [r for r in resolved_today if r.get("status") == "revogada"]

        backlog = []
        for r in rows:
            pdt = parse_dt(r.get("proposed_at"))
            rdt = parse_dt(r.get("resolved_at"))
            if pdt and pdt <= eod and (rdt is None or rdt > eod):
                backlog.append(r)

        latencies = [
            float(r["tempo_resolucao_h"])
            for r in resolved_today
            if r.get("tempo_resolucao_h") not in {"", None}
        ]
        resolved_n = len(resolved_today)
        out.append({
            "data": day.isoformat(),
            "propostas_registradas": len(proposed_today),
            "propostas_resolvidas": resolved_n,
            "propostas_confirmadas": len(confirmed_today),
            "propostas_revogadas": len(revoked_today),
            "taxa_confirmacao_resolvidas_pct": (
                round(100.0 * len(confirmed_today) / resolved_n, 2)
                if resolved_n else ""
            ),
            "taxa_revogacao_resolvidas_pct": (
                round(100.0 * len(revoked_today) / resolved_n, 2)
                if resolved_n else ""
            ),
            "tempo_resolucao_mediana_h": round(median(latencies), 2) if latencies else "",
            "tempo_resolucao_p95_h": (
                round(percentile(latencies, 0.95), 2) if latencies else ""
            ),
            "backlog_fim_dia": len(backlog),
        })
    return out


def daily_dimensions(lifecycle: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(r) for r in lifecycle]
    days = _calendar_days(rows)
    dimensions = sorted({
        (str(r.get("signal") or ""), str(r.get("source_type") or ""))
        for r in rows
    })
    out: list[dict[str, Any]] = []
    for day in days:
        eod = _end_of_day(day)
        for signal, source_type in dimensions:
            scoped = [
                r for r in rows
                if str(r.get("signal") or "") == signal
                and str(r.get("source_type") or "") == source_type
            ]
            proposed = [
                r for r in scoped
                if (dt := parse_dt(r.get("proposed_at"))) and dt.date() == day
            ]
            resolved = [
                r for r in scoped
                if (dt := parse_dt(r.get("resolved_at"))) and dt.date() == day
            ]
            backlog = []
            for r in scoped:
                pdt = parse_dt(r.get("proposed_at"))
                rdt = parse_dt(r.get("resolved_at"))
                if pdt and pdt <= eod and (rdt is None or rdt > eod):
                    backlog.append(r)
            if not proposed and not resolved and not backlog:
                continue
            out.append({
                "data": day.isoformat(),
                "signal": signal,
                "source_type": source_type,
                "propostas_registradas": len(proposed),
                "propostas_confirmadas": sum(1 for r in resolved if r.get("status") == "confirmada"),
                "propostas_revogadas": sum(1 for r in resolved if r.get("status") == "revogada"),
                "backlog_fim_dia": len(backlog),
            })
    return out


def dimension_performance(lifecycle: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resumo consolidado por sinal × tipo de fonte, sem ranking de risco."""
    rows = [dict(r) for r in lifecycle]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("signal") or ""),
            str(row.get("source_type") or ""),
        )
        groups[key].append(row)

    out: list[dict[str, Any]] = []
    for (signal, source_type), scoped in sorted(groups.items()):
        confirmed = [r for r in scoped if r.get("status") == "confirmada"]
        revoked = [r for r in scoped if r.get("status") == "revogada"]
        pending = [r for r in scoped if r.get("status") == "pendente"]
        resolved = confirmed + revoked
        latencies = [
            float(r["tempo_resolucao_h"])
            for r in resolved
            if r.get("tempo_resolucao_h") not in {"", None}
        ]
        resolved_n = len(resolved)
        out.append({
            "signal": signal,
            "source_type": source_type,
            "propostas_total": len(scoped),
            "pendentes": len(pending),
            "confirmadas": len(confirmed),
            "revogadas": len(revoked),
            "resolvidas": resolved_n,
            "taxa_confirmacao_resolvidas_pct": (
                round(100.0 * len(confirmed) / resolved_n, 2)
                if resolved_n else ""
            ),
            "taxa_revogacao_resolvidas_pct": (
                round(100.0 * len(revoked) / resolved_n, 2)
                if resolved_n else ""
            ),
            "tempo_resolucao_mediana_h": (
                round(median(latencies), 2) if latencies else ""
            ),
            "tempo_resolucao_p95_h": (
                round(percentile(latencies, 0.95), 2) if latencies else ""
            ),
        })
    return out
