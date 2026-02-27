import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, jsonify, request

from services.mcq_session import store_mcq_session
from services.openrouter_service import generate_items_from_source, generate_summary_from_source
from utils.extractors import extract_docx_text, extract_pdf_text, extract_pptx_text, extract_txt_text

generate_bp = Blueprint("generate", __name__)


def get_source_text_from_request():
    text = (request.form.get("text") or "").strip()
    upload = request.files.get("file")

    if text and upload:
        raise ValueError("Provide either text or file, not both")

    if text:
        return text, {
            "sourceType": "text",
            "sourceText": text,
            "sourcePreview": text[:300],
            "pdfFileName": "",
            "pdfSizeBytes": 0,
            "pptFileName": "",
            "pptSizeBytes": 0,
        }

    if upload:
        filename = str(upload.filename or "uploaded.file")
        data = upload.read()
        if not data:
            raise ValueError("Uploaded file is empty")

        lower_name = filename.lower()
        extracted_text = ""
        source_type = "file"

        if lower_name.endswith(".pptx"):
            extracted_text = extract_pptx_text(data)
            source_type = "pptx"
        elif lower_name.endswith(".docx"):
            extracted_text = extract_docx_text(data)
            source_type = "docx"
        elif lower_name.endswith(".pdf"):
            extracted_text = extract_pdf_text(data)
            source_type = "pdf"
        elif lower_name.endswith(".txt"):
            extracted_text = extract_txt_text(data)
            source_type = "text"
        elif lower_name.endswith(".doc") or lower_name.endswith(".ppt"):
            raise ValueError("Legacy .doc/.ppt files are not supported. Please upload .docx/.pptx.")
        else:
            raise ValueError("Unsupported file type. Upload txt, pdf, docx, or pptx.")

        if not extracted_text:
            raise ValueError("Unable to extract text from the uploaded file")

        return extracted_text, {
            "sourceType": source_type,
            "sourceText": "",
            "sourcePreview": filename,
            "pdfFileName": filename if source_type == "pdf" else "",
            "pdfSizeBytes": len(data) if source_type == "pdf" else 0,
            "pptFileName": filename if source_type == "pptx" else "",
            "pptSizeBytes": len(data) if source_type == "pptx" else 0,
        }

    raise ValueError("Provide text or upload a file")


@generate_bp.route("/api/generate/study-set", methods=["POST"])
def generate_study_set():
    try:
        source_text, _source_meta = get_source_text_from_request()
        instructions = {
            "mcqs": (
                "Create exactly 10 MCQs from the provided content. "
                "Each item must be: {\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"...\"}"
            ),
            "flashcards": (
                "Create exactly 10 flashcards from the provided content. "
                "Each item must be: {\"front\":\"...\",\"back\":\"...\"}"
            ),
        }

        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(generate_items_from_source, source_text, instruction, 10): key
                for key, instruction in instructions.items()
            }
            futures[executor.submit(generate_summary_from_source, source_text)] = "summary"
            for future in as_completed(futures):
                key = futures[future]
                results[key] = future.result()

        mcqs = results["mcqs"]
        flashcards = results["flashcards"]
        summary = results.get("summary", "")
        mcq_set_id = store_mcq_session(mcqs)
        return jsonify({"mcqs": mcqs, "flashcards": flashcards, "summary": summary, "mcqSetId": mcq_set_id})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500
