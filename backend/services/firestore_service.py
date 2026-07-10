import os
import time
from datetime import datetime, timezone
import json

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    credentials = None
    firestore = None

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
FIREBASE_SESSION_COLLECTION = os.getenv("FIREBASE_SESSION_COLLECTION", "study_sessions")
FIREBASE_SPACED_COLLECTION = os.getenv("FIREBASE_SPACED_COLLECTION", "spaced_plans")

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
        try:
            firebase_admin.get_app()
            app_exists = True
        except ValueError:
            app_exists = False

        if not app_exists:
            if FIREBASE_SERVICE_ACCOUNT_JSON:
                try:
                    data = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
                except Exception:
                    FIREBASE_INIT_ERROR = "Invalid FIREBASE_SERVICE_ACCOUNT_JSON (must be valid JSON)"
                    return None
                cred = credentials.Certificate(data)
                if FIREBASE_PROJECT_ID:
                    firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
                else:
                    firebase_admin.initialize_app(cred)
            elif FIREBASE_SERVICE_ACCOUNT_PATH:
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
    except Exception as exc:
        FIREBASE_DB = None
        FIREBASE_INIT_ERROR = f"Firebase initialization failed: {exc}"
        return None
    return FIREBASE_DB


def ensure_firestore_initialized():
    db = get_firestore_db()
    if db is None:
        raise RuntimeError(FIREBASE_INIT_ERROR or "Firebase is not initialized. Check service account credentials and environment variables.")
    return db


