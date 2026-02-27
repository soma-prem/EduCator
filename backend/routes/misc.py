from flask import Blueprint, jsonify

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Backend is running"})


@misc_bp.route("/api/message", methods=["GET"])
def get_message():
    return jsonify({"message": "Hello from Python Backend"})
