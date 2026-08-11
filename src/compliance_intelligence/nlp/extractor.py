from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    text: str
    label: str
    start: int
    end: int
    rule_or_model: str


class EntityExtractor:
    """Interface boundary for spaCy and domain-rule extraction."""

    def extract(self, text: str) -> tuple[ExtractedEntity, ...]:
        raise NotImplementedError(
            "Load a documented spaCy pipeline and versioned domain rules before extracting entities."
        )

