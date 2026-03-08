import os
import time
import uuid

MCQ_SESSION_TTL_SECONDS = int(os.getenv("MCQ_SESSION_TTL_SECONDS", "3600"))
MCQ_SESSIONS = {}


def store_mcq_session(items):
    now = time.time()
    expired = [key for key, value in MCQ_SESSIONS.items() if value.get("expires_at", 0) <= now]
    for key in expired:
        MCQ_SESSIONS.pop(key, None)

    session_id = str(uuid.uuid4())
    MCQ_SESSIONS[session_id] = {
        "expires_at": now + MCQ_SESSION_TTL_SECONDS,
        "answers": [str(item.get("answer", "")).strip() for item in items],
        "items": items,
        "flashcards": [],
        "source_text": "",
    }
    return session_id


def get_mcq_session(session_id):
    session = MCQ_SESSIONS.get(session_id)
    if not session:
        return None
    if session.get("expires_at", 0) <= time.time():
        MCQ_SESSIONS.pop(session_id, None)
        return None
    return session


def update_mcq_session(session_id, items=None, flashcards=None, source_text=None):
    session = get_mcq_session(session_id)
    if not session:
        return False

    if isinstance(items, list):
        session["items"] = items
        session["answers"] = [str(item.get("answer", "")).strip() for item in items]
    if isinstance(flashcards, list):
        session["flashcards"] = flashcards
    if isinstance(source_text, str):
        session["source_text"] = source_text
    session["expires_at"] = time.time() + MCQ_SESSION_TTL_SECONDS
    return True
