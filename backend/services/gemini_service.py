import json
import os
import re
import time
from urllib import error as urlerror
from urllib import request as urlrequest

from utils.mcq_utils import extract_json_array, extract_json_object


GEMINI_API_KEY = os.getenv("GEMINI_MCQ_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "800"))
GEMINI_SUMMARY_MAX_TOKENS = int(os.getenv("GEMINI_SUMMARY_MAX_TOKENS", "650"))
GEMINI_STUDY_SET_MAX_TOKENS = int(os.getenv("GEMINI_STUDY_SET_MAX_TOKENS", "2200"))
GEMINI_QA_MAX_TOKENS = int(os.getenv("GEMINI_QA_MAX_TOKENS", "900"))
GEMINI_SOURCE_CHAR_LIMIT = int(os.getenv("GEMINI_SOURCE_CHAR_LIMIT", "10000"))
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_TIMEOUT_SECONDS = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "90"))
OPENROUTER_FLASHCARDS_API_KEY = os.getenv("OPENROUTER_FLASHCARDS_API_KEY", "")
OPENROUTER_VOICE_API_KEY = os.getenv("OPENROUTER_VOICE_API_KEY", "")
OPENROUTER_SUMMARIZATION_KEY = os.getenv("OPENROUTER_SUMMARIZATION_KEY", "")
OPENROUTER_FILL_IN_THE_BLANKS_KEY = os.getenv("OPENROUTER_FILL_IN_THE_BLANKS_KEY", "")
OPENROUTER_TRUE_FALSE_KEY = os.getenv("OPENROUTER_TRUE_FALSE_KEY", "")
OPENROUTER_QA_MAX_TOKENS = int(os.getenv("OPENROUTER_QA_MAX_TOKENS", "900"))
MATCH_THE_PAIR_API = os.getenv("MATCH_THE_PAIR_API", "")


def _looks_truncated(text):
    value = str(text or "").strip()
    if not value:
        return False
    # If it ends with a word character, it's often cut off due to token limits.
    # Don't treat '?'/'!' as truncated.
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


def extract_openrouter_text(body):
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return str(content or "").strip()


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
            if remaining > 10:
                max_tokens = max(GEMINI_MAX_TOKENS, 2200)
            else:
                max_tokens = GEMINI_MAX_TOKENS
        else:
            max_tokens = max(GEMINI_MAX_TOKENS, 5000 if remaining > 10 else 1800)

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


def generate_mcqs_from_source_openrouter(source_text, expected_count=10, difficulty="medium"):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    instruction = (
        "Difficulty: easy = basic recall/definitions; medium = conceptual and moderately challenging; "
        "hard = advanced reasoning, nuanced distractors, and deeper understanding.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        f"Create exactly {expected_count} MCQs from the provided content. "
        "Each item must be: "
        "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}. "
        "The explanation should briefly explain why the correct answer is right.\n"
        "Return only a strict JSON array with no markdown fences and no extra text. "
        "Use double quotes for all JSON keys and string values.\n\n"
        f"Source content:\n{source_text}"
    )
    token_budget = max(GEMINI_MAX_TOKENS, 1800 if expected_count <= 10 else 3600)
    body = call_openrouter(instruction, max_output_tokens=token_budget)
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


def generate_flashcards_from_source_openrouter(source_text, expected_count=10, difficulty="medium"):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    instruction = (
        "Difficulty: easy = direct definitions; medium = conceptual Q/A; hard = nuanced, tricky, and application-focused.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        f"Create exactly {expected_count} flashcards from the provided content. "
        "Each item must be: {\"front\":\"...\",\"back\":\"...\",\"topic\":\"...\"}.\n"
        "Return only a strict JSON array with no markdown fences and no extra text. "
        "Use double quotes for all JSON keys and string values.\n\n"
        f"Source content:\n{source_text}"
    )
    token_budget = max(GEMINI_MAX_TOKENS, 1200 if expected_count <= 10 else 2800)
    body = call_openrouter(instruction, max_output_tokens=token_budget, api_key=OPENROUTER_FLASHCARDS_API_KEY)
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


def generate_fill_in_the_blanks_from_source_openrouter(source_text, expected_count=10, difficulty="medium"):
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
    token_budget = max(GEMINI_MAX_TOKENS, 1800 if expected_count <= 10 else 3600)
    body = call_openrouter(instruction, max_output_tokens=token_budget, api_key=OPENROUTER_FILL_IN_THE_BLANKS_KEY)
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("OpenRouter returned empty fill-in-the-blanks response")
    try:
        items = extract_json_array(text)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if not isinstance(items, list) or len(items) < expected_count:
        raise RuntimeError("OpenRouter returned invalid fill-in-the-blanks JSON")
    return items[:expected_count]


def generate_true_false_from_source_openrouter(source_text, expected_count=10, difficulty="medium"):
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
    if not OPENROUTER_TRUE_FALSE_KEY:
        raise RuntimeError("OPENROUTER_TRUE_FALSE_KEY is missing in backend environment")
    token_budget = max(GEMINI_MAX_TOKENS, 1600 if expected_count <= 10 else 3400)
    body = call_openrouter(instruction, max_output_tokens=token_budget, api_key=OPENROUTER_TRUE_FALSE_KEY)
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("OpenRouter returned empty true/false response")
    try:
        items = extract_json_array(text)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if not isinstance(items, list) or len(items) < expected_count:
        raise RuntimeError("OpenRouter returned invalid true/false JSON")
    return items[:expected_count]


