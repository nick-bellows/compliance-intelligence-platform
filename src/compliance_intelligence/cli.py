from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from compliance_intelligence import __version__
from compliance_intelligence.config import Settings
from compliance_intelligence.corpus.federal_register import ingest_corpus
from compliance_intelligence.corpus.store import dense_view, load_corpus
from compliance_intelligence.domain.models import ScreeningQuery, ScreeningRun
from compliance_intelligence.ingestion import ofac, un
from compliance_intelligence.ingestion.base import SourceAdapter
from compliance_intelligence.ingestion.manifest import mark_source_active
from compliance_intelligence.ingestion.store import (
    load_screening_dataset,
    load_screening_snapshots,
    save_snapshot,
)
from compliance_intelligence.ingestion.synthetic import SyntheticFixtureAdapter
from compliance_intelligence.matching.engine import screen_records
from compliance_intelligence.reporting.exports import write_hits_csv, write_json, write_run_tables

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

    batch = subparsers.add_parser(
        "screen-batch", help="Screen a CSV of entities and export analyst tables"
    )
    batch.add_argument("--input", required=True, type=Path)
    batch.add_argument("--output-dir", required=True, type=Path)

    corpus_ingest = subparsers.add_parser(
        "corpus-ingest", help="Fetch the Federal Register notice corpus"
    )
    corpus_ingest.add_argument("--count", type=int, default=200)

    search = subparsers.add_parser("search", help="Search the ingested corpus")
    search.add_argument("--query", required=True)
    search.add_argument("--mode", choices=("bm25", "dense", "hybrid"), default="bm25")
    search.add_argument("--limit", type=int, default=10)

    extract = subparsers.add_parser("extract", help="Extract entities from a text file")
    extract.add_argument("--file", required=True, type=Path)

    dashboard = subparsers.add_parser(
        "dashboard", help="Render a self-contained HTML dashboard from a run directory"
    )
    dashboard.add_argument("--run-dir", required=True, type=Path)
    dashboard.add_argument("--output", type=Path, default=None)

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


def _run_screen_batch(input_path: Path, output_dir: Path, app_settings: Settings) -> int:
    snapshots = load_screening_snapshots(
        app_settings.snapshot_directory, app_settings.allow_synthetic_dataset
    )
    if not snapshots:
        print(
            "No verified sanctions dataset snapshot is loaded; screening is unavailable.",
            file=sys.stderr,
        )
        return 1
    records = [record for snapshot in snapshots for record in snapshot.records]
    snapshot_ids = tuple(snapshot.snapshot_id for snapshot in snapshots)
    thresholds = app_settings.matching_thresholds()

    results = []
    with input_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            query = ScreeningQuery(
                name=row["name"],
                countries=(row["country"],) if row.get("country") else (),
                external_id=row.get("external_id"),
            )
            results.append(screen_records(query, records, snapshot_ids, thresholds))

    created_at = datetime.now(UTC)
    run = ScreeningRun(
        run_id=f"run-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
        created_at=created_at,
        dataset_snapshot_ids=snapshot_ids,
        input_count=len(results),
    )
    tables = write_run_tables(run, results, snapshots, output_dir)
    flagged = sum(1 for result in results if result.review_required)
    print(f"run_id={run.run_id}")
    print(f"entities_screened={len(results)}")
    print(f"entities_flagged={flagged}")
    for name, path in tables.items():
        print(f"table_{name}={path}")
    return 0


def _run_corpus_ingest(count: int, app_settings: Settings) -> int:
    document_count, sha256 = ingest_corpus(
        app_settings.data_directory / "raw",
        app_settings.corpus_directory / "corpus.jsonl",
        app_settings.data_directory / "source-manifest.json",
        count,
    )
    print(f"documents={document_count}")
    print(f"sha256={sha256}")
    print(f"corpus={app_settings.corpus_directory / 'corpus.jsonl'}")
    return 0


def _run_search(query: str, mode: str, limit: int, app_settings: Settings) -> int:
    from compliance_intelligence.retrieval.dense import DenseIndex
    from compliance_intelligence.retrieval.hybrid import reciprocal_rank_fusion
    from compliance_intelligence.retrieval.index import RetrievalIndex

    corpus_path = app_settings.corpus_directory / "corpus.jsonl"
    if not corpus_path.exists():
        print(
            "No corpus is ingested; run 'compliance-intelligence corpus-ingest' first.",
            file=sys.stderr,
        )
        return 1
    documents = [
        {
            "document_id": document.doc_id,
            "title": document.title,
            "text": document.text,
            "dense_text": dense_view(document),
        }
        for document in load_corpus(corpus_path)
    ]
    try:
        if mode == "bm25":
            index = RetrievalIndex()
            index.build(documents)
            hits = index.search(query, limit)
        elif mode == "dense":
            dense = DenseIndex(app_settings.corpus_directory)
            dense.build(documents)
            hits = dense.search(query, limit)
        else:
            index = RetrievalIndex()
            index.build(documents)
            dense = DenseIndex(app_settings.corpus_directory)
            dense.build(documents)
            hits = reciprocal_rank_fusion(
                [index.search(query, limit * 2), dense.search(query, limit * 2)], limit
            )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"query={query}")
    print(f"mode={mode}")
    for rank, hit in enumerate(hits, start=1):
        print(f"  {rank}. [{hit.score}] {hit.document_id} — {hit.title}")
    return 0


def _run_extract(file: Path, app_settings: Settings) -> int:
    from compliance_intelligence.nlp.extractor import EntityExtractor

    try:
        entities = EntityExtractor().extract(file.read_text(encoding="utf-8"))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"file={file}")
    print(f"entities={len(entities)}")
    for entity in entities:
        print(f"  {entity.label}: {entity.text!r} [{entity.start}:{entity.end}] {entity.rule_or_model}")
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
    if args.command == "screen-batch":
        return _run_screen_batch(args.input, args.output_dir, configured)
    if args.command == "corpus-ingest":
        return _run_corpus_ingest(args.count, configured)
    if args.command == "search":
        return _run_search(args.query, args.mode, args.limit, configured)
    if args.command == "extract":
        return _run_extract(args.file, configured)
    if args.command == "dashboard":
        from compliance_intelligence.reporting.dashboard import write_dashboard

        output = args.output if args.output is not None else args.run_dir / "dashboard.html"
        path = write_dashboard(args.run_dir, output, configured.matching_thresholds())
        print(f"dashboard={path}")
        return 0
    parser.print_help()
    return 0
