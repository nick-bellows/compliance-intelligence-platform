from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    doc_id: str
    title: str
    text: str
    publication_date: str
    source_url: str
