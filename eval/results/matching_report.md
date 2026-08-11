# Matching evaluation report

Generated: 2026-08-11T02:35:24.802951+00:00
Scorer version: `rapidfuzz-ratio-tokensort-v2` · Thresholds version: `evaluated-2026.08-v2`
Labeled set: `eval\data\matching_cases.csv` (sha256 `f28830e9973d…`), 163 cases (98 tune / 65 holdout).

Labels encode desired screening behavior (flag-for-review), reviewed by a single
annotator — a documented limitation. All names are fictional.

## Holdout metrics

| Scorer / threshold | t | Precision | Recall | F1 | FP | FN |
|---|---|---|---|---|---|---|
| rapidfuzz @ recommended | 89.0 | 1.000 | 0.833 | 0.909 | 0 | 9 |
| rapidfuzz @ configured default | 89.0 | 1.000 | 0.833 | 0.909 | 0 | 9 |
| difflib (legacy) @ its best | 89.0 | 1.000 | 0.833 | 0.909 | 0 | 9 |
| difflib (legacy) @ configured default | 89.0 | 1.000 | 0.833 | 0.909 | 0 | 9 |

Recommended minimum threshold (tuned on tune split only): **89.0**

## Case-type accuracy (holdout, rapidfuzz @ recommended)

| Case type | Correct | Total |
|---|---|---|
| alias | 0 | 6 |
| ambiguous_near_neighbor | 5 | 6 |
| exact | 5 | 5 |
| hard_negative | 10 | 10 |
| legal_suffix | 4 | 6 |
| misspelling | 12 | 12 |
| token_reorder | 11 | 11 |
| transliteration | 9 | 9 |

## Hardest errors (full set, rapidfuzz @ recommended)

### False positives (should not flag, but scored high)


### False negatives (should flag, but scored low)

- `alias-003` Fabrikam Industrial Works ↔ FI Works (score 48.48)
- `alias-002` Contoso Maritime Group ↔ CM Group (score 53.33)
- `alias-008` Stark Metallurgy Group ↔ SM Group (score 53.33)
- `alias-004` Northwind Shipping Company ↔ NS Company (score 55.56)
- `alias-015` Gringotts Bullion Reserve ↔ GB Reserve (score 57.14)
- `alias-013` Massive Dynamic Ventures ↔ MD Ventures (score 62.86)
- `alias-012` Black Mesa Transit Authority ↔ BMT Authority (score 63.41)
- `alias-009` Sirius Cybernetics Group ↔ Sirius Group (score 66.67)
- `alias-011` Aperture Optics Laboratories ↔ AO Laboratories (score 69.77)
- `alias-010` Duff Beverage Distribution ↔ DB Distribution (score 73.17)
