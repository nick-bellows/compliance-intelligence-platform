from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_source_manifest import validate_manifest  # noqa: E402


def test_planned_source_manifest_is_structurally_valid() -> None:
    assert validate_manifest() == []

