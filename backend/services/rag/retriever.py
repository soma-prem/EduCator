import logging
from typing import Any, Dict, List

from services.rag.embeddings import embed_query
from services.rag import vectordb

logger = logging.getLogger(__name__)


def retrieve_chunks(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the most relevant chunks for a question without using an LLM."""
    if question is None:
        return []

    cleaned_question = str(question).strip()
    if not cleaned_question:
        return []

    if top_k <= 0:
        top_k = 1

    query_vector = embed_query(cleaned_question)
    return vectordb.search(query_vector, top_k=top_k)
