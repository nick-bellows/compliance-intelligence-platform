import pytest

from compliance_intelligence.retrieval.hybrid import RRF_K, reciprocal_rank_fusion
from compliance_intelligence.retrieval.index import RetrievalIndex, SearchHit, tokenize

DOCUMENTS = [
    {
        "document_id": "doc-1",
        "title": "Narcotics trafficking designations",
        "text": "OFAC designated three entities for narcotics trafficking in the region.",
    },
    {
        "document_id": "doc-2",
        "title": "Counter-terrorism designations",
        "text": "Entities designated under counter-terrorism authorities.",
    },
    {
        "document_id": "doc-3",
        "title": "Vessel identification update",
        "text": "A cargo vessel was identified as blocked property.",
    },
]


def test_tokenize_lowercases_and_splits() -> None:
    assert tokenize("OFAC-designated Entities, 2026!") == [
        "ofac",
        "designated",
        "entities",
        "2026",
    ]


def test_bm25_ranks_topical_document_first() -> None:
    index = RetrievalIndex()
    index.build(DOCUMENTS)
    hits = index.search("narcotics trafficking")
    assert hits
    assert hits[0].document_id == "doc-1"


def test_bm25_build_requires_documents() -> None:
    with pytest.raises(ValueError):
        RetrievalIndex().build([])


def test_bm25_search_requires_build() -> None:
    with pytest.raises(RuntimeError):
        RetrievalIndex().search("anything")


def _hit(document_id: str, score: float) -> SearchHit:
    return SearchHit(document_id=document_id, score=score, title=document_id, snippet="")


def test_rrf_fuses_by_reciprocal_rank() -> None:
    bm25_ranked = [_hit("a", 10.0), _hit("b", 5.0)]
    dense_ranked = [_hit("b", 0.9), _hit("c", 0.8)]
    fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])
    assert [hit.document_id for hit in fused] == ["b", "a", "c"]
    expected_b = 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert fused[0].score == round(expected_b, 6)


def test_rrf_respects_limit() -> None:
    fused = reciprocal_rank_fusion([[_hit("a", 1.0), _hit("b", 0.5), _hit("c", 0.2)]], limit=2)
    assert len(fused) == 2


@pytest.mark.requires_models
def test_dense_index_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("sentence_transformers")
    from compliance_intelligence.retrieval.dense import DenseIndex

    dense = DenseIndex(tmp_path)
    dense.build(DOCUMENTS)
    hits = dense.search("drug trafficking sanctions", limit=2)
    assert len(hits) == 2
    assert hits[0].document_id == "doc-1"

    cached = DenseIndex(tmp_path)
    cached.build(DOCUMENTS)
    assert cached.search("drug trafficking sanctions", limit=1)[0].document_id == "doc-1"
