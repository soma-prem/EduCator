import json
import os
import re
import time
from urllib import error as urlerror
from urllib import request as urlrequest

from utils.mcq_utils import extract_json_array


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_MAX_RETRIES = int(os.getenv("OPENROUTER_MAX_RETRIES", "2"))
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "1200"))
APP_ORIGIN = os.getenv("APP_ORIGIN", "http://localhost:3000")
APP_NAME = os.getenv("APP_NAME", "EduCator")


def extract_openrouter_text(data):
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                chunks.append(part.get("text", ""))
        return "\n".join(chunks).strip()
    return ""


def call_openrouter(prompt):
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing in backend environment")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": OPENROUTER_MAX_TOKENS,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(OPENROUTER_MAX_RETRIES + 1):
        req = urlrequest.Request(
            OPENROUTER_ENDPOINT,
            data=payload_bytes,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": APP_ORIGIN,
                "X-Title": APP_NAME,
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=120) as response:
                return response.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            last_error = f"OpenRouter HTTP {exc.code}: {error_body}"

            if exc.code == 429 and attempt < OPENROUTER_MAX_RETRIES:
                retry_after = 1.5
                if exc.headers and exc.headers.get("Retry-After"):
                    try:
                        retry_after = float(exc.headers.get("Retry-After"))
                    except ValueError:
                        retry_after = 1.5
                else:
                    retry_match = re.search(r"retry in ([0-9.]+)s", error_body, flags=re.IGNORECASE)
                    if retry_match:
                        retry_after = float(retry_match.group(1))
                time.sleep(max(1.0, retry_after))
                continue

            if exc.code == 429 and "limit: 0" in error_body:
                raise RuntimeError(
                    "OpenRouter quota/credits are unavailable for this key. "
                    "Add credits or use a key with access to google/gemini-2.5-flash."
                ) from exc

            raise RuntimeError(last_error) from exc

    raise RuntimeError(last_error or "OpenRouter request failed")


def generate_items_from_source(source_text, instruction, expected_count=10):
    prompt = (
        f"{instruction}\n\n"
        "Return only JSON array with no markdown fences and no extra text.\n\n"
        f"Source content:\n{source_text}"
    )

    body = call_openrouter(prompt)
    data = json.loads(body)
    text = extract_openrouter_text(data)
    if not text:
        raise RuntimeError("Model returned empty response")

    items = extract_json_array(text)
    if not isinstance(items, list):
        raise RuntimeError("Model response is not a list")
    if len(items) < expected_count:
        raise RuntimeError(f"Model returned {len(items)} items, expected {expected_count}")

    return items[:expected_count]


def generate_summary_from_source(source_text):
    prompt = (
        "Create a concise study summary from the provided content. "
        "Return 5-7 bullet points as plain text. "
        "Do not include markdown fences or extra commentary.\n\n"
        f"Source content:\n{source_text}"
    )
    body = call_openrouter(prompt)
    data = json.loads(body)
    text = extract_openrouter_text(data).strip()
    if not text:
        raise RuntimeError("Model returned empty summary")
    return text
