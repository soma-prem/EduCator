from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from routes.generate import get_source_text_from_request
from services.mcq_session import store_mcq_session, update_mcq_session, get_mcq_session
from services.gemini_service import (
    GEMINI_API_KEY,
    GEMINI_MCQ_API_KEY,
    GEMINI_FLASHCARD_API_KEY,
    GEMINI_FILLIN_API_KEY,
    GEMINI_TRUEANDFALSE_API_KEY,
    GEMINI_VOICE_API_KEY,
    GEMINI_SUMMARY_API_KEY,
    GEMINI_TEXTAI_API_KEY,
    generate_items_from_source,
    generate_fill_in_the_blanks_from_source,
    generate_true_false_from_source,
    generate_summary_from_source,
    generate_study_set_from_source,
)
from services.pexels_service import PEXELS_API_KEY
from services.unsplash_service import UNSPLASH_ACCESS_KEY
from services.pexels_service import search_photos as search_pexels_photos
from services.unsplash_service import search_photos as search_unsplash_photos
from utils.premium_guard import require_feature

router = APIRouter()

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "define",
    "defined",
    "definition",
    "do",
    "does",
    "explain",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "means",
    "of",
    "on",
    "or",
    "please",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def _extract_keywords(text: str, limit: int = 6) -> list[str]:
    raw = str(text or "").lower()
    raw = raw.replace("\n", " ")
    out: list[str] = []
    for token in raw.replace("?", " ").replace(".", " ").replace(",", " ").replace(":", " ").split():
        t = token.strip().strip("\"'()[]{}")
        if len(t) < 3:
            continue
        if t in _STOPWORDS:
            continue
        if any(ch.isdigit() for ch in t) and len(t) <= 3:
            continue
        if t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _build_image_query(item: dict) -> str:
    topic = str(item.get("topic") or "").strip()
    front = str(item.get("front") or "").strip()
    back = str(item.get("back") or "").strip()

    keywords = _extract_keywords(f"{front} {back}", limit=6)
    if topic:
        # Prefer concept-focused visuals over random photos.
        query = f"{topic} diagram illustration {' '.join(keywords[:2])}".strip()
    else:
        query = " ".join(keywords[:5]) or front
        query = f"{query} diagram".strip()
    query = " ".join(query.replace("\n", " ").split())
    return query[:140]


