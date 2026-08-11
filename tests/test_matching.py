import pytest

from compliance_intelligence.domain.models import RiskTier, SanctionsRecord, ScreeningQuery
from compliance_intelligence.matching.engine import (
    MatchingThresholds,
    classify_score,
    screen_records,
    similarity,
)
from compliance_intelligence.matching.normalization import normalize_country, normalize_entity_name


def test_normalization_is_deterministic() -> None:
    assert normalize_entity_name("  ÁCME—Galactic, LLC ") == "acme galactic llc"


def test_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        MatchingThresholds(minimum=90, strong=80, exact=99)


def test_score_classification() -> None:
    thresholds = MatchingThresholds()
    assert classify_score(100, thresholds) is RiskTier.EXACT
    assert classify_score(96, thresholds) is RiskTier.STRONG
    assert classify_score(92, thresholds) is RiskTier.WEAK
    assert classify_score(80, thresholds) is RiskTier.CLEAR


def test_screening_requires_snapshot_provenance() -> None:
    with pytest.raises(ValueError):
        screen_records(ScreeningQuery(name="Example"), [], ())


def test_screening_returns_explainable_synthetic_candidate() -> None:
    records = [
        SanctionsRecord(
            source="SYNTHETIC_LIST",
            source_record_id="FAKE-001",
            primary_name="Acme Galactic Holdings",
            aliases=("Galactic Acme Holding",),
        )
    ]
    result = screen_records(
        ScreeningQuery(name="Galactic Acme Holding"),
        records,
        ("synthetic-fixture-v1",),
    )
    assert result.review_required is True
    assert result.hits[0].source_record_id == "FAKE-001"
    assert result.hits[0].reasons


def test_similarity_is_bounded_and_symmetric() -> None:
    pairs = [
        ("Acme Galactic Holdings", "Galactic Acme Holding"),
        ("ACME", "Contoso"),
        ("", "Anything"),
    ]
    for left, right in pairs:
        score, _ = similarity(left, right)
        assert 0.0 <= score <= 100.0
        assert score == similarity(right, left)[0]


def test_similarity_self_match_is_exact_after_normalization() -> None:
    score, _ = similarity("  ÁCME—Galactic, LLC ", "acme galactic llc")
    assert score == 100.0


def test_token_reorder_scores_full_match() -> None:
    score, reasons = similarity("Holdings Galactic Acme", "Acme Galactic Holdings")
    assert score == 100.0
    assert "token_order_normalized" in reasons


def test_normalize_country_maps_names_and_codes() -> None:
    assert normalize_country("United States") == "US"
    assert normalize_country("us") == "US"
    assert normalize_country("Russian Federation") == "RU"
    assert normalize_country("Freedonia") == "freedonia"


def test_country_overlap_annotates_without_gating() -> None:
    records = [
        SanctionsRecord(
            source="SYNTHETIC_LIST",
            source_record_id="FAKE-001",
            primary_name="Acme Galactic Holdings",
            countries=("United States",),
        )
    ]
    overlapping = screen_records(
        ScreeningQuery(name="Acme Galactic Holdings", countries=("US",)),
        records,
        ("synthetic-fixture-v1",),
    )
    assert "country_overlap" in overlapping.hits[0].reasons

    disjoint = screen_records(
        ScreeningQuery(name="Acme Galactic Holdings", countries=("FR",)),
        records,
        ("synthetic-fixture-v1",),
    )
    assert disjoint.hits[0].risk_tier is RiskTier.EXACT
    assert "country_overlap" not in disjoint.hits[0].reasons

