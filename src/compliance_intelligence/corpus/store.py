from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from compliance_intelligence.corpus.models import CorpusDocument


def save_corpus(documents: list[CorpusDocument], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".jsonl.tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for document in documents:
            handle.write(json.dumps(asdict(document)) + "\n")
    temp_path.replace(path)


def load_corpus(path: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                documents.append(CorpusDocument(**json.loads(line)))
    return documents
