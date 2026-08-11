import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.ingestion.store import (
    load_screening_dataset,
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
    save_snapshot(_snapshot("synthetic-fixture-abc123def456"), tmp_path)

    records, snapshot_ids = load_screening_dataset(tmp_path, allow_synthetic=False)
    assert snapshot_ids == ("testsource-20260810-abc123def456",)
    assert len(records) == 1

    _, all_ids = load_screening_dataset(tmp_path, allow_synthetic=True)
    assert set(all_ids) == {
        "testsource-20260810-abc123def456",
        "synthetic-fixture-abc123def456",
    }
