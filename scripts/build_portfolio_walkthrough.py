"""Build or verify the committed synthetic analyst walkthrough."""

from __future__ import annotations

import argparse
from pathlib import Path

from compliance_intelligence.config import Settings
from compliance_intelligence.reporting.dashboard import load_run_tables, render_dashboard

ROOT = Path(__file__).resolve().parents[1]
RUN_TABLES = ROOT / "docs" / "walkthrough-run"
OUTPUTS = (ROOT / "docs" / "index.html", ROOT / "docs" / "dashboard.html")


def build(check: bool = False) -> int:
    markup = render_dashboard(
        load_run_tables(RUN_TABLES),
        Settings().matching_thresholds(),
    )
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
