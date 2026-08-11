import pytest

from compliance_intelligence.domain.models import RiskTier, SanctionsRecord, ScreeningQuery
from compliance_intelligence.matching.engine import (
    MatchingThresholds,
    classify_score,
    screen_records,
)
from compliance_intelligence.matching.normalization import normalize_entity_name


def test_normalization_is_deterministic() -> None:
    assert normalize_entity_name("  ÁCME—Galactic, LLC ") == "acme galactic llc"


def test_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        MatchingThresholds(minimum=90, strong=80, exact=99)


def test_score_classification() -> None:
    thresholds = MatchingThresholds()
    assert classify_score(100, thresholds) is RiskTier.EXACT
    assert classify_score(92, thresholds) is RiskTier.STRONG
    assert classify_score(80, thresholds) is RiskTier.WEAK
    assert classify_score(50, thresholds) is RiskTier.CLEAR


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

