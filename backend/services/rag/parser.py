import json
import re
from typing import Any, Dict, List


def parse_json(payload: str) -> Any:
    if payload is None:
        raise ValueError("Empty response")

    cleaned = str(payload).strip()
    if not cleaned:
        raise ValueError("Empty response")

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON: {exc}") from exc


def parse_mcqs(payload: str) -> List[Dict[str, Any]]:
    data = parse_json(payload)
    if not isinstance(data, list):
        raise ValueError("MCQ output must be a JSON array")

    parsed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each MCQ entry must be an object")
        required_fields = {"question", "options", "answer", "explanation", "topic"}
        missing = sorted(required_fields.difference(item.keys()))
        if missing:
            raise ValueError(f"MCQ missing fields: {', '.join(missing)}")
        if not isinstance(item["options"], list) or len(item["options"]) != 4:
            raise ValueError("MCQ options must be a list of four values")
        parsed.append({
            "question": str(item["question"]).strip(),
            "options": [str(option) for option in item["options"]],
            "answer": str(item["answer"]).strip(),
            "explanation": str(item["explanation"]).strip(),
            "topic": str(item["topic"]).strip(),
        })
    return parsed


def parse_flashcards(payload: str) -> List[Dict[str, Any]]:
    data = parse_json(payload)
    if not isinstance(data, list):
        raise ValueError("Flashcard output must be a JSON array")

    parsed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each flashcard entry must be an object")
        required_fields = {"front", "back", "topic"}
        missing = sorted(required_fields.difference(item.keys()))
        if missing:
            raise ValueError(f"Flashcard missing fields: {', '.join(missing)}")
        parsed.append({
            "front": str(item["front"]).strip(),
            "back": str(item["back"]).strip(),
            "topic": str(item["topic"]).strip(),
        })
    return parsed


def parse_true_false(payload: str) -> List[Dict[str, Any]]:
    data = parse_json(payload)
    if not isinstance(data, list):
        raise ValueError("True/False output must be a JSON array")

    parsed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each true/false entry must be an object")
        required_fields = {"question", "answer", "explanation", "topic"}
        missing = sorted(required_fields.difference(item.keys()))
        if missing:
            raise ValueError(f"True/False missing fields: {', '.join(missing)}")
        parsed.append({
            "question": str(item["question"]).strip(),
            "answer": str(item["answer"]).strip().lower() in {"true", "false"},
            "explanation": str(item["explanation"]).strip(),
            "topic": str(item["topic"]).strip(),
        })
    return parsed


def parse_fill_blanks(payload: str) -> List[Dict[str, Any]]:
    data = parse_json(payload)
    if not isinstance(data, list):
        raise ValueError("Fill blank output must be a JSON array")

    parsed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each fill blank entry must be an object")
        required_fields = {"prompt", "answer", "explanation", "topic"}
        missing = sorted(required_fields.difference(item.keys()))
        if missing:
            raise ValueError(f"Fill blank missing fields: {', '.join(missing)}")
        parsed.append({
            "prompt": str(item["prompt"]).strip(),
            "answer": str(item["answer"]).strip(),
            "explanation": str(item["explanation"]).strip(),
            "topic": str(item["topic"]).strip(),
        })
    return parsed
