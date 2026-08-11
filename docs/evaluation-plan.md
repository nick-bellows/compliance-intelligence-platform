# Evaluation plan

## Match-quality questions

1. At what threshold does analyst-review precision become acceptable?
2. Which transformations improve recall without creating excessive false positives?
3. How do transliteration, token order, legal suffixes, and short names affect errors?
4. Does country metadata help ranking without incorrectly suppressing a name match?

## Release metrics

Report metrics only after fixing the held-out set and threshold-selection procedure:

- Candidate generation recall
- Precision, recall, and F1 by tier
- Confusion matrix by case type
- NER per-label and aggregate precision/recall/F1
- Retrieval Recall@1, Recall@5, Recall@10, and MRR
- Latency distribution on documented hardware and corpus size

## Error reporting

For every evaluation, publish representative false positives and false negatives, likely cause, and whether the mitigation belongs in normalization, ranking, metadata, or analyst guidance.

