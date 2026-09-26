import pandas as pd

from vigibarragens.history import detect_changes, dataframe_hash


def test_detect_changes_tracks_only_changed_fields():
    before = pd.DataFrame([{"IdSnisb": "1", "CategoriaRisco": "Médio", "DanoPotencial": "Alto"}])
    after = pd.DataFrame([{"IdSnisb": "1", "CategoriaRisco": "Alto", "DanoPotencial": "Alto"}])
    events = detect_changes(before, after)
    assert len(events) == 1
    assert events[0].id_snisb == "1"
    assert events[0].field == "CategoriaRisco"
    assert events[0].previous == "Médio"
    assert events[0].current == "Alto"


def test_dataframe_hash_is_stable_for_column_order():
    a = pd.DataFrame([{"b": 2, "a": 1}])
    b = pd.DataFrame([{"a": 1, "b": 2}])
    assert dataframe_hash(a) == dataframe_hash(b)
