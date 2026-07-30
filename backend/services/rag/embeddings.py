import logging
from typing import Any, Iterable, List, Sequence, Union

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_MODEL = None


def load_model() -> Any:
    """Load the sentence-transformers model once and reuse it."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required. Install it in the backend environment."
            ) from exc

        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def embed_text(text: str) -> np.ndarray:
    """Return a single embedding vector for a string."""
    if text is None:
        return np.zeros(384, dtype=np.float32)

    cleaned_text = str(text).strip()
    if not cleaned_text:
        return np.zeros(384, dtype=np.float32)

    model = load_model()
    embedding = model.encode([cleaned_text], normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(embedding[0], dtype=np.float32)


def embed_documents(chunks: Sequence[Union[str, dict]]) -> np.ndarray:
    """Return embedding vectors for a collection of text chunks."""
    if not chunks:
        return np.empty((0, 384), dtype=np.float32)

    texts: List[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            text = chunk.get("text") or ""
        else:
            text = chunk
        texts.append(str(text).strip())

    if not any(texts):
        return np.empty((0, 384), dtype=np.float32)

    model = load_model()
    embeddings = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(embeddings, dtype=np.float32)


def embed_query(question: str) -> np.ndarray:
    """Return an embedding vector for a query string."""
    return embed_text(question)
