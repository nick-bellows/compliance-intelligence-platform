from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def mark_source_active(
    manifest_path: Path,
    source_id: str,
    *,
    authoritative_url: str,
    format_name: str,
    terms_note: str,
    retrieved_at: datetime,
    sha256: str,
    record_count: int,
) -> None:
    """Record a completed ingest in the source manifest, flipping the source to active.

    The source entry must already exist: admitting a brand-new source requires the
    governance review documented in docs/data-governance.md, not just an ingest run.
    """

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for source in payload["sources"]:
        if source["source_id"] == source_id:
            source.update(
                {
                    "status": "active",
                    "authoritative_url": authoritative_url,
                    "format": format_name,
                    "terms_note": terms_note,
                    "retrieved_at_utc": retrieved_at.isoformat(),
                    "sha256": sha256,
                    "record_count": record_count,
                }
            )
            break
    else:
        raise KeyError(f"Source {source_id!r} is not registered in the manifest")
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
