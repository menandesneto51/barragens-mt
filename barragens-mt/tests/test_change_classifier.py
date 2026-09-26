from vigibarragens.intelligence.change_classifier import classify_change, sort_changes


def ev(field, previous, current, event_type="FIELD_CHANGED"):
    return {"id_snisb": "1", "field": field, "previous": previous, "current": current, "event_type": event_type}


def test_red_level_worsening_is_emergency_change():
    out = classify_change(ev("nivel", "Laranja", "Vermelho"))
    assert out["criticidade_evento"] == "emergencial"
    assert out["direcao"] == "piora"


def test_loss_of_alertability_is_critical():
    assert classify_change(ev("alertavel", "sim", "não"))["criticidade_evento"] == "critica"


def test_downstream_expansion_is_critical():
    out = classify_change(ev("municipios_potencialmente_afetados", "A|B", "A|B|C"))
    assert out["criticidade_evento"] == "critica"
    assert out["direcao"] == "expansao_territorial"


def test_improvement_is_not_promoted_to_operational_alert():
    out = classify_change(ev("nivel", "Vermelho", "Amarelo"))
    assert out["criticidade_evento"] == "informativa"
    assert out["direcao"] == "melhora"


def test_sort_prioritizes_emergency_then_critical():
    rows = [classify_change(ev("idap", "20", "21")), classify_change(ev("nivel", "Laranja", "Vermelho"))]
    assert sort_changes(rows)[0]["criticidade_evento"] == "emergencial"
