import logging
import time
from typing import Any, Dict, Optional

from services.rag.chunking import chunk_text
from services.rag.embeddings import embed_documents
from services.rag import vectordb

logger = logging.getLogger(__name__)


def ingest_document(
    document_id: str,
    filename: str,
    source_type: str,
    raw_text: str,
) -> Dict[str, Any]:
    """Chunk, embed, and index a document into the vector store."""
    started_at = time.time()
    if raw_text is None:
        raw_text = ""

    cleaned_text = str(raw_text).strip()
    if not cleaned_text:
        return {
            "number_of_chunks": 0,
            "success": False,
            "processing_time": round(time.time() - started_at, 4),
            "error": "Empty text provided for ingestion",
        }

    try:
        chunks = chunk_text(cleaned_text)
        if not chunks:
            return {
                "number_of_chunks": 0,
                "success": False,
                "processing_time": round(time.time() - started_at, 4),
                "error": "No chunks produced from the provided text",
            }

        embeddings = embed_documents(chunks)
        vectordb.initialize()
        vectordb.delete_document(document_id)
        added_count = vectordb.add_documents(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document_id,
            filename=filename,
            source_type=source_type,
        )

        return {
            "number_of_chunks": added_count,
            "success": True,
            "processing_time": round(time.time() - started_at, 4),
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("RAG ingestion failed for document %s", document_id)
        return {
            "number_of_chunks": 0,
            "success": False,
            "processing_time": round(time.time() - started_at, 4),
            "error": str(exc),
        }
