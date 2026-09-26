from types import SimpleNamespace

from vigibarragens.intelligence.rule_lineage import build_rule_lineage


def fired(code: str, minimum=None):
    return SimpleNamespace(
        codigo=code,
        nome=f"Regra {code}",
        nivel_minimo=minimum,
        acao="acao",
        fundamento="fundamento",
    )


def test_r04_expands_to_rain_and_structural_evidence():
    evidence = {
        "A1": {"valor": "120 mm", "tipo_evidencia": "derivada"},
        "A2": {"valor": "210 mm", "tipo_evidencia": "derivada"},
        "B4": {"valor": "5", "tipo_evidencia": "oficial_cadastral"},
    }
    rows = build_rule_lineage(
        fired_rules=[fired("R04")],
        indicator_evidence=evidence,
        signal_values={},
        hydro_lineage={},
        operational_signal_lineage=None,
        dimension_b_completeness=0.8,
    )
    assert [r["evidencia_codigo"] for r in rows] == ["A1", "A2", "B4"]


def test_r10_uses_hydrometeorological_lineage():
    hydro = {
        "produto_observacional": "hidro_barragens_mt.csv",
        "fonte_observacional": "Cemaden|ANA",
        "referencia_temporal": "2026-09-26T12:00:00",
        "tipo_evidencia": "derivada",
        "run_id": "run-1",
        "artifact_sha256": "abc",
    }
    rows = build_rule_lineage(
        fired_rules=[fired("R10")],
        indicator_evidence={},
        signal_values={
            "alerta_cemaden_hidrologico": True,
            "alerta_ana_acima_atencao": False,
        },
        hydro_lineage=hydro,
        operational_signal_lineage=None,
        dimension_b_completeness=1.0,
    )
    assert len(rows) == 2
    assert all(r["produto_observacional"] == "hidro_barragens_mt.csv" for r in rows)
    assert all(r["run_id"] == "run-1" for r in rows)
    active = {r["evidencia_codigo"]: r["evidencia_ativa"] for r in rows}
    assert active["SIGNAL:alerta_cemaden_hidrologico"] is True
    assert active["SIGNAL:alerta_ana_acima_atencao"] is False


def test_unsourced_operational_signal_is_explicit_not_invented():
    rows = build_rule_lineage(
        fired_rules=[fired("R02")],
        indicator_evidence={},
        signal_values={"rompimento_confirmado": True},
        hydro_lineage={},
        operational_signal_lineage=None,
        dimension_b_completeness=1.0,
    )
    assert rows[0]["tipo_evidencia"] == "sinal_sem_fonte_materializada"
    assert rows[0]["produto_observacional"] == ""


def test_r06_keeps_dimension_completeness_as_calculation_evidence():
    rows = build_rule_lineage(
        fired_rules=[fired("R06")],
        indicator_evidence={},
        signal_values={"sensores_criticos_em_falha": 0},
        hydro_lineage={},
        operational_signal_lineage=None,
        dimension_b_completeness=0.2,
    )
    completeness = next(r for r in rows if r["evidencia_codigo"] == "DIM:B:completude")
    assert completeness["evidencia_valor"] == 0.2
    assert completeness["tipo_evidencia"] == "derivada_do_calculo"


def test_persisted_operational_signal_uses_materialized_source():
    rows = build_rule_lineage(
        fired_rules=[fired("R02")],
        indicator_evidence={},
        signal_values={"rompimento_confirmado": True},
        hydro_lineage={},
        operational_signal_lineage={
            "produto_observacional": "sinais_operacionais_mt.csv",
            "fonte_observacional": "Defesa Civil",
            "referencia_temporal": "2026-09-26T10:00:00",
            "tipo_evidencia": "operacional_persistente",
            "run_id": "run-x",
            "artifact_sha256": "abc",
        },
        dimension_b_completeness=1.0,
    )
    assert rows[0]["tipo_evidencia"] == "operacional_persistente"
    assert rows[0]["produto_observacional"] == "sinais_operacionais_mt.csv"
    assert rows[0]["evidencia_ativa"] is True
