from __future__ import annotations

from pydantic import BaseModel, Field


class ScreenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    countries: list[str] = Field(default_factory=list, max_length=20)
    external_id: str | None = Field(default=None, max_length=200)


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
    status: str
    datasets_loaded: bool
    dataset_snapshot_ids: list[str]
    snapshots: list[SnapshotHealth] = Field(default_factory=list)

