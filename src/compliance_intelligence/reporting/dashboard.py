"""Self-contained HTML dashboard rendered from a screening run directory.

Reads the same four reviewed CSV tables the Power BI path consumes
(``write_run_tables`` output) and renders the five documented views — KPI
tiles, review queue, score distribution with threshold lines, hits by source,
and dataset freshness — as one dependency-free HTML file. Charts are inline
SVG; colors come verbatim from a validated palette (single-hue series; status
colors carry tier severity and are never used without a text label).
"""

from __future__ import annotations

import csv
import html
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from compliance_intelligence.matching.engine import (
    SCORER_VERSION,
    THRESHOLDS_VERSION,
    MatchingThresholds,
)

# Keys are RiskTier string values (domain/models.py).
TIER_RANK = {"exact": 0, "strong_fuzzy": 1, "weak_fuzzy": 2}
# Reserved status colors (validated reference palette); tier text is always
# rendered beside the dot, so color never carries the tier alone.
TIER_COLOR = {"exact": "#d03b3b", "strong_fuzzy": "#ec835a", "weak_fuzzy": "#fab219"}


@dataclass(frozen=True)
class RunTables:
    run: dict[str, str]
    entities: list[dict[str, str]]
    hits: list[dict[str, str]]
    snapshots: list[dict[str, str]]


def load_run_tables(run_dir: Path) -> RunTables:
    def read(name: str) -> list[dict[str, str]]:
        path = run_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"{name} not found in {run_dir}")
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    runs = read("screening_runs.csv")
    if len(runs) != 1:
        raise ValueError(f"expected exactly one run row, found {len(runs)}")
    return RunTables(
        run=runs[0],
        entities=read("screening_entities.csv"),
        hits=read("screening_hits.csv"),
        snapshots=read("source_snapshots.csv"),
    )


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _rounded_top_bar(x: float, y: float, w: float, h: float) -> str:
    """A bar with a 4px rounded data-end and a square baseline."""
    r = min(4.0, w / 2, h)
    return (
        f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
        f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
        f"L{x + w:.1f},{y + h:.1f} Z"
    )


def _rounded_right_bar(x: float, y: float, w: float, h: float) -> str:
    """A horizontal bar rounded at its data end (the right)."""
    r = min(4.0, h / 2, w)
    return (
        f"M{x:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
        f"L{x + w:.1f},{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} "
        f"L{x:.1f},{y + h:.1f} Z"
    )


def _score_histogram(
    hits: list[dict[str, str]], thresholds: MatchingThresholds
) -> tuple[str, str]:
    """Returns (svg, fallback-table-rows) for the score distribution."""
    scores = [float(h["score"]) for h in hits]
    if not scores:
        return "", ""
    lo = min(85, math.floor(min(scores)))
    bins = list(range(lo, 100))  # 1-point bins, [b, b+1); 100.0 lands in the last
    counts = [0] * len(bins)
    for s in scores:
        idx = min(int(s) - lo, len(bins) - 1)
        counts[idx] += 1
    peak = max(counts)

    width, height, pad_l, pad_b, pad_t = 640, 220, 36, 26, 30
    plot_w, plot_h = width - pad_l - 12, height - pad_b - pad_t
    step = plot_w / len(bins)
    bar_w = step - 2  # 2px surface gap between adjacent bars

    def x_of(score: float) -> float:
        return pad_l + (score - lo) / (100 - lo) * plot_w

    parts: list[str] = []
    # Recessive y gridlines at nice steps.
    y_step = max(1, math.ceil(peak / 4))
    for gv in range(y_step, peak + 1, y_step):
        gy = pad_t + plot_h * (1 - gv / peak)
        parts.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - 12}" y2="{gy:.1f}" class="grid"/>'
            f'<text x="{pad_l - 6}" y="{gy + 3.5:.1f}" class="tick" text-anchor="end">{gv}</text>'
        )
    # Bars with per-mark tooltips.
    for i, count in enumerate(counts):
        if count == 0:
            continue
        bx = pad_l + i * step + 1
        bh = plot_h * count / peak
        by = pad_t + plot_h - bh
        label = f"{bins[i]}–{bins[i] + 1}: {count} hit{'s' if count != 1 else ''}"
        parts.append(
            f'<path d="{_rounded_top_bar(bx, by, bar_w, bh)}" class="series" '
            f'data-tip="{_esc(label)}"><title>{_esc(label)}</title></path>'
        )
    # Threshold reference lines, labeled.
    for name, value in (
        ("weak ≥", thresholds.minimum),
        ("strong ≥", thresholds.strong),
        ("exact ≥", thresholds.exact),
    ):
        tx = x_of(value)
        parts.append(
            f'<line x1="{tx:.1f}" y1="{pad_t - 4}" x2="{tx:.1f}" y2="{pad_t + plot_h}" '
            f'class="threshold"/>'
            f'<text x="{tx:.1f}" y="{pad_t - 10}" class="tick" text-anchor="middle">'
            f"{_esc(name)} {value:g}</text>"
        )
    # Baseline + x ticks.
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{width - 12}" y2="{pad_t + plot_h}" '
        f'class="baseline"/>'
    )
    for tick in range(lo, 101, 5):
        parts.append(
            f'<text x="{x_of(tick):.1f}" y="{height - 8}" class="tick" '
            f'text-anchor="middle">{tick}</text>'
        )

    svg = (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Match-score distribution">{"".join(parts)}</svg>'
    )
    rows = "".join(
        f"<tr><td>{bins[i]}–{bins[i] + 1}</td><td>{c}</td></tr>"
        for i, c in enumerate(counts)
        if c
    )
    return svg, rows


