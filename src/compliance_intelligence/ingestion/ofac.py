from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.ingestion.http import download_bytes

OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
SOURCE_ID = "ofac_primary"
SOURCE_NAME = "OFAC_SDN"
TERMS_NOTE = (
    "OFAC Specially Designated Nationals list published by the U.S. Department of the "
    "Treasury; U.S. federal government work, public domain (17 U.S.C. 105)."
)


def _local(tag: str) -> str:
    """Element tag without its XML namespace; the OFAC namespace URI has churned before."""
    return tag.rpartition("}")[2]


def _children(element: Element, name: str) -> list[Element]:
    return [child for child in element if _local(child.tag) == name]


def _child_text(element: Element, name: str) -> str:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _person_name(element: Element) -> str:
    parts = (_child_text(element, "firstName"), _child_text(element, "lastName"))
    return " ".join(part for part in parts if part)


def _parse_entry(entry: Element) -> SanctionsRecord:
    uid = _child_text(entry, "uid")
    sdn_type = _child_text(entry, "sdnType")
    if not uid or not sdn_type:
        raise ValueError("SDN entry is missing uid or sdnType; schema may have drifted")
    primary_name = (
        _person_name(entry) if sdn_type == "Individual" else _child_text(entry, "lastName")
    )
    if not primary_name:
        raise ValueError(f"SDN entry {uid} has no primary name; schema may have drifted")

    aliases: list[str] = []
    for aka_list in _children(entry, "akaList"):
        for aka in _children(aka_list, "aka"):
            alias = _person_name(aka)
            if alias:
                aliases.append(alias)

    programs: list[str] = []
    for program_list in _children(entry, "programList"):
        for program in _children(program_list, "program"):
            if program.text and program.text.strip():
                programs.append(program.text.strip())

    countries: list[str] = []
    for address_list in _children(entry, "addressList"):
        for address in _children(address_list, "address"):
            country = _child_text(address, "country")
            if country and country not in countries:
                countries.append(country)

    return SanctionsRecord(
        source=SOURCE_NAME,
        source_record_id=uid,
        primary_name=primary_name,
        aliases=tuple(aliases),
        programs=tuple(programs),
        countries=tuple(countries),
        source_url=OFAC_SDN_URL,
    )


def parse_sdn_xml(payload: bytes) -> tuple[SanctionsRecord, ...]:
    root = fromstring(payload)
    if _local(root.tag) != "sdnList":
        raise ValueError(f"Unexpected root element {root.tag!r}; expected sdnList")
    publish_info = next(iter(_children(root, "publshInformation")), None)
    if publish_info is None:
        raise ValueError("SDN.XML is missing publshInformation; schema may have drifted")
    declared_count = int(_child_text(publish_info, "Record_Count"))
    records = tuple(_parse_entry(entry) for entry in _children(root, "sdnEntry"))
    if len(records) != declared_count:
        raise ValueError(
            f"SDN.XML declares {declared_count} records but {len(records)} were parsed"
        )
    if not records:
        # A well-formed file that declares and contains zero entries is still not a
        # screenable list; accepting it would make every screen come back "clear".
        raise ValueError("SDN.XML parsed to zero records")
    return records


class OfacAdapter:
    """Official OFAC SDN list adapter: download, hash, persist raw, parse, reconcile."""

    def __init__(self, raw_directory: Path, url: str = OFAC_SDN_URL) -> None:
        self._raw_directory = raw_directory
        self._url = url

    def fetch(self) -> SourceSnapshot:
        payload = download_bytes(self._url)
        retrieved_at = datetime.now(UTC)
        digest = hashlib.sha256(payload).hexdigest()
        # Keyed by date and content hash, like the snapshot ID, so a second fetch on
        # the same day cannot overwrite the bytes an earlier snapshot's sha256 names.
        raw_dir = self._raw_directory / SOURCE_ID / f"{retrieved_at:%Y%m%d}-{digest[:12]}"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "SDN.XML").write_bytes(payload)
        records = parse_sdn_xml(payload)
        return SourceSnapshot(
            snapshot_id=f"{SOURCE_ID}-{retrieved_at.strftime('%Y%m%d')}-{digest[:12]}",
            source_name=SOURCE_NAME,
            source_url=self._url,
            retrieved_at=retrieved_at,
            sha256=digest,
            terms_note=TERMS_NOTE,
            records=records,
        )
