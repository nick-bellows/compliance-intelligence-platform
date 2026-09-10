from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from compliance_intelligence.api.schemas import (
    HealthResponse,
    HitResponse,
    ScreenRequest,
    ScreenResponse,
    SnapshotHealth,
)
from compliance_intelligence.config import Settings, settings
from compliance_intelligence.domain.models import SanctionsRecord, ScreeningQuery
from compliance_intelligence.ingestion.store import load_screening_snapshots
from compliance_intelligence.matching.engine import MatchingThresholds, screen_records

DISCLAIMER = (
    "Potential matches require human review and source verification; this output is not a "
    "compliance determination."
)


def create_app(
    records: list[SanctionsRecord] | None = None,
    snapshot_ids: tuple[str, ...] = (),
    thresholds: MatchingThresholds | None = None,
    snapshot_retrieved_at: dict[str, datetime] | None = None,
    max_snapshot_age_days: int | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Compliance Intelligence Platform",
        version="0.1.0",
        description="Auditable public-data screening and extraction portfolio",
    )
    loaded_records = records or []
    # Screenable means a verified snapshot is loaded AND it carries records. A
    # snapshot with zero records must never turn into a "clear" result.
    screenable = bool(snapshot_ids) and bool(loaded_records)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        now = datetime.now(UTC)
        snapshots: list[SnapshotHealth] = []
        degraded = False
        for snapshot_id in snapshot_ids:
            retrieved_at = (snapshot_retrieved_at or {}).get(snapshot_id)
            stale = bool(
                retrieved_at is not None
                and max_snapshot_age_days is not None
                and (now - retrieved_at).days > max_snapshot_age_days
            )
            degraded = degraded or stale
            snapshots.append(
                SnapshotHealth(
                    snapshot_id=snapshot_id,
                    retrieved_at_utc=retrieved_at.isoformat() if retrieved_at else None,
                    stale=stale,
                )
            )
        if not screenable:
            status = "unavailable"
        elif degraded:
            status = "degraded"
        else:
            status = "ok"
        return HealthResponse(
            status=status,
            datasets_loaded=screenable,
            dataset_snapshot_ids=list(snapshot_ids),
            snapshots=snapshots,
        )

    @app.post("/v1/screen", response_model=ScreenResponse)
    def screen(request: ScreenRequest) -> ScreenResponse:
        if not screenable:
            raise HTTPException(
                status_code=503,
                detail="No verified sanctions dataset snapshot is loaded; screening is unavailable.",
            )
        result = screen_records(
            ScreeningQuery(
                name=request.name,
                countries=tuple(request.countries),
                external_id=request.external_id,
            ),
            loaded_records,
            snapshot_ids,
            thresholds,
        )
        return ScreenResponse(
            query_name=request.name,
            review_required=result.review_required,
            dataset_snapshot_ids=list(result.dataset_snapshot_ids),
            hits=[
                HitResponse(
                    source=hit.source,
                    source_record_id=hit.source_record_id,
                    matched_name=hit.matched_name,
                    score=hit.score,
                    risk_tier=hit.risk_tier,
                    reasons=list(hit.reasons),
                )
                for hit in result.hits
            ],
            disclaimer=DISCLAIMER,
        )

    return app


def build_app_from_settings(app_settings: Settings) -> FastAPI:
    """Build the app from on-disk snapshots; with none available it stays fail-closed."""

    snapshots = load_screening_snapshots(
        app_settings.snapshot_directory,
        app_settings.allow_synthetic_dataset,
    )
    records = [record for snapshot in snapshots for record in snapshot.records]
    snapshot_ids = tuple(snapshot.snapshot_id for snapshot in snapshots)
    return create_app(
        records,
        snapshot_ids,
        app_settings.matching_thresholds(),
        {snapshot.snapshot_id: snapshot.retrieved_at for snapshot in snapshots},
        app_settings.max_snapshot_age_days,
    )


app = build_app_from_settings(settings)

