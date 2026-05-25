import json
import re

from services.gemini_service import GEMINI_MAX_TOKENS, call_gemini, extract_gemini_text
from utils.mcq_utils import (
    _aggressive_quote_repair,
    _repair_json_text,
    extract_json_object,
)

GEMINI_EXAM_MAX_TOKENS = max(GEMINI_MAX_TOKENS, 3000)


def _call_gemini_exam(prompt, max_output_tokens=GEMINI_EXAM_MAX_TOKENS):
    return call_gemini(prompt, max_output_tokens=max_output_tokens, response_mime_type="application/json")


def _sanitize_sections(sections):
    safe = []
    for item in sections or []:
        try:
            name = str(item.get("name", "")).strip() or "General"
            count = int(item.get("questions", 0) or 0)
            weight = float(item.get("weight", 0) or 0)
            safe.append({"name": name[:60], "questions": max(1, count), "weight": max(0.0, weight)})
        except Exception:
            continue
    if not safe:
        safe = [
            {"name": "Concepts", "questions": 7, "weight": 0.35},
            {"name": "Applications", "questions": 7, "weight": 0.35},
            {"name": "Challenge", "questions": 6, "weight": 0.3},
        ]
    return safe


def generate_mock_exam(syllabus_text, past_papers_text="", sections=None, total_questions=20, duration_minutes=60):
    sections = _sanitize_sections(sections)
    total_questions = max(5, min(int(total_questions or 20), 80))
    duration_minutes = max(20, min(int(duration_minutes or 60), 240))

    section_lines = "\n".join(
        [f"- {s['name']} ({s['questions']} questions, weight {s['weight']:.2f})" for s in sections]
    )
    prompt = f"""
You are an exam setter. Build ONE timed mock exam focused strictly on the syllabus and (optional) past papers.

STRICT REQUIREMENTS (must follow exactly):
1) Output MUST be a single valid JSON object. No markdown, no comments, no extra text.
2) Output keys MUST be exactly: "sections", "questions", "timing". No other top-level keys.
3) questions MUST contain EXACTLY {total_questions} items.
4) Each question MUST be a single-correct MCQ with EXACTLY 4 options (array of 4 distinct strings).
5) "answer" MUST match EXACTLY one of the 4 option strings (case + spacing).
6) No duplicate questions; no duplicate options inside a question; avoid trivial "All of the above"/"None of the above".
7) Use ONLY the syllabus/past paper topics. If something is missing, ask an easier question from available topics (do not invent).
8) timing.totalMinutes MUST be exactly {duration_minutes} (integer).
9) suggestedTimeMinutes MUST be an integer 1..10. Sum across all questions SHOULD be close to totalMinutes.
10) difficulty MUST be one of: "easy", "medium", "hard".

SECTIONS:
- You MUST respect the requested section distribution below.
- In "sections", include list items: {{name, plannedQuestions, weight, focusTopics}}.
- plannedQuestions across sections MUST sum to {total_questions}.

TIMING:
- timing MUST be: {{ "totalMinutes": {duration_minutes}, "recommendedPacingPerSection": {{ sectionName: minutesInt }} }}
- recommendedPacingPerSection MUST include ALL section names and minutes MUST sum to {duration_minutes}.

QUESTION OBJECT SCHEMA (repeat exactly for each question):
{{
  "id": "q-1",
  "section": "Section name from sections[].name",
  "question": "string",
  "options": ["A", "B", "C", "D"],
  "answer": "one of the options[] strings",
  "explanation": "1-2 sentences",
  "difficulty": "easy|medium|hard",
  "suggestedTimeMinutes": 1
}}

Syllabus:
{syllabus_text}

Past papers (optional):
{past_papers_text}

Sections requested (use these names; adjust plannedQuestions so the sum is exactly {total_questions} if needed):
{section_lines}
""".strip()

    body = _call_gemini_exam(prompt, max_output_tokens=max(GEMINI_EXAM_MAX_TOKENS, 8192))
    data = json.loads(body)
    text = extract_gemini_text(data)
    if not text:
        raise RuntimeError("Gemini returned empty mock exam response")
    text = text.strip()

    def _coerce_json_object(raw: str):
        """
        Gemini sometimes returns:
        - Markdown fences
        - JSON wrapped in a quoted string
        - Slightly malformed JSON (smart quotes, stray commas, etc.)
        Try progressively stronger repairs before giving up.
        """
        # Strip common fences/backticks
        cleaned = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

        # Remove common invisible/bom chars that break json at early positions
        cleaned = cleaned.lstrip("\ufeff\u200b\u200c\u200d")
        # Drop other ASCII control chars (except whitespace that JSON allows between tokens)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", cleaned)

        # Unwrap if the whole payload is a quoted JSON string
        if cleaned.startswith('"') and cleaned.endswith('"'):
            try:
                decoded = json.loads(cleaned)
                if isinstance(decoded, str):
                    cleaned = decoded.strip()
            except Exception:
                pass

        # If stray text before/after JSON, clip to first '{' ... last '}'
        if "{" in cleaned and "}" in cleaned:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            cleaned = cleaned[start : end + 1]

        # 1) Normal path (strict)
        try:
            return extract_json_object(cleaned)
        except Exception:
            pass

        # 1b) Allow control chars inside strings
        try:
            parsed = json.loads(cleaned, strict=False)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 2) Repair common JSON issues (smart quotes, trailing commas)
        try:
            repaired = _repair_json_text(cleaned)
            parsed = json.loads(repaired, strict=False)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 3) Aggressive repair (drop backslashes before quotes)
        repaired_aggressive = _aggressive_quote_repair(cleaned)
        return json.loads(repaired_aggressive, strict=False)

    try:
        result = _coerce_json_object(text)
    except Exception as exc:  # pragma: no cover
        preview = text[:240].replace("\n", " ")
        raise RuntimeError(f"Failed to parse mock exam JSON: {exc}; preview: {preview}") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Mock exam JSON is not an object")

    # Light validation
    questions = result.get("questions", []) if isinstance(result, dict) else []
    if not questions:
        raise RuntimeError("Mock exam JSON missing questions")

    if not isinstance(questions, list):
        raise RuntimeError("Mock exam JSON questions must be a list")

    if len(questions) < total_questions:
        raise RuntimeError(f"Mock exam generated {len(questions)} questions, expected {total_questions}. Please regenerate.")

    if len(questions) > total_questions:
        questions = questions[:total_questions]

    result["questions"] = questions
    timing = result.get("timing", {})
    if not isinstance(timing, dict):
        timing = {}
    timing["totalMinutes"] = duration_minutes
    result["timing"] = timing
    return result
