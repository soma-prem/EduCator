from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from routes.generate import get_source_text_from_request
from services.mcq_session import store_mcq_session, update_mcq_session, get_mcq_session
from services.rag.generation import (
    generate_fill_blanks as generate_fill_blanks_from_rag,
    generate_flashcards as generate_flashcards_from_rag,
    generate_mcqs as generate_mcqs_from_rag,
    generate_summary as generate_summary_from_rag,
    generate_true_false as generate_true_false_from_rag,
)
from utils.premium_guard import require_feature

router = APIRouter()


def _normalize_tool(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "mcq": "mcq",
        "mcqs": "mcq",
        "flashcard": "flashcards",
        "flashcards": "flashcards",
        "fill_blanks": "fill_blanks",
        "fill-blanks": "fill_blanks",
        "fill_blanks_questions": "fill_blanks",
        "fill_in_the_blanks": "fill_blanks",
        "true_false": "true_false",
        "true-false": "true_false",
        "match_the_pair": "match_the_pair",
        "match-the-pair": "match_the_pair",
        "matchthepair": "match_the_pair",
        "summary": "summary",
        "study_set": "study_set",
        "study-set": "study_set",
        "studyset": "study_set",
    }
    return aliases.get(raw, "")


def _normalize_count(value, default=10, max_count=50) -> int:
    try:
        count = int(value)
    except Exception:
        count = default
    if count < 1:
        count = default
    if count > max_count:
        count = max_count
    return count


def _to_bool(value) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _build_match_pair_sets(items, pairs_per_set=5):
    pairs = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        left = str(item.get("left") or item.get("left_item") or item.get("term") or "").strip()
        right = str(item.get("right") or item.get("right_item") or item.get("definition") or "").strip()
        if left and right:
            pairs.append({"left": left, "right": right})

    sets = []
    for index in range(0, len(pairs), pairs_per_set):
        chunk = pairs[index : index + pairs_per_set]
        if chunk:
            sets.append({"title": f"Set {len(sets) + 1}", "pairs": chunk})
    return sets


@router.post("/api/tools/generate")
async def tool_generate(request: Request):
    try:
        form = await request.form()
        tool = _normalize_tool(form.get("tool"))
        if not tool:
            return JSONResponse(
                content={
                    "error": "tool is required (mcq, flashcards, fill_blanks, true_false, match_the_pair, summary, study_set)"
                },
                status_code=400,
            )

        count = _normalize_count(form.get("count"), default=12, max_count=80)
        if tool == "fill_blanks":
            require_feature(request, "fill_blanks")
        if tool == "true_false":
            require_feature(request, "true_false")

        source_text, source_meta = await get_source_text_from_request(request)
        # If client provided an existing MCQ session id and did not request regeneration,
        # return the stored items instead of regenerating.
        mcq_set_id = str(form.get("mcqSetId") or "").strip()
        regenerate = _to_bool(form.get("regenerate"))
        if mcq_set_id and not regenerate:
            session = get_mcq_session(mcq_set_id)
            if session:
                # Serve cached study data depending on requested tool
                if tool == "study_set":
                    return {
                        "tool": tool,
                        "mcqs": session.get("items", []),
                        "flashcards": session.get("flashcards", []),
                        "summary": session.get("summary", ""),
                        "mcqSetId": mcq_set_id,
                        "meta": {"cached": True, **source_meta},
                    }
                if tool == "mcq":
                    return {
                        "tool": tool,
                        "mcqs": session.get("items", []),
                        "mcqSetId": mcq_set_id,
                        "meta": {"cached": True, **source_meta},
                    }
                if tool == "flashcards":
                    return {
                        "tool": tool,
                        "flashcards": session.get("flashcards", []),
                        "mcqSetId": mcq_set_id,
                        "meta": {"cached": True, **source_meta},
                    }
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"

        if tool == "study_set":
            summary_result, _ = generate_summary_from_rag(source_text)
            mcq_result, _ = generate_mcqs_from_rag(source_text)
            flashcard_result, _ = generate_flashcards_from_rag(source_text)

            summary = str(summary_result.get("summary", "") if isinstance(summary_result, dict) else summary_result).strip()
            mcqs = mcq_result or []
            flashcards = flashcard_result or []
            if not mcqs:
                mcqs = []
            if not flashcards:
                flashcards = []
            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(mcq_set_id, items=mcqs, flashcards=flashcards, source_text=source_text)
            return {
                "tool": tool,
                "mcqs": mcqs,
                "flashcards": flashcards,
                "summary": summary,
                "mcqSetId": mcq_set_id,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        if tool == "mcq":
            mcqs, _ = generate_mcqs_from_rag(source_text)
            mcqs = mcqs or []

            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(mcq_set_id, items=mcqs, flashcards=[], source_text=source_text)
            return {
                "tool": tool,
                "mcqs": mcqs,
                "mcqSetId": mcq_set_id,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    "provider": "rag",
                    **source_meta,
                },
            }

        if tool == "flashcards":
            flashcards, _ = generate_flashcards_from_rag(source_text)
            flashcards = flashcards or []
            return {
                "tool": tool,
                "flashcards": flashcards,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        if tool == "fill_blanks":
            items, _ = generate_fill_blanks_from_rag(source_text)
            return {
                "tool": tool,
                "fillBlanks": items,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        if tool == "true_false":
            items, _ = generate_true_false_from_rag(source_text)
            return {
                "tool": tool,
                "trueFalse": items,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        if tool == "match_the_pair":
            pairs_per_set = 5
            items = []
            sets = _build_match_pair_sets(items, pairs_per_set=pairs_per_set)
            if not sets:
                raise RuntimeError("Model returned no match-the-pair sets")
            return {
                "tool": tool,
                "matchThePair": {"sets": sets, "setCount": len(sets), "pairsPerSet": pairs_per_set},
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        if tool == "summary":
            summary_payload, _ = generate_summary_from_rag(source_text)
            summary = str(summary_payload.get("summary", "") if isinstance(summary_payload, dict) else summary_payload).strip()
            return {
                "tool": tool,
                "summary": summary,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    **source_meta,
                },
            }

        return JSONResponse(content={"error": f"Unsupported tool: {tool}"}, status_code=400)
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
