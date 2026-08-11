# Model card — entity extraction

- **Pipeline**: spaCy `en_core_web_sm` (3.8.0, pinned wheel) plus an
  `EntityRuler` with versioned domain rules (`sanctions-rules-v1`): plain program
  codes (SDGT, IFSR, …), `Executive Order NNNNN` / `E.O. NNNNN` references, and
  `IMO NNNNNNN` identifiers. Rule labels are disjoint from model labels, so every
  span attributes to `rule:sanctions-rules-v1` or `model:en_core_web_sm`.
- **Evaluation**: `eval/run_ner_eval.py` over `eval/data/ner_annotations.jsonl`
  (22 designation excerpts, 236 gold spans, single annotator, guidelines in
  `eval/README.md`). Report: `eval/results/ner_report.md`.
- **Results summary**: rules are near-perfect where they apply
  (LEGAL_AUTHORITY and VESSEL_ID F1 1.000; SANCTIONS_PROGRAM precision 0.917).
  The statistical model is strong on GPE (F1 0.882) and very weak on the
  domain's ALL-CAPS comma-inverted PERSON (F1 0.000) and ORG (0.063) mentions —
  micro F1 0.536 overall.
- **Interpretation**: `en_core_web_sm` was trained on conventional prose;
  designation entries are structured legal text far outside its distribution.
  The obvious extensions — a bracketed-program-tag rule and a comma-inverted
  name pattern — were deliberately **not** added after seeing results, because
  tuning rules against the evaluation set would invalidate it. They are future
  work gated on a fresh annotation batch.
- **Usage boundary**: extraction is a CLI/eval feature (`extract`), not part of
  the screening API.
