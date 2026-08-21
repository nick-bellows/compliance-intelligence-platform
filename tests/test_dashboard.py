"""Dashboard rendering from the reviewed run tables."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from compliance_intelligence.matching.engine import MatchingThresholds
from compliance_intelligence.reporting.dashboard import (
    load_run_tables,
    render_dashboard,
    write_dashboard,
)

THRESHOLDS = MatchingThresholds()


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fixture_run(tmp_path: Path, with_hits: bool = True) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write(
        run_dir / "screening_runs.csv",
        [
            {
                "run_id": "run-test-0001",
                "created_at_utc": "2026-08-21T00:00:00+00:00",
                "dataset_snapshot_ids": "synthetic-fixture-testsnap",
                "input_count": "3",
            }
        ],
    )
    _write(
        run_dir / "screening_entities.csv",
        [
            {
                "run_id": "run-test-0001",
                "external_id": "SYN-1",
                "query_name": "Alpha Example Corp",
                "normalized_name": "alpha example corp",
                "best_risk_tier": "exact" if with_hits else "clear",
                "review_required": "True" if with_hits else "False",
                "hit_count": "2" if with_hits else "0",
            },
            {
                "run_id": "run-test-0001",
                "external_id": "SYN-2",
                "query_name": "Beta Example Ltd",
                "normalized_name": "beta example ltd",
                "best_risk_tier": "clear",
                "review_required": "False",
                "hit_count": "0",
            },
        ],
    )
    hits: list[dict[str, str]] = []
    if with_hits:
        hits = [
            {
                "run_id": "run-test-0001",
                "external_id": "SYN-1",
                "query_name": "Alpha Example Corp",
                "source": "SYNTHETIC_LIST",
                "source_record_id": "FAKE-9",
                "matched_name": "Alpha Example Corporation",
                "score": "92.5",
                "risk_tier": "weak_fuzzy",
                "reasons": "normalized_sequence_similarity",
            },
            {
                "run_id": "run-test-0001",
                "external_id": "SYN-1",
                "query_name": "Alpha Example Corp",
                "source": "SYNTHETIC_LIST",
                "source_record_id": "FAKE-8",
                "matched_name": "Alpha Example Corp",
                "score": "100.0",
                "risk_tier": "exact",
                "reasons": "normalized_sequence_similarity|country_overlap",
            },
        ]
    hits_path = run_dir / "screening_hits.csv"
    if hits:
        _write(hits_path, hits)
    else:
        hits_path.write_text(
            "run_id,external_id,query_name,source,source_record_id,"
            "matched_name,score,risk_tier,reasons\n",
            encoding="utf-8",
        )
    _write(
        run_dir / "source_snapshots.csv",
        [
            {
                "snapshot_id": "synthetic-fixture-testsnap",
                "source_name": "SYNTHETIC_LIST",
                "source_url": "data/samples/synthetic_sanctions_fixture.csv",
                "retrieved_at_utc": "2026-08-21T00:00:00+00:00",
                "sha256": "ab" * 32,
                "record_count": "2",
                "terms_note": "Synthetic demonstration data; not authoritative.",
            }
        ],
    )
    return run_dir


def test_renders_all_documented_views(tmp_path: Path) -> None:
    html = render_dashboard(load_run_tables(_fixture_run(tmp_path)), THRESHOLDS)
    # KPI tiles, threshold lines, tier labels, provenance, synthetic banner.
    assert "entities screened" in html
    assert "weak ≥ 89" in html and "exact ≥ 99.5" in html
    assert "weak_fuzzy" in html and "exact" in html
    assert "run-test-0001" in html and "synthetic-fixture-testsnap" in html
    assert "synthetic" in html.lower()
    # Charts are inline SVG with per-mark tooltips, plus a table fallback.
    assert html.count("<svg") == 2
    assert "data-tip" in html
    assert "Score distribution as a table" in html


def test_review_queue_sorted_by_tier_then_score(tmp_path: Path) -> None:
    html = render_dashboard(load_run_tables(_fixture_run(tmp_path)), THRESHOLDS)
    assert html.index(">exact<") < html.index(">weak_fuzzy<")


def test_empty_run_states_the_absence(tmp_path: Path) -> None:
    html = render_dashboard(
        load_run_tables(_fixture_run(tmp_path, with_hits=False)), THRESHOLDS
    )
    assert "No hits" in html
    assert "<svg" not in html  # an empty chart is worse than a sentence


def test_write_dashboard_creates_file(tmp_path: Path) -> None:
    run_dir = _fixture_run(tmp_path)
    out = write_dashboard(run_dir, tmp_path / "docs" / "dash.html", THRESHOLDS)
    assert out.is_file()
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_missing_table_is_an_error(tmp_path: Path) -> None:
    run_dir = _fixture_run(tmp_path)
    (run_dir / "screening_hits.csv").unlink()
    with pytest.raises(FileNotFoundError):
        load_run_tables(run_dir)
