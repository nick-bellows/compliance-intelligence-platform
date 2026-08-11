# Evaluation workspace

Evaluation is a release requirement, not a decorative notebook.

## Matching

- Build a labeled set containing exact names, aliases, reordered tokens, transliterations, misspellings, unrelated hard negatives, and ambiguous near-neighbors.
- Keep train/tuning examples separate from the final evaluation set.
- Report precision, recall, and F1 for each review threshold, plus false-positive examples.

## NER

- Define label guidelines before annotation.
- Report per-label and micro/macro precision, recall, and F1.
- Preserve an error taxonomy for boundary, label, and missed-entity errors.

## Retrieval

- Create realistic questions with document-level relevance judgments.
- Report Recall@k and MRR; include weak queries and corpus limitations.

Do not add numeric results to the README until the evaluation scripts and labeled artifacts are committed and reproducible.

