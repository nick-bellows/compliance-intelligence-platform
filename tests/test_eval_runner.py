"""The committed matching report must be what the current code produces.

The scorer, the thresholds, and the labeled set are all versioned; a change to
any of them has to land together with regenerated reports. This test regenerates
the report into a temporary directory and compares it with the committed one,
ignoring only the generation timestamp, so a silent scorer or threshold change
fails CI instead of leaving stale numbers in the repository. It never writes to
eval/results itself.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_RESULTS = ROOT / "eval" / "results"
TIMESTAMP_KEY = "generated_at_utc"
TIMESTAMP_LINE_PREFIX = "Generated: "


def _json_without_timestamp(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(report, dict)
    report.pop(TIMESTAMP_KEY)
    return report


def _markdown_without_timestamp(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if not line.startswith(TIMESTAMP_LINE_PREFIX)]


def test_matching_eval_regenerates_and_matches_committed_reports(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eval" / "run_matching_eval.py"),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    fresh_json = tmp_path / "matching_report.json"
    fresh_markdown = tmp_path / "matching_report.md"
    assert fresh_json.is_file() and fresh_markdown.is_file()

    report = json.loads(fresh_json.read_text(encoding="utf-8"))
    assert report["scorer_version"]
    assert report["thresholds_version"]
    rapidfuzz_result = report["scorers"]["rapidfuzz"]
    assert rapidfuzz_result["case_count"] >= 150
    assert rapidfuzz_result["tune_count"] + rapidfuzz_result["holdout_count"] == (
        rapidfuzz_result["case_count"]
    )
    holdout = rapidfuzz_result["holdout_at_recommended"]
    assert 0.0 <= holdout["precision"] <= 1.0
    assert 0.0 <= holdout["recall"] <= 1.0

    # Drift check: regenerate eval/results with `python eval/run_matching_eval.py`
    # and commit it together with the scorer/threshold change if this fails.
    assert _json_without_timestamp(fresh_json) == _json_without_timestamp(
        COMMITTED_RESULTS / "matching_report.json"
    )
    assert _markdown_without_timestamp(fresh_markdown) == _markdown_without_timestamp(
        COMMITTED_RESULTS / "matching_report.md"
    )
