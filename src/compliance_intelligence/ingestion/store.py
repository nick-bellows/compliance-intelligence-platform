from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SYNTHETIC_SNAPSHOT_PREFIX, SourceSnapshot

SNAPSHOT_SCHEMA_VERSION = 1


def save_snapshot(snapshot: SourceSnapshot, directory: Path) -> Path:
    """Persist one snapshot as a self-describing JSON file, atomically.

    Snapshot IDs embed a content hash, so rewriting an existing file is
    idempotent rather than destructive.
    """

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot.snapshot_id}.json"
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot.snapshot_id,
        "source_name": snapshot.source_name,
        "source_url": snapshot.source_url,
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "sha256": snapshot.sha256,
        "terms_note": snapshot.terms_note,
        "record_count": len(snapshot.records),
        "records": [asdict(record) for record in snapshot.records],
    }
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return path


def load_snapshots(directory: Path) -> list[SourceSnapshot]:
    """Load every snapshot in the directory; a missing directory yields no snapshots."""

    if not directory.is_dir():
        return []
    snapshots: list[SourceSnapshot] = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = tuple(
            SanctionsRecord(
                source=item["source"],
                source_record_id=item["source_record_id"],
                primary_name=item["primary_name"],
                aliases=tuple(item["aliases"]),
                programs=tuple(item["programs"]),
                countries=tuple(item["countries"]),
                source_url=item["source_url"],
            )
            for item in payload["records"]
        )
        if payload["record_count"] != len(records):
            raise ValueError(
                f"Snapshot {path.name} declares {payload['record_count']} records "
                f"but contains {len(records)}"
            )
        snapshots.append(
            SourceSnapshot(
                snapshot_id=payload["snapshot_id"],
                source_name=payload["source_name"],
                source_url=payload["source_url"],
                retrieved_at=datetime.fromisoformat(payload["retrieved_at"]),
                sha256=payload["sha256"],
                terms_note=payload["terms_note"],
                records=records,
            )
        )
    return snapshots


def load_screening_snapshots(directory: Path, allow_synthetic: bool) -> list[SourceSnapshot]:
    """Load snapshots eligible for screening, excluding synthetic ones unless allowed."""

    return [
        snapshot
        for snapshot in load_snapshots(directory)
        if allow_synthetic or not snapshot.snapshot_id.startswith(SYNTHETIC_SNAPSHOT_PREFIX)
    ]


def load_screening_dataset(
    directory: Path, allow_synthetic: bool
) -> tuple[list[SanctionsRecord], tuple[str, ...]]:
    """Aggregate records and snapshot IDs, excluding synthetic snapshots unless allowed."""

    records: list[SanctionsRecord] = []
    snapshot_ids: list[str] = []
    for snapshot in load_screening_snapshots(directory, allow_synthetic):
        records.extend(snapshot.records)
        snapshot_ids.append(snapshot.snapshot_id)
    return records, tuple(snapshot_ids)
