# Power BI dashboard

> An in-repo HTML dashboard covering the same five views ships with the CLI
> (`compliance-intelligence dashboard --run-dir <run>`; committed demo at
> `docs/dashboard.html`, published on GitHub Pages). This document remains the import guide for teams
> standardized on Power BI — both consume the identical reviewed run tables.

Power BI consumes reviewed aggregate CSV exports; it does not query raw source
files. Generate a run directory first:

```powershell
compliance-intelligence screen-batch --input data/samples/synthetic_entities.csv --output-dir output/run_demo
```

## Tables (produced by `write_run_tables`)

- `screening_runs.csv`: `run_id`, `created_at_utc`, `dataset_snapshot_ids`
  (pipe-joined), `input_count`
- `screening_entities.csv`: `run_id`, `external_id`, `query_name`,
  `normalized_name`, `best_risk_tier`, `review_required`, `hit_count`
- `screening_hits.csv`: `run_id`, `external_id`, `query_name`, `source`,
  `source_record_id`, `matched_name`, `score`, `risk_tier`, `reasons`
  (pipe-joined)
- `source_snapshots.csv`: `snapshot_id`, `source_name`, `source_url`,
  `retrieved_at_utc`, `sha256`, `record_count`, `terms_note`

## Import steps

1. Get Data → Text/CSV; load all four files from one run directory
   (UTF-8, comma-delimited, first row as headers).
2. Set `score` to Decimal Number and `created_at_utc`/`retrieved_at_utc` to
   Date/Time (UTC) in Power Query before load.

## Relationships

- `screening_runs[run_id]` 1—* `screening_entities[run_id]`
- `screening_entities[external_id]` 1—* `screening_hits[external_id]`
  (single run per model; include `run_id` in the join when loading several runs)
- `screening_hits[source]` *—1 `source_snapshots[source_name]`

## Suggested measures (DAX)

```dax
Entities Screened = DISTINCTCOUNT(screening_entities[external_id])
Entities Flagged  = CALCULATE([Entities Screened], screening_entities[review_required] = TRUE())
Flag Rate         = DIVIDE([Entities Flagged], [Entities Screened])
Hits              = COUNTROWS(screening_hits)
Avg Hit Score     = AVERAGE(screening_hits[score])
Exact Hits        = CALCULATE([Hits], screening_hits[risk_tier] = "exact")
```

## Required views

1. Review queue by tier and source — table of `screening_hits` sorted by
   `risk_tier`, `score` descending, sliced by `source`.
2. Match-score distribution — histogram of `screening_hits[score]` with
   threshold reference lines at 89 / 95 / 99.5.
3. Flags by source/program — bar chart of `Hits` by `source`.
4. Dataset freshness — card visuals from `source_snapshots[retrieved_at_utc]`
   and `record_count`, with the snapshot IDs displayed verbatim.
5. Analyst disposition — a disposition column maintained outside this system;
   demonstration uses synthetic entities only.

## Publication checklist

No `.pbix` is committed and none has been built; the shipped dashboard is the
in-repo HTML renderer described above, and `powerbi/*.pbix` is ignored by Git.
If a team builds the report, complete every item before publishing it or its
screenshots:

1. Screenshots use only synthetic entities — build from a synthetic-only run
   such as `data/samples/demo_batch_entities.csv`.
2. Filters and drill-through cannot expose hidden real-person records.
3. The refresh procedure identifies the dataset snapshot. Snapshot IDs are
   first-class columns in every run directory, so this holds by construction.
4. The `.pbix` file has been inspected for embedded data — Power BI imports the
   CSVs into the file — before publication.
