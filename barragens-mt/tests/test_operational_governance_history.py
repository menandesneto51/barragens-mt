from vigibarragens.intelligence.operational_governance_history import (
    daily_dimensions,
    daily_history,
    proposal_lifecycle,
)


def sample_events():
    return [
        {
            "event_id": "p1",
            "id_snisb": "1",
            "signal": "rompimento_confirmado",
            "action": "propose",
            "value": "sim",
            "source_type": "defesa_civil",
            "source_name": "Defesa Civil",
            "confirmed_by": "A",
            "recorded_at": "2026-09-27T12:00:00+00:00",
            "observed_at": "2026-09-27T11:30:00+00:00",
        },
        {
            "event_id": "c1",
            "id_snisb": "1",
            "signal": "rompimento_confirmado",
            "action": "confirm",
            "value": "sim",
            "source_type": "defesa_civil",
            "source_name": "Defesa Civil",
            "confirmed_by": "B",
            "recorded_at": "2026-09-27T14:00:00+00:00",
            "parent_event_id": "p1",
        },
        {
            "event_id": "p2",
            "id_snisb": "2",
            "signal": "evacuacao_determinada",
            "action": "propose",
            "value": "sim",
            "source_type": "ses",
            "source_name": "SES",
            "confirmed_by": "C",
            "recorded_at": "2026-09-27T15:00:00+00:00",
            "observed_at": "2026-09-27T14:50:00+00:00",
        },
        {
            "event_id": "r2",
            "id_snisb": "2",
            "signal": "evacuacao_determinada",
            "action": "revoke",
            "value": "",
            "source_type": "ses",
            "source_name": "SES",
            "confirmed_by": "D",
            "recorded_at": "2026-09-28T15:00:00+00:00",
            "parent_event_id": "p2",
        },
        {
            "event_id": "p3",
            "id_snisb": "3",
            "signal": "mancha_atinge_captacao",
            "action": "propose",
            "value": "sim",
            "source_type": "orgao_fiscalizador",
            "source_name": "Fiscalizador",
            "confirmed_by": "E",
            "recorded_at": "2026-09-28T10:00:00+00:00",
            "observed_at": "2026-09-28T09:50:00+00:00",
        },
    ]


def test_lifecycle_links_resolution_and_latency():
    rows = proposal_lifecycle(sample_events())
    by_id = {r["proposal_event_id"]: r for r in rows}
    assert by_id["p1"]["status"] == "confirmada"
    assert by_id["p1"]["tempo_resolucao_h"] == 2.0
    assert by_id["p2"]["status"] == "revogada"
    assert by_id["p2"]["tempo_resolucao_h"] == 24.0
    assert by_id["p3"]["status"] == "pendente"


def test_daily_history_reconstructs_backlog_end_of_day():
    daily = {r["data"]: r for r in daily_history(proposal_lifecycle(sample_events()))}
    assert daily["2026-09-27"]["propostas_registradas"] == 2
    assert daily["2026-09-27"]["propostas_confirmadas"] == 1
    assert daily["2026-09-27"]["backlog_fim_dia"] == 1
    assert daily["2026-09-28"]["propostas_revogadas"] == 1
    assert daily["2026-09-28"]["backlog_fim_dia"] == 1


def test_confirmation_rates_use_resolved_proposals_only():
    daily = {r["data"]: r for r in daily_history(proposal_lifecycle(sample_events()))}
    assert daily["2026-09-27"]["taxa_confirmacao_resolvidas_pct"] == 100.0
    assert daily["2026-09-28"]["taxa_revogacao_resolvidas_pct"] == 100.0


def test_dimensions_preserve_signal_and_source_type():
    dims = daily_dimensions(proposal_lifecycle(sample_events()))
    assert any(
        r["signal"] == "rompimento_confirmado"
        and r["source_type"] == "defesa_civil"
        and r["backlog_fim_dia"] == 0
        for r in dims
        if r["data"] == "2026-09-27"
    )
