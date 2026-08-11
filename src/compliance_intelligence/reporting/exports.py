from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from compliance_intelligence.domain.models import ScreeningResult


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

