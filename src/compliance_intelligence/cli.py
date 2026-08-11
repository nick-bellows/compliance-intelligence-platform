from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compliance_intelligence import __version__
from compliance_intelligence.config import Settings
from compliance_intelligence.domain.models import ScreeningQuery
from compliance_intelligence.ingestion import ofac, un
from compliance_intelligence.ingestion.base import SourceAdapter
from compliance_intelligence.ingestion.manifest import mark_source_active
from compliance_intelligence.ingestion.store import load_screening_dataset, save_snapshot
from compliance_intelligence.ingestion.synthetic import SyntheticFixtureAdapter
from compliance_intelligence.matching.engine import screen_records
from compliance_intelligence.reporting.exports import write_hits_csv, write_json

SYNTHETIC_FIXTURE_RELATIVE_PATH = Path("samples/synthetic_sanctions_fixture.csv")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compliance-intelligence",
        description="Compliance intelligence project utilities",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Print the package version")

    ingest = subparsers.add_parser("ingest", help="Fetch a source and save a verified snapshot")
    ingest.add_argument("--source", required=True, choices=("synthetic", "ofac", "un"))

    screen = subparsers.add_parser("screen", help="Screen one name against loaded snapshots")
    screen.add_argument("--name", required=True)
    screen.add_argument("--country", action="append", default=[], dest="countries")
    screen.add_argument("--output-dir", type=Path, default=None)

    return parser


def _run_ingest(source: str, app_settings: Settings) -> int:
    raw_directory = app_settings.data_directory / "raw"
    adapter: SourceAdapter
    manifest_source_id: str | None
    if source == "synthetic":
        adapter = SyntheticFixtureAdapter(
            app_settings.data_directory / SYNTHETIC_FIXTURE_RELATIVE_PATH
        )
        manifest_source_id = None
    elif source == "ofac":
        adapter = ofac.OfacAdapter(raw_directory)
        manifest_source_id = ofac.SOURCE_ID
    else:
        adapter = un.UnConsolidatedAdapter(raw_directory)
        manifest_source_id = un.SOURCE_ID
    snapshot = adapter.fetch()
    path = save_snapshot(snapshot, app_settings.snapshot_directory)
    if manifest_source_id is not None:
        mark_source_active(
            app_settings.data_directory / "source-manifest.json",
            manifest_source_id,
            authoritative_url=snapshot.source_url,
            format_name="xml",
            terms_note=snapshot.terms_note,
            retrieved_at=snapshot.retrieved_at,
            sha256=snapshot.sha256,
            record_count=len(snapshot.records),
        )
    print(f"snapshot_id={snapshot.snapshot_id}")
    print(f"record_count={len(snapshot.records)}")
    print(f"sha256={snapshot.sha256}")
    print(f"saved={path}")
    return 0


def _run_screen(
    name: str,
    countries: tuple[str, ...],
    output_dir: Path | None,
    app_settings: Settings,
) -> int:
    records, snapshot_ids = load_screening_dataset(
        app_settings.snapshot_directory,
        app_settings.allow_synthetic_dataset,
    )
    if not snapshot_ids:
        print(
            "No verified sanctions dataset snapshot is loaded; screening is unavailable. "
            "Run 'compliance-intelligence ingest' first "
            "(synthetic snapshots also require ALLOW_SYNTHETIC_DATASET=true).",
            file=sys.stderr,
        )
        return 1
    result = screen_records(
        ScreeningQuery(name=name, countries=countries),
        records,
        snapshot_ids,
        app_settings.matching_thresholds(),
    )
    print(f"query={name}")
    print(f"snapshots={','.join(snapshot_ids)}")
    print(f"review_required={result.review_required}")
    for hit in result.hits:
        print(
            f"  {hit.risk_tier}: {hit.matched_name} "
            f"(score={hit.score}, source={hit.source}/{hit.source_record_id}, "
            f"reasons={'|'.join(hit.reasons)})"
        )
    if output_dir is not None:
        write_json(result, output_dir / "result.json")
        write_hits_csv(result, output_dir / "hits.csv")
        print(f"exported={output_dir}")
    return 0


def main(argv: list[str] | None = None, app_settings: Settings | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configured = app_settings if app_settings is not None else Settings()
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "ingest":
        return _run_ingest(args.source, configured)
    if args.command == "screen":
        return _run_screen(args.name, tuple(args.countries), args.output_dir, configured)
    parser.print_help()
    return 0
