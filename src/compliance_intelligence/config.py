from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    data_directory: Path = Path("data")
    output_directory: Path = Path("output")
    minimum_match_score: float = 75.0
    strong_match_score: float = 90.0
    exact_match_score: float = 99.5


settings = Settings()

