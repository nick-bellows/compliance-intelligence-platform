# Data card — UN Security Council Consolidated List

- **Source**: United Nations Security Council.
- **Endpoint**: `https://scsanctions.un.org/resources/xml/en/consolidated.xml`
  (serves GET only; HEAD requests return 404).
- **Terms**: openly published by the UN for sanctions-compliance use; see
  https://www.un.org/en/about-us/terms-of-use.
- **Format**: `CONSOLIDATED_LIST` XML with `INDIVIDUALS/INDIVIDUAL` and
  `ENTITIES/ENTITY` sections.
- **Fields used**: `REFERENCE_NUMBER` (record ID, `DATAID` fallback), name parts
  `FIRST_NAME`–`FOURTH_NAME` joined for individuals (`FIRST_NAME` holds full
  entity names), `*_ALIAS/ALIAS_NAME` (empty alias elements are skipped),
  `UN_LIST_TYPE` (program), `NATIONALITY/VALUE` and `*_ADDRESS/COUNTRY`.
- **Integrity controls**: SHA-256 in the snapshot ID; strict parse fails closed on
  missing sections or zero records; raw bytes archived under
  `data/raw/un_consolidated/<date>/`.
- **Refresh**: `compliance-intelligence ingest --source un`; staleness reported by
  `/health` as above.
- **Known caveats**: no declared record count exists for reconciliation (unlike
  OFAC); alias quality markers (`a.k.a.`/`f.k.a.`) are not currently preserved;
  transliteration variants of the same name appear as separate aliases.