def _source_bars(hits: list[dict[str, str]]) -> str:
    by_source: dict[str, int] = {}
    for hit in hits:
        by_source[hit["source"]] = by_source.get(hit["source"], 0) + 1
    if not by_source:
        return ""
    ordered = sorted(by_source.items(), key=lambda kv: -kv[1])
    peak = ordered[0][1]

    width, row_h, gap, pad_l = 640, 26, 2, 170
    height = len(ordered) * (row_h + gap) + 8
    plot_w = width - pad_l - 56
    parts: list[str] = []
    for i, (source, count) in enumerate(ordered):
        y = 4 + i * (row_h + gap)
        bw = max(2.0, plot_w * count / peak)
        label = f"{source}: {count} hit{'s' if count != 1 else ''}"
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + row_h / 2 + 4}" class="label" '
            f'text-anchor="end">{_esc(source)}</text>'
            f'<path d="{_rounded_right_bar(pad_l, y, bw, row_h)}" class="series" '
            f'data-tip="{_esc(label)}"><title>{_esc(label)}</title></path>'
            f'<text x="{pad_l + bw + 8:.1f}" y="{y + row_h / 2 + 4}" class="value">{count}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Hits by source">{"".join(parts)}</svg>'
    )


def render_dashboard(tables: RunTables, thresholds: MatchingThresholds) -> str:
    entities = tables.entities
    hits = sorted(
        tables.hits,
        key=lambda h: (TIER_RANK.get(h["risk_tier"], 9), -float(h["score"])),
    )
    screened = len(entities)
    flagged = sum(1 for e in entities if e["review_required"].lower() == "true")
    flag_rate = f"{flagged / screened:.0%}" if screened else "—"
    exact_hits = sum(1 for h in hits if h["risk_tier"] == "exact")

    tiles = "".join(
        f'<div class="tile"><div class="tile-value">{value}</div>'
        f'<div class="tile-label">{label}</div></div>'
        for value, label in (
            (screened, "entities screened"),
            (flagged, "flagged for review"),
            (flag_rate, "flag rate"),
            (len(hits), "hits"),
            (exact_hits, "exact-tier hits"),
        )
    )

    hist_svg, hist_rows = _score_histogram(tables.hits, thresholds)
    source_svg = _source_bars(tables.hits)

    if hits:
        queue_rows = "".join(
            "<tr>"
            f"<td>{_esc(h['query_name'])}</td>"
            f"<td>{_esc(h['matched_name'])}</td>"
            f'<td class="num">{float(h["score"]):.1f}</td>'
            f'<td><span class="dot" style="background:{TIER_COLOR.get(h["risk_tier"], "#898781")}">'
            f"</span>{_esc(h['risk_tier'])}</td>"
            f"<td>{_esc(h['source'])}</td>"
            f"<td class=\"mono\">{_esc(h['source_record_id'])}</td>"
            f"<td>{_esc(h['reasons'].replace('|', ', '))}</td>"
            "</tr>"
            for h in hits
        )
        queue = (
            '<table><thead><tr><th>Query</th><th>Matched name</th><th class="num">Score</th>'
            "<th>Tier</th><th>Source</th><th>Record</th><th>Reasons</th></tr></thead>"
            f"<tbody>{queue_rows}</tbody></table>"
        )
        distribution = (
            f'<figure>{hist_svg}<figcaption>Match-score distribution with the versioned '
            f"review thresholds ({_esc(THRESHOLDS_VERSION)}).</figcaption></figure>"
            f"<details><summary>Score distribution as a table</summary>"
            f"<table><thead><tr><th>Score bin</th><th>Hits</th></tr></thead>"
            f"<tbody>{hist_rows}</tbody></table></details>"
        )
        sources = f"<figure>{source_svg}<figcaption>Hits by source list.</figcaption></figure>"
    else:
        queue = '<p class="empty">No hits at or above the minimum threshold in this run.</p>'
        distribution = queue
        sources = ""

    snapshot_cards = "".join(
        '<div class="card">'
        f"<div class=\"card-title\">{_esc(s['source_name'])}</div>"
        f"<div class=\"card-row\">retrieved <strong>{_esc(s['retrieved_at_utc'][:19])}Z</strong></div>"
        f"<div class=\"card-row\">{int(s['record_count']):,} records · sha256 "
        f"<span class=\"mono\">{_esc(s['sha256'][:12])}…</span></div>"
        f"<div class=\"card-row mono\">{_esc(s['snapshot_id'])}</div>"
        f"<div class=\"card-note\" title=\"{_esc(s['terms_note'])}\">{_esc(s['terms_note'][:110])}"
        f"{'…' if len(s['terms_note']) > 110 else ''}</div>"
        "</div>"
        for s in tables.snapshots
    )

    run = tables.run
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Screening dashboard — {_esc(run["run_id"])}</title>
<style>
:root {{
  color-scheme: light;
  --surface: #fcfcfb; --page: #f9f9f7;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series: #2a78d6;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #1a1a19; --page: #0d0d0d;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series: #3987e5;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #1a1a19; --page: #0d0d0d;
  --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
  --series: #3987e5;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1080px; margin: 0 auto; padding: 24px 20px 48px; }}
h1 {{ font-size: 20px; margin: 0 0 2px; }}
h2 {{ font-size: 15px; margin: 28px 0 10px; }}
.sub {{ color: var(--ink-2); font-size: 12.5px; }}
.mono {{ font-family: ui-monospace, Consolas, monospace; font-size: 12px; }}
.banner {{ margin: 14px 0 0; padding: 8px 12px; border: 1px solid var(--border);
  border-radius: 8px; background: var(--surface); color: var(--ink-2); font-size: 12.5px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px; margin-top: 18px; }}
.tile {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px; }}
.tile-value {{ font-size: 26px; font-weight: 600; }}
.tile-label {{ color: var(--ink-2); font-size: 12px; }}
figure {{ margin: 0; background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px; overflow-x: auto; }}
figcaption {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
svg {{ display: block; width: 100%; height: auto; }}
.series {{ fill: var(--series); }}
.grid {{ stroke: var(--grid); stroke-width: 1; }}
.baseline {{ stroke: var(--baseline); stroke-width: 1; }}
.threshold {{ stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 3; }}
.tick, .label, .value {{ font: 11px system-ui, sans-serif; fill: var(--muted);
  font-variant-numeric: tabular-nums; }}
.label, .value {{ fill: var(--ink-2); }}
table {{ border-collapse: collapse; width: 100%; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px; overflow: hidden;
  font-size: 13px; }}
th, td {{ text-align: left; padding: 7px 10px; border-top: 1px solid var(--grid); }}
thead th {{ border-top: 0; color: var(--ink-2); font-weight: 600; font-size: 12px; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 6px; vertical-align: baseline; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 10px; }}
.card {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px; }}
.card-title {{ font-weight: 600; }}
.card-row {{ color: var(--ink-2); font-size: 12.5px; margin-top: 2px; }}
.card-note {{ color: var(--muted); font-size: 11.5px; margin-top: 6px; }}
.empty {{ color: var(--ink-2); background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px; padding: 14px; }}
details {{ margin-top: 8px; color: var(--ink-2); }}
footer {{ margin-top: 30px; color: var(--muted); font-size: 12px; }}
#tip {{ position: fixed; display: none; pointer-events: none; z-index: 10;
  background: var(--ink); color: var(--page); padding: 4px 8px; border-radius: 6px;
  font-size: 12px; }}
