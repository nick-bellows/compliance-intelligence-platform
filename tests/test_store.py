import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.ingestion.store import (
    load_screening_dataset,
    load_screening_snapshots,
    load_snapshots,
    save_snapshot,
)


def _snapshot(snapshot_id: str = "testsource-20260810-abc123def456") -> SourceSnapshot:
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        source_name="TEST_LIST",
        source_url="https://example.invalid/list.xml",
        retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
        sha256="a" * 64,
        terms_note="test terms",
        records=(
            SanctionsRecord(
                source="TEST_LIST",
                source_record_id="T-1",
                primary_name="Acme Galactic Holdings",
                aliases=("Galactic Acme Holding",),
                programs=("SAMPLE_PROGRAM",),
                countries=("US",),
                source_url="https://example.invalid/record/T-1",
            ),
        ),
    )


def test_snapshot_round_trip(tmp_path: Path) -> None:
    saved_path = save_snapshot(_snapshot(), tmp_path)
    assert saved_path.name == "testsource-20260810-abc123def456.json"
    assert load_snapshots(tmp_path) == [_snapshot()]


def test_missing_directory_yields_no_snapshots(tmp_path: Path) -> None:
    assert load_snapshots(tmp_path / "does-not-exist") == []


def test_tampered_record_count_is_rejected(tmp_path: Path) -> None:
    saved_path = save_snapshot(_snapshot(), tmp_path)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    payload["record_count"] = 99
    saved_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshots(tmp_path)


def test_screening_dataset_excludes_synthetic_unless_allowed(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), tmp_path)
    save_snapshot(
        replace(_snapshot("synthetic-fixture-abc123def456"), source_name="SYNTHETIC_LIST"),
        tmp_path,
    )

    records, snapshot_ids = load_screening_dataset(tmp_path, allow_synthetic=False)
    assert snapshot_ids == ("testsource-20260810-abc123def456",)
    assert len(records) == 1

    _, all_ids = load_screening_dataset(tmp_path, allow_synthetic=True)
    assert set(all_ids) == {
        "testsource-20260810-abc123def456",
        "synthetic-fixture-abc123def456",
    }


def test_screening_snapshots_keep_only_the_newest_per_source(tmp_path: Path) -> None:
    def stamped(snapshot_id: str, retrieved_at: datetime, record_id: str) -> SourceSnapshot:
        base = _snapshot(snapshot_id)
        return replace(
            base,
            retrieved_at=retrieved_at,
            records=(replace(base.records[0], source_record_id=record_id),),
        )

    save_snapshot(
        stamped("testsource-20260801-aaaaaaaaaaaa", datetime(2026, 8, 1, tzinfo=UTC), "OLD"),
        tmp_path,
    )
    save_snapshot(
        stamped("testsource-20260901-bbbbbbbbbbbb", datetime(2026, 9, 1, tzinfo=UTC), "NEW"),
        tmp_path,
    )
    other = replace(
        stamped("other-20260701-cccccccccccc", datetime(2026, 7, 1, tzinfo=UTC), "OTHER"),
        source_name="OTHER_LIST",
    )
    save_snapshot(other, tmp_path)

    snapshots = load_screening_snapshots(tmp_path, allow_synthetic=False)
    assert [snapshot.snapshot_id for snapshot in snapshots] == [
        "other-20260701-cccccccccccc",
        "testsource-20260901-bbbbbbbbbbbb",
    ]
    records, snapshot_ids = load_screening_dataset(tmp_path, allow_synthetic=False)
    assert {record.source_record_id for record in records} == {"NEW", "OTHER"}
    assert "testsource-20260801-aaaaaaaaaaaa" not in snapshot_ids
    # Superseded files are retained on disk for audit; they are just not served.
    assert len(load_snapshots(tmp_path)) == 3
