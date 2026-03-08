import json
import os
import re
import time
from urllib import error as urlerror
from urllib import request as urlrequest

from utils.mcq_utils import extract_json_array, extract_json_object


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "800"))
GEMINI_SUMMARY_MAX_TOKENS = int(os.getenv("GEMINI_SUMMARY_MAX_TOKENS", "220"))
GEMINI_STUDY_SET_MAX_TOKENS = int(os.getenv("GEMINI_STUDY_SET_MAX_TOKENS", "2200"))
GEMINI_SOURCE_CHAR_LIMIT = int(os.getenv("GEMINI_SOURCE_CHAR_LIMIT", "10000"))
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_TIMEOUT_SECONDS = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "90"))
OPENROUTER_FLASHCARDS_API_KEY = os.getenv("OPENROUTER_FLASHCARDS_API_KEY", "")
OPENROUTER_VOICE_API_KEY = os.getenv("OPENROUTER_VOICE_API_KEY", "")


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
    # JSON object/array starts but does not close.
    if (stripped.startswith("{") and not stripped.endswith("}")) or (
        stripped.startswith("[") and not stripped.endswith("]")
    ):
        return True
    return False


def _trim_source_text(source_text):
    if len(source_text) <= GEMINI_SOURCE_CHAR_LIMIT:
        return source_text
    return source_text[:GEMINI_SOURCE_CHAR_LIMIT]


def call_gemini(prompt, max_output_tokens=GEMINI_MAX_TOKENS, response_mime_type="application/json"):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing in backend environment")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
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

            if exc.code == 429 and "Quota exceeded" in error_body:
                raise RuntimeError(
                    "Gemini free-tier quota exceeded. Wait for reset or use a paid key."
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


def call_openrouter(prompt, max_output_tokens=GEMINI_MAX_TOKENS, api_key=OPENROUTER_API_KEY):
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing in backend environment")

    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_output_tokens,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=OPENROUTER_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {error_body}") from exc
    except Exception as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc}") from exc


def generate_items_from_source(source_text, instruction, expected_count=10):
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
            max_tokens = GEMINI_MAX_TOKENS
        else:
            max_tokens = max(GEMINI_MAX_TOKENS, 1800)

        body = call_gemini(prompt, max_output_tokens=max_tokens, response_mime_type="application/json")
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


def generate_mcqs_from_source_openrouter(source_text, expected_count=10):
    source_text = _trim_source_text(source_text)
    instruction = (
        f"Create exactly {expected_count} MCQs from the provided content. "
        "Each item must be: "
        "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}. "
        "The explanation should briefly explain why the correct answer is right.\n"
        "Return only a strict JSON array with no markdown fences and no extra text. "
        "Use double quotes for all JSON keys and string values.\n\n"
        f"Source content:\n{source_text}"
    )
    body = call_openrouter(instruction, max_output_tokens=max(GEMINI_MAX_TOKENS, 1800))
    data = json.loads(body)
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("OpenRouter returned empty MCQs response")
    try:
        items = extract_json_array(text)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if not isinstance(items, list) or len(items) < expected_count:
        raise RuntimeError("OpenRouter returned invalid MCQs JSON")
    return items[:expected_count]


def generate_flashcards_from_source_openrouter(source_text, expected_count=10):
    source_text = _trim_source_text(source_text)
    instruction = (
        f"Create exactly {expected_count} flashcards from the provided content. "
        "Each item must be: {\"front\":\"...\",\"back\":\"...\"}.\n"
        "Return only a strict JSON array with no markdown fences and no extra text. "
        "Use double quotes for all JSON keys and string values.\n\n"
        f"Source content:\n{source_text}"
    )
    body = call_openrouter(
        instruction,
        max_output_tokens=max(GEMINI_MAX_TOKENS, 1200),
        api_key=OPENROUTER_FLASHCARDS_API_KEY,
    )
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("OpenRouter returned empty flashcards response")
    try:
        items = extract_json_array(text)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if not isinstance(items, list) or len(items) < expected_count:
        raise RuntimeError("OpenRouter returned invalid flashcards JSON")
    return items[:expected_count]


def generate_summary_from_source(source_text):
    source_text = _trim_source_text(source_text)
    prompt = (
        "Create a concise study summary from the provided content. "
        "Return 5-7 bullet points as plain text. "
        "Do not include markdown fences or extra commentary.\n\n"
        f"Source content:\n{source_text}"
    )
    body = call_gemini(
        prompt,
        max_output_tokens=GEMINI_SUMMARY_MAX_TOKENS,
        response_mime_type="text/plain",
    )
    data = json.loads(body)
    text = extract_gemini_text(data).strip()
    if not text:
        raise RuntimeError("Model returned empty summary")
    return text


def generate_study_set_from_source(source_text, expected_count=10):
    source_text = _trim_source_text(source_text)
    prompt = (
        "Create a study set from the provided content.\n"
        f"- Return exactly {expected_count} MCQs.\n"
        f"- Return exactly {expected_count} flashcards.\n"
        "- Return a summary with 5-7 bullet points in one plain text string.\n\n"
        "Output must be a strict JSON object with this exact shape:\n"
        "{"
        '"mcqs":[{"question":"...","options":["...","...","...","..."],"answer":"...","explanation":"...","topic":"..."}],'
        '"flashcards":[{"front":"...","back":"..."}],'
        '"summary":"- ...\\n- ...\\n- ..."'
        "}\n"
        'For each MCQ, "explanation" must briefly explain why the correct answer is correct.\n'
        'For each MCQ, "topic" must be a short topic label.\n'
        "No markdown fences and no extra keys.\n\n"
        f"Source content:\n{source_text}"
    )

    # First attempt keeps latency lower. Second attempt expands output budget if truncated.
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


def answer_question_from_source(source_text, question):
    source_text = _trim_source_text(source_text)
    prompt = (
        "You are an educational tutor. Answer the student's question using ONLY the provided study content. "
        "If the answer is not present, clearly say it is not in the provided material. "
        "Keep the answer concise and clear (3-6 sentences).\n\n"
        f"Study content:\n{source_text}\n\n"
        f"Student question:\n{question}"
    )
    body = call_gemini(
        prompt,
        max_output_tokens=max(220, GEMINI_SUMMARY_MAX_TOKENS),
        response_mime_type="text/plain",
    )
    data = json.loads(body)
    text = extract_gemini_text(data).strip()
    if not text:
        raise RuntimeError("Model returned empty answer")
    return text


def answer_question_from_source_openrouter(source_text, question, api_key=OPENROUTER_VOICE_API_KEY):
    source_text = _trim_source_text(source_text)
    prompt = (
        "You are an educational tutor. Answer the student's question using ONLY the provided study content. "
        "If the answer is not present, clearly say it is not in the provided material. "
        "Keep the answer concise and clear (3-6 sentences).\n\n"
        f"Study content:\n{source_text}\n\n"
        f"Student question:\n{question}"
    )
    body = call_openrouter(
        prompt,
        max_output_tokens=max(220, GEMINI_SUMMARY_MAX_TOKENS),
        api_key=api_key,
    )
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("OpenRouter returned empty answer")
    return text
