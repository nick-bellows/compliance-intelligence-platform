import csv
import json
from pathlib import Path

from compliance_intelligence.domain.models import (
    RiskTier,
    ScreeningHit,
    ScreeningQuery,
    ScreeningResult,
)
from compliance_intelligence.reporting.exports import write_hits_csv, write_json


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
