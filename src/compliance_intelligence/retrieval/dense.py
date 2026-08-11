from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compliance_intelligence.retrieval.index import SNIPPET_LENGTH, SearchHit

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDINGS_FILE = "embeddings.npy"
METADATA_FILE = "dense_meta.json"
# Bump when the encoded input changes; invalidates cached embeddings.
ENCODER_INPUT_VERSION = "title+dense_text-v2"


def _load_sentence_transformer() -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "Dense retrieval requires the [retrieval] extra: "
            'pip install -e ".[retrieval]"'
        ) from error
    try:
        return SentenceTransformer(MODEL_NAME)
    except OSError as error:
        raise RuntimeError(
            f"Could not load {MODEL_NAME}; the model is not cached locally "
            "and no network connection is available"
        ) from error


class DenseIndex:
    """Cosine search over cached MiniLM embeddings.

    Embeddings are encoded once per corpus and cached beside it; the cache is
    invalidated when document IDs or the model name change.
    """

    def __init__(self, cache_directory: Path) -> None:
        self._cache_directory = cache_directory
        self._documents: list[dict[str, str]] = []
        self._embeddings: Any = None
        self._model: Any = None

    def build(self, documents: list[dict[str, str]]) -> None:
        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "Dense retrieval requires the [retrieval] extra: "
                'pip install -e ".[retrieval]"'
            ) from error

        if not documents:
            raise ValueError("Cannot build a dense index over zero documents")
        self._documents = documents
        doc_ids = [document["document_id"] for document in documents]

        embeddings_path = self._cache_directory / EMBEDDINGS_FILE
        metadata_path = self._cache_directory / METADATA_FILE
        if embeddings_path.exists() and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (
                metadata.get("model_name") == MODEL_NAME
                and metadata.get("encoder_input") == ENCODER_INPUT_VERSION
                and metadata.get("doc_ids") == doc_ids
            ):
                self._embeddings = np.load(embeddings_path)
                return

        model = self._get_model()
        # The model truncates input, so encode the discriminative view when the
        # caller provides one (see corpus.store.dense_view).
        texts = [
            f"{document['title']} {document.get('dense_text') or document['text']}"
            for document in documents
        ]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        self._cache_directory.mkdir(parents=True, exist_ok=True)
        np.save(embeddings_path, embeddings)
        metadata_path.write_text(
            json.dumps(
                {
                    "model_name": MODEL_NAME,
                    "encoder_input": ENCODER_INPUT_VERSION,
                    "doc_ids": doc_ids,
                }
            ),
            encoding="utf-8",
        )
        self._embeddings = embeddings

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = _load_sentence_transformer()
        return self._model

    def search(self, query: str, limit: int = 10) -> tuple[SearchHit, ...]:
        if self._embeddings is None:
            raise RuntimeError("build() must run before search()")
        query_embedding = self._get_model().encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )[0]
        similarities = self._embeddings @ query_embedding
        ranked = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
        return tuple(
            SearchHit(
                document_id=self._documents[i]["document_id"],
                score=round(float(similarities[i]), 4),
                title=self._documents[i]["title"],
                snippet=self._documents[i]["text"][:SNIPPET_LENGTH],
            )
            for i in ranked[:limit]
        )
