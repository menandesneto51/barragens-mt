"""Snapshots históricos e detecção auditável de mudanças em barragens."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import hashlib
import json

import pandas as pd

TRACKED_FIELDS = (
    "categoria_risco", "dano_potencial_associado", "classe_cnrh",
    "sigbm_nivel_emergencia", "sigbm_status_dce", "possui_pae",
    "completude", "nivel", "idap", "alertavel", "contatos_validados_90d",
    "municipios_potencialmente_afetados",
)

@dataclass(frozen=True)
class ChangeEvent:
    id_snisb: str
    field: str
    previous: object
    current: object
    detected_at: str
    event_type: str = "FIELD_CHANGED"

    def to_dict(self) -> dict:
        return asdict(self)


def _normal(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _id_column(df: pd.DataFrame) -> str | None:
    for candidate in ("id_snisb", "IdSnisb"):
        if candidate in df.columns:
            return candidate
    return None


def dataframe_hash(df: pd.DataFrame) -> str:
    """Hash determinístico, independente da ordem de colunas e, quando possível, linhas."""
    frame = df.sort_index(axis=1).fillna("").astype(str)
    id_col = _id_column(frame)
    if id_col:
        frame = frame.sort_values(id_col, kind="stable").reset_index(drop=True)
    else:
        frame = frame.sort_values(list(frame.columns), kind="stable").reset_index(drop=True)
    payload = frame.to_csv(index=False).encode("utf-8")
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


def _validate_unique(df: pd.DataFrame, id_col: str, label: str) -> None:
    duplicated = df[id_col].astype(str).duplicated(keep=False)
    if duplicated.any():
        ids = sorted(set(df.loc[duplicated, id_col].astype(str)))
        raise ValueError(f"IDs duplicados em {label}: {', '.join(ids[:10])}")


def detect_changes(previous: pd.DataFrame, current: pd.DataFrame, *, id_col: str = "id_snisb", fields: Iterable[str] = TRACKED_FIELDS) -> list[ChangeEvent]:
    if id_col not in previous.columns or id_col not in current.columns:
        raise ValueError(f"Coluna identificadora ausente: {id_col}")
    _validate_unique(previous, id_col, "snapshot anterior")
    _validate_unique(current, id_col, "snapshot atual")
    old = previous.set_index(id_col, drop=False)
    new = current.set_index(id_col, drop=False)
    detected = datetime.now(timezone.utc).isoformat()
    events: list[ChangeEvent] = []
    old_ids, new_ids = set(old.index), set(new.index)
    for dam_id in sorted(new_ids - old_ids, key=str):
        events.append(ChangeEvent(str(dam_id), "__entity__", None, "presente", detected, "BARRAGEM_NOVA"))
    for dam_id in sorted(old_ids - new_ids, key=str):
        events.append(ChangeEvent(str(dam_id), "__entity__", "presente", None, detected, "BARRAGEM_REMOVIDA"))
    for dam_id in sorted(old_ids & new_ids, key=str):
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
