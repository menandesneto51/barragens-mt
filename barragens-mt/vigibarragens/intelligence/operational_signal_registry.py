"""Registro governado de sinais operacionais.

Eventos são append-only. O estado corrente é derivado do último evento válido por
barragem/sinal; correções e revogações geram novos eventos, nunca edição retroativa.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any, Iterable

SIGNALS = {
    "rompimento_confirmado": "bool",
    "perda_subita_de_nivel": "bool",
    "evacuacao_determinada": "bool",
    "sensores_criticos_em_falha": "int",
    "mancha_atinge_unidade_estrategica": "bool",
    "mancha_atinge_captacao": "bool",
    "municipios_zas_sem_confirmacao": "text",
}

SOURCE_TYPES = {
    "defesa_civil",
    "orgao_fiscalizador",
    "empreendedor",
    "ses",
    "sms",
    "sistema_monitoramento",
    "outro_documentado",
}

ACTIONS = {"propose", "confirm", "revoke"}

CRITICAL_SIGNALS = {
    "rompimento_confirmado",
    "perda_subita_de_nivel",
    "evacuacao_determinada",
    "mancha_atinge_unidade_estrategica",
    "mancha_atinge_captacao",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_value(signal: str, value: Any) -> str:
    kind = SIGNALS[signal]
    if kind == "bool":
        txt = str(value).strip().lower()
        if txt in {"1", "true", "sim", "s", "yes"}:
            return "sim"
        if txt in {"0", "false", "nao", "não", "n", "no"}:
            return "não"
        raise ValueError(f"{signal}: valor booleano inválido")
    if kind == "int":
        try:
            number = int(float(str(value).replace(",", ".")))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{signal}: inteiro inválido") from exc
        if number < 0:
            raise ValueError(f"{signal}: valor não pode ser negativo")
        return str(number)
    return str(value or "").strip()


@dataclass(frozen=True)
class OperationalSignalEvent:
    event_id: str
    id_snisb: str
    signal: str
    action: str
    value: str
    observed_at: str
    recorded_at: str
    source_type: str
    source_name: str
    document_reference: str
    confirmed_by: str
    confirmer_role: str
    note: str
    run_id: str
    event_sha256: str
    parent_event_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_event(
    *,
    id_snisb: str,
    signal: str,
    action: str,
    value: Any = "",
    observed_at: str,
    source_type: str,
    source_name: str,
    document_reference: str,
    confirmed_by: str,
    confirmer_role: str,
    note: str = "",
    run_id: str = "",
    event_id: str | None = None,
    recorded_at: str | None = None,
    parent_event_id: str = "",
) -> OperationalSignalEvent:
    id_snisb = str(id_snisb or "").strip()
    if not id_snisb:
        raise ValueError("id_snisb é obrigatório")
    if signal not in SIGNALS:
        raise ValueError(f"sinal não suportado: {signal}")
    if action not in ACTIONS:
        raise ValueError(f"ação inválida: {action}")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"tipo de fonte inválido: {source_type}")
    if not str(observed_at or "").strip():
        raise ValueError("observed_at é obrigatório")
    if not str(source_name or "").strip():
        raise ValueError("source_name é obrigatório")
    if not str(confirmed_by or "").strip():
        raise ValueError("confirmed_by é obrigatório")
    if not str(confirmer_role or "").strip():
        raise ValueError("confirmer_role é obrigatório")

    normalized = "" if action == "revoke" else _normalize_value(signal, value)
    eid = event_id or str(uuid.uuid4())
    recorded = recorded_at or utcnow()
    base = {
        "event_id": eid,
        "id_snisb": id_snisb,
        "signal": signal,
        "action": action,
        "value": normalized,
        "observed_at": str(observed_at).strip(),
        "recorded_at": recorded,
        "source_type": source_type,
        "source_name": str(source_name).strip(),
        "document_reference": str(document_reference or "").strip(),
        "confirmed_by": str(confirmed_by).strip(),
        "confirmer_role": str(confirmer_role).strip(),
        "note": str(note or "").strip(),
        "run_id": str(run_id or "").strip(),
    }
    return OperationalSignalEvent(
        **base,
        event_sha256=canonical_hash(base),
        parent_event_id=str(parent_event_id or "").strip(),
    )


def materialize_latest(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Retorna id_snisb -> sinal -> último evento por recorded_at/event_id."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        bid = str(event.get("id_snisb") or "").strip()
        signal = str(event.get("signal") or "").strip()
        if not bid or signal not in SIGNALS:
            continue
        if str(event.get("action") or "") == "propose":
            continue
        key = (bid, signal)
        rank = (str(event.get("recorded_at") or ""), str(event.get("event_id") or ""))
        current = latest.get(key)
        current_rank = (
            str(current.get("recorded_at") or ""),
            str(current.get("event_id") or ""),
        ) if current else ("", "")
        if rank >= current_rank:
            latest[key] = dict(event)

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for (bid, signal), event in latest.items():
        out.setdefault(bid, {})[signal] = event
    return out


def validate_event_record(event: dict[str, Any]) -> list[str]:
    """Valida estrutura e integridade criptográfica de um evento persistido."""
    errors: list[str] = []
    required = (
        "event_id", "id_snisb", "signal", "action", "observed_at", "recorded_at",
        "source_type", "source_name", "confirmed_by", "confirmer_role", "event_sha256",
    )
    for field in required:
        if not str(event.get(field) or "").strip():
            errors.append(f"campo obrigatório ausente: {field}")

    if str(event.get("signal") or "") not in SIGNALS:
        errors.append("signal inválido")
    if str(event.get("action") or "") not in ACTIONS:
        errors.append("action inválida")
    if str(event.get("source_type") or "") not in SOURCE_TYPES:
        errors.append("source_type inválido")

    expected_payload = {
        key: event.get(key, "")
        for key in (
            "event_id", "id_snisb", "signal", "action", "value", "observed_at",
            "recorded_at", "source_type", "source_name", "document_reference",
            "confirmed_by", "confirmer_role", "note", "run_id",
        )
    }
    expected_hash = canonical_hash(expected_payload)
    if str(event.get("event_sha256") or "") != expected_hash:
        errors.append("event_sha256 divergente do conteúdo canônico")
    return errors


def validate_event_log(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retorna problemas do log; não altera nem corrige eventos."""
    problems: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, event in enumerate(events, start=1):
        event_id = str(event.get("event_id") or "")
        if event_id and event_id in seen_ids:
            problems.append({
                "line": index,
                "event_id": event_id,
                "error": "event_id duplicado",
            })
        if event_id:
            seen_ids.add(event_id)
        for error in validate_event_record(event):
            problems.append({
                "line": index,
                "event_id": event_id,
                "error": error,
            })
    return problems


