from vigibarragens.intelligence.indicator_lineage import indicator_lineage


def test_hydro_indicator_lineage_declares_proxy_when_spatial_aggregation_is_proxy():
    row = indicator_lineage(
        "A1",
        hydro={
            "data_referencia": "2026-09-26",
            "fonte_precip": "sisclima",
            "aproximacao_espacial": "sede_mais_montante_max",
        },
    )
    assert row["produto_observacional"] == "hidro_barragens_mt.csv"
    assert row["campo_observacional"] == "chuva_24h_mm"
    assert row["tipo_evidencia"] == "proxy"
    assert row["referencia_temporal"] == "2026-09-26"


def test_official_registry_indicator_is_not_labeled_proxy():
    row = indicator_lineage("B1", inventory={"categoria_risco": "Alto"})
    assert row["tipo_evidencia"] == "oficial_cadastral"
    assert row["campo_observacional"] == "categoria_risco"


def test_population_and_cnes_exposure_are_explicit_proxies():
    assert indicator_lineage("C1")["tipo_evidencia"] == "proxy"
    assert "otto" in indicator_lineage("C1")["metodo_proxy"].lower()
    assert indicator_lineage("C3")["tipo_evidencia"] == "proxy"


def test_unimplemented_indicator_stays_absent():
    row = indicator_lineage("D6")
    assert row["tipo_evidencia"] == "ausente"
    assert row["produto_observacional"] == ""
