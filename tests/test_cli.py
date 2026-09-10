from pathlib import Path

import pytest

from compliance_intelligence import __version__
from compliance_intelligence.cli import main
from compliance_intelligence.config import Settings

REPO_DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


def _settings(tmp_path: Path, allow_synthetic: bool = True) -> Settings:
    return Settings(
        _env_file=None,
        data_directory=REPO_DATA_DIRECTORY,
        snapshot_directory=tmp_path / "snapshots",
        allow_synthetic_dataset=allow_synthetic,
    )


def test_version_command(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["version"], _settings(tmp_path)) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_ingest_and_screen_round_trip(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    assert main(["ingest", "--source", "synthetic"], settings) == 0
    ingest_output = capsys.readouterr().out
    assert "snapshot_id=synthetic-fixture-" in ingest_output
    assert "record_count=2" in ingest_output

    output_dir = tmp_path / "exports"
    assert (
        main(
            ["screen", "--name", "Acme Galactic Holdings", "--output-dir", str(output_dir)],
            settings,
        )
        == 0
    )
    screen_output = capsys.readouterr().out
    assert "review_required=True" in screen_output
    assert (output_dir / "result.json").exists()
    assert (output_dir / "hits.csv").exists()


def test_screen_fails_closed_without_snapshots(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert main(["screen", "--name", "Anything"], _settings(tmp_path)) == 1
    assert "screening is unavailable" in capsys.readouterr().err


def test_screen_excludes_synthetic_snapshots_by_default(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert main(["ingest", "--source", "synthetic"], _settings(tmp_path)) == 0
    capsys.readouterr()
    assert (
        main(
            ["screen", "--name", "Acme Galactic Holdings"],
            _settings(tmp_path, allow_synthetic=False),
        )
        == 1
    )


def test_screen_batch_writes_run_tables(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    assert main(["ingest", "--source", "synthetic"], settings) == 0
    capsys.readouterr()

    output_dir = tmp_path / "run"
    input_csv = REPO_DATA_DIRECTORY / "samples" / "synthetic_entities.csv"
    assert (
        main(
            ["screen-batch", "--input", str(input_csv), "--output-dir", str(output_dir)],
            settings,
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "entities_screened=3" in output
    for table in (
        "screening_runs.csv",
        "screening_entities.csv",
        "screening_hits.csv",
        "source_snapshots.csv",
    ):
        assert (output_dir / table).exists()


def test_screen_batch_refuses_unscreenable_names(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    assert main(["ingest", "--source", "synthetic"], settings) == 0
    capsys.readouterr()

    input_csv = tmp_path / "batch.csv"
    input_csv.write_text(
        "external_id,name,country\nX-1,Acme Galactic Holdings,\nX-2,   ,\nX-3,***,\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "run"
    assert (
        main(["screen-batch", "--input", str(input_csv), "--output-dir", str(output_dir)], settings)
        == 1
    )
    err = capsys.readouterr().err
    assert "Batch refused" in err
    assert "X-2" in err and "X-3" in err and "X-1" not in err
    assert not output_dir.exists()
