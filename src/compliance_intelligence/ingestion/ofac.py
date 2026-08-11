from __future__ import annotations

from compliance_intelligence.ingestion.base import SourceSnapshot


class OfacAdapter:
    """Placeholder for the official OFAC sanctions-list adapter."""

    def fetch(self) -> SourceSnapshot:
        raise NotImplementedError(
            "Verify the current official endpoint and terms, then implement retrieval, hashing, "
            "schema validation, and parsing."
        )

