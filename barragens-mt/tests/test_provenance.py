from datetime import datetime, timezone
from vigibarragens.intelligence.provenance import build_lineage_record, freshness

NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


def test_semantic_freshness_states():
    assert freshness("2026-09-26T00:00:00+00:00", now=NOW)["estado"] == "atual"
    assert freshness("2026-09-24T12:00:00+00:00", now=NOW)["estado"] == "atencao"
    assert freshness("2026-09-20", now=NOW)["estado"] == "vencido"
    assert freshness("", now=NOW)["estado"] == "desconhecido"


def test_lineage_exposes_sources_and_proxy_without_changing_risk():
    row = build_lineage_record(
        {"id_snisb": "1", "nivel": "Laranja", "municipios_potencialmente_afetados": "A|B"},
        {"data_referencia": "2026-09-26", "fonte_precip": "sisclima", "fonte_hidro": "ana", "aproximacao_espacial": "sede_mais_montante_max"},
        now=NOW,
    )
    assert row["nivel"] == "Laranja"
    assert row["lineage_status"] == "documentado"
    assert "ana" in row["fontes_hidro"]
    assert "territorio:otto_provisorio" in row["proxies"]
