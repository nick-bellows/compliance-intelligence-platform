# Power BI dashboard plan

Power BI consumes reviewed aggregate CSV/JSON exports; it does not query raw source files.

## Proposed tables

- `screening_runs`: run ID, timestamp, snapshot IDs, input count
- `screening_entities`: synthetic external ID, normalized display name, review state
- `screening_hits`: source record ID, source, score, tier, reason codes
- `source_snapshots`: source, snapshot ID, retrieval time, record count

## Required views

1. Review queue by tier and source
2. Match-score distribution
3. Flags by source/program
4. Dataset freshness and snapshot record counts
5. Analyst disposition and reason, using synthetic demonstration data only

## Publication checklist

- [ ] Relationships and measures are documented.
- [ ] Screenshots use only synthetic entities.
- [ ] Filters cannot expose hidden real-person records.
- [ ] The refresh procedure identifies the dataset snapshot.
- [ ] The `.pbix` file has been inspected for embedded data before publication.

