"""IRS proxy — Índice de Recuperação Sanitária (§5.5.7).

Escala 0–1 onde **1 = recuperado**. Dimensões sem dado ficam lacuna
(renormalização pelos termos disponíveis — mesma honestidade do IPAPD).
"""

from __future__ import annotations

from typing import Any

# Pesos iguais 1/11 — proposta a validar (§5.5.7)
DIMENSOES = (
    "aps",
    "hospitalar",
    "agua",
    "rodoviario",
    "equipes",
    "abrigos",
    "agravos",
    "rede_frio",
    "cronicos",
    "saude_mental",
    "ambiental",
)

PESO = 1.0 / len(DIMENSOES)

ROTULOS = {
    "aps": "Restabelecimento da APS",
    "hospitalar": "Funcionamento hospitalar",
    "agua": "Abastecimento de água",
    "rodoviario": "Acesso rodoviário",
    "equipes": "Retorno das equipes",
    "abrigos": "Redução pop. em abrigos",
    "agravos": "Controle dos agravos",
    "rede_frio": "Rede de frio",
    "cronicos": "Continuidade tratamentos",
    "saude_mental": "Saúde mental",
    "ambiental": "Monitoramento ambiental",
}


def _limitar(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def _rotulo_irs(irs: float) -> str:
    if irs >= 0.90:
        return "recuperação avançada (critério de encerramento próximo)"
    if irs >= 0.70:
        return "recuperação em curso"
    if irs >= 0.40:
        return "recuperação parcial"
    return "recuperação inicial / crítica"


def calcular_irs_proxy(
    *,
    ficha_irs: dict[str, Any] | None = None,
    n_us_atingidas: int = 0,
    n_us_isoladas: int = 0,
    n_vias: int = 0,
    n_pontes: int = 0,
    taxa_ocupacao_pct: float | None = None,
    leitos_disponiveis: float | None = None,
    leitos_totais: float | None = None,
) -> dict[str, Any]:
    """Calcula IRS a partir da ficha e sinais da mancha/simulação."""
    ft = ficha_irs or {}
    termos: dict[str, float | None] = {k: None for k in DIMENSOES}
    detalhe: dict[str, str] = {}

    # APS
    if ft.get("fracao_aps_funcionando") is not None:
        termos["aps"] = round(_limitar(float(ft["fracao_aps_funcionando"])), 3)
        detalhe["aps"] = f"ficha: {100*termos['aps']:.0f}% US abertas"
    else:
        detalhe["aps"] = "lacuna — ficha (us_abertas / total)"

    # Hospitalar
    if (
        leitos_totais is not None
        and leitos_disponiveis is not None
        and float(leitos_totais) > 0
    ):
        # proxy fraco: disponibilidade relativa (não é “antes do evento”)
        termos["hospitalar"] = round(
            _limitar(float(leitos_disponiveis) / float(leitos_totais)), 3
        )
        detalhe["hospitalar"] = (
            f"IndicaSUS: {leitos_disponiveis:.0f}/{leitos_totais:.0f} leitos disp."
        )
    elif taxa_ocupacao_pct is not None:
        # ocupação alta → recuperação baixa
        termos["hospitalar"] = round(
            _limitar(1.0 - (float(taxa_ocupacao_pct) / 100.0)), 3
        )
        detalhe["hospitalar"] = f"proxy inverso da ocupação {taxa_ocupacao_pct:.1f}%"
    elif ft.get("fracao_leitos_operacionais") is not None:
        termos["hospitalar"] = round(
            _limitar(float(ft["fracao_leitos_operacionais"])), 3
        )
        detalhe["hospitalar"] = "ficha: leitos operacionais"
    else:
        detalhe["hospitalar"] = "lacuna — IndicaSUS / ficha leitos"

    # Água
    if ft.get("fracao_agua_ok") is not None:
        termos["agua"] = round(_limitar(float(ft["fracao_agua_ok"])), 3)
        detalhe["agua"] = "ficha: abastecimento restabelecido"
    elif ft.get("autonomia_agua_horas") is not None:
        termos["agua"] = round(
            _limitar(float(ft["autonomia_agua_horas"]) / 72.0), 3
        )
        detalhe["agua"] = f"proxy autonomia água {ft['autonomia_agua_horas']} h"
    else:
        detalhe["agua"] = "lacuna — ficha / concessionária"

    # Rodoviário
    afetadas = int(n_vias or 0) + int(n_pontes or 0)
    if afetadas > 0:
        # sem dado de “já liberadas”: assume ainda interrompidas → 0
        termos["rodoviario"] = 0.0
        detalhe["rodoviario"] = (
            f"{afetadas} vias/pontes na mancha ainda sem sinal de liberação"
        )
    elif ft.get("fracao_vias_ok") is not None:
        termos["rodoviario"] = round(_limitar(float(ft["fracao_vias_ok"])), 3)
        detalhe["rodoviario"] = "ficha: vias transitáveis"
    else:
        if n_us_atingidas or n_us_isoladas:
            termos["rodoviario"] = 1.0
            detalhe["rodoviario"] = "sem vias/pontes marcadas na geometria ativa"
        else:
            detalhe["rodoviario"] = "lacuna — sem geometria de vias"

    # Equipes
    if ft.get("fracao_profissionais_presentes") is not None:
        termos["equipes"] = round(
            _limitar(float(ft["fracao_profissionais_presentes"])), 3
        )
        detalhe["equipes"] = (
            f"ficha: {100*float(ft['fracao_profissionais_presentes']):.0f}% escala"
        )
    else:
        detalhe["equipes"] = "lacuna — ficha prof_disp/prof_escala"

    # Abrigos
    if ft.get("fracao_saida_abrigos") is not None:
        termos["abrigos"] = round(_limitar(float(ft["fracao_saida_abrigos"])), 3)
        detalhe["abrigos"] = "ficha: 1 − (ainda abrigados / pico)"
    else:
        detalhe["abrigos"] = "lacuna — ficha abrigados_atual / abrigados_pico"

    # Agravos (proxy fraco a partir de carga sindrômica vs esperado)
    if ft.get("controle_agravos") is not None:
        termos["agravos"] = round(_limitar(float(ft["controle_agravos"])), 3)
        detalhe["agravos"] = "ficha/VIGIPÓS: síndromes sob controle"
    else:
        detalhe["agravos"] = "lacuna — canal endêmico O/E (VIGIPÓS)"

    # Rede de frio
    if ft.get("fracao_rede_frio") is not None:
        termos["rede_frio"] = round(_limitar(float(ft["fracao_rede_frio"])), 3)
        detalhe["rede_frio"] = "ficha: rede de frio operante"
    else:
        detalhe["rede_frio"] = "lacuna — ficha / imunização"

    # Crônicos
    if ft.get("fracao_cronicos_ok") is not None:
        termos["cronicos"] = round(_limitar(float(ft["fracao_cronicos_ok"])), 3)
        detalhe["cronicos"] = "ficha: tratamentos retomados"
    else:
        detalhe["cronicos"] = "lacuna — ficha / APS"

    # Saúde mental
    if ft.get("fracao_saude_mental") is not None:
        termos["saude_mental"] = round(
            _limitar(float(ft["fracao_saude_mental"])), 3
        )
        detalhe["saude_mental"] = "ficha: acompanhamento / necessidade"
    else:
        detalhe["saude_mental"] = "lacuna — ficha"

    # Ambiental
    if ft.get("fracao_ambiental_ok") is not None:
        termos["ambiental"] = round(_limitar(float(ft["fracao_ambiental_ok"])), 3)
        detalhe["ambiental"] = "ficha: pontos dentro do padrão"
    else:
        detalhe["ambiental"] = "lacuna — monitoramento ambiental"

    presentes = {k: v for k, v in termos.items() if v is not None}
    if not presentes:
        return {
            "ok": False,
            "irs": None,
            "rotulo": "indisponível",
            "termos": termos,
            "detalhe": detalhe,
            "completude": 0.0,
            "n_dimensoes": 0,
            "fonte": "IRS proxy (§5.5.7) — sem dimensões preenchíveis",
            "criterio_encerramento": "IRS ≥ 0,90 por 4 semanas (proposta a validar)",
        }

    irs = round(sum(presentes.values()) / len(presentes), 3)
    completude = round(len(presentes) / len(DIMENSOES), 3)

    return {
        "ok": True,
        "irs": irs,
        "rotulo": _rotulo_irs(irs),
        "termos": termos,
        "detalhe": detalhe,
        "completude": completude,
        "n_dimensoes": len(presentes),
        "pesos_iguais": True,
        "fonte": (
            "IRS proxy — média das dimensões disponíveis (§5.5.7); "
            "1 = recuperado; proposta a validar"
        ),
        "criterio_encerramento": "IRS ≥ 0,90 por 4 semanas (proposta a validar)",
    }
