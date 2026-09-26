"""Manifesto estruturado de execução para lineage, freshness e auditoria."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class StageRun:
    name: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    input_rows: int | None = None
    output_rows: int | None = None
    source_hash: str | None = None
    error: str | None = None

@dataclass
class PipelineRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=utcnow)
    finished_at: str | None = None
    status: str = "running"
    stages: list[StageRun] = field(default_factory=list)

    def add_stage(self, name: str) -> StageRun:
        stage = StageRun(name=name, status="running", started_at=utcnow())
        self.stages.append(stage)
        return stage

    def finish(self, status: str = "success") -> None:
        self.status = status
        self.finished_at = utcnow()

    def save(self, directory: str | Path) -> Path:
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{self.run_id}.json"
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
