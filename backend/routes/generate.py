import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from services.mcq_session import get_mcq_session, store_mcq_session, update_mcq_session
from utils.extractors import extract_docx_text, extract_pdf_text, extract_pptx_text, extract_txt_text

router = APIRouter()

TEMP_UPLOAD_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "temp_uploads"))
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

REFILL_POOL_SIZE = int(os.getenv("REFILL_POOL_SIZE", "10"))

from services.gemini_service import (
    OPENROUTER_API_KEY,
    OPENROUTER_FLASHCARDS_API_KEY,
    OPENROUTER_FILL_IN_THE_BLANKS_KEY,
    generate_items_from_source,
    generate_mcqs_from_source_openrouter,
    generate_flashcards_from_source_openrouter,
    generate_fill_in_the_blanks_from_source_openrouter,
    generate_true_false_from_source_openrouter,
    generate_true_false_from_source,
    generate_summary_from_source,
)
from services.gemini_service import generate_study_set_from_source


def _normalize_text(value):
    return str(value or "").strip().lower()


def _resolve_temp_upload(file_id):
    if not file_id:
        return ""
    prefix = f"{file_id}__"
    for name in os.listdir(TEMP_UPLOAD_DIR):
        if name.startswith(prefix):
            return os.path.join(TEMP_UPLOAD_DIR, name)
    return ""


def _extract_text_from_file_bytes(filename, data):
    lower_name = filename.lower()
    extracted_text = ""
    source_type = "file"

    if lower_name.endswith(".pptx"):
        extracted_text = extract_pptx_text(data)
        source_type = "pptx"
    elif lower_name.endswith(".docx"):
        extracted_text = extract_docx_text(data)
        source_type = "docx"
    elif lower_name.endswith(".pdf"):
        extracted_text = extract_pdf_text(data)
        source_type = "pdf"
    elif lower_name.endswith(".txt"):
        extracted_text = extract_txt_text(data)
        source_type = "text"
    elif lower_name.endswith(".doc") or lower_name.endswith(".ppt"):
        raise ValueError("Legacy .doc/.ppt files are not supported. Please upload .docx/.pptx.")
    else:
        raise ValueError("Unsupported file type. Upload txt, pdf, docx, or pptx.")

    return extracted_text, source_type


@router.post("/api/source/upload")
async def upload_source_file(request: Request):
    try:
        form = await request.form()
        upload = form.get("file")
        if not upload or not hasattr(upload, "filename"):
            return JSONResponse(content={"error": "file is required"}, status_code=400)

        filename = os.path.basename(str(upload.filename or "uploaded.file"))
        data = await upload.read()
        if not data:
            return JSONResponse(content={"error": "Uploaded file is empty"}, status_code=400)

        file_id = uuid.uuid4().hex
        stored_name = f"{file_id}__{filename}"
        path = os.path.join(TEMP_UPLOAD_DIR, stored_name)
        with open(path, "wb") as handle:
            handle.write(data)

        return {"fileId": file_id, "fileName": filename, "size": len(data)}
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


def _normalize_mcq_items(items):
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        topic = str(next_item.get("topic", "")).strip()
        if not topic:
            topic = "General"
        next_item["topic"] = topic
        normalized.append(next_item)
    return normalized


def _dedupe_mcqs(existing_mcqs, candidate_mcqs):
    seen = {_normalize_text(item.get("question")) for item in existing_mcqs if isinstance(item, dict)}
    unique = []
    for item in candidate_mcqs:
        if not isinstance(item, dict):
            continue
        key = _normalize_text(item.get("question"))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _dedupe_flashcards(existing_flashcards, candidate_flashcards):
    seen = {_normalize_text(item.get("front")) for item in existing_flashcards if isinstance(item, dict)}
    unique = []
    for item in candidate_flashcards:
        if not isinstance(item, dict):
            continue
        key = _normalize_text(item.get("front"))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _fallback_summary(source_text, max_points=7):
    clean = " ".join(str(source_text or "").split()).strip()
    if not clean:
        raise RuntimeError("Summary unavailable for empty source text")
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if not sentences:
        sentences = [clean]
    points = sentences[: max(1, min(max_points, len(sentences)))]
    return "\n".join([f"- {point}" for point in points])


