from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")
SNIPPET_LENGTH = 200


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: str
    score: float
    title: str
    snippet: str


class RetrievalIndex:
    """BM25 index over the corpus; rebuilt on load (milliseconds at corpus scale)."""

    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._documents: list[dict[str, str]] = []

    def build(self, documents: list[dict[str, str]]) -> None:
        if not documents:
            raise ValueError("Cannot build a retrieval index over zero documents")
        self._documents = documents
        self._bm25 = BM25Okapi(
            [tokenize(f"{document['title']} {document['text']}") for document in documents]
        )

    def search(self, query: str, limit: int = 10) -> tuple[SearchHit, ...]:
        if self._bm25 is None:
            raise RuntimeError("build() must run before search()")
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:limit]
        return tuple(
            SearchHit(
                document_id=self._documents[i]["document_id"],
                score=round(float(scores[i]), 4),
                title=self._documents[i]["title"],
                snippet=self._documents[i]["text"][:SNIPPET_LENGTH],
            )
            for i in ranked
            if scores[i] > 0
        )
