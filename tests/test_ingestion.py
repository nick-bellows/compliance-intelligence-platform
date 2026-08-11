import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from compliance_intelligence.ingestion.manifest import mark_source_active
from compliance_intelligence.ingestion.ofac import OfacAdapter, parse_sdn_xml
from compliance_intelligence.ingestion.un import UnConsolidatedAdapter, parse_consolidated_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SDN_FIXTURE = (FIXTURES / "sdn_fixture.xml").read_bytes()
UN_FIXTURE = (FIXTURES / "un_fixture.xml").read_bytes()


def test_ofac_parse_entity_and_individual() -> None:
    records = parse_sdn_xml(SDN_FIXTURE)
    assert len(records) == 2

    entity = records[0]
    assert entity.source == "OFAC_SDN"
    assert entity.source_record_id == "90001"
    assert entity.primary_name == "ACME GALACTIC HOLDINGS"
    assert entity.aliases == ("GALACTIC ACME HOLDING",)
    assert entity.programs == ("SAMPLE_PROGRAM",)
    assert entity.countries == ("United States",)

    individual = records[1]
    assert individual.primary_name == "Jane DOEBERG"
    assert individual.aliases == ("Janie DOEBERG",)
    assert individual.programs == ("SAMPLE_PROGRAM", "SECOND_PROGRAM")


def test_ofac_record_count_mismatch_is_rejected() -> None:
    tampered = SDN_FIXTURE.replace(b"<Record_Count>2<", b"<Record_Count>5<")
    with pytest.raises(ValueError):
        parse_sdn_xml(tampered)


def test_ofac_unexpected_root_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_sdn_xml(b"<wrongRoot></wrongRoot>")


def test_un_parse_individual_and_entity() -> None:
    records = parse_consolidated_xml(UN_FIXTURE)
    assert len(records) == 2

    individual = records[0]
    assert individual.source == "UN_CONSOLIDATED"
    assert individual.source_record_id == "XXi.001"
    assert individual.primary_name == "JOHN QUIXOTE TESTMAN"
    assert individual.aliases == ("Johnny Testman",)
    assert individual.programs == ("SAMPLE",)
    assert individual.countries == ("Freedonia",)

    entity = records[1]
    assert entity.source_record_id == "XXe.001"
    assert entity.primary_name == "CONTOSO MARITIME GROUP"
    assert entity.aliases == ("Contoso Marine",)
    assert entity.countries == ("Sylvania",)


def test_un_missing_sections_are_rejected() -> None:
    with pytest.raises(ValueError):
        parse_consolidated_xml(b"<CONSOLIDATED_LIST><INDIVIDUALS/></CONSOLIDATED_LIST>")


def test_ofac_adapter_fetch_records_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "compliance_intelligence.ingestion.ofac.download_bytes", lambda url: SDN_FIXTURE
    )
    snapshot = OfacAdapter(tmp_path).fetch()
    assert snapshot.snapshot_id.startswith("ofac_primary-")
    assert snapshot.snapshot_id.endswith(snapshot.sha256[:12])
    assert len(snapshot.records) == 2
    raw_files = list(tmp_path.rglob("SDN.XML"))
    assert len(raw_files) == 1
    assert raw_files[0].read_bytes() == SDN_FIXTURE


def test_un_adapter_fetch_records_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "compliance_intelligence.ingestion.un.download_bytes", lambda url: UN_FIXTURE
    )
    snapshot = UnConsolidatedAdapter(tmp_path).fetch()
    assert snapshot.snapshot_id.startswith("un_consolidated-")
    assert len(snapshot.records) == 2
    assert list(tmp_path.rglob("consolidated.xml"))


def test_manifest_updater_flips_source_to_active(tmp_path: Path) -> None:
    manifest_path = tmp_path / "source-manifest.json"
    repo_manifest = Path(__file__).resolve().parents[1] / "data" / "source-manifest.json"
    manifest_path.write_text(repo_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    mark_source_active(
        manifest_path,
        "ofac_primary",
        authoritative_url="https://example.invalid/SDN.XML",
        format_name="xml",
        terms_note="public domain",
        retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
        sha256="c" * 64,
        record_count=2,
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    ofac_entry = next(s for s in payload["sources"] if s["source_id"] == "ofac_primary")
    assert ofac_entry["status"] == "active"
    assert ofac_entry["record_count"] == 2
    assert ofac_entry["sha256"] == "c" * 64


def test_manifest_updater_rejects_unregistered_source(tmp_path: Path) -> None:
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text('{"sources": []}', encoding="utf-8")
    with pytest.raises(KeyError):
        mark_source_active(
            manifest_path,
            "unknown_source",
            authoritative_url="https://example.invalid",
            format_name="xml",
            terms_note="n/a",
            retrieved_at=datetime(2026, 8, 10, tzinfo=UTC),
            sha256="d" * 64,
            record_count=0,
        )
