# Roadmap

Last verified: 2026-09-10

## Handoff snapshot

| Field | Current state |
| --- | --- |
| Lifecycle | `PORTFOLIO-READY` - finalized for employer review 2026-09-10; maintenance only |
| Portfolio role | Supporting API, ingestion, explainability, data-quality, retrieval, and auditability evidence |
| Public presentation | README plus the synthetic analyst walkthrough, live on GitHub Pages at <https://nick-bellows.github.io/compliance-intelligence-platform/> (legacy Pages build from `master:/docs`; logged-out HTTP 200 verified 2026-09-10). `docs/index.html` and `docs/dashboard.html` are the same generated artifact |
| Data boundary | Public official-source adapters and clearly isolated fictional evaluation/demo records |
| CI (`quality` workflow) | Lint, strict types, tests with an 80% coverage gate, manifest validation, walkthrough and evaluation-report drift checks, clean-tree check, container smoke test, pip-audit, full-history gitleaks; read-only token, SHA-pinned actions, Dependabot version updates |

The system fails closed without a verified snapshot, retains source provenance, exposes an API, produces analyst exports, and evaluates matching, extraction, and retrieval. Presentation is delivered and live. No engineering milestone is scheduled.

## Completed milestone - finalization for review (2026-09-10)

Who: Claude Code, unattended. Changes no threshold or labeled set. The scorer changed only for names that normalize to nothing (see item 6); the walkthrough regenerated only its footer version string.

1. **Claim drift removed.** The README quick start said screening against authoritative data was unavailable "until the M1 source adapters are implemented"; both adapters shipped in M1. It now documents the `ingest --source ofac` / `--source un` path and the `/health` staleness signal. The README and this roadmap also described Pages as not yet enabled; it has served the walkthrough since 2026-09-03 and is now linked from the README opening.
2. **Evaluation-report drift is checked mechanically.** `eval/run_matching_eval.py` takes `--output-dir`; `tests/test_eval_runner.py` regenerates the matching report into a temporary directory and fails on any difference from the committed report other than the timestamp. The suite no longer rewrites `eval/results` on every run, and CI fails if any test modifies a tracked file. The regenerated JSON now ends with a newline so the default regeneration path is byte-stable.
3. **Container contracts proven in CI.** `scripts/smoke_docker.sh` (POSIX twin of the PowerShell script) builds the image, asserts `503` from `/v1/screen` while the synthetic snapshot is present but not allowed, then asserts an exact-tier hit carrying snapshot IDs once it is. The container job previously only built the image.
4. **Supply-chain hardening to the level of the sibling repositories.** `permissions: contents: read`, SHA-pinned `actions/checkout` and `actions/setup-python`, concurrency cancellation, a pip-audit job over the shipped dependency set, a full-history gitleaks job, and `.github/dependabot.yml` for pip, GitHub Actions, and Docker.
5. **Power BI guide made truthful.** Its three open checklist boxes referred to a report nobody built. They are restated as conditions for a team that builds one; the shipped dashboard is the HTML renderer, and `docs/limitations.md` routes the review workflow through it.
6. **Eight verified defects from a code review fixed, each with a regression test.** The review (Claude Code subagent, read-only, findings reproduced against the committed 2026-08-11 OFAC and UN snapshots) found:
   - A name that normalizes to nothing (whitespace, punctuation, Cyrillic, Arabic) scored 100 `exact` against the nine UN records carrying an Arabic-script alias, because RapidFuzz scores two empty strings as 100. The scorer now returns 0 with reason `unscoreable_empty_normalized_name`, so `SCORER_VERSION` is `rapidfuzz-ratio-tokensort-v3`; the regenerated report differs from v2 only in the version string, which the drift test now enforces. The API rejects such names (422) and `screen-batch` refuses the batch instead of exporting a false clear.
   - A well-formed OFAC file declaring zero records became a "verified" empty snapshot, after which every screen returned 200 clear. Zero-record parses are rejected at ingest, and the API and CLI fail closed unless a loaded snapshot carries records.
   - Every snapshot file in the directory was merged, so the documented refresh procedure duplicated hits and kept delisted entities flagged. Only the newest snapshot per source is served; superseded files remain on disk for audit.
   - `/health` said `ok` while nothing was loaded; it now says `unavailable`.
   - Country normalization missed the spellings both lists use for the DPRK, DRC, and UK (an apostrophe split "People's"), so `country_overlap` never fired for 373 DPRK records; annotation only, no score change.
   - Analyst CSV exports wrote names and external IDs verbatim; cells beginning with `=`, `+`, `-`, `@`, tab, or CR are now apostrophe-prefixed so Excel and Power BI treat them as text.
   - A same-day refetch overwrote the raw download whose SHA-256 the earlier snapshot recorded; raw files are now stored under a date-plus-hash directory.
   - Whitespace-only names and unbounded country values passed request validation; both are constrained.
   Nothing that survived verification was found in threshold tiering, dashboard HTML escaping, configuration validation, or XML parsing.

