# Compliance Intelligence Platform

An auditable portfolio system for public sanctions screening and information extraction over legal/government text. It combines entity normalization, explainable fuzzy matching, structured extraction, retrieval, API interoperability, evaluation, and analyst-ready exports.

> Status: scaffolded. The included names and records are fictional. No real screening result or evaluation metric is claimed.

## Intended users

- A diligence analyst screening a customer, partner, or supplier
- A reviewer investigating why an entity was flagged
- A research engineer evaluating extraction and retrieval behavior
- A downstream reporting workflow consuming structured results

## Core principles

1. A possible match is a review lead, not a compliance determination.
2. Every output links back to a source record and dataset snapshot.
3. The API fails closed when sanctions data is unavailable.
4. Matching thresholds are evaluated, versioned, and never silently changed.
5. Synthetic examples are visibly labeled and isolated from authoritative data.

## Architecture

```mermaid
flowchart LR
    A[Official public sources] --> B[Ingestion + provenance]
    B --> C[Normalized records]
    D[Entity or document] --> E[NER + extraction]
    D --> F[Name normalization]
    C --> G[Explainable matcher]
    F --> G
    C --> H[Retrieval index]
    E --> H
    G --> I[Human-review result]
    H --> I
    I --> J[FastAPI]
    I --> K[CSV/JSON + Power BI]
```

## Repository map

```text
src/compliance_intelligence/  Application package
tests/                        Unit and contract tests
data/                         Source manifests, synthetic samples, and local data areas
eval/                         Labeled-set schemas and evaluation entry points
docs/                         Architecture, governance, evaluation, and threat model
powerbi/                      Dashboard schema and build instructions
scripts/                      Developer and data-quality commands
output/                       Ignored generated reports and exports
```

## Quick start

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -e ".[dev]"
pytest
compliance-intelligence ingest --source synthetic
$env:ALLOW_SYNTHETIC_DATASET = "true"
uvicorn compliance_intelligence.api.main:app --reload
```

The health endpoint is available immediately. The screening endpoint returns `503` until a verified dataset snapshot is loaded; this prevents an empty dataset from producing false “clear” results. Snapshots are loaded at startup from `SNAPSHOT_DIRECTORY` (default `data/processed/snapshots`); snapshots produced from the synthetic fixture are excluded unless `ALLOW_SYNTHETIC_DATASET=true`, keeping demonstration data isolated from real screening.

The GitHub Actions workflow in `.github/workflows/quality.yml` activates when this repository is pushed to GitHub; until then `scripts/run_checks.ps1` runs the identical checks locally.

For the containerized API:

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up --build
```

The API port is bound to `127.0.0.1`. The container loads snapshots from the read-only `./data` mount at startup; with `ALLOW_SYNTHETIC_DATASET=true` in `.env` it serves the labeled synthetic fixture. Screening against authoritative data remains unavailable until the M1 source adapters are implemented and verified.

## Delivery milestones

### M1 — Screening MVP

- [x] Implement OFAC plus one secondary official-source adapter (OFAC SDN + UN Consolidated List).
- [x] Capture source URL, retrieval time, terms/license note, and SHA-256.
- [x] Normalize names, aliases, identifiers, countries, and programs.
- [x] Evaluate thresholds on a labeled name-pair set — see [eval/results/matching_report.md](eval/results/matching_report.md).
- [x] Expose `/v1/screen` and generate CSV/JSON review output (`screen`, `screen-batch`).

### M2 — NLP and retrieval

- [x] Select and document a license-clean legal/government corpus (Federal Register OFAC notices, public domain).
- [x] Implement entity extraction with spaCy plus domain rules (`extract`; rule/model attribution per span).
- [x] Define structured records and validation behavior (`CorpusDocument`, corpus jsonl store, manifest entry).
- [x] Implement BM25 retrieval and a labeled query set — plus dense (MiniLM) and hybrid (RRF) modes beyond the original plan.
- [x] Report NER precision/recall/F1 and retrieval Recall@k/MRR — see [eval/results/ner_report.md](eval/results/ner_report.md) and [eval/results/retrieval_report.md](eval/results/retrieval_report.md).

### M3 — Portfolio release

- [ ] Docker build and smoke test pass.
- [ ] CI, lint, types, and tests pass.
- [ ] Data cards and model/evaluation cards are complete.
- [ ] Power BI instructions and reviewed screenshots are present.
- [ ] Limitations, failure cases, and human-review workflow are documented.

## Disclaimer

This project is an educational screening aid. It does not provide legal advice, determine sanctions status, replace source-list review, or replace a qualified compliance professional.
