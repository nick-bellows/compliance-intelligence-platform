# Model card — name matching

- **Scorer**: `rapidfuzz-ratio-tokensort-v3` — max of `fuzz.ratio` and
  `fuzz.token_sort_ratio` over Unicode-normalized names
  (`matching/normalization.py`); 0–100 scale. A name that normalizes to nothing
  (whitespace, punctuation, or a script the ASCII-folding normalizer cannot
  represent) scores 0 with the reason `unscoreable_empty_normalized_name`.
- **Thresholds**: `evaluated-2026.08-v2` — minimum 89.0, strong 95.0, exact 99.5.
  The minimum was chosen by an F1 sweep on the tune split of the labeled set and
  verified on holdout (precision 1.000, recall 0.833); every labeled negative
  scored below 89. `strong` separates single-edit from multi-edit variants and
  is descriptive, not swept. Threshold or scorer changes must land atomically
  with a regenerated report and version bumps.
- **Evaluation**: `eval/run_matching_eval.py` over
  `eval/data/matching_cases.csv` (163 fictional pairs, 8 case types, tune/holdout
  split, single annotator). Report: `eval/results/matching_report.md`. The
  legacy difflib scorer produced identical holdout metrics, validating threshold
  transfer across the migration; its comparison path will be removed next release.
- **Explainability**: every hit carries reason codes
  (`normalized_sequence_similarity`, `token_order_normalized`, `country_overlap`)
  and snapshot provenance. Country overlap annotates, never gates.
- **Scorer history**: v3 (2026-09-10) added the empty-normalization guard.
  RapidFuzz scores two empty strings as 100, so under v2 any unrepresentable
  query (`" "`, `"***"`, a Cyrillic or Arabic name) was an `exact` hit on every
  record carrying an unrepresentable alias — nine UN records on the 2026-08-11
  snapshot. No score between two non-empty normalized names changed; the
  regenerated report is numerically identical to v2's, which
  `tests/test_eval_runner.py` enforces. Country normalization gained the list
  spellings for the DPRK, DRC, and UK plus `UK`/`USA`; it annotates hits and
  does not affect scores.
- **Unsupported scripts**: names in non-Latin scripts have nothing to compare
  after normalization; the API rejects them (422) and `screen-batch` refuses the
  batch rather than reporting a false clear. List aliases in those scripts are
  ignored by the scorer. Transliteration would be a scorer change requiring a
  fresh labeled set.
- **Known failure modes**: abbreviation aliases are structurally invisible to
  character-level fuzz ("Contoso Maritime Group" vs "CM Group" scores 53); brand
  collisions with single-token edits score just below threshold (Duff/Fudd at
  88.5) — near-misses in [85, 89) are worth analyst spot checks. Extending the
  matcher (e.g., initialism expansion) requires a fresh labeled set — the current
  one has been used for tuning.