_FALLBACK_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "but",
    "not",
    "you",
    "your",
    "our",
    "their",
    "its",
    "into",
    "about",
    "than",
    "then",
    "they",
    "them",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "can",
    "could",
    "should",
    "would",
    "will",
    "may",
    "might",
    "such",
    "these",
    "those",
    "also",
    "between",
    "within",
    "over",
    "under",
    "more",
    "most",
    "less",
    "least",
    "each",
    "other",
    "some",
    "any",
    "all",
    "use",
    "using",
    "used",
    "during",
    "before",
    "after",
    "through",
    "because",
    "while",
    "per",
    "via",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
}


def _split_sentences(source_text):
    clean = " ".join(str(source_text or "").split()).strip()
    if not clean:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    return sentences or [clean]


def _extract_keywords(sentences, min_len=4):
    words = []
    for sentence in sentences:
        for raw in re.split(r"[^A-Za-z0-9]+", sentence):
            word = raw.strip().lower()
            if not word or len(word) < min_len or word in _FALLBACK_STOPWORDS:
                continue
            words.append(word)
    # Preserve order and uniqueness.
    seen = set()
    unique = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        unique.append(word)
    return unique


def _fallback_flashcards(source_text, count=10):
    sentences = _split_sentences(source_text)
    if not sentences:
        raise RuntimeError("Flashcards unavailable for empty source text")
    cards = []
    for idx in range(count):
        sentence = sentences[idx % len(sentences)]
        front = sentence
        if len(front) > 90:
            front = front[:87].rsplit(" ", 1)[0] + "..."
        cards.append({"front": front, "back": sentence, "topic": "General"})
    return cards


def _fallback_mcqs(source_text, count=10):
    sentences = _split_sentences(source_text)
    if not sentences:
        raise RuntimeError("MCQs unavailable for empty source text")
    keywords = _extract_keywords(sentences)
    if not keywords:
        keywords = ["concept", "process", "method", "result", "example"]

    mcqs = []
    option_pool = keywords[:]
    for idx in range(count):
        sentence = sentences[idx % len(sentences)]
        keyword = keywords[idx % len(keywords)]
        if keyword not in option_pool:
            option_pool.append(keyword)

        blank_sentence = re.sub(rf"\b{re.escape(keyword)}\b", "____", sentence, flags=re.IGNORECASE)
        if blank_sentence == sentence:
            blank_sentence = sentence.replace(keyword, "____", 1)
        question = f"Fill in the blank: {blank_sentence}"

        # Build options.
        distractors = [w for w in option_pool if w != keyword]
        while len(distractors) < 3:
            distractors.append("option" + str(len(distractors) + 1))
        options = [keyword, distractors[0], distractors[1], distractors[2]]
        options = [opt.capitalize() if opt.islower() else opt for opt in options]
        answer = options[0]
        mcqs.append(
            {
                "question": question,
                "options": options,
                "answer": answer,
                "explanation": f"The correct answer is {answer} based on the source text.",
                "topic": "General",
            }
        )
    return mcqs


def _generate_additional_items(source_text, existing_mcqs, existing_flashcards, count):
    existing_questions = [str(item.get("question", "")).strip() for item in existing_mcqs if isinstance(item, dict)]
    existing_fronts = [str(item.get("front", "")).strip() for item in existing_flashcards if isinstance(item, dict)]

    question_block = "\n".join([f"- {value}" for value in existing_questions[:120]])
    flashcard_block = "\n".join([f"- {value}" for value in existing_fronts[:120]])

    mcq_instruction = (
        f"Create exactly {count} NEW MCQs from the provided content.\n"
        "Each item must be: "
        "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}.\n"
        "The explanation should briefly explain why the correct answer is right.\n"
        "Do not repeat or rephrase these existing questions:\n"
        f"{question_block or '- None'}"
    )

    flashcard_instruction = (
        f"Create exactly {count} NEW flashcards from the provided content.\n"
        "Each item must be: {\"front\":\"...\",\"back\":\"...\",\"topic\":\"...\"}.\n"
        "Do not repeat or rephrase these existing flashcard fronts:\n"
        f"{flashcard_block or '- None'}"
    )

    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(generate_items_from_source, source_text, mcq_instruction, count): "mcqs",
            executor.submit(generate_items_from_source, source_text, flashcard_instruction, count): "flashcards",
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    new_mcqs = _dedupe_mcqs(existing_mcqs, _normalize_mcq_items(results.get("mcqs", [])))
    new_flashcards = _dedupe_flashcards(existing_flashcards, results.get("flashcards", []))
    return new_mcqs[:count], new_flashcards[:count]


