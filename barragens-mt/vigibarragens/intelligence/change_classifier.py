"""Classificação operacional de eventos de mudança da v2.2.

A criticidade do evento descreve a urgência de revisão da mudança; não é nível IDAP.
"""
from __future__ import annotations

from typing import Any

LEVEL_ORDER = {"Verde": 0, "Amarelo": 1, "Laranja": 2, "Vermelho": 3, "Roxo": 4}
RISK_ORDER = {"Baixo": 0, "Baixa": 0, "Médio": 1, "Média": 1, "Alto": 2, "Alta": 2}
SEVERITY_ORDER = {"informativa": 0, "atencao": 1, "critica": 2, "emergencial": 3}


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ".")) if str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _set(value: Any) -> set[str]:
    return {x.strip() for x in str(value or "").split("|") if x.strip()}


def classify_change(event: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta criticidade, direção e razão sem alterar o evento original."""
    field = str(event.get("field") or "")
    before, after = event.get("previous"), event.get("current")
    event_type = str(event.get("event_type") or "FIELD_CHANGED")
    severity, direction, reason = "informativa", "neutra", "alteração cadastral/operacional"

    if event_type == "BARRAGEM_NOVA":
        severity, direction, reason = "atencao", "nova", "nova barragem requer avaliação inicial"
    elif event_type == "BARRAGEM_REMOVIDA":
        severity, direction, reason = "atencao", "removida", "remoção do inventário requer validação de origem"
    elif field == "nivel":
        b, a = LEVEL_ORDER.get(str(before)), LEVEL_ORDER.get(str(after))
        if b is not None and a is not None and a > b:
            direction = "piora"
            severity = "emergencial" if a >= LEVEL_ORDER["Vermelho"] else "critica" if a >= LEVEL_ORDER["Laranja"] else "atencao"
            reason = f"nível operacional agravou de {before} para {after}"
        elif b is not None and a is not None and a < b:
            direction, reason = "melhora", f"nível operacional reduziu de {before} para {after}"
    elif field in {"categoria_risco", "dano_potencial_associado"}:
        b, a = RISK_ORDER.get(str(before)), RISK_ORDER.get(str(after))
        if b is not None and a is not None and a > b:
            severity, direction, reason = "critica", "piora", f"{field} agravou de {before} para {after}"
        elif b is not None and a is not None and a < b:
            direction, reason = "melhora", f"{field} reduziu de {before} para {after}"
    elif field in {"alertavel", "contatos_validados_90d"}:
        if str(before).lower() in {"sim", "true", "1"} and str(after).lower() in {"não", "nao", "false", "0"}:
            severity, direction, reason = "critica", "piora", "perda de capacidade de alertamento/contato validado"
        elif str(after).lower() in {"sim", "true", "1"}:
            direction, reason = "melhora", "capacidade de alertamento/contato restabelecida"
    elif field == "confiabilidade":
        order = {"insuficiente": 0, "parcial": 1, "suficiente": 2}
        b, a = order.get(str(before).lower()), order.get(str(after).lower())
        if b is not None and a is not None and a < b:
            severity, direction, reason = "atencao", "piora", "confiabilidade do cálculo diminuiu"
        elif b is not None and a is not None and a > b:
            direction, reason = "melhora", "confiabilidade do cálculo aumentou"
    elif field == "completude":
        b, a = _num(before), _num(after)
        if b is not None and a is not None and a < b:
            severity, direction, reason = "atencao", "piora", "completude dos dados diminuiu"
        elif b is not None and a is not None and a > b:
            direction, reason = "melhora", "completude dos dados aumentou"
    elif field == "idap":
        b, a = _num(before), _num(after)
        if b is not None and a is not None and a > b:
            severity, direction, reason = "atencao", "piora", "IDAP aumentou dentro da comparação histórica"
        elif b is not None and a is not None and a < b:
            direction, reason = "melhora", "IDAP diminuiu dentro da comparação histórica"
    elif field == "municipios_potencialmente_afetados":
        added, removed = _set(after) - _set(before), _set(before) - _set(after)
        if added:
            severity, direction = "critica", "expansao_territorial"
            reason = f"expansão do território potencialmente afetado: +{len(added)} município(s)"
        elif removed:
            direction, reason = "reducao_territorial", f"redução do território potencialmente afetado: -{len(removed)} município(s)"

    return {**event, "criticidade_evento": severity, "direcao": direction, "razao_classificacao": reason}


def sort_changes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=lambda e: (-SEVERITY_ORDER.get(str(e.get("criticidade_evento")), 0), str(e.get("id_snisb")), str(e.get("field"))))
