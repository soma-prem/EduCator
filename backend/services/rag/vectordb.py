import logging
import os
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import numpy as np

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(__file__), ".chroma_db")
_COLLECTION_NAME = "edu_rag_chunks"
_CLIENT = None
_COLLECTION = None


def initialize(persist_directory: Optional[str] = None) -> Any:
    """Create and cache a ChromaDB client and collection."""
    global _CLIENT, _COLLECTION

    if _COLLECTION is not None and _CLIENT is not None:
        return _COLLECTION

    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("chromadb is required. Install it in the backend environment.") from exc

    db_path = persist_directory or _DB_PATH
    os.makedirs(db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name=_COLLECTION_NAME)
    _CLIENT = client
    _COLLECTION = collection
    return _COLLECTION


def get_collection() -> Any:
    """Return the cached ChromaDB collection."""
    return initialize()


def add_documents(
    chunks: Sequence[Mapping[str, Any]],
    embeddings: Union[np.ndarray, Sequence[Sequence[float]]],
    document_id: str,
    filename: str,
    source_type: str,
    upload_time: Optional[str] = None,
) -> int:
    """Store chunk documents and their embeddings in ChromaDB."""
    if not chunks:
        return 0

    collection = initialize()
    upload_time = upload_time or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    document_id = str(document_id or uuid.uuid4())

    vector_array = np.asarray(embeddings, dtype=np.float32)
    if vector_array.ndim == 1:
        vector_array = np.expand_dims(vector_array, axis=0)

    if len(chunks) != len(vector_array):
        raise ValueError("The number of chunks and embeddings must match")

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    vectors: List[List[float]] = []

    for index, chunk in enumerate(chunks):
        chunk_data = dict(chunk)
        text = str(chunk_data.get("text") or "").strip()
        if not text:
            continue

        chunk_id = chunk_data.get("chunk_id", index)
        metadata = {
            "document_id": document_id,
            "filename": str(filename or ""),
            "chunk_id": int(chunk_id),
            "source_type": str(source_type or ""),
            "upload_time": upload_time,
            "total_chunks": len(chunks),
        }

        ids.append(f"{document_id}::chunk::{index}")
        documents.append(text)
        metadatas.append(metadata)
        vectors.append(vector_array[index].tolist())

    if not documents:
        return 0

    collection.add(ids=ids, documents=documents, embeddings=vectors, metadatas=metadatas)
    return len(documents)


def delete_document(document_id: str) -> None:
    """Delete all chunks belonging to a document from the collection."""
    if not document_id:
        return
    collection = initialize()
    collection.delete(where={"document_id": str(document_id)})


def search(query_vector: Union[np.ndarray, Sequence[float]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Search the vector store for the nearest matching chunks."""
    collection = initialize()
    if top_k <= 0:
        top_k = 1

    vector_array = np.asarray(query_vector, dtype=np.float32)
    if vector_array.ndim == 1:
        vector_array = np.expand_dims(vector_array, axis=0)

    results = collection.query(
        query_embeddings=vector_array.tolist(),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    scored_results: List[Dict[str, Any]] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        score = max(0.0, 1.0 - float(distance))
        scored_results.append(
            {
                "text": document,
                "score": round(score, 4),
                "metadata": metadata or {},
            }
        )

    return scored_results


def list_documents() -> List[Dict[str, Any]]:
    """List stored documents and associated metadata."""
    collection = initialize()
    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas", []) or []

    docs: List[Dict[str, Any]] = []
    for metadata in metadatas:
        if not metadata:
            continue
        docs.append(
            {
                "document_id": metadata.get("document_id"),
                "filename": metadata.get("filename"),
                "chunk_id": metadata.get("chunk_id"),
                "source_type": metadata.get("source_type"),
                "upload_time": metadata.get("upload_time"),
            }
        )
    return docs


def health_check() -> Dict[str, Any]:
    """Check the health of the ChromaDB vector store."""
    try:
        collection = initialize()
        results = collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", []) or []
        total_documents = len([metadata for metadata in metadatas if metadata])
        return {
            "ok": True,
            "provider": "chroma",
            "document_count": total_documents,
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": "chroma",
            "error": str(exc),
        }
