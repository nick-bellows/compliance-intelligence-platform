from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: str
    score: float
    title: str
    snippet: str


class RetrievalIndex:
    """BM25 index boundary; implementation begins after corpus licensing review."""

    def build(self, documents: list[dict[str, str]]) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int = 10) -> tuple[SearchHit, ...]:
        raise NotImplementedError

