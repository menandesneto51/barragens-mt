import pandas as pd
import pytest

from vigibarragens.history import detect_changes, dataframe_hash


def test_detect_changes_tracks_only_changed_fields():
    before = pd.DataFrame([{"id_snisb": "1", "categoria_risco": "Médio", "dano_potencial_associado": "Alto"}])
    after = pd.DataFrame([{"id_snisb": "1", "categoria_risco": "Alto", "dano_potencial_associado": "Alto"}])
    events = detect_changes(before, after)
    assert len(events) == 1
    assert events[0].field == "categoria_risco"


def test_dataframe_hash_is_stable_for_column_and_row_order():
    a = pd.DataFrame([{"id_snisb": "2", "b": 4, "a": 3}, {"id_snisb": "1", "b": 2, "a": 1}])
    b = pd.DataFrame([{"a": 1, "b": 2, "id_snisb": "1"}, {"a": 3, "id_snisb": "2", "b": 4}])
    assert dataframe_hash(a) == dataframe_hash(b)


def test_detects_new_and_removed_dams():
    before = pd.DataFrame([{"id_snisb": "1"}, {"id_snisb": "2"}])
    after = pd.DataFrame([{"id_snisb": "2"}, {"id_snisb": "3"}])
    types = {(e.id_snisb, e.event_type) for e in detect_changes(before, after)}
    assert ("1", "BARRAGEM_REMOVIDA") in types
    assert ("3", "BARRAGEM_NOVA") in types


def test_duplicate_ids_fail_explicitly():
    before = pd.DataFrame([{"id_snisb": "1"}, {"id_snisb": "1"}])
    after = pd.DataFrame([{"id_snisb": "1"}])
    with pytest.raises(ValueError, match="duplicados"):
        detect_changes(before, after)
