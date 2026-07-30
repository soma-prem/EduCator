import os
import uuid
import tempfile
import subprocess
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from utils.extractors import extract_docx_text, extract_pdf_text, extract_pptx_text, extract_txt_text
from services.gemini_service import generate_items_from_source

router = APIRouter()

TEMP_UPLOAD_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "temp_uploads"))
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


def _resolve_temp_upload(file_id: str) -> str:
    if not file_id:
        return ""
    prefix = f"{file_id}__"
    for name in os.listdir(TEMP_UPLOAD_DIR):
        if name.startswith(prefix):
            return os.path.join(TEMP_UPLOAD_DIR, name)
    return ""


def _extract_text_from_file_bytes(filename: str, data: bytes):
    lower = filename.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")):
        return None  # handled in diagram endpoint
    if lower.endswith(".pdf"):
        return extract_pdf_text(data)
    if lower.endswith(".docx"):
        return extract_docx_text(data)
    if lower.endswith(".pptx"):
        return extract_pptx_text(data)
    if lower.endswith(".txt"):
        return extract_txt_text(data)
    raise ValueError("Unsupported file type for topic extraction. Use pdf, txt, docx, or pptx.")


async def _load_source_from_request(request: Request):
    form = await request.form()
    file_id = str(form.get("fileId") or "").strip()
    text_value = str(form.get("text") or "").strip()
    upload = form.get("file")

    if text_value:
        return text_value

    if upload and hasattr(upload, "filename"):
        filename = os.path.basename(upload.filename or "uploaded.file")
        data = await upload.read()
        if not data:
            raise ValueError("Uploaded file is empty")
        return _extract_text_from_file_bytes(filename, data)

    if file_id:
        path = _resolve_temp_upload(file_id)
        if not path or not os.path.exists(path):
            raise FileNotFoundError("Stored upload not found. Re-upload and try again.")
        with open(path, "rb") as handle:
            data = handle.read()
        filename = os.path.basename(path.split("__", 1)[-1])
        return _extract_text_from_file_bytes(filename, data)

    raise ValueError("Provide text or a file/fileId for topic analysis.")


def _fallback_topics(text: str, limit: int = 8):
    # Lightweight keyword-ish fallback when LLM keys are unavailable.
    import re
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    stop = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "about",
        "these",
        "those",
        "which",
        "there",
        "their",
        "your",
        "into",
        "using",
        "they",
        "them",
        "been",
        "will",
        "would",
    }
    freq = {}
    for word in words:
        if word in stop:
            continue
        freq[word] = freq.get(word, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [
        {
            "topic": key.title(),
            "summary": "",
            "importance": min(5, max(1, count // 2 + 1)),
            "difficulty": "medium",
        }
        for key, count in ranked
    ]


@router.post("/api/analyze/topics")
async def analyze_topics(request: Request):
    try:
        source_text = await _load_source_from_request(request)
        if not source_text.strip():
            raise ValueError("Source text is empty")

        instruction = (
            "Extract 8-12 concise topics from the study content. For each item return:\n"
            '{"topic":"short label","summary":"one-sentence gist","importance":1-5,"difficulty":"easy|medium|hard"}\n'
            "Keep topics distinct (no duplicates). Return only a strict JSON array."
        )
        topics = generate_items_from_source(source_text, instruction, expected_count=10)
        if not isinstance(topics, list) or len(topics) == 0:
            topics = _fallback_topics(source_text)
        return {"topics": topics}
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)


@router.post("/api/analyze/diagram")
async def analyze_diagram(request: Request):
    try:
        form = await request.form()
        upload = form.get("file")
        if not upload or not hasattr(upload, "filename"):
            raise ValueError("Upload a diagram/whiteboard image file to analyze.")
        filename = os.path.basename(upload.filename or "image.png")
        data = await upload.read()
        if not data:
            raise ValueError("Uploaded image is empty")

        suffix = os.path.splitext(filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name

        try:

            process = subprocess.run(
                ["tesseract", temp_path, "stdout"],
                capture_output=True,
                text=True,
                check=True,
            )
            ocr_text = process.stdout or ""
        except FileNotFoundError:
            raise RuntimeError("Tesseract binary not found. Install Tesseract and ensure it is on PATH.")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Tesseract OCR failed: {exc.stderr or exc.stdout or exc}")
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        ocr_clean = ocr_text.strip()
        lines = [line.strip() for line in ocr_clean.splitlines() if line.strip()]

        return {
            "fileName": filename,
            "sizeBytes": len(data),
            "engine": "tesseract-cli",
            "text": ocr_clean,
            "lines": lines,
        }
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
