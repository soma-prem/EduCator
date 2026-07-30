import logging
import os
import re
import time
from typing import List, Optional, Tuple

from services.gemini_service import answer_question_from_source
from services.rag.retriever import retrieve_chunks

logger = logging.getLogger(__name__)

TOP_K = int(os.getenv("RAG_QA_TOP_K", "5"))
MIN_SCORE = float(os.getenv("RAG_QA_MIN_SCORE", "0.15"))


def _tokenize(text: str) -> List[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9]{3,}", str(text or "").lower())
        if token not in {"what", "when", "where", "which", "how", "this", "that", "from", "with", "into"}
    ]


def _split_chunks(text: str, size: int = 700) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", raw) if part.strip()]
    chunks: List[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= size:
            chunks.append(paragraph)
            continue
        for index in range(0, len(paragraph), size):
            part = paragraph[index : index + size].strip()
            if part:
                chunks.append(part)
    return chunks or [raw[:size]]


def _fallback_retrieve_from_text(source_text: str, question: str, top_k: int) -> Tuple[List[str], List[float]]:
    if not source_text:
        return [], []

    question_tokens = set(_tokenize(question))
    chunks = _split_chunks(source_text)
    scored: List[Tuple[float, str]] = []
    for chunk in chunks:
        chunk_tokens = set(_tokenize(chunk))
        overlap = len(question_tokens.intersection(chunk_tokens))
        density = overlap / max(1, len(chunk_tokens))
        score = overlap + density
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = []
    scores = []
    for score, chunk in scored[:top_k]:
        if score <= 0:
            continue
        selected.append(chunk)
        scores.append(float(score))

    if not selected:
        selected = chunks[:top_k]
        scores = [0.0] * len(selected)

    return selected, scores


def generate_answer_from_chunks(
    question: str,
    source_text: Optional[str] = None,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
):
    started_at = time.perf_counter()
    question_text = str(question or "").strip()
    if not question_text:
        return "", {"retrieved_chunk_count": 0, "scores": [], "retrieval_time": 0.0, "llm_time": 0.0, "total_time": 0.0}

    selected_top_k = top_k if top_k is not None else TOP_K
    selected_min_score = min_score if min_score is not None else MIN_SCORE
    retrieval_started = time.perf_counter()

    retrieved_chunks: List[str] = []
    scores: List[float] = []

    if document_id:
        results = retrieve_chunks(
            question_text,
            top_k=selected_top_k,
            document_id=document_id,
            min_score=selected_min_score,
        )
        retrieved_chunks = [str(item.get("text", "")).strip() for item in results if str(item.get("text", "")).strip()]
        scores = [float(item.get("score", 0.0)) for item in results]
    elif source_text:
        retrieved_chunks, scores = _fallback_retrieve_from_text(source_text, question_text, selected_top_k)

    retrieval_duration = time.perf_counter() - retrieval_started

    if not retrieved_chunks:
        logger.info(
            "QA retrieval found no chunks for question=%s document_id=%s top_k=%s min_score=%.3f",
            question_text[:160],
            document_id or "inline",
            selected_top_k,
            selected_min_score,
        )
        return (
            "I couldn't find this information in the uploaded study material.",
            {
                "retrieved_chunk_count": 0,
                "scores": [],
                "retrieval_time": round(retrieval_duration, 4),
                "llm_time": 0.0,
                "total_time": round(time.perf_counter() - started_at, 4),
            },
        )

    context = "\n\n".join(retrieved_chunks)
    prompt = (
        "You are an expert educational tutor.\n"
        "Only answer using the provided context.\n"
        "If the answer cannot be found in the context, reply that the information is not available in the uploaded study material.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question_text}\n\n"
        "Answer:"
    )

    llm_started = time.perf_counter()
    answer = answer_question_from_source(context, question_text)
    llm_duration = time.perf_counter() - llm_started
    total_duration = time.perf_counter() - started_at

    logger.info(
        "QA question=%s retrieved_chunk_count=%s scores=%s retrieval_time=%.3fs llm_time=%.3fs total_time=%.3fs",
        question_text[:160],
        len(retrieved_chunks),
        scores,
        round(retrieval_duration, 4),
        round(llm_duration, 4),
        round(total_duration, 4),
    )

    return answer, {
        "retrieved_chunk_count": len(retrieved_chunks),
        "scores": scores,
        "retrieval_time": round(retrieval_duration, 4),
        "llm_time": round(llm_duration, 4),
        "total_time": round(total_duration, 4),
    }
