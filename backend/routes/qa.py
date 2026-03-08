import os
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from utils.extractors import extract_docx_text, extract_pdf_text, extract_pptx_text, extract_txt_text

router = APIRouter()

from services.gemini_service import OPENROUTER_VOICE_API_KEY, answer_question_from_source, answer_question_from_source_openrouter

TEMP_UPLOAD_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "temp_uploads"))


def _resolve_temp_upload(file_id):
    if not file_id:
        return ""
    prefix = f"{file_id}__"
    try:
        for name in os.listdir(TEMP_UPLOAD_DIR):
            if name.startswith(prefix):
                return os.path.join(TEMP_UPLOAD_DIR, name)
    except FileNotFoundError:
        return ""
    return ""


def _extract_text_from_file_bytes(filename, data):
    lower_name = filename.lower()
    if lower_name.endswith(".pptx"):
        return extract_pptx_text(data)
    if lower_name.endswith(".docx"):
        return extract_docx_text(data)
    if lower_name.endswith(".pdf"):
        return extract_pdf_text(data)
    if lower_name.endswith(".txt"):
        return extract_txt_text(data)
    if lower_name.endswith(".doc") or lower_name.endswith(".ppt"):
        raise ValueError("Legacy .doc/.ppt files are not supported. Please upload .docx/.pptx.")
    raise ValueError("Unsupported file type. Upload txt, pdf, docx, or pptx.")


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


@router.post("/api/qa/source")
async def answer_question_from_upload(request: Request):
    try:
        form = await request.form()
        question = str(form.get("question") or "").strip()
        if not question:
            return JSONResponse(content={"error": "question is required"}, status_code=400)
        text = str(form.get("text") or "").strip()
        upload = form.get("file")
        file_id = str(form.get("fileId") or "").strip()
        mode = str(form.get("mode") or "").strip().lower()

        if text and (upload or file_id):
            return JSONResponse(content={"error": "Provide either text or file, not both"}, status_code=400)
        if upload and file_id:
            return JSONResponse(content={"error": "Provide either file upload or fileId, not both"}, status_code=400)

        if text:
            source_text = text
        elif file_id:
            path = _resolve_temp_upload(file_id)
            if not path or not os.path.exists(path):
                return JSONResponse(content={"error": "Uploaded file not found. Please re-upload."}, status_code=400)
            filename = os.path.basename(path).split("__", 1)[-1] or "uploaded.file"
            with open(path, "rb") as handle:
                data = handle.read()
            if not data:
                return JSONResponse(content={"error": "Uploaded file is empty"}, status_code=400)
            source_text = _extract_text_from_file_bytes(filename, data)
            if not source_text:
                return JSONResponse(content={"error": "Unable to extract text from the uploaded file"}, status_code=400)
        elif upload and hasattr(upload, "filename"):
            filename = str(upload.filename or "uploaded.file")
            data = await upload.read()
            if not data:
                return JSONResponse(content={"error": "Uploaded file is empty"}, status_code=400)
            source_text = _extract_text_from_file_bytes(filename, data)
            if not source_text:
                return JSONResponse(content={"error": "Unable to extract text from the uploaded file"}, status_code=400)
        else:
            return JSONResponse(content={"error": "source text is required"}, status_code=400)

        context = _retrieve_relevant_context(source_text, question, top_k=3)
        if mode == "voice" and OPENROUTER_VOICE_API_KEY:
            answer = answer_question_from_source_openrouter(context, question)
        else:
            answer = answer_question_from_source(context, question)
        return {"question": question, "answer": answer}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