def generate_match_the_pair_from_source_openrouter(
    source_text,
    expected_set_count=5,
    expected_pairs_per_set=5,
    difficulty="medium",
):
    source_text = _trim_source_text(source_text)
    difficulty = str(difficulty or "medium").strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    if not MATCH_THE_PAIR_API:
        raise RuntimeError("MATCH_THE_PAIR_API is missing in backend environment")

    instruction = (
        "You are creating content for a 'Match the Pair' activity based on the source.\n"
        "Difficulty: easy = obvious term/definition; medium = conceptual pairings; hard = nuanced, tricky pairings.\n"
        f"Selected difficulty: {difficulty}.\n\n"
        f"Create exactly {expected_set_count} sets.\n"
        f"Each set must contain exactly {expected_pairs_per_set} pairs.\n"
        "Pairs should be grounded in the source content.\n"
        "Avoid near-duplicates within a set.\n\n"
        "Return ONLY a strict JSON object with this exact shape:\n"
        "{\n"
        '  "sets":[\n'
        "    {\n"
        '      "title":"...",\n'
        '      "pairs":[{"left":"...","right":"..."}, ...]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "No markdown fences, no extra keys, no extra text.\n\n"
        f"Source content:\n{source_text}"
    )

    token_budget = max(GEMINI_MAX_TOKENS, 2200)
    body = call_openrouter(instruction, max_output_tokens=token_budget, api_key=MATCH_THE_PAIR_API)
    text = extract_openrouter_text(body)
    if not text:
        raise RuntimeError("OpenRouter returned empty match-the-pair response")
    try:
        data = extract_json_object(text)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc

    sets = data.get("sets") if isinstance(data, dict) else None
    if not isinstance(sets, list) or len(sets) < expected_set_count:
        raise RuntimeError("OpenRouter returned invalid match-the-pair JSON")

    normalized_sets = []
    for raw_set in sets[:expected_set_count]:
        title = str((raw_set or {}).get("title") or "").strip() or "Match the Pair"
        pairs = (raw_set or {}).get("pairs")
        if not isinstance(pairs, list) or len(pairs) < expected_pairs_per_set:
            raise RuntimeError("OpenRouter returned invalid match-the-pair pairs")
        normalized_pairs = []
        for pair in pairs[:expected_pairs_per_set]:
            left = str((pair or {}).get("left") or "").strip()
            right = str((pair or {}).get("right") or "").strip()
            if not left or not right:
                raise RuntimeError("OpenRouter returned empty match-the-pair pair values")
            normalized_pairs.append({"left": left, "right": right})
        normalized_sets.append({"title": title, "pairs": normalized_pairs})

    return normalized_sets


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

    if OPENROUTER_SUMMARIZATION_KEY:
        body = call_openrouter(
            prompt,
            max_output_tokens=max(GEMINI_SUMMARY_MAX_TOKENS, 1200),
            api_key=OPENROUTER_SUMMARIZATION_KEY,
        )
        text = extract_openrouter_text(body)
    else:
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
        'For each MCQ, "explanation" must briefly explain why the correct answer is correct.\n'
        'For each MCQ, "topic" must be a short topic label.\n'
        'For each flashcard, "topic" must be a short topic label.\n'
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
        "Write a detailed answer (8-12 sentences) and ensure the final sentence ends with a period.\n\n"
        f"Study content:\n{source_text}\n\n"
        f"Student question:\n{question}"
    )
    max_tokens = max(350, GEMINI_QA_MAX_TOKENS)
    for attempt in range(2):
        body = call_gemini(prompt, max_output_tokens=max_tokens, response_mime_type="text/plain")
        data = json.loads(body)
        text = extract_gemini_text(data).strip()
        if not text:
            raise RuntimeError("Model returned empty answer")
        if not _looks_truncated(text):
            return text
        # Retry once with higher budget to avoid cut-off endings.
        max_tokens = max(max_tokens * 2, 1200)
    return text


def answer_question_from_source_openrouter(source_text, question, api_key=OPENROUTER_VOICE_API_KEY):
    source_text = _trim_source_text(source_text)
    prompt = (
        "You are an educational tutor. Answer the student's question using ONLY the provided study content. "
        "If the answer is not present, clearly say it is not in the provided material. "
        "Write a detailed answer (8-12 sentences) and ensure the final sentence ends with a period.\n\n"
        f"Study content:\n{source_text}\n\n"
        f"Student question:\n{question}"
    )
    max_tokens = max(350, OPENROUTER_QA_MAX_TOKENS)
    for attempt in range(2):
        body = call_openrouter(prompt, max_output_tokens=max_tokens, api_key=api_key)
        data = json.loads(body)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        text = str(content or "").strip()
        if not text:
            raise RuntimeError("OpenRouter returned empty answer")
        if not _looks_truncated(text):
            return text
        max_tokens = max(max_tokens * 2, 1200)
    return text
