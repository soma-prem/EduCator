import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks.

    The function prefers ``langchain_text_splitters.RecursiveCharacterTextSplitter``
    when available, and falls back to a simple overlapping sliding-window splitter.
    """
    if text is None:
        return []

    normalized_text = str(text).strip()
    if not normalized_text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except Exception:
        RecursiveCharacterTextSplitter = None

    if RecursiveCharacterTextSplitter is not None:
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                keep_separator=False,
            )
            raw_chunks = splitter.split_text(normalized_text)
            return _build_chunk_records(raw_chunks, normalized_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("RecursiveCharacterTextSplitter failed, falling back to simple chunking: %s", exc)

    return _fallback_chunk_text(normalized_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def _build_chunk_records(raw_chunks: List[str], text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    cursor = 0
    for index, chunk_text in enumerate(raw_chunks):
        if not chunk_text.strip():
            continue
        start = text.find(chunk_text, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk_text)
        records.append(
            {
                "chunk_id": index,
                "text": chunk_text.strip(),
                "start": start,
                "end": end,
            }
        )
        cursor = max(cursor + 1, end - chunk_overlap)
    return records


def _fallback_chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    start = 0
    index = 0
    text_length = len(text)

    while start < text_length:
        end = min(text_length, start + chunk_size)
        chunk_text = text[start:end].strip()
        if not chunk_text:
            break
        chunks.append(
            {
                "chunk_id": index,
                "text": chunk_text,
                "start": start,
                "end": end,
            }
        )
        index += 1
        if end >= text_length:
            break
        start = max(start + 1, end - chunk_overlap)

    return chunks
