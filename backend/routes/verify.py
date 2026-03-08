from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from services.mcq_session import get_mcq_session
from utils.mcq_utils import is_correct_option, resolve_correct_index, resolve_selected_index

router = APIRouter()


@router.post("/api/verify/mcq")
def verify_mcq(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        mcq_set_id = str(payload.get("mcqSetId", "")).strip()
        question_index = payload.get("questionIndex")
        selected_answer = str(payload.get("selectedAnswer", "")).strip()

        if not mcq_set_id:
            return JSONResponse(content={"error": "mcqSetId is required"}, status_code=400)
        if not isinstance(question_index, int):
            return JSONResponse(content={"error": "questionIndex must be an integer"}, status_code=400)
        if not selected_answer:
            return JSONResponse(content={"error": "selectedAnswer is required"}, status_code=400)

        session_data = get_mcq_session(mcq_set_id)
        if not session_data:
            return JSONResponse(
                content={"error": "MCQ session expired. Generate study set again."},
                status_code=410,
            )

        answers = session_data.get("answers", [])
        if question_index < 0 or question_index >= len(answers):
            return JSONResponse(content={"error": "questionIndex is out of range"}, status_code=400)

        correct_answer = answers[question_index]
        items = session_data.get("items", [])
        options = []
        explanation = ""
        if 0 <= question_index < len(items):
            question_item = items[question_index] or {}
            options = question_item.get("options", []) or []
            explanation = str(question_item.get("explanation", "")).strip()

        correct_index = resolve_correct_index(options, correct_answer)
        selected_index = resolve_selected_index(options, selected_answer)
        if correct_index != -1 and selected_index != -1:
            is_correct = correct_index == selected_index
        else:
            is_correct = is_correct_option(selected_answer, correct_answer)

        verdict = {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "correct_index": correct_index,
            "correct_option": options[correct_index] if 0 <= correct_index < len(options) else "",
            "explanation": explanation or "Checked with stored answer key.",
        }
        return verdict
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
