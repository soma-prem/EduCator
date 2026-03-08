import csv
import io
import re
import textwrap

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, Response

router = APIRouter()


def _as_text(value):
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _safe_filename_part(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", _as_text(value))
    return cleaned.strip("._-") or "study_set"


def _pdf_escape(text):
    ascii_text = _as_text(text).encode("ascii", "replace").decode("ascii")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _hex_to_rgb_float(hex_color):
    value = _as_text(hex_color).lstrip("#")
    if len(value) != 6:
        return 0.0, 0.0, 0.0
    try:
        r = int(value[0:2], 16) / 255.0
        g = int(value[2:4], 16) / 255.0
        b = int(value[4:6], 16) / 255.0
    except ValueError:
        return 0.0, 0.0, 0.0
    return r, g, b


def _estimate_wrap_width(font_size, indent):
    # Approximation for Helvetica glyph width to keep wrapping predictable.
    usable_width = 500 - max(0, int(indent))
    estimated_char_width = max(5.2, font_size * 0.52)
    return max(18, int(usable_width / estimated_char_width))


def _normalize_pdf_entries(entries):
    normalized = []
    for entry in entries:
        if isinstance(entry, str):
            entry = {"text": entry}
        if not isinstance(entry, dict):
            continue
        if entry.get("page_break"):
            normalized.append({"page_break": True})
            continue
        text = _as_text(entry.get("text"))
        style = {
            "font_size": int(entry.get("font_size", 11)),
            "color": _as_text(entry.get("color") or "1A2E44"),
            "align": _as_text(entry.get("align") or "left").lower(),
            "bold": bool(entry.get("bold", False)),
            "indent": int(entry.get("indent", 50)),
            "before": float(entry.get("before", 0)),
            "after": float(entry.get("after", 0)),
            "line_height": float(entry.get("line_height", 1.35)),
        }

        if text:
            width = _estimate_wrap_width(style["font_size"], style["indent"])
            wrapped = textwrap.wrap(text, width=width, break_long_words=True, replace_whitespace=False)
        else:
            wrapped = [""]

        normalized.append({"lines": wrapped, "style": style})
    return normalized


def _build_pdf_bytes(entries):
    page_width = 612
    page_height = 792
    start_y = 755
    min_y = 40

    pages = []
    current = []
    y = start_y
    normalized_entries = _normalize_pdf_entries(entries)

    for entry in normalized_entries:
        if entry.get("page_break"):
            if current:
                pages.append(current)
            current = []
            y = start_y
            continue

        style = entry["style"]
        y -= style["before"]
        for segment in entry["lines"]:
            line_height = max(11.0, style["font_size"] * style["line_height"])
            if y < min_y:
                pages.append(current)
                current = []
                y = start_y
            current.append({"text": segment, "style": style.copy(), "y": y})
            y -= line_height
        y -= style["after"]

    if current or not pages:
        pages.append(current)

    objects = {}
    page_count = len(pages)
    font_regular_obj_id = 3 + (page_count * 2)
    font_bold_obj_id = font_regular_obj_id + 1

    objects[1] = f"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join([f"{3 + (idx * 2)} 0 R" for idx in range(page_count)])
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>"

    for idx, page_lines in enumerate(pages):
        page_obj = 3 + (idx * 2)
        content_obj = page_obj + 1

        stream_lines = ["BT"]
        for line in page_lines:
            style = line["style"]
            text = line["text"]
            font_id = "F2" if style["bold"] else "F1"
            font_size = max(8, min(32, int(style["font_size"])))
            r, g, b = _hex_to_rgb_float(style["color"])

            indent = max(30, min(120, int(style["indent"])))
            if style["align"] == "center":
                approx_width = len(text) * (font_size * 0.5)
                x = max(30, (page_width - approx_width) / 2)
            else:
                x = indent

            y_pos = max(min_y, min(start_y, float(line["y"])))
            stream_lines.append(f"/{font_id} {font_size} Tf")
            stream_lines.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
            stream_lines.append(f"1 0 0 1 {x:.2f} {y_pos:.2f} Tm")
            stream_lines.append(f"({_pdf_escape(text)}) Tj")
        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("ascii", "replace")

        objects[content_obj] = f"<< /Length {len(stream_data)} >>\nstream\n{stream_data.decode('ascii')}\nendstream"
        objects[page_obj] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_regular_obj_id} 0 R /F2 {font_bold_obj_id} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        )

    objects[font_regular_obj_id] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects[font_bold_obj_id] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for obj_id in sorted(objects.keys()):
        offsets[obj_id] = output.tell()
        output.write(f"{obj_id} 0 obj\n".encode("ascii"))
        output.write(objects[obj_id].encode("ascii", "replace"))
        output.write(b"\nendobj\n")

    xref_start = output.tell()
    max_obj = max(objects.keys())
    output.write(f"xref\n0 {max_obj + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for obj_id in range(1, max_obj + 1):
        offset = offsets.get(obj_id, 0)
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))

    output.write(
        (
            "trailer\n"
            f"<< /Size {max_obj + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF"
        ).encode("ascii")
    )
    return output.getvalue()


def _render_csv(mcqs, flashcards):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "index", "question", "option_a", "option_b", "option_c", "option_d", "answer", "front", "back"])

    for idx, item in enumerate(mcqs, start=1):
        options = item.get("options") if isinstance(item, dict) else []
        options = options if isinstance(options, list) else []
        padded = [str(options[i]) if i < len(options) else "" for i in range(4)]
        writer.writerow(
            [
                "mcq",
                idx,
                _as_text(item.get("question") if isinstance(item, dict) else ""),
                padded[0],
                padded[1],
                padded[2],
                padded[3],
                _as_text(item.get("answer") if isinstance(item, dict) else ""),
                "",
                "",
            ]
        )

    for idx, item in enumerate(flashcards, start=1):
        writer.writerow(
            [
                "flashcard",
                idx,
                "",
                "",
                "",
                "",
                "",
                "",
                _as_text(item.get("front") if isinstance(item, dict) else ""),
                _as_text(item.get("back") if isinstance(item, dict) else ""),
            ]
        )

    return output.getvalue().encode("utf-8")