async def get_source_text_from_request(request: Request):
    form = await request.form()
    text_values = form.getlist("text") if hasattr(form, "getlist") else [form.get("text")]
    texts = [str(value or "").strip() for value in text_values if str(value or "").strip()]
    upload = form.get("file")
    file_id_values = form.getlist("fileId") if hasattr(form, "getlist") else [form.get("fileId")]
    file_ids = [str(value or "").strip() for value in file_id_values if str(value or "").strip()]
    difficulty_raw = str(form.get("difficulty") or "").strip().lower()
    difficulty = difficulty_raw if difficulty_raw in {"easy", "medium", "hard"} else "medium"

    combined_chunks = []
    previews = []
    file_meta = {"pdfFileName": "", "pdfSizeBytes": 0, "pptFileName": "", "pptSizeBytes": 0}

    for txt in texts:
        combined_chunks.append(txt)
        previews.append(txt[:80] or "Text source")

    for file_id in file_ids:
        path = _resolve_temp_upload(file_id)
        if not path or not os.path.exists(path):
            raise ValueError("Uploaded file not found. Please re-upload.")
        filename = os.path.basename(path).split("__", 1)[-1] or "uploaded.file"
        with open(path, "rb") as handle:
            data = handle.read()
        if not data:
            raise ValueError("Uploaded file is empty")
        extracted_text, source_type = _extract_text_from_file_bytes(filename, data)
        if not extracted_text:
            raise ValueError("Unable to extract text from the uploaded file")
        combined_chunks.append(extracted_text)
        previews.append(filename)
        if source_type == "pdf" and not file_meta["pdfFileName"]:
            file_meta["pdfFileName"] = filename
            file_meta["pdfSizeBytes"] = len(data)
        if source_type == "pptx" and not file_meta["pptFileName"]:
            file_meta["pptFileName"] = filename
            file_meta["pptSizeBytes"] = len(data)

    if upload and hasattr(upload, "filename"):
        filename = str(upload.filename or "uploaded.file")
        data = await upload.read()
        if not data:
            raise ValueError("Uploaded file is empty")
        extracted_text, source_type = _extract_text_from_file_bytes(filename, data)
        if not extracted_text:
            raise ValueError("Unable to extract text from the uploaded file")
        combined_chunks.append(extracted_text)
        previews.append(filename)
        if source_type == "pdf" and not file_meta["pdfFileName"]:
            file_meta["pdfFileName"] = filename
            file_meta["pdfSizeBytes"] = len(data)
        if source_type == "pptx" and not file_meta["pptFileName"]:
            file_meta["pptFileName"] = filename
            file_meta["pptSizeBytes"] = len(data)

    combined_text = "\n\n---\n\n".join([chunk for chunk in combined_chunks if chunk]).strip()
    if not combined_text:
        raise ValueError("Provide text or upload a file")

    source_type = "multi" if (len(texts) + len(file_ids) + (1 if upload else 0)) > 1 else ("text" if texts else "file")
    preview = ", ".join([p for p in previews[:4] if p]).strip()
    return combined_text, {
        "sourceType": source_type,
        "sourceText": combined_text if source_type == "text" else "",
        "sourcePreview": preview or "Multiple sources",
        "difficulty": difficulty,
        **file_meta,
    }


