import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from services.llm.factory import create_provider
from services.rag.parser import parse_flashcards, parse_fill_blanks, parse_json, parse_mcqs, parse_true_false
from services.rag.prompts import (
    FILL_BLANK_PROMPT_TEMPLATE,
    FLASHCARD_PROMPT_TEMPLATE,
    MCQ_PROMPT_TEMPLATE,
    QA_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
    TRUE_FALSE_PROMPT_TEMPLATE,
)
from services.rag.retriever import retrieve_chunks

logger = logging.getLogger(__name__)

TOP_K = int(os.getenv("RAG_QA_TOP_K", "5"))
MIN_SCORE = float(os.getenv("RAG_QA_MIN_SCORE", "0.15"))


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    return "\n\n".join(str(item.get("text", "")).strip() for item in chunks if str(item.get("text", "")).strip())


def _prepare_context(
    question: str,
    source_text: Optional[str] = None,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> Tuple[List[Dict[str, Any]], str, List[float]]:
    selected_top_k = top_k if top_k is not None else TOP_K
    selected_min_score = min_score if min_score is not None else MIN_SCORE

    if document_id:
        results = retrieve_chunks(question, top_k=selected_top_k, document_id=document_id, min_score=selected_min_score)
    elif source_text:
        from services.rag.qa import _fallback_retrieve_from_text as fallback_retrieve

        chunks, scores = fallback_retrieve(source_text, question, selected_top_k)
        return [{"text": chunk, "score": score} for chunk, score in zip(chunks, scores)], _build_context([{"text": chunk, "score": score} for chunk, score in zip(chunks, scores)]), scores

    return results, _build_context(results), [float(item.get("score", 0.0) or 0.0) for item in results]


def _prompt_text(feature: str, context: str, question: Optional[str] = None) -> str:
    if feature == "qa":
        return QA_PROMPT_TEMPLATE.format(context=context, question=question or "")
    if feature == "summary":
        return SUMMARY_PROMPT_TEMPLATE.format(context=context)
    if feature == "mcq":
        return MCQ_PROMPT_TEMPLATE.format(context=context)
    if feature == "flashcard":
        return FLASHCARD_PROMPT_TEMPLATE.format(context=context)
    if feature == "true_false":
        return TRUE_FALSE_PROMPT_TEMPLATE.format(context=context)
    if feature == "fill_blank":
        return FILL_BLANK_PROMPT_TEMPLATE.format(context=context)
    raise ValueError(f"Unsupported feature: {feature}")


def _call_llm(prompt: str, feature: str, max_output_tokens: int = 1200) -> str:
    provider = create_provider()
    response = provider.generate(prompt, max_output_tokens=max_output_tokens, response_mime_type="application/json")
    data = parse_json(response)
    if isinstance(data, dict):
        return str(data.get("text") or "")
    return str(response)


def _safe_parse(feature: str, payload: str) -> Any:
    if feature == "qa":
        return payload.strip()
    if feature == "summary":
        return {"summary": payload.strip()}
    if feature == "mcq":
        return parse_mcqs(payload)
    if feature == "flashcard":
        return parse_flashcards(payload)
    if feature == "true_false":
        return parse_true_false(payload)
    if feature == "fill_blank":
        return parse_fill_blanks(payload)
    raise ValueError(f"Unsupported feature: {feature}")


def _run_generation(
    feature: str,
    question: Optional[str] = None,
    source_text: Optional[str] = None,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> Tuple[Any, Dict[str, Any]]:
    started_at = time.perf_counter()
    retrieval_started = time.perf_counter()

    chunks, context, scores = _prepare_context(question or "", source_text, document_id, top_k, min_score)
    retrieval_time = time.perf_counter() - retrieval_started

    if not context:
        if feature == "qa":
            payload = "I couldn't find this information in the uploaded study material."
        elif feature == "summary":
            payload = {"summary": ""}
        elif feature == "mcq":
            payload = []
        elif feature == "flashcard":
            payload = []
        elif feature == "true_false":
            payload = []
        elif feature == "fill_blank":
            payload = []
        else:
            payload = None

        return (
            payload,
            {
                "feature": feature,
                "retrieved_chunk_count": 0,
                "scores": [],
                "retrieval_time": round(retrieval_time, 4),
                "llm_time": 0.0,
                "total_time": round(time.perf_counter() - started_at, 4),
                "error": "No relevant context was found.",
            },
        )

    prompt = _prompt_text(feature, context, question)
    prompt_length = len(prompt)

    llm_started = time.perf_counter()
    try:
        if feature == "qa":
            provider = create_provider()
            llm_output = provider.generate(
                QA_PROMPT_TEMPLATE.format(context=context, question=question or ""),
                max_output_tokens=900,
                response_mime_type="text/plain",
            )
        else:
            llm_output = _call_llm(prompt, feature)
    except Exception as exc:
        logger.exception("LLM generation failed for feature=%s", feature)
        return (
            None,
            {
                "feature": feature,
                "retrieved_chunk_count": len(chunks),
                "scores": scores,
                "retrieval_time": round(retrieval_time, 4),
                "llm_time": round(time.perf_counter() - llm_started, 4),
                "total_time": round(time.perf_counter() - started_at, 4),
                "error": str(exc),
            },
        )

    llm_time = time.perf_counter() - llm_started
    parsing_started = time.perf_counter()

    try:
        parsed = _safe_parse(feature, llm_output)
    except Exception as exc:
        logger.exception("Parsing failed for feature=%s", feature)
        return (
            None,
            {
                "feature": feature,
                "retrieved_chunk_count": len(chunks),
                "scores": scores,
                "retrieval_time": round(retrieval_time, 4),
                "llm_time": round(llm_time, 4),
                "parsing_time": round(time.perf_counter() - parsing_started, 4),
                "total_time": round(time.perf_counter() - started_at, 4),
                "error": str(exc),
            },
        )

    logger.info(
        "feature=%s chunk_count=%s prompt_length=%s retrieval_time=%.3fs llm_time=%.3fs parsing_time=%.3fs total_time=%.3fs",
        feature,
        len(chunks),
        prompt_length,
        round(retrieval_time, 4),
        round(llm_time, 4),
        round(time.perf_counter() - parsing_started, 4),
        round(time.perf_counter() - started_at, 4),
    )

    return (
        parsed,
        {
            "feature": feature,
            "retrieved_chunk_count": len(chunks),
            "scores": scores,
            "retrieval_time": round(retrieval_time, 4),
            "llm_time": round(llm_time, 4),
            "parsing_time": round(time.perf_counter() - parsing_started, 4),
            "total_time": round(time.perf_counter() - started_at, 4),
        },
    )


def generate_answer(question: str, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[str, Dict[str, Any]]:
    return _run_generation("qa", question=question, document_id=document_id, top_k=top_k, min_score=min_score)


def generate_summary(source_text: Optional[str] = None, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return _run_generation("summary", source_text=source_text, document_id=document_id, top_k=top_k, min_score=min_score)


def generate_mcqs(source_text: Optional[str] = None, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _run_generation("mcq", source_text=source_text, document_id=document_id, top_k=top_k, min_score=min_score)


def generate_flashcards(source_text: Optional[str] = None, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _run_generation("flashcard", source_text=source_text, document_id=document_id, top_k=top_k, min_score=min_score)


def generate_true_false(source_text: Optional[str] = None, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _run_generation("true_false", source_text=source_text, document_id=document_id, top_k=top_k, min_score=min_score)


def generate_fill_blanks(source_text: Optional[str] = None, document_id: Optional[str] = None, top_k: Optional[int] = None, min_score: Optional[float] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _run_generation("fill_blank", source_text=source_text, document_id=document_id, top_k=top_k, min_score=min_score)
