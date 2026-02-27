import time

from flask import Blueprint, jsonify, request

from services.mcq_session import get_mcq_session
from utils.mcq_utils import is_correct_option, resolve_correct_index, resolve_selected_index

verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/api/verify/mcq", methods=["POST"])
def verify_mcq():
    try:
        payload = request.get_json(silent=True) or {}
        mcq_set_id = str(payload.get("mcqSetId", "")).strip()
        question_index = payload.get("questionIndex")
        selected_answer = str(payload.get("selectedAnswer", "")).strip()

        if not mcq_set_id:
            return jsonify({"error": "mcqSetId is required"}), 400
        if not isinstance(question_index, int):
            return jsonify({"error": "questionIndex must be an integer"}), 400
        if not selected_answer:
            return jsonify({"error": "selectedAnswer is required"}), 400

        session_data = get_mcq_session(mcq_set_id)
        if not session_data:
            return jsonify({"error": "MCQ session expired. Generate study set again."}), 410

        answers = session_data.get("answers", [])
        if question_index < 0 or question_index >= len(answers):
            return jsonify({"error": "questionIndex is out of range"}), 400

        correct_answer = answers[question_index]
        items = session_data.get("items", [])
        options = []
        if 0 <= question_index < len(items):
            options = items[question_index].get("options", []) or []

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
            "explanation": "Checked with stored answer key.",
        }
        return jsonify(verdict)
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500
