# Data card — OFAC Specially Designated Nationals (SDN) list

- **Source**: U.S. Department of the Treasury, Office of Foreign Assets Control.
- **Endpoint**: `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML`
- **Terms**: U.S. federal government work; public domain (17 U.S.C. § 105).
- **Format**: classic `SDN.XML` — namespaced `sdnList` with a `publshInformation`
  header declaring `Record_Count`, then one `sdnEntry` per designation.
- **Fields used**: `uid` (record ID), `firstName`/`lastName` (individual names are
  joined; entity/vessel/aircraft names live in `lastName`), `akaList` (aliases),
  `programList` (programs), `addressList` country values, `sdnType`.
- **Integrity controls**: SHA-256 of the raw payload embedded in the snapshot ID;
  declared `Record_Count` reconciled against parsed records (mismatch fails
  closed); raw bytes archived under `data/raw/ofac_primary/<date>/`.
- **Refresh**: on demand via `compliance-intelligence ingest --source ofac`;
  `/health` reports snapshots older than `MAX_SNAPSHOT_AGE_DAYS` (default 45) as stale.
- **Known caveats**: the richer `sdn_advanced.xml` data model (identity documents,
  relationships, extended vessel data) is deliberately out of scope; address
  countries are not the same as nationality or citizenship; the classic format
  carries no per-record change history.
