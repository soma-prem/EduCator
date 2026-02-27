import json
import re


def extract_json_array(raw_text):
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("Model did not return JSON array")
    return json.loads(cleaned[start : end + 1])


def extract_option_key(value):
    match = re.match(r"^\s*([A-Da-d])(?:[\).\:\-\s]|$)", str(value or ""))
    if not match:
        return ""
    return match.group(1).upper()


def normalize_option_text(value):
    text = str(value or "").strip().lower()
    return re.sub(r"^[a-d](?:[\).\:\-\s]+|$)", "", text)


def is_correct_option(option, answer):
    option_key = extract_option_key(option)
    answer_key = extract_option_key(answer)
    if option_key and answer_key:
        return option_key == answer_key
    return normalize_option_text(option) == normalize_option_text(answer)


def resolve_correct_index(options, answer):
    if not options:
        return -1

    answer_key = extract_option_key(answer)
    if answer_key:
        index = ord(answer_key) - ord("A")
        if 0 <= index < len(options):
            return index

    normalized_answer = normalize_option_text(answer)
    if not normalized_answer:
        return -1

    for idx, option in enumerate(options):
        if normalize_option_text(option) == normalized_answer:
            return idx

    for idx, option in enumerate(options):
        normalized_option = normalize_option_text(option)
        if normalized_answer in normalized_option or normalized_option in normalized_answer:
            return idx

    return -1


def resolve_selected_index(options, selected_answer):
    if not options:
        return -1

    for idx, option in enumerate(options):
        if option == selected_answer:
            return idx

    normalized_selected = normalize_option_text(selected_answer)
    for idx, option in enumerate(options):
        if normalize_option_text(option) == normalized_selected:
            return idx

    return -1
