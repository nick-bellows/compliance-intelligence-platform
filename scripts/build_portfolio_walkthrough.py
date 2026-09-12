"""Build or verify the committed synthetic analyst walkthrough.

The walkthrough is the product dashboard rendered from the committed run
tables, plus one portfolio-only section: a recruiter FAQ. The FAQ's figures are
read from the committed evaluation reports at build time, never typed, so the
``--check`` gate fails if a report changes without the page being regenerated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compliance_intelligence.config import Settings
from compliance_intelligence.reporting.dashboard import load_run_tables, render_dashboard

ROOT = Path(__file__).resolve().parents[1]
RUN_TABLES = ROOT / "docs" / "walkthrough-run"
RESULTS = ROOT / "eval" / "results"
OUTPUTS = (ROOT / "docs" / "index.html", ROOT / "docs" / "dashboard.html")

REPO = "https://github.com/nick-bellows/compliance-intelligence-platform"
BLOB = f"{REPO}/blob/master"

FAQ_CSS = """#faq { margin-top: 30px; }
#faq .faq-note { color: var(--ink-2); font-size: 12.5px; max-width: 78ch; margin: 0 0 10px; }
#faq .faq-box { background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 2px 14px; }
#faq details { margin: 0; color: var(--ink); border-top: 1px solid var(--grid); }
#faq details:first-of-type { border-top: 0; }
#faq summary { cursor: pointer; font-weight: 600; padding: 10px 0; }
#faq summary:hover, #faq details[open] summary { color: var(--series); }
#faq details p { color: var(--ink-2); margin: 0 0 12px; max-width: 78ch; }
#faq details p strong { color: var(--ink); }
"""


def _link(path: str, text: str) -> str:
    return f'<a href="{BLOB}/{path}">{text}</a>'


def _load(name: str) -> dict[str, Any]:
    report = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    assert isinstance(report, dict)
    return report


def faq_figures() -> dict[str, str]:
    """Every number the FAQ quotes, formatted from the committed reports."""
    rapidfuzz = _load("matching_report.json")["scorers"]["rapidfuzz"]
    holdout = rapidfuzz["holdout_at_recommended"]
    # The FAQ describes every holdout error as a miss. That is only true while
    # the split has no false positives; if one appears, the wording must change.
    assert holdout["false_positives"] == 0, "FAQ wording assumes no holdout false positives"
    breakdown = rapidfuzz["case_type_breakdown_holdout_at_recommended"]
    missed = {kind: v["total"] - v["correct"] for kind, v in breakdown.items()}
    missed = {kind: n for kind, n in missed.items() if n}
    alias_missed = missed.pop("alias", 0)
    assert sum(missed.values()) + alias_missed == holdout["false_negatives"]
    other_misses = ", ".join(
        f"{n} {kind.replace('_', '-')}" for kind, n in sorted(missed.items(), key=lambda kv: -kv[1])
    )
    ner = _load("ner_report.json")
    retrieval = _load("retrieval_report.json")
    aggregate = retrieval["aggregate"]
    return {
        "cases": f"{rapidfuzz['case_count']}",
        "holdout": f"{rapidfuzz['holdout_count']}",
        "threshold": f"{holdout['threshold']:g}",
        "precision": f"{holdout['precision']:.3f}",
        "recall": f"{holdout['recall']:.3f}",
        "f1": f"{holdout['f1']:.3f}",
        "misses": f"{holdout['false_negatives']}",
        "alias_missed": f"{alias_missed}",
        "alias_total": f"{breakdown['alias']['total']}",
        "other_misses": other_misses,
        "ner_micro_f1": f"{ner['micro']['f1']:.3f}",
        "ner_person_f1": f"{ner['per_label']['PERSON']['f1']:.3f}",
        "ner_gpe_f1": f"{ner['per_label']['GPE']['f1']:.3f}",
        "bm25_r10": f"{aggregate['bm25']['recall@10']:.3f}",
        "dense_r10": f"{aggregate['dense']['recall@10']:.3f}",
        "hybrid_mrr": f"{aggregate['hybrid']['mrr']:.3f}",
        "hybrid_r10": f"{aggregate['hybrid']['recall@10']:.3f}",
        "bm25_mrr": f"{aggregate['bm25']['mrr']:.3f}",
        "corpus": f"{retrieval['corpus_document_count']}",
        "queries": f"{retrieval['query_count']}",
    }


def portfolio_faq() -> str:
    f = faq_figures()
    entries: list[tuple[str, str]] = [
        (
            "What is this, in one sentence?",
            (
                "A sanctions-screening reference system: submit a name and get back either an "
                "explainable review lead against the OFAC and UN lists, or a refusal because the "
                "data behind the answer could not be trusted. It never issues a compliance "
                "determination."
            ),
        ),
        (
            "Is it a real compliance tool? Can it clear someone?",
            (
                "No. It is an educational screening aid. Every output is a review lead for a "
                "qualified person, and a &ldquo;clear&rdquo; result means only that no name-similarity "
                "lead crossed the threshold in the loaded snapshots on that date. The disclaimer, the "
                f"limits, and the human-review workflow are in {_link('docs/limitations.md', 'limitations.md')}."
            ),
        ),
        (
            "What role is this evidence for?",
            (
                "Backend and data engineering: ingestion with recorded provenance, a FastAPI service "
                "with contract tests, explainable fuzzy matching, versioned thresholds, evaluation "
                "that is regenerated in CI, analyst exports, and a container path. It is "
                "<strong>not</strong> evidence of legal or compliance credentials, and does not claim "
                "to be."
            ),
        ),
        (
            "Is the data real?",
            (
                "The adapters pull the real, public OFAC SDN and UN Consolidated lists, and nothing "
                "from either is committed to the repository. Everything on this page and in the "
                "evaluation is fictional: synthetic rows carry an explicit flag, snapshots built from "
                "them get a <span class=\"mono\">synthetic-</span> prefix, and the API refuses to "
                "screen against them unless told to. "
                f"{_link('docs/data-cards/synthetic-fixture.md', 'The data card')} records the "
                "isolation controls."
            ),
        ),
        (
            "Was it built with AI?",
            (
                f"Yes, with Claude Code, and {_link('ROADMAP.md', 'ROADMAP.md')} says what it did "
                "rather than leaving it to be inferred: the finalization round ran unattended, and a "
                "read-only review of the code found eight defects that were each fixed with a "
                "regression test. The guardrail is mechanical rather than a promise. This page and "
                "the committed evaluation reports are regenerated in CI, and the build fails if "
                "either differs from what the code produces."
            ),
        ),
        (
            "How good is the matching?",
            (
                f"On the {f['holdout']}-case holdout split of a {f['cases']}-case labelled set, "
                f"precision is {f['precision']}, recall {f['recall']}, F1 {f['f1']} at the "
                f"recommended threshold of {f['threshold']}. {f['alias_missed']} of the "
                f"{f['misses']} misses are abbreviation aliases such as &ldquo;CM Group&rdquo; "
                f"({f['alias_missed']} of {f['alias_total']} alias cases in the split); the rest are "
                f"{f['other_misses']} cases. The "
                f"{_link('docs/limitations.md', 'limitations')} name these as the known gaps. The labelled "
                "set is synthetic, single-annotator, and has been consumed for tuning, so the next "
                "scorer change needs fresh annotations. "
                f"{_link('eval/results/matching_report.md', 'The full report')} is committed."
            ),
        ),
        (
            "Some of the numbers are bad. Why publish them?",
            (
                f"Because they are the measurement. Entity extraction scores a micro F1 of "
                f"{f['ner_micro_f1']}, and {f['ner_person_f1']} on PERSON, because the small spaCy "
                "model fails on the ALL-CAPS, comma-inverted names sanctions notices use; place names "
                f"score {f['ner_gpe_f1']}. In retrieval, over {f['queries']} labelled queries against "
                f"{f['corpus']} Federal Register notices, dense encoding alone is the weakest mode "
                f"(Recall@10 {f['dense_r10']} against BM25&rsquo;s {f['bm25_r10']}), and hybrid "
                f"ranking edges BM25 on MRR ({f['hybrid_mrr']} against {f['bm25_mrr']}) while "
                f"trailing it at Recall@10 ({f['hybrid_r10']}). The "
                f"{_link('docs/model-cards/ner.md', 'model cards')} say which to use. Adjusting a "
                "number to look better would fail CI, because the reports are regenerated there."
            ),
        ),
        (
            "What happens when the source data is missing or stale?",
            (
                "The API fails closed. With no verified snapshot loaded, screening returns HTTP 503 "
                "instead of an empty &ldquo;clear&rdquo;; a source file that parses to zero records "
                "is rejected at ingest; a name that normalizes to nothing is rejected with 422; and "
                "only the newest snapshot per source is served, with superseded files kept on disk "
                "for audit. The health endpoint reports snapshot age and turns "
                "<span class=\"mono\">degraded</span> past the configured maximum. Each of these is "
                f"a row in the {_link('docs/threat-model.md', 'threat model')} with a test behind it."
            ),
        ),
        (
            "What can it not do?",
            (
                "It screens names only: identifiers such as passport or registration numbers are "
                "not matched. It covers two lists, not the EU or UK lists. The normalizer folds to "
                "ASCII, so names in Cyrillic, Arabic, or CJK are refused rather than silently "
                "cleared. There is no audit database of who screened what; runs are exported files. "
                f"All of it is in {_link('docs/limitations.md', 'limitations.md')} rather than "
                "discovered later."
            ),
        ),
        (
            "Can I run it, and is there a hosted version?",
            (
                "It runs locally from the README quick start with a Python virtual environment, or "
                "as a container with Docker Compose bound to localhost. There is deliberately no "
                "hosted endpoint: a public free-text screening service creates abuse, privacy, "
                "freshness, and legal-presentation risks without adding evidence, so this page is "
                "the interactive artefact. The CI container job proves the two runtime contracts "
                "on every push: 503 without a verified snapshot, then an exact hit carrying "
                "snapshot provenance."
            ),
        ),
        (
            "Are the numbers on this page hand-typed?",
            (
                "No. The dashboard above is rendered from committed run tables by the same code the "
                "CLI uses, and CI fails if the committed page differs from what the renderer "
                "produces. The figures in this FAQ are read from the committed evaluation reports "
                "when the page is built, and a test pins them to those reports. The matching report "
                "itself is regenerated in CI and compared with the committed copy. See "
                f"{_link('scripts/build_portfolio_walkthrough.py', 'the build script')} and "
                f"{_link('tests/test_walkthrough_faq.py', 'its test')}."
            ),
        ),
        (
            "Has anyone reviewed it?",
            (
                "A read-only code review on 10 September 2026, with findings reproduced against the "
                "committed OFAC and UN snapshots, found eight defects: an empty name scored a perfect "
                "match against records with Arabic-script aliases, a zero-record source file became a "
                "&ldquo;verified&rdquo; snapshot after which every screen returned clear, superseded "
                "snapshots were merged so delisted entities stayed flagged, the health check said "
                "&ldquo;ok&rdquo; with nothing loaded, and exports were open to spreadsheet formula "
                f"injection, among others. Each is fixed with a regression test and listed in "
                f"{_link('ROADMAP.md', 'ROADMAP.md')}."
            ),
        ),
        (
            "How long did it take?",
            (
                "The commit history is the record. The first commit is 10 August 2026 and the core "
                "system landed in the first two days; the walkthrough followed on 2 September and "
                "the review-and-finalization round on 10 September. Speed is not the point. The "
                "discipline is: thresholds are versioned and never silently changed, and every "
                "score-affecting change lands together with a regenerated report."
            ),
        ),
        (
            "Is it finished, and is it maintained?",
            (
                f"Finished, deliberately. {_link('ROADMAP.md', 'ROADMAP.md')} marks it portfolio-ready "
                "and maintenance-only, schedules no engineering milestone, and states what would "
                "justify one: an observed weakness in the retained matching, extraction, or "
                "retrieval evaluation. It also carries stop conditions, including never exposing a "
                "public screening endpoint and never hand-authoring a result on this page."
            ),
        ),
        (
            "Where should an engineer spend ten minutes?",
            (
                f"{_link('src/compliance_intelligence/matching/engine.py', 'engine.py')} for the "
                f"scorer and the reason codes, {_link('tests/test_api.py', 'test_api.py')} for the "
                f"fail-closed contract, {_link('eval/results/matching_report.md', 'the matching report')} "
                f"for what the scorer misses, and {_link('docs/threat-model.md', 'the threat model')} "
                "for how each failure mode maps to a control."
            ),
        ),
    ]
    items = "".join(
        f"<details><summary>{question}</summary><p>{answer}</p></details>"
        for question, answer in entries
    )
    return (
        '<section id="faq" aria-labelledby="faq-heading">\n'
        '    <h2 id="faq-heading">Questions a screen actually asks</h2>\n'
        '    <p class="faq-note">Written for a recruiter or hiring manager with a few minutes, '
        "ahead of the engineer with an hour. Every answer links to the evidence it rests on, "
        "and every figure is read from the committed evaluation reports when this page is "
        "built.</p>\n"
        f'    <div class="faq-box">{items}</div>\n'
        "  </section>\n"
    )


def render_walkthrough() -> str:
    markup = render_dashboard(load_run_tables(RUN_TABLES), Settings().matching_thresholds())
    for marker in ("</style>", "  <footer>"):
        assert markup.count(marker) == 1, f"dashboard markup changed shape around {marker!r}"
    markup = markup.replace("</style>", FAQ_CSS + "</style>")
    return markup.replace("  <footer>", portfolio_faq() + "\n  <footer>")


def build(check: bool = False) -> int:
    markup = render_walkthrough()
    stale: list[Path] = []
    for output in OUTPUTS:
        if check:
            if not output.is_file() or output.read_text(encoding="utf-8") != markup:
                stale.append(output)
        else:
            output.write_text(markup, encoding="utf-8")

    if stale:
        joined = ", ".join(str(path.relative_to(ROOT)) for path in stale)
        raise SystemExit(f"walkthrough is stale: {joined}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail instead of rewriting stale files")
    return build(parser.parse_args().check)


if __name__ == "__main__":
    raise SystemExit(main())
