from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source-manifest.json"
VALID_STATUSES = {"planned", "active", "retired"}


def validate_manifest() -> list[str]:
    errors: list[str] = []
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_ids: set[str] = set()
    for source in payload.get("sources", []):
        source_id = source.get("source_id")
        if not source_id:
            errors.append("source is missing source_id")
            continue
        if source_id in source_ids:
            errors.append(f"duplicate source_id: {source_id}")
        source_ids.add(source_id)
        if source.get("status") not in VALID_STATUSES:
            errors.append(f"{source_id}: invalid status")
        if source.get("status") == "active":
            for field in ("authoritative_url", "terms_note", "retrieved_at_utc", "sha256"):
                value = source.get(field)
                if not value or str(value).startswith("INPUT_REQUIRED"):
                    errors.append(f"{source_id}: active source missing {field}")
    if len(source_ids) < 2:
        errors.append("manifest must reserve at least two source IDs")
    return errors


def main() -> int:
    errors = validate_manifest()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Source manifest structure is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

