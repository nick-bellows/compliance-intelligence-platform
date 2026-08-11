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
