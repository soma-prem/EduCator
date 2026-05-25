import base64
import io
import json
import re
from urllib.parse import quote
from urllib.request import urlopen

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from services.mcq_session import get_mcq_session

router = APIRouter()

from services.gemini_service import answer_question_from_source


def _tokenize(text):
    return [
        token
        for token in re.findall(r"[A-Za-z0-9]{3,}", str(text or "").lower())
        if token not in {"what", "when", "where", "which", "how", "this", "that", "from", "with", "into"}
    ]


def _split_chunks(text, size=700):
    raw = str(text or "").strip()
    if not raw:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", raw) if part.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= size:
            chunks.append(para)
            continue
        for index in range(0, len(para), size):
            part = para[index : index + size].strip()
            if part:
                chunks.append(part)
    return chunks or [raw[:size]]


def _retrieve_relevant_context(source_text, question, top_k=3):
    q_tokens = set(_tokenize(question))
    chunks = _split_chunks(source_text)
    scored = []
    for chunk in chunks:
        c_tokens = set(_tokenize(chunk))
        overlap = len(q_tokens.intersection(c_tokens))
        density = overlap / max(1, len(c_tokens))
        score = overlap + density
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    top_chunks = [chunk for score, chunk in scored[:top_k] if score > 0]
    if not top_chunks:
        top_chunks = chunks[:top_k]
    return "\n\n".join(top_chunks)


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

        context = _retrieve_relevant_context(source_text, question, top_k=3)
        answer = answer_question_from_source(context, question)
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
