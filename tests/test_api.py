from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from compliance_intelligence.api.main import build_app_from_settings, create_app
from compliance_intelligence.config import Settings
from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.ingestion.store import save_snapshot
from compliance_intelligence.matching.engine import MatchingThresholds


def test_health_exposes_dataset_state() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["datasets_loaded"] is False


def test_screen_fails_closed_without_verified_data() -> None:
    client = TestClient(create_app())
    response = client.post("/v1/screen", json={"name": "Synthetic Example"})
    assert response.status_code == 503


def test_screen_returns_candidate_with_snapshot() -> None:
    records = [
        SanctionsRecord(
            source="SYNTHETIC_LIST",
            source_record_id="FAKE-001",
            primary_name="Acme Galactic Holdings",
        )
    ]
    client = TestClient(create_app(records, ("synthetic-fixture-v1",)))
    response = client.post("/v1/screen", json={"name": "Acme Galactic Holdings"})
    assert response.status_code == 200
    body = response.json()
    assert body["review_required"] is True
    assert body["dataset_snapshot_ids"] == ["synthetic-fixture-v1"]


def test_create_app_applies_injected_thresholds() -> None:
    records = [
        SanctionsRecord(
            source="SYNTHETIC_LIST",
            source_record_id="FAKE-001",
            primary_name="Acme Galactic Holdings",
        )
    ]
    strict = MatchingThresholds(minimum=99.0, strong=99.5, exact=100.0)
    client = TestClient(create_app(records, ("synthetic-fixture-v1",), strict))
    response = client.post("/v1/screen", json={"name": "Acme Galactic Holding"})
    assert response.status_code == 200
    assert response.json()["hits"] == []


def _write_synthetic_snapshot(directory: Path) -> None:
    save_snapshot(
        SourceSnapshot(
            snapshot_id="synthetic-fixture-test1234",
            source_name="SYNTHETIC_LIST",
            source_url="data/samples/synthetic_sanctions_fixture.csv",
            retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
            sha256="b" * 64,
            terms_note="synthetic",
            records=(
                SanctionsRecord(
                    source="SYNTHETIC_LIST",
                    source_record_id="FAKE-001",
                    primary_name="Acme Galactic Holdings",
                ),
            ),
        ),
        directory,
    )


def test_settings_app_blocks_synthetic_by_default(tmp_path: Path) -> None:
    _write_synthetic_snapshot(tmp_path)
    settings = Settings(_env_file=None, snapshot_directory=tmp_path)
    client = TestClient(build_app_from_settings(settings))
    assert client.get("/health").json()["datasets_loaded"] is False
    assert client.post("/v1/screen", json={"name": "Acme Galactic Holdings"}).status_code == 503


def test_settings_app_serves_synthetic_when_allowed(tmp_path: Path) -> None:
    _write_synthetic_snapshot(tmp_path)
    settings = Settings(_env_file=None, snapshot_directory=tmp_path, allow_synthetic_dataset=True)
    client = TestClient(build_app_from_settings(settings))
    assert client.get("/health").json()["datasets_loaded"] is True
    response = client.post("/v1/screen", json={"name": "Acme Galactic Holdings"})
    assert response.status_code == 200
    body = response.json()
    assert body["review_required"] is True
    assert body["dataset_snapshot_ids"] == ["synthetic-fixture-test1234"]

