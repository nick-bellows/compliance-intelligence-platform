from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from compliance_intelligence.domain.models import (
    RiskTier,
    SanctionsRecord,
    ScreeningHit,
    ScreeningQuery,
    ScreeningResult,
)
from compliance_intelligence.matching.normalization import normalize_country, normalize_entity_name

# Version every score-affecting change here; eval reports record it so thresholds
# are never reused across incompatible scorers.
SCORER_VERSION = "rapidfuzz-ratio-tokensort-v2"
# Bump whenever the default thresholds change, citing the eval report that justified it.
# v2: minimum 89.0 from the tune-split sweep in eval/results/matching_report.md
# (holdout precision 1.0 / recall 0.833); strong 95.0 separates single-edit from
# multi-edit variants; every labeled negative scored below 89.
THRESHOLDS_VERSION = "evaluated-2026.08-v2"


@dataclass(frozen=True, slots=True)
class MatchingThresholds:
    minimum: float = 89.0
    strong: float = 95.0
    exact: float = 99.5

    def __post_init__(self) -> None:
        if not 0 <= self.minimum <= self.strong <= self.exact <= 100:
            raise ValueError("Thresholds must be ordered between 0 and 100")


def similarity(left: str, right: str) -> tuple[float, tuple[str, ...]]:
    left_normalized = normalize_entity_name(left)
    right_normalized = normalize_entity_name(right)
    direct = fuzz.ratio(left_normalized, right_normalized)
    token = fuzz.token_sort_ratio(left_normalized, right_normalized)
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
    query_countries = {normalize_country(country) for country in query.countries}
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
        # Country overlap annotates the hit for reviewers; it never gates a name match.
        if query_countries and query_countries.intersection(
            normalize_country(country) for country in record.countries
        ):
            best_reasons = (*best_reasons, "country_overlap")
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

