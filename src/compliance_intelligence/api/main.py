from __future__ import annotations

from fastapi import FastAPI, HTTPException

from compliance_intelligence.api.schemas import (
    HealthResponse,
    HitResponse,
    ScreenRequest,
    ScreenResponse,
)
from compliance_intelligence.domain.models import SanctionsRecord, ScreeningQuery
from compliance_intelligence.matching.engine import screen_records


DISCLAIMER = (
    "Potential matches require human review and source verification; this output is not a "
    "compliance determination."
)


def create_app(
    records: list[SanctionsRecord] | None = None,
    snapshot_ids: tuple[str, ...] = (),
) -> FastAPI:
    app = FastAPI(
        title="Compliance Intelligence Platform",
        version="0.1.0",
        description="Auditable public-data screening and extraction portfolio",
    )
    loaded_records = records or []

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            datasets_loaded=bool(snapshot_ids),
            dataset_snapshot_ids=list(snapshot_ids),
        )

    @app.post("/v1/screen", response_model=ScreenResponse)
    def screen(request: ScreenRequest) -> ScreenResponse:
        if not snapshot_ids:
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


app = create_app()

