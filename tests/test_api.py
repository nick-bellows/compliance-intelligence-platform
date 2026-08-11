from fastapi.testclient import TestClient

from compliance_intelligence.api.main import create_app
from compliance_intelligence.domain.models import SanctionsRecord


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