@router.post("/api/generate/study-set")
async def generate_study_set(request: Request):
    try:
        initial_count = 10
        source_text, source_meta = await get_source_text_from_request(request)
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"
        try:
            result = generate_study_set_from_source(source_text, expected_count=initial_count, difficulty=difficulty)
            mcqs = _normalize_mcq_items(result["mcqs"])
            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(
                mcq_set_id,
                items=mcqs,
                flashcards=result["flashcards"],
                source_text=source_text,
            )
            return {
                "mcqs": mcqs,
                "flashcards": result["flashcards"],
                "summary": result["summary"],
                "mcqSetId": mcq_set_id,
            }
        except RuntimeError:
            # Fallback to independent generation when strict combined JSON is malformed.
            # This keeps the endpoint resilient to occasional model formatting drift.
            pass

        difficulty_hint = (
            "Difficulty: easy = basic recall/definitions; medium = conceptual and moderately challenging; "
            "hard = advanced reasoning, nuanced distractors, and deeper understanding.\n"
            f"Selected difficulty: {difficulty}.\n"
        )

        instructions = {
            "mcqs": (
                f"{difficulty_hint}"
                "Create exactly 10 MCQs from the provided content. "
                "Each item must be: "
                "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}. "
                "The explanation should briefly explain why the correct answer is right."
            ),
            "flashcards": (
                f"{difficulty_hint}"
                "Create exactly 10 flashcards from the provided content. "
                "Each item must be: {\"front\":\"...\",\"back\":\"...\",\"topic\":\"...\"}"
            ),
        }

        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(generate_items_from_source, source_text, instruction, initial_count): key
                for key, instruction in instructions.items()
            }
            futures[executor.submit(generate_summary_from_source, source_text)] = "summary"
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except RuntimeError:
                    if key == "summary":
                        results[key] = _fallback_summary(source_text)
                    elif key == "mcqs":
                        results[key] = _fallback_mcqs(source_text, count=initial_count)
                    elif key == "flashcards":
                        results[key] = _fallback_flashcards(source_text, count=initial_count)
                    else:
                        raise

        mcqs = _normalize_mcq_items(results["mcqs"])
        flashcards = results["flashcards"]
        summary = results.get("summary", "")
        mcq_set_id = store_mcq_session(mcqs)
        update_mcq_session(mcq_set_id, items=mcqs, flashcards=flashcards, source_text=source_text)
        return {
            "mcqs": mcqs,
            "flashcards": flashcards,
            "summary": summary,
            "mcqSetId": mcq_set_id,
        }
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        try:
            mcqs = _normalize_mcq_items(_fallback_mcqs(source_text, count=count))
            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(mcq_set_id, items=mcqs, flashcards=[], source_text=source_text)
            return {"mcqs": mcqs, "mcqSetId": mcq_set_id, "fallback": True, "warning": str(exc)}
        except Exception:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/mcqs")
async def generate_mcqs(request: Request):
    try:
        count = 10
        source_text, source_meta = await get_source_text_from_request(request)
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"
        if OPENROUTER_API_KEY:
            mcqs = _normalize_mcq_items(generate_mcqs_from_source_openrouter(source_text, count, difficulty=difficulty))
        else:
            mcq_instruction = (
                "Difficulty: easy = basic recall/definitions; medium = conceptual and moderately challenging; "
                "hard = advanced reasoning, nuanced distractors, and deeper understanding.\n"
                f"Selected difficulty: {difficulty}.\n\n"
                f"Create exactly {count} MCQs from the provided content. "
                "Each item must be: "
                "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}. "
                "The explanation should briefly explain why the correct answer is right."
            )
            mcqs = _normalize_mcq_items(generate_items_from_source(source_text, mcq_instruction, count))
        mcq_set_id = store_mcq_session(mcqs)
        update_mcq_session(mcq_set_id, items=mcqs, flashcards=[], source_text=source_text)
        return {"mcqs": mcqs, "mcqSetId": mcq_set_id}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        if OPENROUTER_API_KEY:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
        try:
            mcqs = _normalize_mcq_items(_fallback_mcqs(source_text, count=count))
            mcq_set_id = store_mcq_session(mcqs)
            update_mcq_session(mcq_set_id, items=mcqs, flashcards=[], source_text=source_text)
            return {"mcqs": mcqs, "mcqSetId": mcq_set_id, "fallback": True, "warning": str(exc)}
        except Exception:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/flashcards")
async def generate_flashcards(request: Request):
    try:
        count = 10
        source_text, source_meta = await get_source_text_from_request(request)
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"
        if OPENROUTER_FLASHCARDS_API_KEY:
            flashcards = generate_flashcards_from_source_openrouter(source_text, count, difficulty=difficulty)
        else:
            flashcard_instruction = (
                "Difficulty: easy = direct definitions; medium = conceptual Q/A; hard = nuanced, tricky, and application-focused.\n"
                f"Selected difficulty: {difficulty}.\n\n"
                f"Create exactly {count} flashcards from the provided content. "
                "Each item must be: {\"front\":\"...\",\"back\":\"...\",\"topic\":\"...\"}."
            )
            flashcards = generate_items_from_source(source_text, flashcard_instruction, count)
        return {"flashcards": flashcards}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        if OPENROUTER_FLASHCARDS_API_KEY:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
        try:
            flashcards = _fallback_flashcards(source_text, count=count)
            return {"flashcards": flashcards, "fallback": True, "warning": str(exc)}
        except Exception:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/fill-blanks")
