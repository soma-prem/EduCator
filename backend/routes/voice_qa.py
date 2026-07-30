import base64
import io
import json
from urllib.parse import quote
from urllib.request import urlopen

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from services.mcq_session import get_mcq_session
from services.rag.generation import generate_answer

router = APIRouter()


def _translate_if_needed(text, language):
    if language == "en":
        return text
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
        return translated_text.strip() or text
    except Exception:
        return text


def _audio_base64(text, language):
    try:
        from gtts import gTTS
        from gtts.lang import tts_langs
    except ImportError:
        return ""

    lang = str(language or "en").strip().lower() or "en"
    if lang not in tts_langs():
        lang = "en"
    speech_text = _translate_if_needed(text, lang)
    try:
        audio_buffer = io.BytesIO()
        tts = gTTS(text=speech_text, lang=lang)
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return base64.b64encode(audio_buffer.read()).decode("ascii")
    except Exception:
        return ""


@router.post("/api/qa/voice")
def voice_question_answering(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        mcq_set_id = str(payload.get("mcqSetId", "")).strip()
        question = str(payload.get("question", "")).strip()
        language = str(payload.get("language", "en")).strip().lower() or "en"
        if not mcq_set_id:
            return JSONResponse(content={"error": "mcqSetId is required"}, status_code=400)
        if not question:
            return JSONResponse(content={"error": "question is required"}, status_code=400)

        session_data = get_mcq_session(mcq_set_id)
        if not session_data:
            return JSONResponse(content={"error": "MCQ session expired. Generate study set again."}, status_code=410)
        source_text = str(session_data.get("source_text", "")).strip()
        if not source_text:
            return JSONResponse(content={"error": "Source content missing for this session."}, status_code=400)

        answer, metadata = generate_answer(
            question=question,
            source_text=source_text,
            document_id=None,
            top_k=5,
            min_score=0.15,
        )
        audio_base64 = _audio_base64(answer, language=language)
        return {
            "question": question,
            "answer": answer,
            "audioBase64": audio_base64,
        }
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
