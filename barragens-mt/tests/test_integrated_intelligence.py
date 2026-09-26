from vigibarragens.intelligence.integrated_state import build_intelligence_state, classify_trend


def test_level_worsening_has_precedence_over_idap_delta():
    assert classify_trend("Laranja", "Amarelo", "41", "39") == "agravamento_nivel"


def test_same_level_tracks_idap_direction():
    assert classify_trend("Amarelo", "Amarelo", "32", "28") == "aumento_idap_mesmo_nivel"


def test_state_does_not_create_second_risk_score():
    state = build_intelligence_state({
        "id_snisb": "1", "nivel": "Laranja", "idap": "45",
        "pontos_a": "15", "pontos_b": "12", "pontos_c": "10", "pontos_d": "8",
        "completude": "0.75", "municipios_potencialmente_afetados": "A|B",
        "municipios_posicao_indeterminada": "C", "versao_pesos": "x",
    })
    assert state["nivel_operacional"] == "Laranja"
    assert state["pressao_hidro_pct"] == 50.0
    assert state["dimensao_dominante"] == "D"
    assert "score_integrado" not in state
    assert "jusante_otto_provisorio" in state["proxy_flags"]
