from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from compliance_intelligence.corpus.models import CorpusDocument
from compliance_intelligence.corpus.store import save_corpus
from compliance_intelligence.ingestion.http import USER_AGENT
from compliance_intelligence.ingestion.manifest import mark_source_active

API_URL = "https://www.federalregister.gov/api/v1/documents.json"
AGENCY_SLUG = "foreign-assets-control-office"
SOURCE_ID = "federal_register_corpus"
TERMS_NOTE = (
    "Federal Register OFAC notices retrieved via the federalregister.gov API; "
    "U.S. federal government works, public domain (17 U.S.C. 105)."
)
# The corpus tolerates individual document failures (a notice occasionally lacks
# full text), but a low success rate means the API contract changed: fail closed.
MINIMUM_SUCCESS_RATE = 0.9


def fetch_document_index(client: httpx.Client, document_count: int) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    page = 1
    while len(entries) < document_count:
        response = client.get(
            API_URL,
            params={
                "conditions[agencies][]": AGENCY_SLUG,
                "conditions[type][]": "NOTICE",
                "per_page": min(100, document_count - len(entries)),
                "page": page,
                "order": "newest",
                "fields[]": [
                    "document_number",
                    "title",
                    "publication_date",
                    "raw_text_url",
                    "html_url",
                ],
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            break
        entries.extend(results)
        page += 1
    return entries[:document_count]


def ingest_corpus(
    raw_directory: Path,
    corpus_path: Path,
    manifest_path: Path,
    document_count: int = 200,
) -> tuple[int, str]:
    """Fetch OFAC Federal Register notices into corpus.jsonl and update the manifest."""

    retrieved_at = datetime.now(UTC)
    with httpx.Client(
        timeout=60.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        index = fetch_document_index(client, document_count)
        raw_dir = raw_directory / SOURCE_ID / retrieved_at.strftime("%Y%m%d")
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "document_index.json").write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )

        documents: list[CorpusDocument] = []
        failures = 0
        for entry in index:
            raw_text_url = entry.get("raw_text_url")
            if not raw_text_url:
                failures += 1
                continue
            try:
                response = client.get(raw_text_url)
                response.raise_for_status()
            except httpx.HTTPError:
                failures += 1
                continue
            text = response.text.strip()
            if not text:
                failures += 1
                continue
            documents.append(
                CorpusDocument(
                    doc_id=entry["document_number"],
                    title=entry["title"],
                    text=text,
                    publication_date=entry["publication_date"],
                    source_url=entry["html_url"],
                )
            )

    if not index or len(documents) / len(index) < MINIMUM_SUCCESS_RATE:
        raise ValueError(
            f"Corpus ingest retrieved {len(documents)} of {len(index)} documents; "
            "the API contract may have changed"
        )

    save_corpus(documents, corpus_path)
    sha256 = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    mark_source_active(
        manifest_path,
        SOURCE_ID,
        authoritative_url=API_URL,
        format_name="jsonl",
        terms_note=TERMS_NOTE,
        retrieved_at=retrieved_at,
        sha256=sha256,
        record_count=len(documents),
    )
    return len(documents), sha256
