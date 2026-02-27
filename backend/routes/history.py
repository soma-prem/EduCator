from flask import Blueprint, jsonify, request

from services.firestore_service import (
    FIREBASE_INIT_ERROR,
    clear_history,
    delete_history_item,
    list_history,
    save_session_history,
)

history_bp = Blueprint("history", __name__)


@history_bp.route("/api/history", methods=["GET"])
def get_history():
    try:
        limit_raw = request.args.get("limit", "20")
        try:
            limit = max(1, min(100, int(limit_raw)))
        except ValueError:
            limit = 20

        items, message = list_history(limit=limit)
        if message:
            return jsonify({"items": [], "message": f"Firebase error: {message}"}), 200
        return jsonify({"items": items})
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


@history_bp.route("/api/history/clear", methods=["POST"])
def clear_history_route():
    try:
        cleared, message = clear_history()
        if message:
            return jsonify({"cleared": 0, "message": f"Firebase error: {message}"}), 200
        return jsonify({"cleared": cleared})
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


@history_bp.route("/api/history/<doc_id>", methods=["DELETE"])
def delete_history_route(doc_id):
    try:
        deleted, message = delete_history_item(doc_id)
        if not deleted:
            return jsonify({"deleted": False, "message": f"Firebase error: {message}"}), 200
        return jsonify({"deleted": True})
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


@history_bp.route("/api/history/session", methods=["POST"])
def save_session_history_route():
    try:
        payload = request.get_json(silent=True) or {}
        session_id = save_session_history(payload)
        return jsonify({"sessionId": session_id, "stored": session_id is not None})
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500