### Verification run for this milestone

| Check | Result |
| --- | --- |
| `scripts/run_checks.ps1` (local venv, Python 3.13) | ruff and mypy clean; 74 tests passed; coverage 91% against the 80% gate; manifest valid; walkthrough not stale; working tree clean afterwards |
| `scripts/smoke_docker.ps1` (local, Docker 29.6.2) | passed with the same two contracts as the POSIX script |
| `scripts/smoke_docker.sh` (local, Git Bash) | passed: `503` with the fixture snapshot present but not allowed, then an exact hit whose `dataset_snapshot_ids` is exactly the synthetic fixture; the isolated smoke directory is removed afterwards |
| gitleaks v8.24.3 over the full history (14 commits) | no leaks found |
| Logged-out fetch of the Pages URL | HTTP 200 for `/` and `/dashboard.html`, 2026-09-10 |
| Evaluation regeneration | `python eval/run_matching_eval.py` reproduces the committed reports; only `generated_at_utc` differs |
| Public CI on the finalization commit | PENDING_CI |
| Cold clone from GitHub | PENDING_COLDCLONE |

Local Python 3.13 results do not prove the Python 3.12 CI environment; the public workflow run does. Local tests do not prove that the OFAC or UN endpoints are available on a later date; the walkthrough shows the snapshot date and hash it actually uses.

## Remaining work, by owner

### Owner - account-level actions outside the repository

1. Pin decision and order (workspace `ROADMAP.md`). Pinning is an account action.
2. Social preview image: a 1280x640 crop of the live walkthrough, uploaded in repository settings.

Nothing in the repository blocks either.

### Claude Code - nothing scheduled

Further engineering work must be motivated by an observed weakness in the retained matching, NER, or retrieval evaluation (see "Next engineering milestone"). No non-essential pushes while an application is under active review.

## Completed milestone - synthetic analyst walkthrough (2026-09-02)

Goal: publish a fast, static, recruiter-safe experience that demonstrates how an analyst moves from a submitted name or document to reviewable evidence.

### Delivered

1. `docs/index.html` provides a responsive three-case reviewer path: clear result, explainable review candidate, and no-snapshot fail-closed behavior.
2. Clear and candidate examples are selected from committed reviewed run tables generated by the real package; the page does not reproduce matching logic in JavaScript.
3. Cases link directly to the matcher, FastAPI schemas and contract tests, matching evaluation, threat model, and limitations.
4. The generator includes keyboard focus, a skip link, semantic case markup, text labels alongside color, and table fallbacks for charts.
5. `scripts/build_portfolio_walkthrough.py --check` is part of local and CI quality gates, preventing the committed Pages artifact from drifting from its inputs.

GitHub Pages was enabled by the owner on 2026-09-03 (legacy build from `master:/docs`). The logged-out URL was verified on 2026-09-10 and is linked from the README.

### Acceptance criteria

- Every displayed output can be regenerated by a documented CLI command from committed fictional fixtures or a pinned public-source snapshot.
- The UI calls a possible match a review lead, never a compliance determination.
- Source freshness/unavailability and the fail-closed behavior are visible, not buried in documentation.
- No live public screening endpoint, user-supplied names, credentials, or server-side state is required.
- GitHub Pages deployment and claim-drift checks are green.

## Hosting decision

Use GitHub Pages for the analyst walkthrough. It is safer and more reliable for recruiters than a sleeping free API, and the repository's FastAPI/container evidence remains inspectable and locally runnable.

Do not migrate this project to Vercel or Replit. A temporary Render or Railway API could support an interview rehearsal, but a public free-text screening service creates abuse, privacy, freshness, and legal-presentation risks without adding much evidence. Streamlit is only justified if a future role specifically values it; otherwise it duplicates the existing dashboard and API.

## Next engineering milestone

After presentation, choose work only from an observed weakness in the retained matching, NER, or retrieval evaluation. Add a new source only when its public terms, schema, update behavior, provenance, and failure semantics can be tested. Do not broaden the system into generic regulatory intelligence.

## Stop conditions

- Do not present any output as legal advice or a sanctions determination.
- Do not cache or publish uncontrolled third-party data snapshots without terms/provenance review.
- Do not expose an open public screening endpoint.
- Do not hand-author results in the static walkthrough.

## Verification before changing status

Run `scripts/run_checks.ps1` (which includes the walkthrough and evaluation-report drift checks), `scripts/smoke_docker.ps1` or `scripts/smoke_docker.sh`, a full-history secret scan (`gitleaks git .`), and a logged-out Pages review; confirm the public `quality` workflow is green on the commit. Local tests do not prove source availability at a later date; the presentation must show the snapshot date and hash it actually uses.
