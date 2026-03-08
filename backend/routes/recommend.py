import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from services.mcq_session import get_mcq_session
from utils.mcq_utils import is_correct_option, resolve_correct_index, resolve_selected_index

router = APIRouter()

RECOMMEND_MAX_WEAK_TOPICS = int(os.getenv("RECOMMEND_MAX_WEAK_TOPICS", "2"))
RECOMMEND_SOURCE_CHAR_LIMIT = int(os.getenv("RECOMMEND_SOURCE_CHAR_LIMIT", "1800"))

from services.gemini_service import generate_items_from_source, generate_summary_from_source


def _safe_topic(value):
    topic = str(value or "").strip()
    return topic or "General"


def _topic_context(items, answers, topic):
    chunks = []
    for index, item in enumerate(items):
        if _safe_topic(item.get("topic")) != topic:
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options", []) if isinstance(item, dict) else []
        options = options if isinstance(options, list) else []
        answer = str(answers[index]).strip() if index < len(answers) else str(item.get("answer", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        option_text = " | ".join([str(opt) for opt in options[:4]])
        chunks.append(
            f"Q: {question}\nOptions: {option_text}\nCorrect: {answer}\nWhy: {explanation}"
        )
    text = "\n\n".join(chunks)
    if len(text) > RECOMMEND_SOURCE_CHAR_LIMIT:
        return text[:RECOMMEND_SOURCE_CHAR_LIMIT]
    return text


def _compute_topic_stats(items, answers, selected_answers):
    by_topic = {}
    for index, item in enumerate(items):
        if index >= len(answers):
            continue
        topic = _safe_topic(item.get("topic"))
        correct_answer = answers[index]
        selected_answer = str(selected_answers.get(str(index), "") or selected_answers.get(index, "")).strip()
        if not selected_answer:
            continue

        options = item.get("options", []) if isinstance(item, dict) else []
        options = options if isinstance(options, list) else []
        correct_index = resolve_correct_index(options, correct_answer)
        selected_index = resolve_selected_index(options, selected_answer)
        if correct_index != -1 and selected_index != -1:
            correct = correct_index == selected_index
        else:
            correct = is_correct_option(selected_answer, correct_answer)

        entry = by_topic.setdefault(topic, {"correct": 0, "total": 0, "question_indices": []})
        entry["total"] += 1
        entry["correct"] += 1 if correct else 0
        entry["question_indices"].append(index)
    return by_topic


def _make_audio_base64(text, language="en"):
    try:
        from gtts import gTTS
        from gtts.lang import tts_langs
    except ImportError:
        return ""
    if not text:
        return ""

    lang = str(language or "en").strip().lower()
    if lang not in tts_langs():
        lang = "en"
    try:
        audio_buffer = io.BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return base64.b64encode(audio_buffer.read()).decode("ascii")
    except Exception:
        return ""


def _build_local_revision_summary(topic, flashcards, mcqs):
    points = []
    if isinstance(flashcards, list):
        for item in flashcards[:3]:
            back = str(item.get("back", "")).strip()
            if back:
                points.append(back)
    if isinstance(mcqs, list):
        for item in mcqs[:2]:
            explanation = str(item.get("explanation", "")).strip()
            if explanation:
                points.append(explanation)
    unique_points = []
    seen = set()
    for point in points:
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_points.append(point)
    if not unique_points:
        return f"- Revise key ideas for {topic}.\n- Practice similar questions.\n- Review concepts daily."
    return "\n".join([f"- {point}" for point in unique_points[:4]])


def _generate_topic_recommendation(topic_context, topic):
    focused_source = (
        f"Focus topic: {topic}\n\n"
        "Study content:\n"
        f"{topic_context}"
    )
    instructions = {
        "flashcards": (
            "Create exactly 5 flashcards for revision.\n"
            "Each item must be: {\"front\":\"...\",\"back\":\"...\"}."
        ),
        "mcqs": (
            "Create exactly 3 revision MCQs for this topic.\n"
            "Each item must be: "
            "{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\",\"explanation\":\"...\",\"topic\":\"...\"}."
        ),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_items_from_source, focused_source, instructions["flashcards"], 5): "flashcards",
            executor.submit(generate_items_from_source, focused_source, instructions["mcqs"], 3): "mcqs",
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    summary = _build_local_revision_summary(topic, results.get("flashcards", []), results.get("mcqs", []))
    return {
        "topic": topic,
        "flashcards": results.get("flashcards", [])[:5],
        "mcqs": results.get("mcqs", [])[:3],
        "summary": summary,
    }


@router.post("/api/recommend/knowledge-gaps")
def recommend_knowledge_gaps(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        mcq_set_id = str(payload.get("mcqSetId", "")).strip()
        selected_answers = payload.get("selectedAnswers", {}) or {}
        threshold = float(payload.get("threshold", 0.6))
        language = str(payload.get("language", "en")).strip().lower() or "en"

        if not mcq_set_id:
            return JSONResponse(content={"error": "mcqSetId is required"}, status_code=400)
        if not isinstance(selected_answers, dict):
            return JSONResponse(content={"error": "selectedAnswers must be an object"}, status_code=400)

        session_data = get_mcq_session(mcq_set_id)
        if not session_data:
            return JSONResponse(content={"error": "MCQ session expired. Generate study set again."}, status_code=410)

        items = session_data.get("items", []) or []
        answers = session_data.get("answers", []) or []
        source_text = str(session_data.get("source_text", "")).strip()

        topic_stats = _compute_topic_stats(items, answers, selected_answers)
        topic_results = []
        weak_topics = []
        for topic, stats in topic_stats.items():
            total = stats["total"]
            correct = stats["correct"]
            accuracy = (correct / total) if total > 0 else 0.0
            entry = {
                "topic": topic,
                "correct": correct,
                "total": total,
                "accuracy": round(accuracy, 4),
            }
            topic_results.append(entry)
            if total > 0 and accuracy < threshold:
                weak_topics.append(entry)

        weak_topics.sort(key=lambda value: value["accuracy"])
        weak_topics = weak_topics[: max(1, RECOMMEND_MAX_WEAK_TOPICS)]
        recommendations = []
        for weak_topic in weak_topics:
            topic_context = _topic_context(items, answers, weak_topic["topic"])
            if not topic_context and source_text:
                topic_context = source_text[:RECOMMEND_SOURCE_CHAR_LIMIT]
            rec = _generate_topic_recommendation(topic_context or "No source available.", weak_topic["topic"])
            rec["audioBase64"] = _make_audio_base64(rec["summary"], language=language)
            recommendations.append(rec)

        return {
            "weakTopics": weak_topics,
            "topicAccuracy": topic_results,
            "recommendedStudy": recommendations,
        }
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
