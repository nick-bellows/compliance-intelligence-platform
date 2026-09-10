# Data governance

## Source admission checklist

- [ ] The source is authoritative for the represented list or corpus.
- [ ] Automated access and reuse terms have been reviewed and recorded.
- [ ] The exact URL, format, retrieval time, and SHA-256 are recorded.
- [ ] Schema validation rejects unexpected structural changes.
- [ ] Raw and normalized record counts are reconciled.
- [ ] Raw third-party data is excluded from Git unless redistribution is explicitly permitted.

## Privacy

Portfolio examples use fictional entities. Real-world source records may be public, but generated review files can still be sensitive and remain ignored. Logs must not contain full request payloads by default.

## Refresh and rollback

Each refresh creates a new immutable snapshot ID. Never silently overwrite the dataset used for a recorded evaluation or screenshot. Retain enough metadata to reproduce or explain the prior result. The API and CLI screen against the newest snapshot per source; superseded files are retained on disk, not loaded. Raw downloads are stored under a date-plus-hash directory so a same-day refetch cannot overwrite the bytes an earlier snapshot's SHA-256 names.

