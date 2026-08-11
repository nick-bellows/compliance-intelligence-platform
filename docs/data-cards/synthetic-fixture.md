# Data card — synthetic demonstration fixture

- **Source**: authored in-repo; every name is fictional.
- **Files**: `data/samples/synthetic_sanctions_fixture.csv` (2 fake sanctions
  records), `data/samples/synthetic_entities.csv` (3 fake screening subjects).
- **Purpose**: demos, tests, and the Docker smoke test — never real screening.
- **Isolation controls**: every fixture row carries `synthetic=true` (the adapter
  rejects unlabeled rows); snapshots built from the fixture get the
  `synthetic-` snapshot-ID prefix and are excluded from screening unless
  `ALLOW_SYNTHETIC_DATASET=true` is set explicitly.
- **Caveats**: none of the labeled-evaluation data derives from this fixture; the
  matching evaluation set (`eval/data/matching_cases.csv`) is a separate,
  larger synthetic artifact with its own generator and review process.
