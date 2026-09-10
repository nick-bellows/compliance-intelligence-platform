# Threat model

| Threat | Example | Control |
| --- | --- | --- |
| Stale source data | Screening against an old snapshot | Expose snapshot IDs and freshness; fail health checks when stale policy is exceeded |
| Source schema drift | Parser silently drops aliases | Strict schema validation and record-count reconciliation |
| False clear | Empty dataset returns no hits | API returns 503 unless a verified snapshot with records is loaded; a zero-record source file is rejected at ingest; a name with nothing to compare after normalization is rejected (422) rather than screened |
| Superseded data | Old and new snapshots of one source load together, duplicating hits and keeping delisted entities flagged | Only the newest snapshot per source is served; superseded files are retained for audit, not loaded |
| Export injection | A screened name or external ID beginning with `=` executes as a formula when the CSV is opened in Excel or Power BI | Free-text cells starting with formula characters are prefixed with an apostrophe in every export |
| False positive | Similar short names are treated as identity | Tiered candidates, reasons, metadata, and mandatory human review |
| Input abuse | Oversized names or documents | API length limits and request-size controls |
| Sensitive logs | Screened names appear in application logs | Structured logging with payload exclusion/redaction |
| Supply-chain risk | Compromised dependency or image | Pinned ranges, CI scanning, reviewed updates, non-root container |

