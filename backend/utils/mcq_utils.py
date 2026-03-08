import json
import re


def _repair_json_text(text):
    # Fix common model mistakes: smart quotes and trailing commas
    repaired = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    # Fix escaped quotes in keys like "question\": and in values like \"A)
    repaired = re.sub(r'"([^"]*?)\\\"\s*:', r'"\1":', repaired)
    repaired = re.sub(r'([\[\{:,]\s*)\\"', r'\1"', repaired)
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    repaired = _escape_unquoted_inner_quotes(repaired)
    repaired = _close_unterminated_strings(repaired)
    repaired = _balance_brackets(repaired)
    return repaired


def _aggressive_quote_repair(text):
    # As a last resort, drop backslashes before quotes and re-run repairs.
    return _repair_json_text(text.replace('\\"', '"'))


def _escape_unquoted_inner_quotes(text):
    # Convert unescaped quotes inside strings into escaped quotes.
    out = []
    in_string = False
    escape = False

    def _next_non_space(idx):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        return text[idx] if idx < len(text) else ""

    for idx, char in enumerate(text):
        if escape:
            out.append(char)
            escape = False
            continue
        if char == "\\":
            out.append(char)
            escape = True
            continue
        if char == '"':
            if in_string:
                next_char = _next_non_space(idx + 1)
                if next_char and next_char not in (",", "}", "]"):
                    out.append('\\"')
                    continue
                in_string = False
                out.append(char)
                continue
            in_string = True
            out.append(char)
            continue
        out.append(char)

    return "".join(out)


def _close_unterminated_strings(text):
    # If a string is missing its closing quote, close it before a structural ] or }.
    out = []
    in_string = False
    escape = False

    for char in text:
        if escape:
            out.append(char)
            escape = False
            continue
        if char == "\\":
            out.append(char)
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            out.append(char)
            continue
        if in_string and char in ("]", "}"):
            out.append('"')
            in_string = False
        out.append(char)

    if in_string:
        out.append('"')
    return "".join(out)


def _balance_brackets(text):
    # Ensure brackets close in the correct order by inserting missing closers.
    out = []
    stack = []
    in_string = False
    escape = False

    for char in text:
        if escape:
            out.append(char)
            escape = False
            continue
        if char == "\\":
            out.append(char)
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            out.append(char)
            continue
        if in_string:
            out.append(char)
            continue

        if char == "{":
            stack.append("}")
            out.append(char)
            continue
        if char == "[":
            stack.append("]")
            out.append(char)
            continue
        if char in ("}", "]"):
            while stack and stack[-1] != char:
                out.append(stack.pop())
            if stack and stack[-1] == char:
                stack.pop()
                out.append(char)
            else:
                out.append(char)
            continue

        out.append(char)

    while stack:
        out.append(stack.pop())
    return "".join(out)


def _close_array_candidate(text):
    candidate = text.strip()
    if not candidate.startswith("["):
        return candidate

    open_square = candidate.count("[")
    close_square = candidate.count("]")
    open_curly = candidate.count("{")
    close_curly = candidate.count("}")

    if close_curly < open_curly:
        candidate += "}" * (open_curly - close_curly)
    candidate = re.sub(r",\s*$", "", candidate)
    if close_square < open_square:
        candidate += "]" * (open_square - close_square)
    return candidate


def _extract_json_objects_from_array_text(text):
    start = text.find("[")
    if start == -1:
        return []
    body = text[start + 1 :]

    objects = []
    depth = 0
    item_start = -1
    in_string = False
    escape = False

    for idx, char in enumerate(body):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if char == "{":
            if depth == 0:
                item_start = idx
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and item_start != -1:
                    chunk = body[item_start : idx + 1]
                    try:
                        parsed = json.loads(_repair_json_text(chunk))
                        if isinstance(parsed, dict):
                            objects.append(parsed)
                    except json.JSONDecodeError:
                        try:
                            parsed = json.loads(_aggressive_quote_repair(chunk))
                            if isinstance(parsed, dict):
                                objects.append(parsed)
                        except json.JSONDecodeError:
                            pass
                    item_start = -1
    return objects


def extract_json_array(raw_text):
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()

    # Fast path: sometimes the model returns a full JSON object wrapper.
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("items", "mcqs", "flashcards", "data", "result"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return value
            for value in parsed.values():
                if isinstance(value, list):
                    return value
    except json.JSONDecodeError:
        pass

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1:
        preview = cleaned[:220].replace("\n", " ")
        raise ValueError(f"Model did not return JSON array. Preview: {preview}...")

    if end == -1:
        candidate = _close_array_candidate(cleaned[start:])
    else:
        candidate = cleaned[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        repaired = _repair_json_text(candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            aggressive = _aggressive_quote_repair(repaired)
            try:
                return json.loads(aggressive)
            except json.JSONDecodeError:
                recovered = _extract_json_objects_from_array_text(aggressive)
            if recovered:
                return recovered
            preview = aggressive[:220].replace("\n", " ")
            raise ValueError(
                f"Model returned invalid JSON array near char {exc.pos}: {preview}..."
            ) from exc


def extract_json_object(raw_text):
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        preview = cleaned[:220].replace("\n", " ")
        raise ValueError(f"Model did not return JSON object. Preview: {preview}...")

    candidate = cleaned[start : end + 1]
    try:
        parsed = json.loads(candidate)
        if not isinstance(parsed, dict):
            raise ValueError("Model response is not a JSON object")
        return parsed
    except json.JSONDecodeError:
        repaired = _repair_json_text(candidate)
        try:
            parsed = json.loads(repaired)
            if not isinstance(parsed, dict):
                raise ValueError("Model response is not a JSON object")
            return parsed
        except json.JSONDecodeError as exc:
            preview = repaired[:220].replace("\n", " ")
            raise ValueError(
                f"Model returned invalid JSON object near char {exc.pos}: {preview}..."
            ) from exc


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
