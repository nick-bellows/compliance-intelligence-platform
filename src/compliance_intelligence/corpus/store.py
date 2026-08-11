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


_SUPPLEMENTARY_MARKER = "SUPPLEMENTARY INFORMATION"


def dense_view(document: CorpusDocument) -> str:
    """Discriminative text for embedding models with short input windows.

    Federal Register notices share an identical boilerplate header longer than
    a small embedding model's token window; encoding from the SUPPLEMENTARY
    INFORMATION section (where designations live) keeps embeddings distinctive.
    """

    position = document.text.find(_SUPPLEMENTARY_MARKER)
    return document.text[position:] if position >= 0 else document.text
