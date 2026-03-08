import os
import time
from datetime import datetime, timezone

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    credentials = None
    firestore = None

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
FIREBASE_SESSION_COLLECTION = os.getenv("FIREBASE_SESSION_COLLECTION", "study_sessions")

FIREBASE_DB = None
FIREBASE_INIT_ERROR = ""


def get_firestore_db():
    global FIREBASE_DB, FIREBASE_INIT_ERROR
    if FIREBASE_DB is not None:
        return FIREBASE_DB
    if firebase_admin is None:
        FIREBASE_INIT_ERROR = "firebase_admin is not installed"
        return None

    try:
        if not firebase_admin._apps:
            if FIREBASE_SERVICE_ACCOUNT_PATH:
                service_path = FIREBASE_SERVICE_ACCOUNT_PATH
                if not os.path.isabs(service_path):
                    service_path = os.path.join(os.path.dirname(__file__), "..", service_path)
                    service_path = os.path.normpath(service_path)
                if not os.path.exists(service_path):
                    FIREBASE_INIT_ERROR = f"Service account file not found: {service_path}"
                    return None
                cred = credentials.Certificate(service_path)
                if FIREBASE_PROJECT_ID:
                    firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
                else:
                    firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        FIREBASE_DB = firestore.client()
        FIREBASE_INIT_ERROR = ""
    except Exception:
        FIREBASE_DB = None
        FIREBASE_INIT_ERROR = "Firebase initialization failed. Check service account JSON and project ID."
        return None
    return FIREBASE_DB


def serialize_history_doc(doc_id, doc):
    return {
        "id": str(doc_id),
        "kind": doc.get("kind", ""),
        "sourceType": doc.get("sourceType", ""),
        "sourceText": doc.get("sourceText", ""),
        "sourcePreview": doc.get("sourcePreview", ""),
        "pdfFileName": doc.get("pdfFileName", ""),
        "pdfSizeBytes": doc.get("pdfSizeBytes", 0),
        "pptFileName": doc.get("pptFileName", ""),
        "pptSizeBytes": doc.get("pptSizeBytes", 0),
        "generatedItems": doc.get("generatedItems", []),
        "hadMcqs": doc.get("hadMcqs", False),
        "hadFlashcards": doc.get("hadFlashcards", False),
        "mcqTotal": doc.get("mcqTotal", 0),
        "mcqCorrect": doc.get("mcqCorrect", 0),
        "mcqs": doc.get("mcqs", []),
        "flashcards": doc.get("flashcards", []),
        "summary": doc.get("summary", ""),
        "createdAt": doc.get("createdAt", ""),
        "createdAtEpoch": doc.get("createdAtEpoch", 0),
    }


def save_completed_session(payload):
    db = get_firestore_db()
    if db is None:
        return None
    try:
        ref = db.collection(FIREBASE_SESSION_COLLECTION).document()
        ref.set(payload)
        return ref.id
    except Exception:
        return None


def list_history(limit=20):
    db = get_firestore_db()
    if db is None:
        return [], FIREBASE_INIT_ERROR or "Firebase is not configured"
    docs = (
        db.collection(FIREBASE_SESSION_COLLECTION)
        .order_by("createdAtEpoch", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    items = [serialize_history_doc(doc.id, doc.to_dict() or {}) for doc in docs]
    return items, ""


def save_session_history(payload):
    source_type = str(payload.get("sourceType", "")).strip()
    source_preview = str(payload.get("sourcePreview", "")).strip()
    had_mcqs = bool(payload.get("hadMcqs", False))
    had_flashcards = bool(payload.get("hadFlashcards", False))
    mcq_total = int(payload.get("mcqTotal", 0))
    mcq_correct = int(payload.get("mcqCorrect", 0))
    mcqs = payload.get("mcqs", [])
    flashcards = payload.get("flashcards", [])
    summary = str(payload.get("summary", "")).strip()

    session_doc = {
        "sourceType": source_type,
        "sourcePreview": source_preview[:500],
        "hadMcqs": had_mcqs,
        "hadFlashcards": had_flashcards,
        "mcqTotal": max(0, mcq_total),
        "mcqCorrect": max(0, mcq_correct),
        "mcqs": mcqs if isinstance(mcqs, list) else [],
        "flashcards": flashcards if isinstance(flashcards, list) else [],
        "summary": summary[:4000],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdAtEpoch": int(time.time()),
    }
    session_id = save_completed_session(session_doc)
    return session_id


def clear_history():
    db = get_firestore_db()
    if db is None:
        return 0, FIREBASE_INIT_ERROR or "Firebase is not configured"

    docs = db.collection(FIREBASE_SESSION_COLLECTION).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    if count % 400 != 0:
        batch.commit()

    return count, ""


def delete_history_item(doc_id):
    db = get_firestore_db()
    if db is None:
        return False, FIREBASE_INIT_ERROR or "Firebase is not configured"

    ref = db.collection(FIREBASE_SESSION_COLLECTION).document(str(doc_id))
    ref.delete()
    return True, ""
