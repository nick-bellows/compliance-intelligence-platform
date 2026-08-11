import json
from pathlib import Path
from typing import Any, Self

import pytest

from compliance_intelligence.corpus.federal_register import ingest_corpus
from compliance_intelligence.corpus.models import CorpusDocument
from compliance_intelligence.corpus.store import dense_view, load_corpus, save_corpus


def _document(text: str = "Header boilerplate. SUPPLEMENTARY INFORMATION: The details.") -> (
    CorpusDocument
):
    return CorpusDocument(
        doc_id="2026-00001",
        title="Notice of Test Actions",
        text=text,
        publication_date="2026-08-01",
        source_url="https://example.invalid/doc",
    )


def test_corpus_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "corpus.jsonl"
    save_corpus([_document()], path)
    assert load_corpus(path) == [_document()]


def test_dense_view_starts_at_supplementary_information() -> None:
    assert dense_view(_document()).startswith("SUPPLEMENTARY INFORMATION")
    plain = _document(text="No marker anywhere in this text.")
    assert dense_view(plain) == plain.text


class _FakeResponse:
    def __init__(self, payload: Any = None, text: str = "") -> None:
        self._payload = payload
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.page_served = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, url: str, params: Any = None) -> _FakeResponse:
        if "documents.json" in url:
            if self.page_served:
                return _FakeResponse({"results": []})
            self.page_served = True
            return _FakeResponse(
                {
                    "results": [
                        {
                            "document_number": "2026-00001",
                            "title": "Notice One",
                            "publication_date": "2026-08-01",
                            "raw_text_url": "https://example.invalid/raw/1",
                            "html_url": "https://example.invalid/doc/1",
                        },
                        {
                            "document_number": "2026-00002",
                            "title": "Notice Two",
                            "publication_date": "2026-08-02",
                            "raw_text_url": "https://example.invalid/raw/2",
                            "html_url": "https://example.invalid/doc/2",
                        },
                    ]
                }
            )
        return _FakeResponse(text=f"Full text for {url}")


def _manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {"source_id": "federal_register_corpus", "status": "planned"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_ingest_corpus_writes_corpus_and_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "compliance_intelligence.corpus.federal_register.httpx.Client", _FakeClient
    )
    corpus_path = tmp_path / "corpus" / "corpus.jsonl"
    manifest_path = _manifest(tmp_path)

    count, sha256 = ingest_corpus(tmp_path / "raw", corpus_path, manifest_path, 2)
    assert count == 2
    assert len(sha256) == 64
    documents = load_corpus(corpus_path)
    assert [document.doc_id for document in documents] == ["2026-00001", "2026-00002"]
    assert list((tmp_path / "raw").rglob("document_index.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["sources"][0]["status"] == "active"
    assert manifest["sources"][0]["record_count"] == 2


def test_ingest_corpus_fails_closed_on_low_fetch_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _BrokenClient(_FakeClient):
        def get(self, url: str, params: Any = None) -> _FakeResponse:
            response = super().get(url, params)
            if "raw" in url:
                return _FakeResponse(text="   ")
            return response

    monkeypatch.setattr(
        "compliance_intelligence.corpus.federal_register.httpx.Client", _BrokenClient
    )
    with pytest.raises(ValueError):
        ingest_corpus(tmp_path / "raw", tmp_path / "corpus.jsonl", _manifest(tmp_path), 2)
