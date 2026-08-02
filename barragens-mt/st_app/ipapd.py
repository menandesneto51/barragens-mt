"""IPAPD proxy — Índice de Pressão Assistencial Pós-Desastre (§5.5.5).

Usa sinais já disponíveis na Simulação. Termos sem dado ficam como lacuna
(não entram como zero falso). Escala e pesos: proposta a validar.
"""

from __future__ import annotations

from typing import Any


PESOS = {
    "O": 0.25,
    "A": 0.20,
    "P": 0.15,
    "E": 0.15,
    "C": 0.15,
    "S": 0.10,
}


def _limitar(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def _rotulo(ipapd: float) -> str:
    if ipapd < 0.25:
        return "operação normal"
    if ipapd < 0.50:
        return "pressão moderada"
    if ipapd < 0.75:
        return "pressão alta"
    return "saturação"


def calcular_ipapd_proxy(
    *,
    taxa_ocupacao_pct: float | None = None,
    n_us_atingidas: int = 0,
    n_us_isoladas: int = 0,
    pessoas_isoladas: int = 0,
    pop_exposta: float | int | None = None,
    n_servicos_essenciais_mancha: int = 0,
    n_servicos_essenciais_eixo: int = 0,
) -> dict[str, Any]:
    """
    Termos preenchíveis sem ficha rápida / DW completo:
      O — taxa ocupação IndicaSUS (se houver)
      E — US isoladas / (atingidas+isoladas) ou pessoas isoladas / pop exposta
      S — ativos essenciais na mancha / total no eixo (proxy de interrupção territorial)
    A, P, C — lacuna até ficha rápida / escala / autonomia.
    """
    termos: dict[str, float | None] = {
        "O": None,
        "A": None,
        "P": None,
        "E": None,
        "C": None,
        "S": None,
    }
    detalhe: dict[str, str] = {}

    if taxa_ocupacao_pct is not None:
        try:
            taxa = float(taxa_ocupacao_pct) / 100.0
            termos["O"] = round(_limitar((taxa - 0.70) / 0.30), 3)
            detalhe["O"] = f"ocupação {taxa_ocupacao_pct:.1f}%"
        except (TypeError, ValueError):
            detalhe["O"] = "lacuna"
    else:
        detalhe["O"] = "lacuna — sem IndicaSUS"

    detalhe["A"] = "lacuna — requer linha de base de atendimentos"
    detalhe["P"] = "lacuna — requer escala/ficha rápida"
    detalhe["C"] = "lacuna — requer autonomia energia/água/oxigênio"

    # E — perda de acesso
    den_us = n_us_atingidas + n_us_isoladas
    if den_us > 0 and n_us_isoladas > 0:
        termos["E"] = round(_limitar(n_us_isoladas / den_us), 3)
        detalhe["E"] = f"{n_us_isoladas} US isoladas / {den_us} sob pressão"
    elif pop_exposta and pessoas_isoladas > 0:
        try:
            pop = float(pop_exposta)
            if pop > 0:
                termos["E"] = round(_limitar(pessoas_isoladas / pop), 3)
                detalhe["E"] = f"{pessoas_isoladas} pessoas isoladas / {int(pop)} expostas"
        except (TypeError, ValueError):
            detalhe["E"] = "lacuna"
    else:
        detalhe["E"] = "lacuna — sem isolamento detectado ou sem pop. de referência"
        if den_us > 0 or (pop_exposta and float(pop_exposta) > 0):
            termos["E"] = 0.0
            detalhe["E"] = "sem US/pessoas isoladas na geometria ativa"

    # S — interrupção territorial de serviços essenciais (proxy)
    if n_servicos_essenciais_eixo > 0:
        termos["S"] = round(
            _limitar(n_servicos_essenciais_mancha / n_servicos_essenciais_eixo), 3
        )
        detalhe["S"] = (
            f"{n_servicos_essenciais_mancha} essenciais na mancha / "
            f"{n_servicos_essenciais_eixo} no eixo"
        )
    else:
        detalhe["S"] = "lacuna — sem base de ativos essenciais"

    presentes = {k: v for k, v in termos.items() if v is not None}
    if not presentes:
        return {
            "ok": False,
            "ipapd": None,
            "rotulo": "indisponível",
            "termos": termos,
            "detalhe": detalhe,
            "completude": 0.0,
            "pesos_usados": 0.0,
            "fonte": "IPAPD proxy (§5.5.5) — sem termos preenchíveis",
        }

    peso_ok = sum(PESOS[k] for k in presentes)
    soma = sum(PESOS[k] * float(presentes[k]) for k in presentes)
    # renormaliza pelos pesos disponíveis (não pune com zero falso)
    ipapd = round(soma / peso_ok, 3) if peso_ok > 0 else None
    completude = round(peso_ok / sum(PESOS.values()), 3)

    return {
        "ok": True,
        "ipapd": ipapd,
        "rotulo": _rotulo(float(ipapd)) if ipapd is not None else "indisponível",
        "termos": termos,
        "detalhe": detalhe,
        "completude": completude,
        "pesos_usados": round(peso_ok, 3),
        "fonte": (
            "IPAPD proxy — pesos §5.5.5 renormalizados pelos termos disponíveis; "
            "proposta a validar"
        ),
    }