def _render_quiz_text(mcqs, flashcards, summary):
    lines = ["EduCator Quiz Export", ""]
    if summary:
        lines.extend(["Summary:", _as_text(summary), ""])

    if mcqs:
        lines.append("MCQs")
        lines.append("")
        for idx, item in enumerate(mcqs, start=1):
            question = _as_text(item.get("question") if isinstance(item, dict) else "")
            answer = _as_text(item.get("answer") if isinstance(item, dict) else "")
            options = item.get("options") if isinstance(item, dict) else []
            options = options if isinstance(options, list) else []

            lines.append(f"{idx}. {question}")
            for option_idx, option in enumerate(options):
                label = chr(65 + option_idx) if option_idx < 26 else "?"
                lines.append(f"   {label}) {_as_text(option)}")
            lines.append(f"   Answer: {answer}")
            lines.append("")

    if flashcards:
        lines.append("Flashcards")
        lines.append("")
        for idx, item in enumerate(flashcards, start=1):
            front = _as_text(item.get("front") if isinstance(item, dict) else "")
            back = _as_text(item.get("back") if isinstance(item, dict) else "")
            lines.append(f"{idx}. Front: {front}")
            lines.append(f"   Back: {back}")
            lines.append("")

    return "\n".join(lines).encode("utf-8")


def _render_pdf(mcqs, flashcards, summary):
    entries = [
        {
            "text": "EduCator Study Set",
            "font_size": 20,
            "bold": True,
            "align": "center",
            "color": "1F5D8F",
            "before": 4,
            "after": 10,
        },
        {
            "text": "MCQs + Flashcards Export",
            "font_size": 11,
            "align": "center",
            "color": "5C748B",
            "after": 12,
        },
    ]

    if summary:
        entries.extend(
            [
                {"text": "Summary", "font_size": 14, "bold": True, "color": "0F7A5B", "after": 4},
                {"text": _as_text(summary), "font_size": 11, "color": "24384D", "after": 10},
            ]
        )

    if mcqs:
        entries.extend(
            [
                {"text": "Multiple Choice Questions", "font_size": 14, "bold": True, "color": "1A4F7A", "after": 6},
            ]
        )
        for idx, item in enumerate(mcqs, start=1):
            question = _as_text(item.get("question") if isinstance(item, dict) else "")
            answer = _as_text(item.get("answer") if isinstance(item, dict) else "")
            options = item.get("options") if isinstance(item, dict) else []
            options = options if isinstance(options, list) else []

            entries.append(
                {
                    "text": f"{idx}. {question}",
                    "font_size": 11,
                    "bold": True,
                    "color": "102A43",
                    "after": 2,
                }
            )
            for option_idx, option in enumerate(options):
                label = chr(65 + option_idx) if option_idx < 26 else "?"
                entries.append(
                    {
                        "text": f"{label}) {_as_text(option)}",
                        "font_size": 10,
                        "color": "334E68",
                        "indent": 64,
                    }
                )
            entries.append(
                {
                    "text": f"Answer: {answer}",
                    "font_size": 10,
                    "bold": True,
                    "color": "0F7A5B",
                    "indent": 64,
                    "after": 6,
                }
            )

    if flashcards:
        entries.extend(
            [
                {"page_break": True},
                {"text": "Flashcards", "font_size": 14, "bold": True, "color": "8C5A11", "before": 4, "after": 6},
            ]
        )
        for idx, item in enumerate(flashcards, start=1):
            front = _as_text(item.get("front") if isinstance(item, dict) else "")
            back = _as_text(item.get("back") if isinstance(item, dict) else "")
            entries.append({"text": f"{idx}. Question: {front}", "font_size": 11, "bold": True, "color": "3E2A12"})
            entries.append({"text": f"Answer: {back}", "font_size": 10, "color": "5C3B13", "indent": 64, "after": 6})

    return _build_pdf_bytes(entries)


@router.post("/api/export/study-set/{export_format}")
def export_study_set(export_format: str, payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        export_format = _as_text(export_format).lower()
        if export_format not in {"pdf", "csv", "quiz"}:
            return JSONResponse(content={"error": "Unsupported export format. Use pdf, csv, or quiz."}, status_code=400)

        mcqs = payload.get("mcqs")
        flashcards = payload.get("flashcards")
        summary = _as_text(payload.get("summary"))
        title = _safe_filename_part(payload.get("title") or "study_set")

        mcqs = mcqs if isinstance(mcqs, list) else []
        flashcards = flashcards if isinstance(flashcards, list) else []
        if not mcqs and not flashcards and not summary:
            return JSONResponse(content={"error": "No study content found to export"}, status_code=400)

        if export_format == "csv":
            body = _render_csv(mcqs, flashcards)
            media_type = "text/csv; charset=utf-8"
            extension = "csv"
        elif export_format == "quiz":
            body = _render_quiz_text(mcqs, flashcards, summary)
            media_type = "text/plain; charset=utf-8"
            extension = "quiz.txt"
        else:
            body = _render_pdf(mcqs, flashcards, summary)
            media_type = "application/pdf"
            extension = "pdf"

        filename = f"{title}.{extension}" if extension != "quiz.txt" else f"{title}.quiz.txt"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=body, media_type=media_type, headers=headers)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
