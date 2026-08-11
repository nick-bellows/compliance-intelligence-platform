# Threat model

| Threat | Example | Control |
| --- | --- | --- |
| Stale source data | Screening against an old snapshot | Expose snapshot IDs and freshness; fail health checks when stale policy is exceeded |
| Source schema drift | Parser silently drops aliases | Strict schema validation and record-count reconciliation |
| False clear | Empty dataset returns no hits | API returns 503 when no verified snapshot is loaded |
| False positive | Similar short names are treated as identity | Tiered candidates, reasons, metadata, and mandatory human review |
| Input abuse | Oversized names or documents | API length limits and request-size controls |
| Sensitive logs | Screened names appear in application logs | Structured logging with payload exclusion/redaction |
| Supply-chain risk | Compromised dependency or image | Pinned ranges, CI scanning, reviewed updates, non-root container |

