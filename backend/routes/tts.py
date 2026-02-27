import io

from flask import Blueprint, jsonify, request, current_app

tts_bp = Blueprint("tts", __name__)


@tts_bp.route("/api/tts", methods=["POST"])
def generate_tts_audio():
    try:
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        if not text:
            return jsonify({"error": "text is required"}), 400

        try:
            from gtts import gTTS
        except ImportError as exc:
            raise RuntimeError("Text-to-speech requires gTTS. Install it in the backend environment.") from exc

        tts = gTTS(text=text)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return current_app.response_class(audio_buffer.read(), mimetype="audio/mpeg")
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500
