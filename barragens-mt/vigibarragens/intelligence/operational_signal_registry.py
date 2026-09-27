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

ACTIONS = {"confirm", "revoke"}


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
    return OperationalSignalEvent(**base, event_sha256=canonical_hash(base))


def materialize_latest(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Retorna id_snisb -> sinal -> último evento por recorded_at/event_id."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        bid = str(event.get("id_snisb") or "").strip()
        signal = str(event.get("signal") or "").strip()
        if not bid or signal not in SIGNALS:
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
