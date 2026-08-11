from __future__ import annotations

from compliance_intelligence.ingestion.base import SourceSnapshot


class SecondarySanctionsAdapter:
    """Placeholder for the selected second official sanctions source."""

    def fetch(self) -> SourceSnapshot:
        raise NotImplementedError(
            "Select one authoritative secondary source and document its terms before implementation."
        )

