"""Utilitários de lineage de execução e artefato."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


RUN_ID_ENV = "VIGIBARRAGENS_RUN_ID"
STAGE_ENV = "VIGIBARRAGENS_STAGE"


def current_run_id() -> str:
    return os.environ.get(RUN_ID_ENV, "").strip()


def current_stage() -> str:
    return os.environ.get(STAGE_ENV, "").strip()


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    if not target.exists() or not target.is_file():
        return ""
    h = hashlib.sha256()
    with target.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_metadata(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists() or not target.is_file():
        return {
            "artifact_path": str(target),
            "artifact_sha256": "",
            "artifact_size_bytes": None,
        }
    return {
        "artifact_path": str(target),
        "artifact_sha256": sha256_file(target),
        "artifact_size_bytes": target.stat().st_size,
    }
