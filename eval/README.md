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

### Label guidelines (annotations in `data/ner_annotations.jsonl`)

Annotations cover whitespace-normalized, truncated excerpts from Federal
Register designation entries (`doc_id` links each excerpt to its source
document). Within each excerpt, every mention of an in-scope label is
annotated; other text is unlabeled. Single-annotator labels — a documented
limitation.

- **PERSON** — individual names, including each alias listed after `a.k.a.`
  and quoted personal nicknames (```El R5''``). Comma-inverted forms are one
  span (`AL-SHABBANI, Basheer Abdulkadhim Alwan`). Online account handles
  (```JOBBERJOBBER777''```) are **not** PERSON.
- **ORG** — companies, cartels, armed groups, agencies, and their alias names
  and abbreviations. Organization mentions embedded in regulation titles
  (`Hizballah Financial Sanctions Regulations`) are **not** annotated.
- **GPE** — countries, cities, states/provinces, districts, as noun mentions
  (including after `nationality` and inside parentheses). Nationality
  adjectives (`Iranian`), street addresses, and building names are out of
  scope. Country words inside hyphenated regulation names
  (`Ukraine-/Russia-Related`) are not annotated.
- **SANCTIONS_PROGRAM** — the OFAC program tag string appearing in square
  brackets (`SDGT`, `ILLICIT-DRUGS-EO14059`), annotated without the brackets.
- **LEGAL_AUTHORITY** — executive-order references in the forms
  `Executive Order NNNNN` or `E.O. NNNNN`. Bare section/CFR citations are out
  of scope.
- **VESSEL_ID** — IMO identifier phrases (`IMO 0178209`), whether attached to
  a vessel or a company.

Format: one JSON object per line with `doc_id`, `text`, and `entities`
(each `{"text", "label", "occurrence"}`; `occurrence` is the 1-based index of
that exact substring in the excerpt, defaulting to 1). The eval runner
resolves substrings to character offsets and fails on any ambiguity.

## Retrieval

- Create realistic questions with document-level relevance judgments.
- Report Recall@k and MRR; include weak queries and corpus limitations.

Do not add numeric results to the README until the evaluation scripts and labeled artifacts are committed and reproducible.