def _build_image_fallback_query(item: dict) -> str:
    front = str(item.get("front") or "").strip()
    back = str(item.get("back") or "").strip()
    topic = str(item.get("topic") or "").strip()
    keywords = _extract_keywords(f"{topic} {back} {front}", limit=6)
    if topic:
        query = f"{topic} concept diagram".strip()
    else:
        query = (" ".join(keywords) or front).strip()
        query = f"{query} concept".strip()
    query = " ".join(str(query).replace("\n", " ").split())
    return query[:140]


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
        include_images = _to_bool(form.get("includeImages"))

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
            result = generate_study_set_from_source(source_text, expected_count=count, difficulty=difficulty)
            mcqs = result.get("mcqs", [])
            flashcards = result.get("flashcards", [])
            summary = result.get("summary", "")
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
            # Decide provider and track it in response meta for debugging
            provider = ""
            if GEMINI_MCQ_API_KEY or GEMINI_API_KEY:
                provider = "gemini"
                instruction = (
                    "Difficulty: easy = basic recall/definitions; medium = conceptual and moderately challenging; "
                    "hard = advanced reasoning, nuanced distractors, and deeper understanding.\n"
                    f"Selected difficulty: {difficulty}.\n\n"
                    f"Create exactly {count} MCQs from the provided content. "
                    "Each item must be: "
                    "{\"question\":\"...\",\"options\": [\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}. "
                    "The explanation should briefly explain why the correct answer is right."
                )
                mcq_api_key = GEMINI_MCQ_API_KEY or GEMINI_API_KEY
                if not mcq_api_key:
                    raise RuntimeError("GEMINI_MCQ_API_KEY or GEMINI_API_KEY is required for MCQ generation")
                mcqs = generate_items_from_source(source_text, instruction, expected_count=count, api_key=mcq_api_key)

            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(mcq_set_id, items=mcqs, flashcards=[], source_text=source_text)
            return {
                "tool": tool,
                "mcqs": mcqs,
                "mcqSetId": mcq_set_id,
                "meta": {
                    "difficulty": difficulty,
                    "count": count,
                    "provider": provider,
                    **source_meta,
                },
            }

        if tool == "flashcards":
            # Use Gemini flashcard key (required)
            api_key = GEMINI_FLASHCARD_API_KEY or GEMINI_API_KEY
            if not api_key:
                raise RuntimeError("GEMINI_FLASHCARD_API_KEY or GEMINI_API_KEY is required for flashcard generation")
            instruction = (
                "Difficulty: easy = direct definitions; medium = conceptual Q/A; hard = nuanced, tricky, and application-focused.\n"
                f"Selected difficulty: {difficulty}.\n\n"
                f"Create exactly {count} flashcards from the provided content. "
                "Each item must be: {\"front\":\"...\",\"back\":\"...\",\"topic\":\"...\"}."
            )
            flashcards = generate_items_from_source(source_text, instruction, expected_count=count, api_key=api_key)

            if include_images and isinstance(flashcards, list) and len(flashcards) > 0:
                candidate_cache = {}
                cursor_cache = {}
                used_ids = set()
                used_urls = set()
                for idx in range(len(flashcards)):
                    item = flashcards[idx]
                    if not isinstance(item, dict):
                        continue
                    query = _build_image_query(item)
                    fallback_query = _build_image_fallback_query(item)

                    provider = "unsplash" if UNSPLASH_ACCESS_KEY else ("pexels" if PEXELS_API_KEY else "")
                    search_many = (
                        search_unsplash_photos
                        if provider == "unsplash"
                        else (search_pexels_photos if provider == "pexels" else None)
                    )

                    if not provider or not search_many:
                        break

                    def _get_next_candidate(q: str):
                        if not q:
                            return None
                        if q not in candidate_cache:
                            try:
                                candidate_cache[q] = search_many(q, per_page=8) or []
                            except Exception:
                                candidate_cache[q] = []
                            cursor_cache[q] = 0
                        cur = int(cursor_cache.get(q, 0) or 0)
                        candidates = candidate_cache.get(q) or []
                        while cur < len(candidates):
                            cand = candidates[cur]
                            cur += 1
                            cursor_cache[q] = cur
                            if provider == "unsplash":
                                image_url, page_url, author_name, author_url, photo_id = cand
                                unique_key = photo_id or page_url or image_url
                            else:
                                image_url, page_url, photo_id = cand
                                author_name, author_url = "", ""
                                unique_key = photo_id or page_url or image_url

                            if unique_key in used_ids:
                                continue
                            if page_url and page_url in used_urls:
                                continue
                            used_ids.add(unique_key)
                            if page_url:
                                used_urls.add(page_url)
                            return image_url, page_url, author_name, author_url
                        return None

                    chosen = _get_next_candidate(query) or _get_next_candidate(fallback_query)
                    if chosen:
                        image_url, page_url, author_name, author_url = chosen
                        item["imageUrl"] = image_url
                        item["imagePageUrl"] = page_url
                        if provider == "unsplash":
                            item["imageAuthorName"] = author_name
                            item["imageAuthorUrl"] = author_url
                        item["imageProvider"] = provider
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
            # Use Gemini fill-in-the-blanks key (required)
            api_key = GEMINI_FILLIN_API_KEY or GEMINI_API_KEY
            if not api_key:
                raise RuntimeError("GEMINI_FILLIN_API_KEY or GEMINI_API_KEY is required for fill-in-the-blanks generation")
            items = generate_fill_in_the_blanks_from_source(source_text, expected_count=count, difficulty=difficulty, api_key=api_key)
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
            # Use Gemini per-tool key for true/false (required)
            tf_api_key = GEMINI_TRUEANDFALSE_API_KEY or GEMINI_API_KEY
            if not tf_api_key:
                raise RuntimeError("GEMINI_TRUEANDFALSE_API_KEY or GEMINI_API_KEY is required for true/false generation")
            items = generate_true_false_from_source(source_text, expected_count=count, difficulty=difficulty, api_key=tf_api_key)
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
            raise RuntimeError("match_the_pair is not supported: no provider configured")

        if tool == "summary":
            summary = generate_summary_from_source(source_text)
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