async def generate_fill_blanks(request: Request):
    try:
        count = 10
        source_text, source_meta = await get_source_text_from_request(request)
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"
        if not OPENROUTER_FILL_IN_THE_BLANKS_KEY:
            raise RuntimeError("OPENROUTER_FILL_IN_THE_BLANKS_KEY is missing in backend environment")
        items = generate_fill_in_the_blanks_from_source_openrouter(source_text, count, difficulty=difficulty)
        return {"fillBlanks": items}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/true-false")
async def generate_true_false(request: Request):
    try:
        count = 10
        source_text, source_meta = await get_source_text_from_request(request)
        difficulty = str(source_meta.get("difficulty", "medium")).strip().lower() or "medium"
        # Prefer Gemini true/false key; fall back to legacy OpenRouter if configured.
        if os.getenv("GEMINI_TRUEANDFALSE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            api_key = os.getenv("GEMINI_TRUEANDFALSE_API_KEY") or os.getenv("GEMINI_API_KEY")
            items = generate_true_false_from_source(source_text, expected_count=count, difficulty=difficulty, api_key=api_key)
        else:
            if not OPENROUTER_TRUE_FALSE_KEY:
                raise RuntimeError("No true/false provider configured in backend environment")
            items = generate_true_false_from_source_openrouter(source_text, count, difficulty=difficulty)
        return {"trueFalse": items}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/summary")
async def generate_summary(request: Request):
    try:
        source_text, _source_meta = await get_source_text_from_request(request)
        summary = generate_summary_from_source(source_text)
        return {"summary": summary}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        try:
            summary = _fallback_summary(source_text)
            return {"summary": summary}
        except Exception:
            return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/generate/study-set/more")
def generate_more_study_items(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        mcq_set_id = str(payload.get("mcqSetId", "")).strip()
        count = payload.get("count", REFILL_POOL_SIZE)

        if not mcq_set_id:
            return JSONResponse(content={"error": "mcqSetId is required"}, status_code=400)
        if not isinstance(count, int) or count < 1 or count > 80:
            return JSONResponse(content={"error": "count must be an integer between 1 and 80"}, status_code=400)

        session_data = get_mcq_session(mcq_set_id)
        if not session_data:
            return JSONResponse(
                content={"error": "MCQ session expired. Generate study set again."},
                status_code=410,
            )

        source_text = str(session_data.get("source_text", "")).strip()
        if not source_text:
            return JSONResponse(
                content={"error": "Source text missing for this session. Generate study set again."},
                status_code=400,
            )

        existing_mcqs = session_data.get("items", []) or []
        existing_flashcards = session_data.get("flashcards", []) or []

        all_new_mcqs = []
        all_new_flashcards = []
        attempts = 0
        while (len(all_new_mcqs) < count or len(all_new_flashcards) < count) and attempts < 3:
            attempts += 1
            needed_mcqs = max(1, count - len(all_new_mcqs))
            needed_flashcards = max(1, count - len(all_new_flashcards))
            round_count = max(needed_mcqs, needed_flashcards)

            round_new_mcqs, round_new_flashcards = _generate_additional_items(
                source_text,
                existing_mcqs + all_new_mcqs,
                existing_flashcards + all_new_flashcards,
                round_count,
            )
            all_new_mcqs.extend(round_new_mcqs)
            all_new_flashcards.extend(round_new_flashcards)

        if len(all_new_mcqs) < count or len(all_new_flashcards) < count:
            return JSONResponse(
                content={"error": "Could not generate enough unique additional items. Try again."},
                status_code=502,
            )

        merged_mcqs = existing_mcqs + all_new_mcqs[:count]
        merged_flashcards = existing_flashcards + all_new_flashcards[:count]
        update_mcq_session(mcq_set_id, items=merged_mcqs, flashcards=merged_flashcards)
        return {"mcqs": merged_mcqs, "flashcards": merged_flashcards, "mcqSetId": mcq_set_id}
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
