from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from compliance_intelligence.domain.models import SanctionsRecord

SYNTHETIC_SNAPSHOT_PREFIX = "synthetic-"


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    snapshot_id: str
    source_name: str
    source_url: str
    retrieved_at: datetime
    sha256: str
    terms_note: str
    records: tuple[SanctionsRecord, ...]


class SourceAdapter(Protocol):
    def fetch(self) -> SourceSnapshot:
        """Retrieve, hash, parse, and validate one authoritative source snapshot."""

