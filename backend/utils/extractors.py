import io
import zipfile
import xml.etree.ElementTree as ET


def extract_pptx_text(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            slide_files = [
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ]
            if not slide_files:
                return ""

            def slide_index(name):
                match = __import__("re").search(r"slide(\d+)\.xml$", name)
                return int(match.group(1)) if match else 0

            slide_files.sort(key=slide_index)
            slides_text = []
            for slide_name in slide_files:
                xml_bytes = archive.read(slide_name)
                try:
                    root = ET.fromstring(xml_bytes)
                except ET.ParseError:
                    continue

                chunks = []
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        text = node.text.strip()
                        if text:
                            chunks.append(text)
                if chunks:
                    slides_text.append(" ".join(chunks))
            return "\n".join(slides_text).strip()
    except zipfile.BadZipFile:
        return ""


def extract_docx_text(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                return ""
            xml_bytes = archive.read("word/document.xml")
            try:
                root = ET.fromstring(xml_bytes)
            except ET.ParseError:
                return ""
            chunks = []
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    text = node.text.strip()
                    if text:
                        chunks.append(text)
            return "\n".join(chunks).strip()
    except zipfile.BadZipFile:
        return ""


def extract_txt_text(data):
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return ""


def extract_pdf_text(data):
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise ValueError("PDF text extraction requires PyPDF2. Install it in the backend environment.") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError("Unable to read PDF file") from exc

    chunks = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            chunks.append(text.strip())
    return "\n".join(chunks).strip()
