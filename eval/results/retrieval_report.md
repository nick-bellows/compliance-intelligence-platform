# Retrieval evaluation report

Generated: 2026-08-11T02:56:08.630618+00:00
Corpus: 200 Federal Register notices; 24 labeled queries (sha256 `43f048e26777…`). Dense model `sentence-transformers/all-MiniLM-L6-v2`; RRF k=60 fixed a priori. All queries are holdout; judgments are doc-level anchor-phrase containment (methodology and limitation documented in the queries file and eval/README.md).

## Aggregate comparison

| Mode | Recall@1 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| bm25 | 0.241 | 0.658 | 0.818 | 0.839 |
| dense | 0.241 | 0.476 | 0.546 | 0.726 |
| hybrid | 0.267 | 0.607 | 0.763 | 0.853 |

## Weakest queries (hybrid, by Recall@10)

- `q004` recall@10=0.0833 (relevant docs: 12)
- `q014` recall@10=0.25 (relevant docs: 4)
- `q017` recall@10=0.3704 (relevant docs: 27)
- `q023` recall@10=0.4545 (relevant docs: 11)
- `q013` recall@10=0.5 (relevant docs: 14)
