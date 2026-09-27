from datetime import datetime, timezone

from vigibarragens.intelligence.operational_observability import (
    age_hours,
    enrich_pending,
    governance_summary,
    governance_actions,
)


NOW = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)


def test_age_hours_uses_recorded_timestamp():
    assert age_hours("2026-09-27T12:00:00+00:00", now=NOW) == 4.0


def test_pending_without_sla_policy_is_not_labeled_breach():
    rows = enrich_pending(
        [{"recorded_at": "2026-09-27T12:00:00+00:00"}],
        now=NOW,
        sla_hours=None,
    )
    assert rows[0]["idade_aguardando_h"] == 4.0
    assert rows[0]["sla_status"] == "sem_politica"


def test_configured_sla_marks_only_actual_breach():
    rows = enrich_pending(
        [
            {"recorded_at": "2026-09-27T15:00:00+00:00"},
            {"recorded_at": "2026-09-27T12:00:00+00:00"},
        ],
        now=NOW,
        sla_hours=2.0,
    )
    assert rows[0]["sla_status"] == "dentro_sla"
    assert rows[1]["sla_status"] == "fora_sla"


def test_governance_summary_does_not_invent_sla():
    summary = governance_summary(
        events=[
            {"action": "propose"},
            {"action": "confirm"},
            {"action": "revoke"},
        ],
        pending=[{"recorded_at": "2026-09-27T12:00:00+00:00"}],
        latest_state={
            "1": {
                "a": {"action": "confirm"},
                "b": {"action": "revoke"},
            }
        },
        integrity_status="ok",
        integrity_problems=0,
        now=NOW,
        sla_hours=None,
    )
    assert summary["propostas_pendentes"] == 1
    assert summary["sinais_ativos"] == 1
    assert summary["sinais_revogados"] == 1
    assert summary["sla_politica"] == "nao_configurada"
    assert summary["pendencias_fora_sla"] == ""
    assert summary["integridade_status"] == "ok"


def test_governance_actions_separate_integrity_and_confirmation_work():
    actions = governance_actions(
        pending_rows=[
            {
                "id_snisb": "1",
                "signal": "rompimento_confirmado",
                "event_id": "prop-1",
                "idade_aguardando_h": 5.0,
                "sla_status": "fora_sla",
            }
        ],
        integrity_status="failure",
        integrity_problems=2,
    )
    assert actions[0]["tipo_acao"] == "tratar_integridade_ledger"
    assert actions[1]["tipo_acao"] == "confirmacao_pendente"
    assert "segunda confirmação" in actions[1]["acao_requerida"]
