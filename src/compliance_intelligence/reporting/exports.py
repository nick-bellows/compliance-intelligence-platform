from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from pathlib import Path

from compliance_intelligence.domain.models import RiskTier, ScreeningResult, ScreeningRun
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.matching.normalization import normalize_entity_name


def write_json(result: ScreeningResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def write_hits_csv(result: ScreeningResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "query_name",
                "source",
                "source_record_id",
                "matched_name",
                "score",
                "risk_tier",
                "reasons",
            ),
        )
        writer.writeheader()
        for hit in result.hits:
            writer.writerow(
                {
                    "query_name": result.query.name,
                    "source": hit.source,
                    "source_record_id": hit.source_record_id,
                    "matched_name": hit.matched_name,
                    "score": hit.score,
                    "risk_tier": hit.risk_tier,
                    "reasons": "|".join(hit.reasons),
                }
            )


def _write_table(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_run_tables(
    run: ScreeningRun,
    results: Sequence[ScreeningResult],
    snapshots: Sequence[SourceSnapshot],
    output_directory: Path,
) -> dict[str, Path]:
    """Write the four analyst-facing tables the Power BI model consumes."""

    tables = {
        "screening_runs": output_directory / "screening_runs.csv",
        "screening_entities": output_directory / "screening_entities.csv",
        "screening_hits": output_directory / "screening_hits.csv",
        "source_snapshots": output_directory / "source_snapshots.csv",
    }

    _write_table(
        tables["screening_runs"],
        ("run_id", "created_at_utc", "dataset_snapshot_ids", "input_count"),
        [
            {
                "run_id": run.run_id,
                "created_at_utc": run.created_at.isoformat(),
                "dataset_snapshot_ids": "|".join(run.dataset_snapshot_ids),
                "input_count": run.input_count,
            }
        ],
    )

    _write_table(
        tables["screening_entities"],
        (
            "run_id",
            "external_id",
            "query_name",
            "normalized_name",
            "best_risk_tier",
            "review_required",
            "hit_count",
        ),
        [
            {
                "run_id": run.run_id,
                "external_id": result.query.external_id or "",
                "query_name": result.query.name,
                "normalized_name": normalize_entity_name(result.query.name),
                "best_risk_tier": result.hits[0].risk_tier if result.hits else RiskTier.CLEAR,
                "review_required": result.review_required,
                "hit_count": len(result.hits),
            }
            for result in results
        ],
    )

    _write_table(
        tables["screening_hits"],
        (
            "run_id",
            "external_id",
            "query_name",
            "source",
            "source_record_id",
            "matched_name",
            "score",
            "risk_tier",
            "reasons",
        ),
        [
            {
                "run_id": run.run_id,
                "external_id": result.query.external_id or "",
                "query_name": result.query.name,
                "source": hit.source,
                "source_record_id": hit.source_record_id,
                "matched_name": hit.matched_name,
                "score": hit.score,
                "risk_tier": hit.risk_tier,
                "reasons": "|".join(hit.reasons),
            }
            for result in results
            for hit in result.hits
        ],
    )

    _write_table(
        tables["source_snapshots"],
        (
            "snapshot_id",
            "source_name",
            "source_url",
            "retrieved_at_utc",
            "sha256",
            "record_count",
            "terms_note",
        ),
        [
            {
                "snapshot_id": snapshot.snapshot_id,
                "source_name": snapshot.source_name,
                "source_url": snapshot.source_url,
                "retrieved_at_utc": snapshot.retrieved_at.isoformat(),
                "sha256": snapshot.sha256,
                "record_count": len(snapshot.records),
                "terms_note": snapshot.terms_note,
            }
            for snapshot in snapshots
        ],
    )

    return tables