def serialize_history_doc(doc_id, doc):
    return {
        "id": str(doc_id),
        "kind": doc.get("kind", ""),
        "sourceType": doc.get("sourceType", ""),
        "sources": doc.get("sources", []),
        "sourceText": doc.get("sourceText", ""),
        "sourceFileId": doc.get("sourceFileId", ""),
        "sourceFileName": doc.get("sourceFileName", ""),
        "sourcePreview": doc.get("sourcePreview", ""),
        "difficultyByMode": doc.get("difficultyByMode", {}),
        "mcqSetId": doc.get("mcqSetId", ""),
        "pdfFileName": doc.get("pdfFileName", ""),
        "pdfSizeBytes": doc.get("pdfSizeBytes", 0),
        "pptFileName": doc.get("pptFileName", ""),
        "pptSizeBytes": doc.get("pptSizeBytes", 0),
        "generatedItems": doc.get("generatedItems", []),
        "hadMcqs": doc.get("hadMcqs", False),
        "hadFlashcards": doc.get("hadFlashcards", False),
        "hadFillBlanks": doc.get("hadFillBlanks", False),
        "hadTrueFalse": doc.get("hadTrueFalse", False),
        "hadMatchThePair": doc.get("hadMatchThePair", False),
        "mcqTotal": doc.get("mcqTotal", 0),
        "mcqCorrect": doc.get("mcqCorrect", 0),
        "mcqs": doc.get("mcqs", []),
        "flashcards": doc.get("flashcards", []),
        "fillBlanks": doc.get("fillBlanks", []),
        "trueFalse": doc.get("trueFalse", []),
        "matchThePair": doc.get("matchThePair", {"sets": [], "setCount": 5, "pairsPerSet": 5}),
        "summary": doc.get("summary", ""),
        "examConcepts": doc.get("examConcepts", []),
        "examTotalQuestions": doc.get("examTotalQuestions", 0),
        "examDurationMinutes": doc.get("examDurationMinutes", 0),
        "examAttempted": doc.get("examAttempted", 0),
        "examCorrect": doc.get("examCorrect", 0),
        "examWrong": doc.get("examWrong", 0),
        "examNotAttempted": doc.get("examNotAttempted", 0),
        "examSectionStats": doc.get("examSectionStats", {}),
        "createdAt": doc.get("createdAt", ""),
        "createdAtEpoch": doc.get("createdAtEpoch", 0),
        "updatedAt": doc.get("updatedAt", ""),
        "updatedAtEpoch": doc.get("updatedAtEpoch", 0),
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
    session_id = str(payload.get("sessionId", "")).strip()
    source_type = str(payload.get("sourceType", "")).strip()
    source_preview = str(payload.get("sourcePreview", "")).strip()
    kind = str(payload.get("kind", "workspace")).strip() or "workspace"
    sources = payload.get("sources", [])
    source_text = str(payload.get("sourceText", "")).strip()
    source_file_id = str(payload.get("sourceFileId", "")).strip()
    source_file_name = str(payload.get("sourceFileName", "")).strip()
    difficulty_by_mode = payload.get("difficultyByMode", {})
    mcq_set_id = str(payload.get("mcqSetId", "")).strip()
    had_mcqs = bool(payload.get("hadMcqs", False))
    had_flashcards = bool(payload.get("hadFlashcards", False))
    had_fill_blanks = bool(payload.get("hadFillBlanks", False))
    had_true_false = bool(payload.get("hadTrueFalse", False))
    had_match_the_pair = bool(payload.get("hadMatchThePair", False))
    mcq_total = int(payload.get("mcqTotal", 0))
    mcq_correct = int(payload.get("mcqCorrect", 0))
    mcqs = payload.get("mcqs", [])
    flashcards = payload.get("flashcards", [])
    fill_blanks = payload.get("fillBlanks", [])
    true_false = payload.get("trueFalse", [])
    match_the_pair = payload.get("matchThePair", {"sets": [], "setCount": 5, "pairsPerSet": 5})
    summary = str(payload.get("summary", "")).strip()

    exam_concepts = payload.get("examConcepts", [])
    exam_total_questions = int(payload.get("examTotalQuestions", 0) or 0)
    exam_duration_minutes = int(payload.get("examDurationMinutes", 0) or 0)
    exam_attempted = int(payload.get("examAttempted", 0) or 0)
    exam_correct = int(payload.get("examCorrect", 0) or 0)
    exam_wrong = int(payload.get("examWrong", 0) or 0)
    exam_not_attempted = int(payload.get("examNotAttempted", 0) or 0)
    exam_section_stats = payload.get("examSectionStats", {})

    now_iso = datetime.now(timezone.utc).isoformat()
    now_epoch = int(time.time())

    session_doc = {
        "kind": kind,
        "sourceType": source_type,
        "sourcePreview": source_preview[:500],
        "sources": sources if isinstance(sources, list) else [],
        "sourceText": source_text[:20000],
        "sourceFileId": source_file_id[:200],
        "sourceFileName": source_file_name[:300],
        "difficultyByMode": difficulty_by_mode if isinstance(difficulty_by_mode, dict) else {},
        "mcqSetId": mcq_set_id[:200],
        "hadMcqs": had_mcqs,
        "hadFlashcards": had_flashcards,
        "hadFillBlanks": had_fill_blanks,
        "hadTrueFalse": had_true_false,
        "hadMatchThePair": had_match_the_pair,
        "mcqTotal": max(0, mcq_total),
        "mcqCorrect": max(0, mcq_correct),
        "mcqs": mcqs if isinstance(mcqs, list) else [],
        "flashcards": flashcards if isinstance(flashcards, list) else [],
        "fillBlanks": fill_blanks if isinstance(fill_blanks, list) else [],
        "trueFalse": true_false if isinstance(true_false, list) else [],
        "matchThePair": match_the_pair if isinstance(match_the_pair, dict) else {"sets": [], "setCount": 5, "pairsPerSet": 5},
        "summary": summary[:12000],
        "examConcepts": exam_concepts if isinstance(exam_concepts, list) else [],
        "examTotalQuestions": max(0, exam_total_questions),
        "examDurationMinutes": max(0, exam_duration_minutes),
        "examAttempted": max(0, exam_attempted),
        "examCorrect": max(0, exam_correct),
        "examWrong": max(0, exam_wrong),
        "examNotAttempted": max(0, exam_not_attempted),
        "examSectionStats": exam_section_stats if isinstance(exam_section_stats, dict) else {},
        "createdAt": now_iso,
        "createdAtEpoch": now_epoch,
        "updatedAt": now_iso,
        "updatedAtEpoch": now_epoch,
    }
    db = get_firestore_db()
    if db is None:
        return None

    try:
        if session_id:
            ref = db.collection(FIREBASE_SESSION_COLLECTION).document(session_id)
            ref.set(session_doc)
            return session_id
    except Exception:
        return None

    return save_completed_session(session_doc)


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


def save_spaced_plan(user_id, plan_id, boxes, schedule):
    db = get_firestore_db()
    if db is None:
        return False, FIREBASE_INIT_ERROR or "Firebase is not configured"
    if not user_id or not plan_id:
        return False, "userId and planId are required"
    try:
        doc_ref = db.collection(FIREBASE_SPACED_COLLECTION).document(f"{user_id}__{plan_id}")
        doc_ref.set(
            {
                "userId": user_id,
                "planId": plan_id,
                "boxes": boxes or {},
                "schedule": schedule or [],
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "updatedAtEpoch": int(time.time()),
            }
        )
        return True, ""
    except Exception:
        return False, "Failed to save spaced plan"


def load_spaced_plan(user_id, plan_id):
    db = get_firestore_db()
    if db is None:
        return None, FIREBASE_INIT_ERROR or "Firebase is not configured"
    if not user_id or not plan_id:
        return None, "userId and planId are required"
    try:
        doc_ref = db.collection(FIREBASE_SPACED_COLLECTION).document(f"{user_id}__{plan_id}")
        doc = doc_ref.get()
        if not doc.exists:
            return None, ""
        data = doc.to_dict() or {}
        return {
            "boxes": data.get("boxes", {}),
            "schedule": data.get("schedule", []),
            "updatedAt": data.get("updatedAt", ""),
            "planId": data.get("planId", plan_id),
        }, ""
    except Exception:
        return None, "Failed to load spaced plan"
