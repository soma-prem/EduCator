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
