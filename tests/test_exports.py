import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from compliance_intelligence.domain.models import (
    RiskTier,
    SanctionsRecord,
    ScreeningHit,
    ScreeningQuery,
    ScreeningResult,
    ScreeningRun,
)
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.reporting.exports import write_hits_csv, write_json, write_run_tables


def _result() -> ScreeningResult:
    return ScreeningResult(
        query=ScreeningQuery(name="Acme Galactic Holdings", countries=("US",)),
        hits=(
            ScreeningHit(
                source="SYNTHETIC_LIST",
                source_record_id="FAKE-001",
                matched_name="Galactic Acme Holding",
                score=93.75,
                risk_tier=RiskTier.STRONG,
                reasons=("normalized_sequence_similarity", "token_order_normalized"),
            ),
        ),
        dataset_snapshot_ids=("synthetic-fixture-v1",),
    )


def test_write_json_creates_parents_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "result.json"
    write_json(_result(), path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["query"]["name"] == "Acme Galactic Holdings"
    assert payload["hits"][0]["risk_tier"] == "strong_fuzzy"
    assert payload["dataset_snapshot_ids"] == ["synthetic-fixture-v1"]


def test_write_hits_csv_joins_reasons(tmp_path: Path) -> None:
    path = tmp_path / "hits.csv"
    write_hits_csv(_result(), path)
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    assert rows[0]["matched_name"] == "Galactic Acme Holding"
    assert rows[0]["risk_tier"] == "strong_fuzzy"
    assert rows[0]["reasons"] == "normalized_sequence_similarity|token_order_normalized"


def test_write_run_tables_emits_four_related_tables(tmp_path: Path) -> None:
    clear_result = ScreeningResult(
        query=ScreeningQuery(name="Unrelated Startup", external_id="SYN-002"),
        hits=(),
        dataset_snapshot_ids=("snap-1",),
    )
    flagged_result = ScreeningResult(
        query=ScreeningQuery(name="Acme Galactic Holdings", external_id="SYN-001"),
        hits=_result().hits,
        dataset_snapshot_ids=("snap-1",),
    )
    run = ScreeningRun(
        run_id="run-test-0001",
        created_at=datetime(2026, 8, 11, 3, 0, tzinfo=UTC),
        dataset_snapshot_ids=("snap-1",),
        input_count=2,
    )
    snapshot = SourceSnapshot(
        snapshot_id="snap-1",
        source_name="SYNTHETIC_LIST",
        source_url="fixture.csv",
        retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
        sha256="e" * 64,
        terms_note="synthetic",
        records=(
            SanctionsRecord(
                source="SYNTHETIC_LIST", source_record_id="FAKE-001", primary_name="Acme"
            ),
        ),
    )

    tables = write_run_tables(run, [flagged_result, clear_result], [snapshot], tmp_path)
    assert set(tables) == {
        "screening_runs",
        "screening_entities",
        "screening_hits",
        "source_snapshots",
    }

    runs = list(csv.DictReader(tables["screening_runs"].read_text(encoding="utf-8").splitlines()))
    assert runs[0]["run_id"] == "run-test-0001"
    assert runs[0]["input_count"] == "2"

    entities = list(
        csv.DictReader(tables["screening_entities"].read_text(encoding="utf-8").splitlines())
    )
    assert len(entities) == 2
    flagged = next(row for row in entities if row["external_id"] == "SYN-001")
    assert flagged["best_risk_tier"] == "strong_fuzzy"
    assert flagged["review_required"] == "True"
    cleared = next(row for row in entities if row["external_id"] == "SYN-002")
    assert cleared["best_risk_tier"] == "clear"
    assert cleared["hit_count"] == "0"

    hits = list(csv.DictReader(tables["screening_hits"].read_text(encoding="utf-8").splitlines()))
    assert len(hits) == 1
    assert hits[0]["run_id"] == "run-test-0001"
    assert hits[0]["external_id"] == "SYN-001"

    snapshots = list(
        csv.DictReader(tables["source_snapshots"].read_text(encoding="utf-8").splitlines())
    )
    assert snapshots[0]["snapshot_id"] == "snap-1"
    assert snapshots[0]["record_count"] == "1"
