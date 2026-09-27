from vigibarragens.intelligence.operational_signal_registry import (
    create_event,
    materialize_latest,
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
