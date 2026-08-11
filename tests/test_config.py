import pytest

from compliance_intelligence.config import Settings


def test_threshold_env_overrides_reach_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMUM_MATCH_SCORE", "80.5")
    monkeypatch.setenv("STRONG_MATCH_SCORE", "91")
    monkeypatch.setenv("EXACT_MATCH_SCORE", "99.9")
    thresholds = Settings(_env_file=None).matching_thresholds()
    assert thresholds.minimum == 80.5
    assert thresholds.strong == 91.0
    assert thresholds.exact == 99.9


def test_misordered_threshold_env_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMUM_MATCH_SCORE", "95")
    monkeypatch.setenv("STRONG_MATCH_SCORE", "80")
    with pytest.raises(ValueError):
        Settings(_env_file=None).matching_thresholds()


def test_synthetic_data_is_blocked_by_default() -> None:
    assert Settings(_env_file=None).allow_synthetic_dataset is False
