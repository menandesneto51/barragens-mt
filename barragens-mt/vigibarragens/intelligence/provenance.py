"""Proveniência e freshness semântico da v2.2.

Política de freshness é de governança de dados, não regra de risco:
<=24 h atual; >24–72 h atenção; >72 h vencido; sem referência = desconhecido.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any

FRESHNESS_POLICY_VERSION = "freshness-v1-24h-72h"


def parse_reference(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def freshness(reference: Any, *, now: datetime | None = None) -> dict[str, Any]:
    ref = parse_reference(reference)
    if ref is None:
        return {"idade_h": None, "estado": "desconhecido", "politica": FRESHNESS_POLICY_VERSION}
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    hours = max(0.0, (current - ref).total_seconds() / 3600.0)
    state = "atual" if hours <= 24 else "atencao" if hours <= 72 else "vencido"
    return {"idade_h": round(hours, 1), "estado": state, "politica": FRESHNESS_POLICY_VERSION}


def evidence_state(idap_confidence: Any, freshness_state: str) -> str:
    """Qualifica a evidência sem produzir score e sem modificar o risco."""
    confidence = str(idap_confidence or "").strip().lower()
    if confidence == "insuficiente":
        return "insuficiente"
    if confidence == "suficiente" and freshness_state == "atual":
        return "adequada"
    return "degradada"


def build_lineage_record(idap: dict[str, Any], hydro: dict[str, Any] | None, *, now: datetime | None = None) -> dict[str, Any]:
    hydro = hydro or {}
    f = freshness(hydro.get("data_referencia"), now=now)
    sources = [hydro.get(k) for k in ("fonte_precip", "fonte_previsao", "fonte_solo", "fonte_hidro", "fonte_glofas")]
    sources = sorted({str(x).strip() for x in sources if str(x or "").strip()})
    proxies = []
    spatial = str(hydro.get("aproximacao_espacial") or "")
    if spatial and spatial != "":
        if spatial in {"municipio_sede", "sede_mais_montante_max"}:
            proxies.append(f"hidro:{spatial}")
    affected = str(idap.get("municipios_potencialmente_afetados") or "")
    if affected:
        proxies.append("territorio:otto_provisorio")
    return {
        "id_snisb": idap.get("id_snisb"),
        "nome": idap.get("nome"),
        "municipio_sede": idap.get("municipio_sede"),
        "nivel": idap.get("nivel"),
        "confiabilidade_idap": idap.get("confiabilidade"),
        "completude_idap": idap.get("completude"),
        "data_referencia_hidro": hydro.get("data_referencia") or "",
        "idade_h_hidro": f["idade_h"],
        "freshness_hidro": f["estado"],
        "fontes_hidro": "|".join(sources),
        "aproximacao_espacial_hidro": spatial,
        "proxies": "|".join(proxies),
        "politica_freshness": f["politica"],
        "lineage_status": "documentado" if sources else "parcial",
        "estado_evidencia": evidence_state(idap.get("confiabilidade"), f["estado"]),
    }
