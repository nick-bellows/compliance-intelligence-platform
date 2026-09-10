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
    assert response.json()["status"] == "unavailable"


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


def _write_synthetic_snapshot(
    directory: Path, retrieved_at: datetime = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
) -> None:
    save_snapshot(
        SourceSnapshot(
            snapshot_id="synthetic-fixture-test1234",
            source_name="SYNTHETIC_LIST",
            source_url="data/samples/synthetic_sanctions_fixture.csv",
            retrieved_at=retrieved_at,
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


def test_health_reports_fresh_snapshot_as_ok(tmp_path: Path) -> None:
    _write_synthetic_snapshot(tmp_path, retrieved_at=datetime.now(UTC))
    settings = Settings(_env_file=None, snapshot_directory=tmp_path, allow_synthetic_dataset=True)
    body = TestClient(build_app_from_settings(settings)).get("/health").json()
    assert body["status"] == "ok"
    assert body["snapshots"][0]["stale"] is False


def test_health_degrades_when_snapshot_exceeds_max_age(tmp_path: Path) -> None:
    _write_synthetic_snapshot(tmp_path, retrieved_at=datetime(2025, 1, 1, tzinfo=UTC))
    settings = Settings(_env_file=None, snapshot_directory=tmp_path, allow_synthetic_dataset=True)
    body = TestClient(build_app_from_settings(settings)).get("/health").json()
    assert body["status"] == "degraded"
    assert body["snapshots"][0]["stale"] is True
    assert body["snapshots"][0]["retrieved_at_utc"].startswith("2025-01-01")



def _one_record() -> list[SanctionsRecord]:
    return [
        SanctionsRecord(
            source="SYNTHETIC_LIST",
            source_record_id="FAKE-001",
            primary_name="Acme Galactic Holdings",
        )
    ]


def test_screen_rejects_names_with_nothing_to_compare() -> None:
    client = TestClient(create_app(_one_record(), ("synthetic-fixture-v1",)))
    for name in (" ", "\t\n", "***", "\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440"):
        assert client.post("/v1/screen", json={"name": name}).status_code == 422


def test_screen_rejects_oversized_country_values() -> None:
    client = TestClient(create_app(_one_record(), ("synthetic-fixture-v1",)))
    response = client.post("/v1/screen", json={"name": "Acme", "countries": ["x" * 101]})
    assert response.status_code == 422


def test_screen_fails_closed_when_loaded_snapshot_has_no_records() -> None:
    client = TestClient(create_app([], ("ofac_primary-20260910-000000000000",)))
    health = client.get("/health").json()
    assert health["datasets_loaded"] is False
    assert health["status"] == "unavailable"
    assert client.post("/v1/screen", json={"name": "Anyone"}).status_code == 503


def _ofac_snapshot(snapshot_id: str, retrieved_at: datetime, name: str) -> SourceSnapshot:
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        source_name="OFAC_SDN",
        source_url="https://example.invalid/sdn.xml",
        retrieved_at=retrieved_at,
        sha256=(snapshot_id[-12:] * 6)[:64],
        terms_note="test",
        records=(SanctionsRecord(source="OFAC_SDN", source_record_id=name, primary_name=name),),
    )


def test_settings_app_serves_only_the_newest_snapshot_per_source(tmp_path: Path) -> None:
    save_snapshot(
        _ofac_snapshot(
            "ofac_primary-20260801-aaaaaaaaaaaa",
            datetime(2026, 8, 1, tzinfo=UTC),
            "Delisted Alpha Trading",
        ),
        tmp_path,
    )
    save_snapshot(
        _ofac_snapshot(
            "ofac_primary-20260901-bbbbbbbbbbbb",
            datetime(2026, 9, 1, tzinfo=UTC),
            "Zulu Maritime Nine",
        ),
        tmp_path,
    )
    client = TestClient(build_app_from_settings(Settings(_env_file=None, snapshot_directory=tmp_path)))
    assert client.get("/health").json()["dataset_snapshot_ids"] == [
        "ofac_primary-20260901-bbbbbbbbbbbb"
    ]
    # The delisted name is only in the superseded snapshot, so it must not hit.
    delisted = client.post("/v1/screen", json={"name": "Delisted Alpha Trading"}).json()
    assert delisted["hits"] == []
    assert delisted["review_required"] is False
    current = client.post("/v1/screen", json={"name": "Zulu Maritime Nine"}).json()
    assert current["review_required"] is True
    assert current["hits"][0]["source_record_id"] == "Zulu Maritime Nine"
