"""Reproducible matching evaluation: threshold sweep, holdout metrics, error analysis.

Sweeps decision thresholds on the tune split only; the holdout split is scored
once at the recommended and current-default thresholds. The legacy difflib
scorer is evaluated alongside rapidfuzz to document the scorer migration; the
difflib path will be removed after one release.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from compliance_intelligence.matching.engine import (
    SCORER_VERSION,
    THRESHOLDS_VERSION,
    MatchingThresholds,
    similarity,
)
from compliance_intelligence.matching.normalization import normalize_entity_name, token_sorted

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "eval" / "data" / "matching_cases.csv"
RESULTS_DIR = ROOT / "eval" / "results"
SWEEP_START = 70.0
SWEEP_STOP = 100.0
SWEEP_STEP = 0.5


@dataclass(frozen=True)
class ScoredCase:
    case_id: str
    query_name: str
    candidate_name: str
    expected_match: bool
    case_type: str
    split: str
    score: float


def difflib_score(left: str, right: str) -> float:
    """The pre-migration scorer, kept only for the published comparison."""

    direct = SequenceMatcher(
        None, normalize_entity_name(left), normalize_entity_name(right)
    ).ratio()
    token = SequenceMatcher(None, token_sorted(left), token_sorted(right)).ratio()
    return round(max(direct, token) * 100, 2)


def load_cases(scorer: str) -> list[ScoredCase]:
    cases: list[ScoredCase] = []
    with CASES_PATH.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if scorer == "rapidfuzz":
                score = similarity(row["query_name"], row["candidate_name"])[0]
            else:
                score = difflib_score(row["query_name"], row["candidate_name"])
            cases.append(
                ScoredCase(
                    case_id=row["case_id"],
                    query_name=row["query_name"],
                    candidate_name=row["candidate_name"],
                    expected_match=row["expected_match"] == "true",
                    case_type=row["case_type"],
                    split=row["split"],
                    score=score,
                )
            )
    return cases


def metrics_at(cases: list[ScoredCase], threshold: float) -> dict[str, float | int]:
    true_positive = sum(1 for c in cases if c.expected_match and c.score >= threshold)
    false_positive = sum(1 for c in cases if not c.expected_match and c.score >= threshold)
    false_negative = sum(1 for c in cases if c.expected_match and c.score < threshold)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
    }


def sweep(cases: list[ScoredCase]) -> list[dict[str, float | int]]:
    thresholds: list[float] = []
    value = SWEEP_START
    while value <= SWEEP_STOP:
        thresholds.append(round(value, 1))
        value += SWEEP_STEP
    return [metrics_at(cases, threshold) for threshold in thresholds]


def best_threshold(sweep_rows: list[dict[str, float | int]]) -> float:
    # Highest F1; ties resolved toward the higher threshold to favor precision.
    best = max(sweep_rows, key=lambda row: (row["f1"], row["threshold"]))
    return float(best["threshold"])


def case_type_breakdown(cases: list[ScoredCase], threshold: float) -> dict[str, dict[str, int]]:
    breakdown: dict[str, dict[str, int]] = {}
    for case in cases:
        entry = breakdown.setdefault(case.case_type, {"total": 0, "correct": 0})
        entry["total"] += 1
        predicted = case.score >= threshold
        if predicted == case.expected_match:
            entry["correct"] += 1
    return dict(sorted(breakdown.items()))


def error_examples(cases: list[ScoredCase], threshold: float) -> dict[str, list[dict[str, object]]]:
    def describe(case: ScoredCase) -> dict[str, object]:
        return {
            "case_id": case.case_id,
            "query_name": case.query_name,
            "candidate_name": case.candidate_name,
            "score": case.score,
            "case_type": case.case_type,
        }

    false_positives = sorted(
        (c for c in cases if not c.expected_match and c.score >= threshold),
        key=lambda c: -c.score,
    )
    false_negatives = sorted(
        (c for c in cases if c.expected_match and c.score < threshold),
        key=lambda c: c.score,
    )
    return {
        "false_positives": [describe(c) for c in false_positives[:10]],
        "false_negatives": [describe(c) for c in false_negatives[:10]],
    }


def evaluate(scorer: str) -> dict[str, object]:
    cases = load_cases(scorer)
    tune = [c for c in cases if c.split == "tune"]
    holdout = [c for c in cases if c.split == "holdout"]
    sweep_rows = sweep(tune)
    recommended = best_threshold(sweep_rows)
    current_default = MatchingThresholds().minimum
    return {
        "case_count": len(cases),
        "tune_count": len(tune),
        "holdout_count": len(holdout),
        "sweep_tune": sweep_rows,
        "recommended_minimum_threshold": recommended,
        "holdout_at_recommended": metrics_at(holdout, recommended),
        "holdout_at_current_default": metrics_at(holdout, current_default),
        "case_type_breakdown_holdout_at_recommended": case_type_breakdown(holdout, recommended),
        "error_examples_full_set_at_recommended": error_examples(cases, recommended),
    }


def render_markdown(report: dict[str, object]) -> str:
    rapidfuzz_result = report["scorers"]["rapidfuzz"]  # type: ignore[index]
    difflib_result = report["scorers"]["difflib"]  # type: ignore[index]

    def metric_line(label: str, metrics: dict[str, float | int]) -> str:
        return (
            f"| {label} | {metrics['threshold']} | {metrics['precision']:.3f} | "
            f"{metrics['recall']:.3f} | {metrics['f1']:.3f} | {metrics['false_positives']} | "
            f"{metrics['false_negatives']} |"
        )

    lines = [
        "# Matching evaluation report",
        "",
        f"Generated: {report['generated_at_utc']}",
        f"Scorer version: `{report['scorer_version']}` · Thresholds version: `{report['thresholds_version']}`",
        (
            f"Labeled set: `{report['cases_file']}` "
            f"(sha256 `{str(report['cases_file_sha256'])[:12]}…`), "
            f"{rapidfuzz_result['case_count']} cases "
            f"({rapidfuzz_result['tune_count']} tune / {rapidfuzz_result['holdout_count']} holdout)."
        ),
        "",
        "Labels encode desired screening behavior (flag-for-review), reviewed by a single",
        "annotator — a documented limitation. All names are fictional.",
        "",
        "## Holdout metrics",
        "",
        "| Scorer / threshold | t | Precision | Recall | F1 | FP | FN |",
        "|---|---|---|---|---|---|---|",
        metric_line("rapidfuzz @ recommended", rapidfuzz_result["holdout_at_recommended"]),
        metric_line("rapidfuzz @ configured default", rapidfuzz_result["holdout_at_current_default"]),
        metric_line("difflib (legacy) @ its best", difflib_result["holdout_at_recommended"]),
        metric_line("difflib (legacy) @ configured default", difflib_result["holdout_at_current_default"]),
        "",
        (
            "Recommended minimum threshold (tuned on tune split only): "
            f"**{rapidfuzz_result['recommended_minimum_threshold']}**"
        ),
        "",
        "## Case-type accuracy (holdout, rapidfuzz @ recommended)",
        "",
        "| Case type | Correct | Total |",
        "|---|---|---|",
    ]
    for case_type, entry in rapidfuzz_result["case_type_breakdown_holdout_at_recommended"].items():
        lines.append(f"| {case_type} | {entry['correct']} | {entry['total']} |")
    lines += [
        "",
        "## Hardest errors (full set, rapidfuzz @ recommended)",
        "",
        "### False positives (should not flag, but scored high)",
        "",
    ]
    errors = rapidfuzz_result["error_examples_full_set_at_recommended"]
    for example in errors["false_positives"]:
        lines.append(
            f"- `{example['case_id']}` {example['query_name']} ↔ {example['candidate_name']} "
            f"(score {example['score']})"
        )
    lines += ["", "### False negatives (should flag, but scored low)", ""]
    for example in errors["false_negatives"]:
        lines.append(
            f"- `{example['case_id']}` {example['query_name']} ↔ {example['candidate_name']} "
            f"(score {example['score']})"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_DIR,
        help=(
            "where to write matching_report.{json,md}; defaults to the committed "
            "eval/results, which is the documented regeneration path. The test suite "
            "passes a temporary directory and compares against the committed reports."
        ),
    )
    return parser.parse_args()


def main() -> int:
    output_dir = parse_args().output_dir
    report: dict[str, object] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scorer_version": SCORER_VERSION,
        "thresholds_version": THRESHOLDS_VERSION,
        "cases_file": str(CASES_PATH.relative_to(ROOT)),
        "cases_file_sha256": hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
        "scorers": {scorer: evaluate(scorer) for scorer in ("rapidfuzz", "difflib")},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "matching_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "matching_report.md").write_text(render_markdown(report), encoding="utf-8")
    rapidfuzz_result = report["scorers"]["rapidfuzz"]  # type: ignore[index]
    print(f"cases={rapidfuzz_result['case_count']}")
    print(f"recommended_minimum={rapidfuzz_result['recommended_minimum_threshold']}")
    print(f"holdout_at_recommended={rapidfuzz_result['holdout_at_recommended']}")
    print(f"reports={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
