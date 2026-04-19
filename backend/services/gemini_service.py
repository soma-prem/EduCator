import json
import os
import re
import time
from urllib import error as urlerror
from urllib import request as urlrequest

from utils.mcq_utils import extract_json_array, extract_json_object


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MCQ_API_KEY = os.getenv("GEMINI_MCQ_API_KEY", "")
GEMINI_FLASHCARD_API_KEY = os.getenv("GEMINI_FLASHCARD_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "800"))
GEMINI_SUMMARY_MAX_TOKENS = int(os.getenv("GEMINI_SUMMARY_MAX_TOKENS", "650"))
GEMINI_STUDY_SET_MAX_TOKENS = int(os.getenv("GEMINI_STUDY_SET_MAX_TOKENS", "2200"))
GEMINI_QA_MAX_TOKENS = int(os.getenv("GEMINI_QA_MAX_TOKENS", "900"))
GEMINI_SOURCE_CHAR_LIMIT = int(os.getenv("GEMINI_SOURCE_CHAR_LIMIT", "10000"))
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))
GEMINI_TRUEANDFALSE_API_KEY = os.getenv("GEMINI_TRUEANDFALSE_API_KEY", "")

GEMINI_VOICE_API_KEY = os.getenv("GEMINI_VOICE_API_KEY", "")
GEMINI_FILLIN_API_KEY = os.getenv("GEMINI_FILLIN_API_KEY", "")
GEMINI_SUMMARY_API_KEY = os.getenv("GEMINI_SUMMARY_API_KEY", "")
GEMINI_TEXTAI_API_KEY = os.getenv("GEMINI_TEXTAI_API_KEY", "")


def _looks_truncated(text):
    value = str(text or "").strip()
    if not value:
        return False
    return value[-1].isalnum()


def extract_gemini_text(data):
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    chunks = []
    for part in parts:
        text = part.get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _is_truncated_generation(data, text):
    candidates = data.get("candidates", [])
    if candidates:
        finish_reason = str(candidates[0].get("finishReason", "")).upper()
        if finish_reason == "MAX_TOKENS":
            return True
    stripped = (text or "").rstrip()
    if (stripped.startswith("{") and not stripped.endswith("}")) or (
        stripped.startswith("[") and not stripped.endswith("]")
    ):
        return True
    return False


def _trim_source_text(source_text):
    if len(source_text) <= GEMINI_SOURCE_CHAR_LIMIT:
        return source_text
    return source_text[:GEMINI_SOURCE_CHAR_LIMIT]


