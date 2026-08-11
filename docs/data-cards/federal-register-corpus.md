# Data card — Federal Register OFAC notices (NLP/retrieval corpus)

- **Source**: federalregister.gov API, agency `foreign-assets-control-office`,
  type `NOTICE`, newest first.
- **Terms**: U.S. federal government works; public domain (17 U.S.C. § 105).
- **Format**: `data/processed/corpus/corpus.jsonl` — one JSON object per document
  with `doc_id` (Federal Register document number), `title`, `text` (raw full
  text), `publication_date`, `source_url`.
- **Size**: 200 documents at ingest time (configurable via
  `corpus-ingest --count`).
- **Integrity controls**: the fetched document index is archived under
  `data/raw/federal_register_corpus/<date>/`; SHA-256 of `corpus.jsonl` recorded
  in the source manifest; ingest fails closed below a 90% per-document fetch
  success rate.
- **Known caveats**: notices share a long identical boilerplate header — dense
  retrieval therefore encodes from the `SUPPLEMENTARY INFORMATION` section
  (`corpus.store.dense_view`); raw text contains OCR/layout artifacts
  (`[[Page NNNNN]]` markers, `[GRAPHIC] [TIFF OMITTED]` placeholders, CDN-mangled
  email addresses) that are passed through unmodified.
