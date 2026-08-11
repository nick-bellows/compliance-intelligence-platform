"""Retrieval evaluation: BM25 vs dense vs hybrid on labeled queries.

All queries are holdout — nothing is tuned on them (BM25 uses library
defaults; RRF k is fixed a priori). Relevance judgments are doc-level,
derived from anchor-phrase containment as documented in the queries file.
Requires the [retrieval] extra.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from compliance_intelligence.corpus.store import dense_view, load_corpus
from compliance_intelligence.retrieval.dense import MODEL_NAME, DenseIndex
from compliance_intelligence.retrieval.hybrid import RRF_K, reciprocal_rank_fusion
from compliance_intelligence.retrieval.index import RetrievalIndex, SearchHit

ROOT = Path(__file__).resolve().parents[1]
QUERIES_PATH = ROOT / "eval" / "data" / "retrieval_queries.csv"
CORPUS_PATH = ROOT / "data" / "processed" / "corpus" / "corpus.jsonl"
CORPUS_CACHE_DIR = ROOT / "data" / "processed" / "corpus"
RESULTS_DIR = ROOT / "eval" / "results"
RECALL_CUTOFFS = (1, 5, 10)
POOL_DEPTH = 20


def load_queries() -> list[dict[str, object]]:
    queries: list[dict[str, object]] = []
    with QUERIES_PATH.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            queries.append(
                {
                    "query_id": row["query_id"],
                    "query": row["query"],
                    "relevant": set(row["relevant_document_ids"].split("|")),
                }
            )
    return queries


def query_metrics(ranked: tuple[SearchHit, ...], relevant: set[str]) -> dict[str, float]:
    ranked_ids = [hit.document_id for hit in ranked]
    metrics: dict[str, float] = {}
    for cutoff in RECALL_CUTOFFS:
        metrics[f"recall@{cutoff}"] = round(
            len(set(ranked_ids[:cutoff]) & relevant) / len(relevant), 4
        )
    reciprocal_rank = 0.0
    for position, document_id in enumerate(ranked_ids, start=1):
        if document_id in relevant:
            reciprocal_rank = 1.0 / position
            break
    metrics["reciprocal_rank"] = round(reciprocal_rank, 4)
    return metrics


def evaluate() -> dict[str, object]:
    documents = [
        {
            "document_id": document.doc_id,
            "title": document.title,
            "text": document.text,
            "dense_text": dense_view(document),
        }
        for document in load_corpus(CORPUS_PATH)
    ]
    queries = load_queries()

    bm25 = RetrievalIndex()
    bm25.build(documents)
    dense = DenseIndex(CORPUS_CACHE_DIR)
    dense.build(documents)

    modes: dict[str, list[dict[str, object]]] = {"bm25": [], "dense": [], "hybrid": []}
    for entry in queries:
        query = str(entry["query"])
        relevant = entry["relevant"]
        assert isinstance(relevant, set)
        bm25_ranked = bm25.search(query, POOL_DEPTH)
        dense_ranked = dense.search(query, POOL_DEPTH)
        hybrid_ranked = reciprocal_rank_fusion([bm25_ranked, dense_ranked], max(RECALL_CUTOFFS))
        for mode, ranked in (
            ("bm25", bm25_ranked[: max(RECALL_CUTOFFS)]),
            ("dense", dense_ranked[: max(RECALL_CUTOFFS)]),
            ("hybrid", hybrid_ranked),
        ):
            modes[mode].append(
                {
                    "query_id": entry["query_id"],
                    "relevant_count": len(relevant),
                    **query_metrics(tuple(ranked), relevant),
                }
            )

    def aggregate(rows: list[dict[str, object]]) -> dict[str, float]:
        aggregated = {}
        for metric in [f"recall@{cutoff}" for cutoff in RECALL_CUTOFFS] + ["reciprocal_rank"]:
            aggregated[metric if metric != "reciprocal_rank" else "mrr"] = round(
                sum(float(row[metric]) for row in rows) / len(rows), 4
            )
        return aggregated

    return {
        "corpus_document_count": len(documents),
        "query_count": len(queries),
        "pool_depth": POOL_DEPTH,
        "rrf_k": RRF_K,
        "dense_model": MODEL_NAME,
        "aggregate": {mode: aggregate(rows) for mode, rows in modes.items()},
        "per_query": modes,
    }


def render_markdown(report: dict[str, object]) -> str:
    aggregate = report["aggregate"]
    assert isinstance(aggregate, dict)
    lines = [
        "# Retrieval evaluation report",
        "",
        f"Generated: {report['generated_at_utc']}",
        (
            f"Corpus: {report['corpus_document_count']} Federal Register notices; "
            f"{report['query_count']} labeled queries "
            f"(sha256 `{str(report['queries_sha256'])[:12]}…`). "
            f"Dense model `{report['dense_model']}`; RRF k={report['rrf_k']} fixed a priori. "
            "All queries are holdout; judgments are doc-level anchor-phrase containment "
            "(methodology and limitation documented in the queries file and eval/README.md)."
        ),
        "",
        "## Aggregate comparison",
        "",
        "| Mode | Recall@1 | Recall@5 | Recall@10 | MRR |",
        "|---|---|---|---|---|",
    ]
    for mode in ("bm25", "dense", "hybrid"):
        metrics = aggregate[mode]
        lines.append(
            f"| {mode} | {metrics['recall@1']:.3f} | {metrics['recall@5']:.3f} | "
            f"{metrics['recall@10']:.3f} | {metrics['mrr']:.3f} |"
        )
    lines += [
        "",
        "## Weakest queries (hybrid, by Recall@10)",
        "",
    ]
    per_query = report["per_query"]
    assert isinstance(per_query, dict)
    weakest = sorted(per_query["hybrid"], key=lambda row: float(row["recall@10"]))[:5]
    for row in weakest:
        lines.append(
            f"- `{row['query_id']}` recall@10={row['recall@10']} "
            f"(relevant docs: {row['relevant_count']})"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = evaluate()
    report["generated_at_utc"] = datetime.now(UTC).isoformat()
    report["queries_sha256"] = hashlib.sha256(QUERIES_PATH.read_bytes()).hexdigest()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "retrieval_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "retrieval_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"queries={report['query_count']}")
    for mode, metrics in report["aggregate"].items():  # type: ignore[union-attr]
        print(f"{mode}={metrics}")
    print(f"reports={RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
