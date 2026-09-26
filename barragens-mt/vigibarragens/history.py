"""Snapshots históricos e detecção auditável de mudanças em barragens."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import hashlib
import json

import pandas as pd

TRACKED_FIELDS = (
    "CategoriaRisco", "DanoPotencial", "ClasseCNRH", "NivelEmergencia",
    "StatusDCE", "PossuiPAE", "UltimaInspecao", "UltimaFiscalizacao",
    "Completude", "NivelVigibarragens", "IDAP",
)

@dataclass(frozen=True)
class ChangeEvent:
    id_snisb: str
    field: str
    previous: object
    current: object
    detected_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normal(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def dataframe_hash(df: pd.DataFrame) -> str:
    payload = df.sort_index(axis=1).fillna("").astype(str).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_snapshot(df: pd.DataFrame, output_dir: str | Path, *, snapshot_at: datetime | None = None) -> Path:
    when = snapshot_at or datetime.now(timezone.utc)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = df.copy()
    frame["_snapshot_at"] = when.isoformat()
    frame["_snapshot_hash"] = dataframe_hash(df)
    path = out / f"barragens_{when.strftime('%Y%m%dT%H%M%SZ')}.csv"
    frame.to_csv(path, index=False)
    return path


def detect_changes(previous: pd.DataFrame, current: pd.DataFrame, *, id_col: str = "IdSnisb", fields: Iterable[str] = TRACKED_FIELDS) -> list[ChangeEvent]:
    if id_col not in previous.columns or id_col not in current.columns:
        raise ValueError(f"Coluna identificadora ausente: {id_col}")
    old = previous.set_index(id_col, drop=False)
    new = current.set_index(id_col, drop=False)
    detected = datetime.now(timezone.utc).isoformat()
    events: list[ChangeEvent] = []
    for dam_id in sorted(set(old.index) & set(new.index), key=str):
        for field in fields:
            if field not in old.columns or field not in new.columns:
                continue
            before, after = _normal(old.at[dam_id, field]), _normal(new.at[dam_id, field])
            if before != after:
                events.append(ChangeEvent(str(dam_id), field, before, after, detected))
    return events


def write_change_events(events: Iterable[ChangeEvent], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n")
    return target
