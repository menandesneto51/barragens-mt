"""Estimativa de demanda sanitária a partir da população exposta (roadmap 4.3).

Parâmetros são **propostas a validar** com a SES-MT (mesma lógica do D6 em
`docs/03-idap.md` §3.6.7). Não substituem dimensionamento oficial de resposta.
"""

from __future__ import annotations

import math
from typing import Any


# Propostas a validar — documentadas na UI/caption.
FRACAO_INTERNACAO = 0.02  # D6: 2% da pop. exposta
FRACAO_ATENDIMENTO_72H = 0.08  # urgência/APS nas primeiras 72 h
LITROS_AGUA_PESSOA_DIA = 15.0  # Sphere / emergência humanitária
AMBULANCIAS_POR_10MIL = 1.0  # alinhado ao espírito do D5


def estimar_demanda(
    pop_exposta: float | int | None,
    *,
    leitos_disponiveis: float | int | None = None,
) -> dict[str, Any]:
    """Calcula demanda bruta e, se houver leitos, a razão D6."""
    try:
        pop = float(pop_exposta or 0)
    except (TypeError, ValueError):
        pop = 0.0
    if pop <= 0:
        return {
            "ok": False,
            "pop_exposta": 0,
            "demanda_internacao": 0,
            "demanda_atendimentos_72h": 0,
            "demanda_agua_L_dia": 0,
            "ambulancias_ref": 0,
            "razao_leitos_demanda": None,
            "parametros": {
                "fracao_internacao": FRACAO_INTERNACAO,
                "fracao_atendimento_72h": FRACAO_ATENDIMENTO_72H,
                "litros_agua_pessoa_dia": LITROS_AGUA_PESSOA_DIA,
                "ambulancias_por_10mil": AMBULANCIAS_POR_10MIL,
            },
        }

    intern = int(math.ceil(pop * FRACAO_INTERNACAO))
    atend = int(math.ceil(pop * FRACAO_ATENDIMENTO_72H))
    agua = int(round(pop * LITROS_AGUA_PESSOA_DIA))
    amb = max(1, int(math.ceil(pop / 10_000.0 * AMBULANCIAS_POR_10MIL)))

    razao = None
    if leitos_disponiveis is not None:
        try:
            disp = float(leitos_disponiveis)
            if intern > 0:
                razao = round(disp / intern, 3)
        except (TypeError, ValueError):
            razao = None

    return {
        "ok": True,
        "pop_exposta": int(round(pop)),
        "demanda_internacao": intern,
        "demanda_atendimentos_72h": atend,
        "demanda_agua_L_dia": agua,
        "ambulancias_ref": amb,
        "razao_leitos_demanda": razao,
        "parametros": {
            "fracao_internacao": FRACAO_INTERNACAO,
            "fracao_atendimento_72h": FRACAO_ATENDIMENTO_72H,
            "litros_agua_pessoa_dia": LITROS_AGUA_PESSOA_DIA,
            "ambulancias_por_10mil": AMBULANCIAS_POR_10MIL,
        },
        "nota": (
            "Parâmetros de planejamento (proposta a validar). "
            "Internação = 2% pop. exposta (D6); água = 15 L/pessoa/dia; "
            "atendimentos 72 h = 8% pop.; ambulâncias ref. = 1/10 mil."
        ),
    }
