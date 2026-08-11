# Model card — corpus retrieval

- **Modes**: BM25 (`rank-bm25` defaults, alnum tokenizer, rebuilt on load),
  dense (`sentence-transformers/all-MiniLM-L6-v2`, cosine over cached
  normalized embeddings), hybrid (reciprocal rank fusion, k=60 fixed a priori).
- **Evaluation**: `eval/run_retrieval_eval.py` over
  `eval/data/retrieval_queries.csv` — 24 queries, doc-level relevance judged by
  corpus-wide anchor-phrase containment (methodology recorded per query). All
  queries are holdout; nothing is tuned on them. Report:
  `eval/results/retrieval_report.md`.
- **Results summary**: BM25 Recall@10 0.818 / MRR 0.839; dense 0.546 / 0.726;
  hybrid 0.763 / **0.853** (best MRR and Recall@1). On this keyword-heavy corpus
  BM25 is a strong baseline; hybrid improves early precision; dense earns its
  keep on vocabulary-mismatch queries (e.g., English "Jalisco New Generation
  Cartel" vs Spanish document text).
- **Documented defect and fix**: initial dense retrieval was near-random
  (Recall@10 0.091) because every notice opens with identical boilerplate longer
  than the model's token window, making all document embeddings nearly
  identical. Documents are now encoded from their `SUPPLEMENTARY INFORMATION`
  section (`corpus.store.dense_view`) with versioned embedding-cache
  invalidation. Remaining limitation: a single window still truncates long
  designation lists — chunked encoding is future work.
- **Judgment caveat**: anchor-phrase containment approximates relevance for
  these single-topic notices; a document discussing a topic in unanchored
  wording would be scored as non-relevant.
