import logging
from typing import Any, Dict, List, Optional

from services.rag.embeddings import embed_query
from services.rag import vectordb

logger = logging.getLogger(__name__)


def retrieve_chunks(
    question: str,
    top_k: int = 5,
    document_id: Optional[str] = None,
    min_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Retrieve the most relevant chunks for a question without using an LLM."""
    if question is None:
        return []

    cleaned_question = str(question).strip()
    if not cleaned_question:
        return []

    if top_k <= 0:
        top_k = 1

    query_vector = embed_query(cleaned_question)
    results = vectordb.search(query_vector, top_k=top_k)

    if document_id is None:
        document_id = ""

    filtered_results: List[Dict[str, Any]] = []
    for item in results:
        metadata = item.get("metadata") or {}
        if document_id and str(metadata.get("document_id", "")) != str(document_id):
            continue
        score = float(item.get("score", 0.0) or 0.0)
        if min_score is not None and score < float(min_score):
            continue
        filtered_results.append(item)

    return filtered_results
