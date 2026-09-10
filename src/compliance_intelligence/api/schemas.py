from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from compliance_intelligence.matching.normalization import normalize_entity_name

CountryValue = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class ScreenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    countries: list[CountryValue] = Field(default_factory=list, max_length=20)
    external_id: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def name_must_be_screenable(cls, value: str) -> str:
        # A name that normalizes to nothing (whitespace, punctuation, or a script the
        # normalizer cannot represent) cannot be screened. Rejecting it is the
        # fail-closed choice; screening it would report a false "clear".
        if not normalize_entity_name(value):
            raise ValueError(
                "name has no comparable characters after normalization; "
                "non-Latin scripts are not supported by this matcher (see docs/limitations.md)"
            )
        return value


class HitResponse(BaseModel):
    source: str
    source_record_id: str
    matched_name: str
    score: float
    risk_tier: str
    reasons: list[str]


class ScreenResponse(BaseModel):
    query_name: str
    review_required: bool
    dataset_snapshot_ids: list[str]
    hits: list[HitResponse]
    disclaimer: str


class SnapshotHealth(BaseModel):
    snapshot_id: str
    retrieved_at_utc: str | None
    stale: bool


class HealthResponse(BaseModel):
    # "unavailable": nothing screenable is loaded and /v1/screen returns 503;
    # "degraded": loaded, but at least one snapshot exceeds the maximum age; else "ok".
    status: str
    datasets_loaded: bool
    dataset_snapshot_ids: list[str]
    snapshots: list[SnapshotHealth] = Field(default_factory=list)
