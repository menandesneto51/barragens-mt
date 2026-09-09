"""IPAPD proxy — Índice de Pressão Assistencial Pós-Desastre (§5.5.5).

Usa sinais da Simulação e, quando houver, ficha rápida exportada.
Termos sem dado ficam lacuna (não entram como zero falso).
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
    ficha_termos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    termos: dict[str, float | None] = {
        "O": None,
        "A": None,
        "P": None,
        "E": None,
        "C": None,
        "S": None,
    }
    detalhe: dict[str, str] = {}
    ft = ficha_termos or {}

    if taxa_ocupacao_pct is not None:
        try:
            taxa = float(taxa_ocupacao_pct) / 100.0
            termos["O"] = round(_limitar((taxa - 0.70) / 0.30), 3)
            detalhe["O"] = f"ocupação {taxa_ocupacao_pct:.1f}%"
        except (TypeError, ValueError):
            detalhe["O"] = "lacuna"
    else:
        detalhe["O"] = "lacuna — sem IndicaSUS"

    # A — aumento de atendimentos (ficha)
    obs = ft.get("atendimentos_observados")
    esp = ft.get("atendimentos_esperados")
    if obs is not None and esp and float(esp) > 0:
        termos["A"] = round(_limitar((float(obs) / float(esp) - 1.0) / 1.0), 3)
        detalhe["A"] = (
            f"ficha: {obs:.0f} obs / {esp:.0f} esp "
            f"({ft.get('fonte_ficha')})"
        )
    else:
        detalhe["A"] = "lacuna — importe ficha rápida (atendimentos) ou linha de base"

    # P — profissionais (ficha)
    frac_p = ft.get("fracao_profissionais_presentes")
    if frac_p is not None:
        termos["P"] = round(_limitar(1.0 - float(frac_p)), 3)
        detalhe["P"] = f"ficha: {100*float(frac_p):.0f}% da escala presente"
    else:
        detalhe["P"] = "lacuna — ficha rápida (prof_disp / prof_escala)"

    # C — autonomia crítica (ficha)
    aut_h = ft.get("autonomia_min_horas")
    if aut_h is not None:
        termos["C"] = round(_limitar(1.0 - (float(aut_h) / 72.0)), 3)
        detalhe["C"] = f"ficha: menor autonomia {float(aut_h):.1f} h"
    else:
        detalhe["C"] = "lacuna — ficha rápida (aut_energia/água/O₂)"

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
                detalhe["E"] = f"{pessoas_isoladas} isoladas / {int(pop)} expostas"
        except (TypeError, ValueError):
            detalhe["E"] = "lacuna"
    else:
        if den_us > 0 or (pop_exposta and float(pop_exposta or 0) > 0):
            termos["E"] = 0.0
            detalhe["E"] = "sem US/pessoas isoladas na geometria ativa"
        else:
            detalhe["E"] = "lacuna — sem isolamento detectado"

    # S — serviços
    frac_us = ft.get("fracao_us_interrompidas")
    if frac_us is not None:
        termos["S"] = round(_limitar(float(frac_us)), 3)
        detalhe["S"] = f"ficha: {100*float(frac_us):.0f}% US fechadas/danificadas"
    elif n_servicos_essenciais_eixo > 0:
        termos["S"] = round(
            _limitar(n_servicos_essenciais_mancha / n_servicos_essenciais_eixo), 3
        )
        detalhe["S"] = (
            f"{n_servicos_essenciais_mancha} essenciais na mancha / "
            f"{n_servicos_essenciais_eixo} no eixo"
        )
    else:
        detalhe["S"] = "lacuna — sem ativos essenciais / ficha"

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
