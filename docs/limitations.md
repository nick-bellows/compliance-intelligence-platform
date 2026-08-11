# Limitations and human-review workflow

## What this system is not

This is an educational screening aid. It does not determine sanctions status,
provide legal advice, or replace source-list review by a qualified compliance
professional. Every output is a review lead.

## Known limitations

- **Matching**: abbreviation aliases ("CM Group") score far below threshold;
  near-identical distinct brands (Duff/Fudd, 88.5) sit just under the flag
  floor; scores in [85, 89) deserve spot checks. Identifiers (passport,
  registration numbers) are not matched — name-only screening. The labeled set
  is synthetic, single-annotator, and has been consumed for threshold tuning.
- **Coverage**: two lists (OFAC classic SDN, UN Consolidated). `sdn_advanced`
  fields, EU/UK lists, and delisting histories are out of scope. Address
  countries are weak proxies for nationality.
- **NER**: the small spaCy model largely fails on ALL-CAPS comma-inverted names
  (PERSON F1 0.000 on the labeled excerpts); rule coverage of program tags is
  precision-first (hyphenated codes missed). See docs/model-cards/ner.md.
- **Retrieval**: dense encoding truncates long designation lists; relevance
  judgments are anchor-phrase approximations.
- **Data freshness**: snapshots are point-in-time; `/health` flags staleness
  after `MAX_SNAPSHOT_AGE_DAYS` but nothing auto-refreshes.
- **No persistence layer**: screening runs are exported files, not a queryable
  store; there is no audit database of who screened what.

## Human-review workflow

1. Ingest fresh snapshots (`ingest --source ofac`, `--source un`); confirm
   `/health` reports `status: ok` and the expected snapshot IDs.
2. Run `screen-batch` over the entity file; import the four CSVs into the
   Power BI model (see powerbi/README.md).
3. Triage the review queue by tier: `exact` and `strong_fuzzy` hits first, then
   `weak_fuzzy`. Use the reason codes and matched alias to understand *why* a
   hit fired; `country_overlap` is corroborating context, never sufficient.
4. For each hit, verify against the authoritative source record (the
   `source_record_id` and snapshot's `source_url` identify it) before any
   business decision. Record the disposition outside this system.
5. A "clear" result means no name-similarity lead above threshold in the loaded
   snapshots on that date — not sanctions clearance.
