from __future__ import annotations

from collections.abc import Sequence

from compliance_intelligence.retrieval.index import SearchHit

# Fixed a priori (standard RRF constant) so the hybrid mode is never tuned on
# the evaluation queries; the BM25 / dense / hybrid comparison stays honest.
RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[SearchHit]], limit: int = 10
) -> tuple[SearchHit, ...]:
    """Fuse ranked lists by reciprocal rank; no score normalization required."""

    fused_scores: dict[str, float] = {}
    first_seen: dict[str, SearchHit] = {}
    for ranked in ranked_lists:
        for rank, hit in enumerate(ranked, start=1):
            fused_scores[hit.document_id] = fused_scores.get(hit.document_id, 0.0) + 1.0 / (
                RRF_K + rank
            )
            first_seen.setdefault(hit.document_id, hit)
    ordered = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    return tuple(
        SearchHit(
            document_id=document_id,
            score=round(score, 6),
            title=first_seen[document_id].title,
            snippet=first_seen[document_id].snippet,
        )
        for document_id, score in ordered
    )