</style>
</head>
<body>
<main>
  <h1>Sanctions-screening dashboard</h1>
  <div class="sub mono">{_esc(run["run_id"])} · created {_esc(run["created_at_utc"][:19])}Z</div>
  <div class="banner">All entities in this dashboard are <strong>synthetic</strong>.
  Generated from the reviewed run tables only — never from raw source files.</div>

  <div class="tiles">{tiles}</div>

  <h2>Match-score distribution</h2>
  {distribution}

  <h2>Hits by source</h2>
  {sources if sources else '<p class="empty">No hits in this run.</p>'}

  <h2>Review queue</h2>
  {queue}

  <h2>Dataset freshness</h2>
  <div class="cards">{snapshot_cards}</div>

  <footer>
    scorer {_esc(SCORER_VERSION)} · thresholds {_esc(THRESHOLDS_VERSION)}
    (weak ≥ {thresholds.minimum:g}, strong ≥ {thresholds.strong:g},
    exact ≥ {thresholds.exact:g}) · snapshots {_esc(run["dataset_snapshot_ids"])}
    · dashboard generated {generated}
  </footer>
</main>
<div id="tip"></div>
<script>
(function () {{
  var tip = document.getElementById("tip");
  document.querySelectorAll("[data-tip]").forEach(function (el) {{
    el.addEventListener("mousemove", function (ev) {{
      tip.textContent = el.getAttribute("data-tip");
      tip.style.display = "block";
      tip.style.left = (ev.clientX + 12) + "px";
      tip.style.top = (ev.clientY - 28) + "px";
    }});
    el.addEventListener("mouseleave", function () {{ tip.style.display = "none"; }});
  }});
}})();
</script>
</body>
</html>
"""


def write_dashboard(
    run_dir: Path, output_path: Path, thresholds: MatchingThresholds
) -> Path:
    tables = load_run_tables(run_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard(tables, thresholds), encoding="utf-8")
    return output_path
