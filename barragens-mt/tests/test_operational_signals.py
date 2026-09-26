from vigibarragens.intelligence.operational_signals import (
    normalized_signal_values,
    parse_bool,
    parse_municipalities,
)


def test_boolean_parser_requires_explicit_truthy_value():
    assert parse_bool("sim") is True
    assert parse_bool("true") is True
    assert parse_bool("") is False
    assert parse_bool("não") is False


def test_operational_signal_normalization_does_not_invent_values():
    row = normalized_signal_values({})
    assert row["rompimento_confirmado"] is False
    assert row["sensores_criticos_em_falha"] == 0
    assert row["municipios_zas_sem_confirmacao"] == ()


def test_municipality_list_accepts_pipe_or_semicolon():
    assert parse_municipalities("Cuiabá | Várzea Grande") == ("Cuiabá", "Várzea Grande")
    assert parse_municipalities("Cuiabá;Várzea Grande") == ("Cuiabá", "Várzea Grande")
