import io
import json
from urllib.parse import quote
from urllib.request import urlopen

from fastapi import APIRouter, Body, Response
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/api/tts")
def generate_tts_audio(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        text = str(payload.get("text", "")).strip()
        language = str(payload.get("language", "en")).strip().lower() or "en"
        tld = str(payload.get("tld", "com")).strip().lower() or "com"
        translate = bool(payload.get("translate", True))
        if not text:
            return JSONResponse(content={"error": "text is required"}, status_code=400)

        try:
            from gtts import gTTS
            from gtts.lang import tts_langs
        except ImportError as exc:
            raise RuntimeError("Text-to-speech requires gTTS. Install it in the backend environment.") from exc

        supported_languages = tts_langs()
        if language not in supported_languages:
            return JSONResponse(content={"error": f"Unsupported language: {language}"}, status_code=400)

        speech_text = text
        if translate and language != "en":
            try:
                endpoint = (
                    "https://translate.googleapis.com/translate_a/single"
                    f"?client=gtx&sl=auto&tl={quote(language)}&dt=t&q={quote(text)}"
                )
                with urlopen(endpoint, timeout=20) as response:
                    translated_raw = response.read().decode("utf-8", errors="ignore")
                translated_json = json.loads(translated_raw)
                segments = translated_json[0] if isinstance(translated_json, list) and translated_json else []
                translated_text = "".join([str(seg[0]) for seg in segments if isinstance(seg, list) and seg and seg[0]])
                if translated_text.strip():
                    speech_text = translated_text.strip()
            except Exception:
                # Keep original text if translation service is unavailable.
                speech_text = text

        tts = gTTS(text=speech_text, lang=language, tld=tld)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return Response(content=audio_buffer.read(), media_type="audio/mpeg")
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
