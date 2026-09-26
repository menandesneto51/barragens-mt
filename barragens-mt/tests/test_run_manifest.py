import json

from vigibarragens.run_manifest import PipelineRun


def test_manifest_is_persisted(tmp_path):
    run = PipelineRun()
    stage = run.add_stage("01_snisb")
    stage.status = "success"
    stage.output_rows = 1248
    run.finish()
    path = run.save(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["stages"][0]["output_rows"] == 1248
