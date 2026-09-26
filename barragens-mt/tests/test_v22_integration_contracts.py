"""Gate estrutural da v2.2: sintaxe, ordem do pipeline e contratos críticos."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_entrypoints_compile():
    for rel in (
        "executar.py",
        "streamlit_app.py",
        "scripts/16_idap_estadual.py",
        "scripts/35_detectar_mudancas.py",
        "scripts/36_inteligencia_integrada.py",
        "scripts/37_proveniencia_freshness.py",
        "vigibarragens/history.py",
        "vigibarragens/intelligence/integrated_state.py",
        "vigibarragens/intelligence/change_classifier.py",
        "vigibarragens/intelligence/provenance.py",
        "st_app/data.py",
    ):
        source = (ROOT / rel).read_text(encoding="utf-8")
        ast.parse(source, filename=rel)


def test_v22_pipeline_order_is_preserved():
    source = (ROOT / "executar.py").read_text(encoding="utf-8")
    expected = [
        "17_hidro_sisclima_titan.py",
        "19_contatos_alertabilidade.py",
        "16_idap_estadual.py",
        "35_detectar_mudancas.py",
        "36_inteligencia_integrada.py",
        "37_proveniencia_freshness.py",
    ]
    positions = [source.index(name) for name in expected]
    assert positions == sorted(positions)


def test_streamlit_loaders_are_non_breaking_by_contract():
    source = (ROOT / "st_app" / "data.py").read_text(encoding="utf-8")
    assert 'if not caminho.exists():\n        return pd.DataFrame()' in source
    for loader in (
        "carregar_inteligencia",
        "carregar_mudancas_recentes",
        "carregar_proveniencia",
        "carregar_evidencias_idap",
    ):
        assert f"def {loader}" in source


def test_idap_materializes_indicator_evidence():
    source = (ROOT / "scripts" / "16_idap_estadual.py").read_text(encoding="utf-8")
    assert "resultado.indicadores" in source
    assert "idap_evidencias_indicadores_mt.csv" in source
    for field in (
        "codigo_indicador",
        "dimensao",
        "pontos",
        "teto",
        "valor",
        "fonte_metodologica",
        "versao_pesos",
    ):
        assert field in source


def test_change_event_has_serializable_contract():
    from vigibarragens.history import ChangeEvent

    event = ChangeEvent("1", "nivel", "Amarelo", "Laranja", "2026-09-26T12:00:00Z")
    payload = event.to_dict()
    assert payload["id_snisb"] == "1"
    assert payload["event_type"] == "FIELD_CHANGED"
