import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import numpy as np

from services.rag import cache, vectordb
from services.rag.embeddings import embed_query

logger = logging.getLogger(__name__)

RETRIEVAL_MODE = os.getenv("RAG_RETRIEVAL_MODE", "vector").strip().lower()
HYBRID_KEYWORD_WEIGHT = float(os.getenv("RAG_HYBRID_KEYWORD_WEIGHT", "0.35") or 0.35)

if RETRIEVAL_MODE not in {"vector", "hybrid"}:
    logger.warning("Invalid RAG_RETRIEVAL_MODE=%s, falling back to vector", RETRIEVAL_MODE)
    RETRIEVAL_MODE = "vector"


def _tokenize_text(text: str) -> List[str]:
    return [token for token in re.findall(r"[A-Za-z0-9]{3,}", str(text or "").lower())]


def _build_cache_key(question: str, document_id: Optional[str], top_k: int, min_score: Optional[float], mode: str) -> str:
    payload = {
        "question": str(question or "").strip(),
        "document_id": str(document_id or ""),
        "top_k": top_k,
        "min_score": min_score,
        "mode": mode,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return f"retrieve:{digest}"


def _rank_lexical_matches(question: str, top_k: int = 5, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
    tokens = set(_tokenize_text(question))
    if not tokens:
        return []

    collection = vectordb.get_collection()
    results = collection.get(include=["documents", "metadatas"])
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    scored: List[Dict[str, Any]] = []
    for document, metadata in zip(documents, metadatas):
        if document_id and str(metadata.get("document_id", "")) != str(document_id):
            continue
        text = str(document or "")
        if not text:
            continue
        text_tokens = set(_tokenize_text(text))
        overlap = len(tokens.intersection(text_tokens))
        if overlap <= 0:
            continue
        density = overlap / max(1, len(text_tokens))
        score = overlap + density
        scored.append({"text": text, "score": float(score), "metadata": metadata or {}})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _merge_hybrid_results(vector_results: List[Dict[str, Any]], lexical_results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}

    for item in vector_results:
        text = str(item.get("text", "") or "").strip()
        if not text:
            continue
        merged[text] = {
            "text": text,
            "metadata": item.get("metadata") or {},
            "vector_score": float(item.get("score", 0.0) or 0.0),
            "lexical_score": 0.0,
            "score": float(item.get("score", 0.0) or 0.0),
        }

    for item in lexical_results:
        text = str(item.get("text", "") or "").strip()
        if not text:
            continue
        lexical_score = float(item.get("score", 0.0) or 0.0)
        if text in merged:
            merged[text]["lexical_score"] = lexical_score
            merged[text]["score"] = merged[text]["vector_score"] + HYBRID_KEYWORD_WEIGHT * lexical_score
        else:
            merged[text] = {
                "text": text,
                "metadata": item.get("metadata") or {},
                "vector_score": 0.0,
                "lexical_score": lexical_score,
                "score": HYBRID_KEYWORD_WEIGHT * lexical_score,
            }

    sorted_items = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    return [
        {"text": item["text"], "metadata": item["metadata"], "score": round(item["score"], 4)}
        for item in sorted_items[:top_k]
    ]


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

    if document_id is None:
        document_id = ""

    cache_key = _build_cache_key(cleaned_question, document_id, top_k, min_score, RETRIEVAL_MODE)
    cached_results = cache.get_cache(cache_key)
    if cached_results is not None:
        return cached_results

    query_vector = embed_query(cleaned_question)
    if RETRIEVAL_MODE == "hybrid":
        vector_results = vectordb.search(query_vector, top_k=max(top_k * 2, 5))
        lexical_results = _rank_lexical_matches(cleaned_question, top_k=max(top_k * 2, 5), document_id=document_id or None)
        results = _merge_hybrid_results(vector_results, lexical_results, top_k)
    else:
        results = vectordb.search(query_vector, top_k=top_k)

    filtered_results: List[Dict[str, Any]] = []
    for item in results:
        metadata = item.get("metadata") or {}
        if document_id and str(metadata.get("document_id", "")) != str(document_id):
            continue
        score = float(item.get("score", 0.0) or 0.0)
        if min_score is not None and score < float(min_score):
            continue
        filtered_results.append(item)

    cache.set_cache(cache_key, filtered_results)
    return filtered_results
