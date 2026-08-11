from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring

from compliance_intelligence.domain.models import SanctionsRecord
from compliance_intelligence.ingestion.base import SourceSnapshot
from compliance_intelligence.ingestion.http import download_bytes

UN_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
SOURCE_ID = "un_consolidated"
SOURCE_NAME = "UN_CONSOLIDATED"
TERMS_NOTE = (
    "UN Security Council Consolidated List, openly published by the United Nations "
    "for sanctions-compliance use; see https://www.un.org/en/about-us/terms-of-use. "
    "Endpoint serves GET only (HEAD returns 404)."
)

_INDIVIDUAL_NAME_PARTS = ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")


def _local(tag: str) -> str:
    return tag.rpartition("}")[2]


def _children(element: Element, name: str) -> list[Element]:
    return [child for child in element if _local(child.tag) == name]


def _child_text(element: Element, name: str) -> str:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _record_id(entry: Element) -> str:
    record_id = _child_text(entry, "REFERENCE_NUMBER") or _child_text(entry, "DATAID")
    if not record_id:
        raise ValueError("UN entry has neither REFERENCE_NUMBER nor DATAID")
    return record_id


def _aliases(entry: Element, alias_element: str) -> tuple[str, ...]:
    aliases: list[str] = []
    for alias in _children(entry, alias_element):
        name = _child_text(alias, "ALIAS_NAME")
        if name:
            aliases.append(name)
    return tuple(aliases)


def _countries(entry: Element, address_element: str) -> tuple[str, ...]:
    countries: list[str] = []
    for nationality in _children(entry, "NATIONALITY"):
        for value in _children(nationality, "VALUE"):
            if value.text and value.text.strip() and value.text.strip() not in countries:
                countries.append(value.text.strip())
    for address in _children(entry, address_element):
        country = _child_text(address, "COUNTRY")
        if country and country not in countries:
            countries.append(country)
    return tuple(countries)


def _parse_individual(entry: Element) -> SanctionsRecord:
    name = " ".join(
        part for part in (_child_text(entry, p) for p in _INDIVIDUAL_NAME_PARTS) if part
    )
    if not name:
        raise ValueError(f"UN individual {_record_id(entry)} has no name parts")
    return SanctionsRecord(
        source=SOURCE_NAME,
        source_record_id=_record_id(entry),
        primary_name=name,
        aliases=_aliases(entry, "INDIVIDUAL_ALIAS"),
        programs=(_child_text(entry, "UN_LIST_TYPE"),),
        countries=_countries(entry, "INDIVIDUAL_ADDRESS"),
        source_url=UN_CONSOLIDATED_URL,
    )


def _parse_entity(entry: Element) -> SanctionsRecord:
    name = _child_text(entry, "FIRST_NAME")
    if not name:
        raise ValueError(f"UN entity {_record_id(entry)} has no name")
    return SanctionsRecord(
        source=SOURCE_NAME,
        source_record_id=_record_id(entry),
        primary_name=name,
        aliases=_aliases(entry, "ENTITY_ALIAS"),
        programs=(_child_text(entry, "UN_LIST_TYPE"),),
        countries=_countries(entry, "ENTITY_ADDRESS"),
        source_url=UN_CONSOLIDATED_URL,
    )


def parse_consolidated_xml(payload: bytes) -> tuple[SanctionsRecord, ...]:
    root = fromstring(payload)
    if _local(root.tag) != "CONSOLIDATED_LIST":
        raise ValueError(f"Unexpected root element {root.tag!r}; expected CONSOLIDATED_LIST")
    individuals_container = next(iter(_children(root, "INDIVIDUALS")), None)
    entities_container = next(iter(_children(root, "ENTITIES")), None)
    if individuals_container is None or entities_container is None:
        raise ValueError("Consolidated list is missing INDIVIDUALS or ENTITIES sections")
    records = [
        _parse_individual(entry) for entry in _children(individuals_container, "INDIVIDUAL")
    ]
    records.extend(_parse_entity(entry) for entry in _children(entities_container, "ENTITY"))
    if not records:
        raise ValueError("Consolidated list parsed to zero records")
    return tuple(records)


class UnConsolidatedAdapter:
    """UN Security Council Consolidated List adapter (the project's secondary source)."""

    def __init__(self, raw_directory: Path, url: str = UN_CONSOLIDATED_URL) -> None:
        self._raw_directory = raw_directory
        self._url = url

    def fetch(self) -> SourceSnapshot:
        payload = download_bytes(self._url)
        retrieved_at = datetime.now(UTC)
        digest = hashlib.sha256(payload).hexdigest()
        raw_dir = self._raw_directory / SOURCE_ID / retrieved_at.strftime("%Y%m%d")
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "consolidated.xml").write_bytes(payload)
        records = parse_consolidated_xml(payload)
        return SourceSnapshot(
            snapshot_id=f"{SOURCE_ID}-{retrieved_at.strftime('%Y%m%d')}-{digest[:12]}",
            source_name=SOURCE_NAME,
            source_url=self._url,
            retrieved_at=retrieved_at,
            sha256=digest,
            terms_note=TERMS_NOTE,
            records=records,
        )
