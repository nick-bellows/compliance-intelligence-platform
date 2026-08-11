from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from compliance_intelligence.domain.models import (
    RiskTier,
    SanctionsRecord,
    ScreeningHit,
    ScreeningQuery,
    ScreeningResult,
)
from compliance_intelligence.matching.normalization import normalize_entity_name, token_sorted


@dataclass(frozen=True, slots=True)
class MatchingThresholds:
    minimum: float = 75.0
    strong: float = 90.0
    exact: float = 99.5

    def __post_init__(self) -> None:
        if not 0 <= self.minimum <= self.strong <= self.exact <= 100:
            raise ValueError("Thresholds must be ordered between 0 and 100")


def similarity(left: str, right: str) -> tuple[float, tuple[str, ...]]:
    left_normalized = normalize_entity_name(left)
    right_normalized = normalize_entity_name(right)
    direct = SequenceMatcher(None, left_normalized, right_normalized).ratio() * 100
    token = SequenceMatcher(None, token_sorted(left), token_sorted(right)).ratio() * 100
    reasons = ["normalized_sequence_similarity"]
    if token > direct:
        reasons.append("token_order_normalized")
    return round(max(direct, token), 2), tuple(reasons)


def classify_score(score: float, thresholds: MatchingThresholds) -> RiskTier:
    if score >= thresholds.exact:
        return RiskTier.EXACT
    if score >= thresholds.strong:
        return RiskTier.STRONG
    if score >= thresholds.minimum:
        return RiskTier.WEAK
    return RiskTier.CLEAR


def screen_records(
    query: ScreeningQuery,
    records: list[SanctionsRecord],
    snapshot_ids: tuple[str, ...],
    thresholds: MatchingThresholds | None = None,
) -> ScreeningResult:
    """Return explainable candidates; callers must ensure records are authoritative."""

    if not snapshot_ids:
        raise ValueError("At least one verified dataset snapshot ID is required")
    configured = thresholds or MatchingThresholds()
    hits: list[ScreeningHit] = []
    for record in records:
        candidates = (record.primary_name, *record.aliases)
        best_name = record.primary_name
        best_score = -1.0
        best_reasons: tuple[str, ...] = ()
        for candidate in candidates:
            score, reasons = similarity(query.name, candidate)
            if score > best_score:
                best_name, best_score, best_reasons = candidate, score, reasons
        tier = classify_score(best_score, configured)
        if tier is RiskTier.CLEAR:
            continue
        hits.append(
            ScreeningHit(
                source=record.source,
                source_record_id=record.source_record_id,
                matched_name=best_name,
                score=best_score,
                risk_tier=tier,
                reasons=best_reasons,
            )
        )
    hits.sort(key=lambda item: item.score, reverse=True)
    return ScreeningResult(query=query, hits=tuple(hits), dataset_snapshot_ids=snapshot_ids)