def call_gemini(prompt, max_output_tokens=GEMINI_MAX_TOKENS, response_mime_type="application/json", api_key=None):
    key = str(api_key or GEMINI_API_KEY or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing in backend environment")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": response_mime_type,
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
    tried_global_fallback = False
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        req = urlrequest.Request(
            endpoint,
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=GEMINI_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            last_error = f"Gemini HTTP {exc.code}: {error_body}"

            # If a per-tool key hits free-tier quota, try the global GEMINI_API_KEY as a fallback once.
            if exc.code == 429 and re.search(r"quota", error_body, flags=re.IGNORECASE):
                # If we tried a specific key and there is a different global key available, attempt it once.
                global_key = str(GEMINI_API_KEY or "").strip()
                if global_key and global_key != key and not tried_global_fallback:
                    tried_global_fallback = True
                    key = global_key
                    endpoint = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
                        f"?key={key}"
                    )
                    # retry immediately with the global key
                    continue
                # If fallback not available or already tried, surface a clear message.
                raise RuntimeError(
                    "Gemini quota exceeded on provided key. Wait for quota reset or use a paid key."
                ) from exc

            if exc.code == 429 and attempt < GEMINI_MAX_RETRIES:
                retry_after = 1.5
                retry_match = re.search(r"retry in ([0-9.]+)s", error_body, flags=re.IGNORECASE)
                if retry_match:
                    retry_after = float(retry_match.group(1))
                time.sleep(max(1.0, retry_after))
                continue

            raise RuntimeError(last_error) from exc

    raise RuntimeError(last_error or "Gemini request failed")


def generate_items_from_source(source_text, instruction, expected_count=10, api_key=None):
    source_text = _trim_source_text(source_text)

    def item_signature(item):
        if not isinstance(item, dict):
            return str(item)
        if item.get("question"):
            return str(item.get("question")).strip().lower()
        if item.get("front"):
            return str(item.get("front")).strip().lower()
        return json.dumps(item, sort_keys=True, ensure_ascii=False)

    collected = []
    seen = set()
    last_error = None

    for attempt_index in range(5):
        remaining = max(1, expected_count - len(collected))
        existing_list = "\n".join([f"- {item_signature(it)}" for it in collected[:80]])
        prompt = (
            f"{instruction}\n\n"
            f"Generate exactly {remaining} items this turn.\n"
            "Return only a strict JSON array with no markdown fences and no extra text. "
            "Use double quotes for all JSON keys and string values.\n"
            "Do not repeat previously generated items.\n"
            f"Already generated items:\n{existing_list or '- None'}\n\n"
            f"Source content:\n{source_text}"
        )
        if attempt_index == 0:
            if remaining > 10:
                max_tokens = max(GEMINI_MAX_TOKENS, 2200)
            else:
                max_tokens = GEMINI_MAX_TOKENS
        else:
            max_tokens = max(GEMINI_MAX_TOKENS, 5000 if remaining > 10 else 1800)

        body = call_gemini(prompt, max_output_tokens=max_tokens, response_mime_type="application/json", api_key=api_key)
        data = json.loads(body)
        text = extract_gemini_text(data)
        if not text:
            last_error = RuntimeError("Model returned empty response")
            continue

        try:
            items = extract_json_array(text)
        except ValueError as exc:
            last_error = RuntimeError(str(exc))
            if _is_truncated_generation(data, text):
                continue
            continue

        if not isinstance(items, list):
            last_error = RuntimeError("Model response is not a list")
            continue

        for item in items:
            signature = item_signature(item)
            if signature in seen:
                continue
            seen.add(signature)
            collected.append(item)
            if len(collected) >= expected_count:
                return collected[:expected_count]

        last_error = RuntimeError(f"Model returned {len(collected)} unique items, expected {expected_count}")

    raise last_error or RuntimeError(f"Model returned {len(collected)} unique items, expected {expected_count}")


def generate_fill_in_the_blanks_from_source(source_text, expected_count=10, difficulty="medium", api_key=None):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    instruction = (
        "Difficulty: easy = obvious blanks; medium = key-term blanks; hard = nuanced concept blanks.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        f"Create exactly {expected_count} fill-in-the-blank questions from the provided content.\n"
        "Each item must be a JSON object with this exact shape:\n"
        "{\"prompt\":\"... ____ ...\",\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}\n"
        "- The prompt must include exactly one blank shown as four underscores: ____\n"
        "- The answer must be a short word/phrase.\n"
        "- The explanation must be 1-2 sentences.\n"
        "- The topic must be a short topic label.\n"
        "Return only a strict JSON array with no markdown fences and no extra text.\n\n"
        f"Source content:\n{source_text}"
    )

    key = api_key or GEMINI_FILLIN_API_KEY or GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_FILLIN_API_KEY or GEMINI_API_KEY is required for fill-in-the-blanks generation")

    items = generate_items_from_source(source_text, instruction, expected_count=expected_count, api_key=key)
    return items


def generate_true_false_from_source(source_text, expected_count=10, difficulty="medium", api_key=None):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    instruction = (
        "Difficulty: easy = straightforward facts; medium = moderately tricky statements; hard = nuanced and subtle statements.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        f"Create exactly {expected_count} True/False questions from the provided content.\n"
        "Each item must be a JSON object with this exact shape:\n"
        "{\"statement\":\"...\",\"answer\":true,\"explanation\":\"...\",\"topic\":\"...\"}\n"
        "- The statement must be clear and factual.\n"
        "- The answer must be a JSON boolean (true/false), not a string.\n"
        "- The explanation must be 1-2 sentences.\n"
        "- The topic must be a short topic label.\n"
        "Return only a strict JSON array with no markdown fences and no extra text.\n\n"
        f"Source content:\n{source_text}"
    )

    key = api_key or GEMINI_TRUEANDFALSE_API_KEY or GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_TRUEANDFALSE_API_KEY or GEMINI_API_KEY is required for true/false generation")

    items = generate_items_from_source(source_text, instruction, expected_count=expected_count, api_key=key)
    return items


def generate_summary_from_source(source_text):
    source_text = _trim_source_text(source_text)
    prompt = (
        "Create a detailed, student-friendly study summary from the provided content.\n"
        "- Return 12-16 bullet points as plain text.\n"
        "- Each bullet should be a complete idea (definition, key fact, cause/effect, or example).\n"
        "- Keep it grounded strictly in the provided content.\n"
        "Do not include markdown fences or extra commentary.\n\n"
        f"Source content:\n{source_text}"
    )

    key = GEMINI_SUMMARY_API_KEY or GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_SUMMARY_API_KEY or GEMINI_API_KEY is required for summary generation")
    body = call_gemini(
        prompt,
        max_output_tokens=GEMINI_SUMMARY_MAX_TOKENS,
        response_mime_type="text/plain",
        api_key=key,
    )
    data = json.loads(body)
    text = extract_gemini_text(data).strip()

    if not text:
        raise RuntimeError("Model returned empty summary")
    return text


def generate_study_set_from_source(source_text, expected_count=10, difficulty="medium"):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    prompt = (
        "Difficulty: easy = basic recall/definitions; medium = conceptual and moderately challenging; "
        "hard = advanced reasoning and deeper understanding.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        "Create a study set from the provided content.\n"
        f"- Return exactly {expected_count} MCQs.\n"
        f"- Return exactly {expected_count} flashcards.\n"
        "- Return a summary with 5-7 bullet points in one plain text string.\n\n"
        "Output must be a strict JSON object with this exact shape:\n"
        "{"
        '"mcqs":[{"question":"...","options":["...","...","...","..."],"answer":"...","explanation":"...","topic":"..."}],'
        '"flashcards":[{"front":"...","back":"...","topic":"..."}],'
        '"summary":"- ...\\n- ...\\n- ..."'
        "}\n"
        "For each MCQ, \"explanation\" must briefly explain why the correct answer is correct.\n"
        "For each MCQ, \"topic\" must be a short topic label.\n"
        "For each flashcard, \"topic\" must be a short topic label.\n"
        "No markdown fences and no extra keys.\n\n"
        f"Source content:\n{source_text}"
    )

    token_budgets = [GEMINI_STUDY_SET_MAX_TOKENS, max(GEMINI_STUDY_SET_MAX_TOKENS, 5000)]
    result = None
    last_parse_error = None
    for token_budget in token_budgets:
        body = call_gemini(
            prompt,
            max_output_tokens=token_budget,
            response_mime_type="application/json",
        )
        data = json.loads(body)
        text = extract_gemini_text(data).strip()
        if not text:
            last_parse_error = RuntimeError("Model returned empty study set")
            continue

        try:
            result = extract_json_object(text)
            break
        except ValueError as exc:
            last_parse_error = exc
            if _is_truncated_generation(data, text):
                continue
            raise RuntimeError(str(exc)) from exc

    if result is None:
        raise RuntimeError(str(last_parse_error or "Model returned invalid JSON study set"))
    mcqs = result.get("mcqs")
    flashcards = result.get("flashcards")
    summary = str(result.get("summary", "")).strip()

    if not isinstance(mcqs, list) or len(mcqs) < expected_count:
        raise RuntimeError("Model returned invalid MCQs JSON")
    if not isinstance(flashcards, list) or len(flashcards) < expected_count:
        raise RuntimeError("Model returned invalid flashcards JSON")
    if not summary:
        raise RuntimeError("Model returned empty summary")

    return {
        "mcqs": mcqs[:expected_count],
        "flashcards": flashcards[:expected_count],
        "summary": summary,
    }


def answer_question_from_source(source_text, question, api_key=None):
    source_text = _trim_source_text(source_text)
    prompt = (
        "You are an educational tutor. Answer the student's question using ONLY the provided study content. "
        "If the answer is not present, clearly say it is not in the provided material. "
        "Write a detailed answer (8-12 sentences) and ensure the final sentence ends with a period.\n\n"
        f"Study content:\n{source_text}\n\n"
        f"Student question:\n{question}"
    )
    max_tokens = max(350, GEMINI_QA_MAX_TOKENS)
    key = api_key or GEMINI_VOICE_API_KEY or GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_VOICE_API_KEY or GEMINI_API_KEY is required for voice QA")
    for attempt in range(2):
        body = call_gemini(prompt, max_output_tokens=max_tokens, response_mime_type="text/plain", api_key=key)
        data = json.loads(body)
        text = extract_gemini_text(data).strip()
        if not text:
            raise RuntimeError("Model returned empty answer")
        if not _looks_truncated(text):
            return text
        max_tokens = max(max_tokens * 2, 1200)
    return text
