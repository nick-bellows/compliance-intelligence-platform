import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_matching_eval_reproduces_reports() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "run_matching_eval.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    report_path = ROOT / "eval" / "results" / "matching_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
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
    assert (ROOT / "eval" / "results" / "matching_report.md").exists()
