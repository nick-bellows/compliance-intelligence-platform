from __future__ import annotations

import csv
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SYNTHETIC_SNAPSHOT_PREFIX, SourceSnapshot

_MULTI_VALUE_SEPARATOR = ";"


def _split_values(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(_MULTI_VALUE_SEPARATOR) if part.strip())


class SyntheticFixtureAdapter:
    """Loads the labeled synthetic fixture for demos and tests.

    Snapshots carry the synthetic ID prefix so downstream loaders can exclude
    them from real screening unless explicitly allowed.
    """

    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    def fetch(self) -> SourceSnapshot:
        raw = self._fixture_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        records: list[SanctionsRecord] = []
        for row in csv.DictReader(raw.decode("utf-8").splitlines()):
            if row["synthetic"].strip().lower() != "true":
                raise ValueError(
                    f"Fixture row {row['source_record_id']!r} is not marked synthetic; "
                    "only labeled synthetic rows may enter a synthetic snapshot"
                )
            records.append(
                SanctionsRecord(
                    source=row["source"],
                    source_record_id=row["source_record_id"],
                    primary_name=row["primary_name"],
                    aliases=_split_values(row["aliases"]),
                    programs=_split_values(row["programs"]),
                    countries=_split_values(row["countries"]),
                    source_url=self._fixture_path.as_posix(),
                )
            )
        return SourceSnapshot(
            snapshot_id=f"{SYNTHETIC_SNAPSHOT_PREFIX}fixture-{digest[:12]}",
            source_name="SYNTHETIC_LIST",
            source_url=self._fixture_path.as_posix(),
            retrieved_at=datetime.now(UTC),
            sha256=digest,
            terms_note="Synthetic demonstration data; not authoritative.",
            records=tuple(records),
        )
