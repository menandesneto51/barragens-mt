from pathlib import Path

from vigibarragens.lineage_runtime import file_metadata, sha256_file
from vigibarragens.intelligence.indicator_lineage import indicator_lineage


def test_file_metadata_separates_artifact_time_and_hash(tmp_path: Path):
    p = tmp_path / "x.csv"
    p.write_text("a;b\n1;2\n", encoding="utf-8")
    meta = file_metadata(p)
    assert len(meta["artifact_sha256"]) == 64
    assert meta["artifact_size_bytes"] > 0
    assert meta["artifact_materialized_at"]
    assert sha256_file(p) == meta["artifact_sha256"]


def test_ibge_cnes_and_contacts_preserve_semantic_reference_dates():
    c1 = indicator_lineage("C1", population_reference="2022")
    c3 = indicator_lineage("C3", cnes_reference="2026-09-25")
    d8 = indicator_lineage(
        "D8",
        alertability={"data_referencia_contatos": "2026-08-01"},
    )
    assert c1["referencia_temporal"] == "2022"
    assert c3["referencia_temporal"] == "2026-09-25"
    assert d8["referencia_temporal"] == "2026-08-01"
