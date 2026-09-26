"""Lineage das regras determinísticas R01–R12.

A função não decide nem reavalia regra alguma. Recebe apenas regras já disparadas pelo
motor oficial e descreve quais evidências sustentam cada gatilho.
"""
from __future__ import annotations

from typing import Any, Iterable


RULE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "R01": ("B2",),
    "R02": ("SIGNAL:rompimento_confirmado",),
    "R03": ("SIGNAL:perda_subita_de_nivel", "B4"),
    "R04": ("A1", "A2", "B4"),
    "R05": ("SIGNAL:evacuacao_determinada",),
    "R06": ("SIGNAL:sensores_criticos_em_falha", "DIM:B:completude"),
    "R07": ("SIGNAL:mancha_atinge_unidade_estrategica",),
    "R08": ("SIGNAL:mancha_atinge_captacao",),
    "R09": ("SIGNAL:municipios_zas_sem_confirmacao",),
    "R10": ("SIGNAL:alerta_cemaden_hidrologico", "SIGNAL:alerta_ana_acima_atencao"),
    "R11": ("SIGNAL:nivel_alerta_integrado_sis",),
    "R12": ("A3", "SIGNAL:chuva_prevista_extrema"),
}


def _indicator_row(
    code: str,
    indicator_evidence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = indicator_evidence.get(code) or {}
    return {
        "evidencia_codigo": code,
        "evidencia_tipo": "indicador_idap",
        "evidencia_valor": row.get("valor", ""),
        "produto_observacional": row.get("produto_observacional", ""),
        "campo_observacional": row.get("campo_observacional", ""),
        "fonte_observacional": row.get("fonte_observacional", ""),
        "referencia_temporal": row.get("referencia_temporal", ""),
        "tipo_evidencia": row.get("tipo_evidencia", "ausente"),
        "metodo_proxy": row.get("metodo_proxy", ""),
        "run_id": row.get("run_id", ""),
        "artifact_path": row.get("artifact_path", ""),
        "artifact_sha256": row.get("artifact_sha256", ""),
        "artifact_materialized_at": row.get("artifact_materialized_at", ""),
    }


def _signal_row(
    signal: str,
    *,
    hydro_lineage: dict[str, Any],
    signal_values: dict[str, Any],
) -> dict[str, Any]:
    hydro_signals = {
        "alerta_cemaden_hidrologico",
        "alerta_ana_acima_atencao",
        "nivel_alerta_integrado_sis",
        "chuva_prevista_extrema",
    }
    if signal in hydro_signals:
        return {
            "evidencia_codigo": f"SIGNAL:{signal}",
            "evidencia_tipo": "sinal_operacional",
            "evidencia_valor": signal_values.get(signal, ""),
            "produto_observacional": hydro_lineage.get("produto_observacional", ""),
            "campo_observacional": signal,
            "fonte_observacional": hydro_lineage.get("fonte_observacional", ""),
            "referencia_temporal": hydro_lineage.get("referencia_temporal", ""),
            "tipo_evidencia": hydro_lineage.get("tipo_evidencia", "derivada"),
            "metodo_proxy": hydro_lineage.get("metodo_proxy", ""),
            "run_id": hydro_lineage.get("run_id", ""),
            "artifact_path": hydro_lineage.get("artifact_path", ""),
            "artifact_sha256": hydro_lineage.get("artifact_sha256", ""),
            "artifact_materialized_at": hydro_lineage.get("artifact_materialized_at", ""),
        }
    return {
        "evidencia_codigo": f"SIGNAL:{signal}",
        "evidencia_tipo": "sinal_operacional",
        "evidencia_valor": signal_values.get(signal, ""),
        "produto_observacional": "",
        "campo_observacional": signal,
        "fonte_observacional": "",
        "referencia_temporal": "",
        "tipo_evidencia": "sinal_sem_fonte_materializada",
        "metodo_proxy": "",
        "run_id": "",
        "artifact_path": "",
        "artifact_sha256": "",
        "artifact_materialized_at": "",
    }


def build_rule_lineage(
    *,
    fired_rules: Iterable[Any],
    indicator_evidence: dict[str, dict[str, Any]],
    signal_values: dict[str, Any],
    hydro_lineage: dict[str, Any],
    dimension_b_completeness: float,
) -> list[dict[str, Any]]:
    """Expande cada regra disparada em uma ou mais linhas de evidência."""
    out: list[dict[str, Any]] = []
    for fired in fired_rules:
        code = str(fired.codigo)
        for evidence in RULE_EVIDENCE.get(code, ()):
            if evidence.startswith("SIGNAL:"):
                base = _signal_row(
                    evidence.split(":", 1)[1],
                    hydro_lineage=hydro_lineage,
                    signal_values=signal_values,
                )
            elif evidence == "DIM:B:completude":
                base = {
                    "evidencia_codigo": evidence,
                    "evidencia_tipo": "metrica_calculo",
                    "evidencia_valor": dimension_b_completeness,
                    "produto_observacional": "idap_evidencias_indicadores_mt.csv",
                    "campo_observacional": "dimensao=B; ausente",
                    "fonte_observacional": "motor IDAP",
                    "referencia_temporal": "",
                    "tipo_evidencia": "derivada_do_calculo",
                    "metodo_proxy": "",
                    "run_id": "",
                    "artifact_path": "",
                    "artifact_sha256": "",
                    "artifact_materialized_at": "",
                }
            else:
                base = _indicator_row(evidence, indicator_evidence)
            out.append({
                "regra_codigo": code,
                "regra_nome": fired.nome,
                "nivel_minimo": fired.nivel_minimo.rotulo if fired.nivel_minimo else "",
                "acao": fired.acao,
                **base,
            })
    return out