def validate_governance_chain(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valida transições proposta→confirmação/revogação para sinais críticos.

    Eventos legados sem parent_event_id continuam aceitos somente quando não houver
    proposta no novo fluxo. Para novos sinais críticos, confirmação/revogação deve
    referenciar explicitamente um evento anterior compatível.
    """
    rows = [dict(e) for e in events]
    by_id = {
        str(e.get("event_id") or ""): e
        for e in rows
        if str(e.get("event_id") or "").strip()
    }
    problems: list[dict[str, Any]] = []
    proposals_exist = any(str(e.get("action") or "") == "propose" for e in rows)

    for index, event in enumerate(rows, start=1):
        signal = str(event.get("signal") or "")
        action = str(event.get("action") or "")
        parent_id = str(event.get("parent_event_id") or "").strip()

        if signal not in CRITICAL_SIGNALS or action not in {"confirm", "revoke"}:
            continue

        # Compatibilidade: logs anteriores à implantação do workflow não são invalidados.
        if not parent_id:
            if proposals_exist:
                problems.append({
                    "line": index,
                    "event_id": event.get("event_id") or "",
                    "error": "sinal crítico sem parent_event_id no fluxo governado",
                })
            continue

        parent = by_id.get(parent_id)
        if not parent:
            problems.append({
                "line": index,
                "event_id": event.get("event_id") or "",
                "error": f"parent_event_id inexistente: {parent_id}",
            })
            continue

        if str(parent.get("id_snisb") or "") != str(event.get("id_snisb") or ""):
            problems.append({
                "line": index,
                "event_id": event.get("event_id") or "",
                "error": "parent_event_id pertence a outra barragem",
            })
        if str(parent.get("signal") or "") != signal:
            problems.append({
                "line": index,
                "event_id": event.get("event_id") or "",
                "error": "parent_event_id pertence a outro sinal",
            })

        if action == "confirm":
            if str(parent.get("action") or "") != "propose":
                problems.append({
                    "line": index,
                    "event_id": event.get("event_id") or "",
                    "error": "confirmação crítica deve referenciar uma proposta",
                })
            if str(parent.get("value") or "") != str(event.get("value") or ""):
                problems.append({
                    "line": index,
                    "event_id": event.get("event_id") or "",
                    "error": "valor confirmado diverge da proposta",
                })
            proposer = str(parent.get("confirmed_by") or "").strip().casefold()
            confirmer = str(event.get("confirmed_by") or "").strip().casefold()
            if proposer and confirmer and proposer == confirmer:
                problems.append({
                    "line": index,
                    "event_id": event.get("event_id") or "",
                    "error": "dupla confirmação exige pessoas distintas",
                })

        if action == "revoke":
            if str(parent.get("action") or "") != "confirm":
                problems.append({
                    "line": index,
                    "event_id": event.get("event_id") or "",
                    "error": "revogação crítica deve referenciar a confirmação ativa",
                })

    return problems


def pending_proposals(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retorna propostas ainda sem confirmação/revogação filha."""
    rows = [dict(e) for e in events]
    resolved_parent_ids = {
        str(e.get("parent_event_id") or "").strip()
        for e in rows
        if str(e.get("action") or "") in {"confirm", "revoke"}
        and str(e.get("parent_event_id") or "").strip()
    }
    pending = [
        e for e in rows
        if str(e.get("action") or "") == "propose"
        and str(e.get("event_id") or "").strip() not in resolved_parent_ids
    ]
    return sorted(
        pending,
        key=lambda e: (
            str(e.get("recorded_at") or ""),
            str(e.get("event_id") or ""),
        ),
    )
