# Model card — name matching

- **Scorer**: `rapidfuzz-ratio-tokensort-v2` — max of `fuzz.ratio` and
  `fuzz.token_sort_ratio` over Unicode-normalized names
  (`matching/normalization.py`); 0–100 scale.
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
- **Known failure modes**: abbreviation aliases are structurally invisible to
  character-level fuzz ("Contoso Maritime Group" vs "CM Group" scores 53); brand
  collisions with single-token edits score just below threshold (Duff/Fudd at
  88.5) — near-misses in [85, 89) are worth analyst spot checks. Extending the
  matcher (e.g., initialism expansion) requires a fresh labeled set — the current
  one has been used for tuning.
