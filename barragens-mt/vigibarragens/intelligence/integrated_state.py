"""Estado integrado v2.2 sem criar um segundo escore de risco.

O nível oficial permanece o resultado determinístico do IDAP + regras de sobreposição.
Esta camada organiza explicabilidade, tendência, qualidade e proxies para consumo operacional.
"""
from __future__ import annotations

from typing import Any

DIMENSION_CEILINGS = {"A": 30.0, "B": 30.0, "C": 25.0, "D": 15.0}
LEVEL_ORDER = {"Verde": 0, "Amarelo": 1, "Laranja": 2, "Vermelho": 3, "Roxo": 4}


def _number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _percent(points: Any, ceiling: float) -> float | None:
    value = _number(points)
    return None if value is None else round(100.0 * value / ceiling, 1)


def classify_trend(current_level: str, previous_level: str | None, current_idap: Any, previous_idap: Any) -> str:
    """Classifica apenas a direção temporal; não altera o nível operacional."""
    if not previous_level:
        return "sem_historico"
    cur_rank = LEVEL_ORDER.get(current_level)
    prev_rank = LEVEL_ORDER.get(previous_level)
    if cur_rank is not None and prev_rank is not None:
        if cur_rank > prev_rank:
            return "agravamento_nivel"
        if cur_rank < prev_rank:
            return "melhora_nivel"
    cur = _number(current_idap)
    prev = _number(previous_idap)
    if cur is None or prev is None:
        return "estavel_sem_comparacao_idap"
    if cur > prev:
        return "aumento_idap_mesmo_nivel"
    if cur < prev:
        return "reducao_idap_mesmo_nivel"
    return "estavel"


def build_intelligence_state(current: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = previous or {}
    dimension_pct = {
        code: _percent(current.get(f"pontos_{code.lower()}"), ceiling)
        for code, ceiling in DIMENSION_CEILINGS.items()
    }
    available = {k: v for k, v in dimension_pct.items() if v is not None}
    dominant = max(available, key=available.get) if available else None
    level = str(current.get("nivel") or "")
    prev_level = str(previous.get("nivel") or "") or None
    trend = classify_trend(level, prev_level, current.get("idap"), previous.get("idap"))
    affected = str(current.get("municipios_potencialmente_afetados") or "")
    method = str(current.get("metodo_estimativa_populacao") or "")
    proxy_flags = []
    if affected:
        proxy_flags.append("jusante_otto_provisorio")
    if "ibge_soma_municipios" in method:
        proxy_flags.append("populacao_teto_municipal")
    if str(current.get("municipios_posicao_indeterminada") or ""):
        proxy_flags.append("posicao_territorial_indeterminada")

    cur_idap = _number(current.get("idap"))
    prev_idap = _number(previous.get("idap"))
    delta = round(cur_idap - prev_idap, 1) if cur_idap is not None and prev_idap is not None else None

    return {
        "id_snisb": current.get("id_snisb"),
        "nome": current.get("nome"),
        "municipio_sede": current.get("municipio_sede"),
        "nivel_operacional": level,
        "idap": cur_idap,
        "idap_anterior": prev_idap,
        "delta_idap": delta,
        "tendencia": trend,
        "dimensao_dominante": dominant,
        "pressao_hidro_pct": dimension_pct["A"],
        "condicao_estrutura_pct": dimension_pct["B"],
        "exposicao_pct": dimension_pct["C"],
        "deficit_resposta_pct": dimension_pct["D"],
        "completude": _number(current.get("completude")),
        "confiabilidade": current.get("confiabilidade"),
        "idap_projetado": _number(current.get("idap_projetado")),
        "alertavel": current.get("alertavel"),
        "contatos_validados_90d": current.get("contatos_validados_90d"),
        "municipios_potencialmente_afetados": affected,
        "n_municipios_afetados": current.get("n_municipios_afetados"),
        "regras_disparadas": current.get("regras_disparadas"),
        "lacunas": current.get("lacunas"),
        "proxy_flags": "|".join(proxy_flags),
        "versao_pesos": current.get("versao_pesos"),
        "instante": current.get("instante"),
    }
