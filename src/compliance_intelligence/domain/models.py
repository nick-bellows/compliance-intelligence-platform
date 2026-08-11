from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskTier(StrEnum):
    EXACT = "exact"
    STRONG = "strong_fuzzy"
    WEAK = "weak_fuzzy"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class SanctionsRecord:
    source: str
    source_record_id: str
    primary_name: str
    aliases: tuple[str, ...] = ()
    programs: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    source_url: str = ""


@dataclass(frozen=True, slots=True)
class ScreeningQuery:
    name: str
    countries: tuple[str, ...] = ()
    external_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScreeningHit:
    source: str
    source_record_id: str
    matched_name: str
    score: float
    risk_tier: RiskTier
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    query: ScreeningQuery
    hits: tuple[ScreeningHit, ...] = field(default_factory=tuple)
    dataset_snapshot_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def review_required(self) -> bool:
        return any(hit.risk_tier is not RiskTier.CLEAR for hit in self.hits)

