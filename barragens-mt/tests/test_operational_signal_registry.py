from vigibarragens.intelligence.operational_signal_registry import (
    create_event,
    materialize_latest,
    validate_event_log,
    validate_governance_chain,
)


def test_create_event_hash_is_stable_for_fixed_payload():
    e1 = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa",
        confirmer_role="Coordenador",
        event_id="evt-1",
        recorded_at="2026-09-27T14:01:00+00:00",
    )
    e2 = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa",
        confirmer_role="Coordenador",
        event_id="evt-1",
        recorded_at="2026-09-27T14:01:00+00:00",
    )
    assert e1.event_sha256 == e2.event_sha256
    assert len(e1.event_sha256) == 64


def test_revocation_supersedes_confirmation_without_deleting_history():
    confirm = create_event(
        id_snisb="1",
        signal="evacuacao_determinada",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="Ato-1",
        confirmed_by="Pessoa",
        confirmer_role="Coordenador",
        event_id="evt-1",
        recorded_at="2026-09-27T14:00:00+00:00",
    ).to_dict()
    revoke = create_event(
        id_snisb="1",
        signal="evacuacao_determinada",
        action="revoke",
        observed_at="2026-09-27T10:30:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="Ato-2",
        confirmed_by="Pessoa",
        confirmer_role="Coordenador",
        event_id="evt-2",
        recorded_at="2026-09-27T14:30:00+00:00",
    ).to_dict()

    latest = materialize_latest([confirm, revoke])
    assert latest["1"]["evacuacao_determinada"]["action"] == "revoke"
    assert len([confirm, revoke]) == 2


def test_confirmation_requires_identified_source_and_responsible():
    try:
        create_event(
            id_snisb="1",
            signal="rompimento_confirmado",
            action="confirm",
            value="sim",
            observed_at="2026-09-27T10:00:00-04:00",
            source_type="defesa_civil",
            source_name="",
            document_reference="",
            confirmed_by="",
            confirmer_role="",
        )
    except ValueError as exc:
        assert "source_name" in str(exc) or "confirmed_by" in str(exc)
    else:
        raise AssertionError("evento sem fonte/responsável deveria ser rejeitado")


def test_integrity_validator_detects_tampering_and_duplicate_ids():
    event = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa",
        confirmer_role="Coordenador",
        event_id="evt-1",
        recorded_at="2026-09-27T14:01:00+00:00",
    ).to_dict()
    tampered = dict(event)
    tampered["value"] = "não"
    problems = validate_event_log([event, tampered])
    messages = [p["error"] for p in problems]
    assert "event_id duplicado" in messages
    assert "event_sha256 divergente do conteúdo canônico" in messages


def test_proposal_does_not_materialize_operational_state():
    proposal = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="propose",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa A",
        confirmer_role="Operador",
        event_id="prop-1",
        recorded_at="2026-09-27T14:00:00+00:00",
    ).to_dict()
    assert materialize_latest([proposal]) == {}


def test_critical_confirmation_requires_distinct_second_person():
    proposal = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="propose",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa A",
        confirmer_role="Operador",
        event_id="prop-1",
        recorded_at="2026-09-27T14:00:00+00:00",
    ).to_dict()
    confirm = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa A",
        confirmer_role="Coordenador",
        parent_event_id="prop-1",
        event_id="conf-1",
        recorded_at="2026-09-27T14:05:00+00:00",
    ).to_dict()
    problems = validate_governance_chain([proposal, confirm])
    assert any("pessoas distintas" in p["error"] for p in problems)


def test_critical_confirmation_by_second_person_is_valid():
    proposal = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="propose",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa A",
        confirmer_role="Operador",
        event_id="prop-1",
        recorded_at="2026-09-27T14:00:00+00:00",
    ).to_dict()
    confirm = create_event(
        id_snisb="1",
        signal="rompimento_confirmado",
        action="confirm",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="SITREP-1",
        confirmed_by="Pessoa B",
        confirmer_role="Coordenador",
        parent_event_id="prop-1",
        event_id="conf-1",
        recorded_at="2026-09-27T14:05:00+00:00",
    ).to_dict()
    assert validate_governance_chain([proposal, confirm]) == []
    latest = materialize_latest([proposal, confirm])
    assert latest["1"]["rompimento_confirmado"]["action"] == "confirm"


def test_critical_revocation_must_reference_confirmation():
    proposal = create_event(
        id_snisb="1",
        signal="evacuacao_determinada",
        action="propose",
        value="sim",
        observed_at="2026-09-27T10:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="ATO-1",
        confirmed_by="Pessoa A",
        confirmer_role="Operador",
        event_id="prop-1",
        recorded_at="2026-09-27T14:00:00+00:00",
    ).to_dict()
    revoke = create_event(
        id_snisb="1",
        signal="evacuacao_determinada",
        action="revoke",
        observed_at="2026-09-27T11:00:00-04:00",
        source_type="defesa_civil",
        source_name="Defesa Civil",
        document_reference="ATO-2",
        confirmed_by="Pessoa B",
        confirmer_role="Coordenador",
        parent_event_id="prop-1",
        event_id="rev-1",
        recorded_at="2026-09-27T15:00:00+00:00",
    ).to_dict()
    problems = validate_governance_chain([proposal, revoke])
    assert any("confirmação ativa" in p["error"] for p in problems)
