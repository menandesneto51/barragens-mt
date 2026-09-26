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
    description: str | None = None
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    return_code: int | None = None
    input_rows: int | None = None
    output_rows: int | None = None
    source_hash: str | None = None
    error: str | None = None

    def finish(self, *, status: str, return_code: int | None = None, error: str | None = None) -> None:
        self.status = status
        self.return_code = return_code
        self.error = error
        self.finished_at = utcnow()


@dataclass
class PipelineRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=utcnow)
    finished_at: str | None = None
    status: str = "running"
    requested_stages: list[str] = field(default_factory=list)
    stages: list[StageRun] = field(default_factory=list)

    def add_stage(self, name: str, description: str | None = None) -> StageRun:
        stage = StageRun(name=name, description=description, status="running", started_at=utcnow())
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
