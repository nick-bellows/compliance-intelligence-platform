from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from compliance_intelligence.matching.engine import MatchingThresholds


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file.

    Threshold defaults must mirror MatchingThresholds until the Phase 1
    evaluation versions them; MatchingThresholds is the single source of truth.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    data_directory: Path = Path("data")
    output_directory: Path = Path("output")
    snapshot_directory: Path = Path("data/processed/snapshots")
    allow_synthetic_dataset: bool = False
    minimum_match_score: float = 89.0
    strong_match_score: float = 95.0
    exact_match_score: float = 99.5

    def matching_thresholds(self) -> MatchingThresholds:
        return MatchingThresholds(
            minimum=self.minimum_match_score,
            strong=self.strong_match_score,
            exact=self.exact_match_score,
        )


settings = Settings()
