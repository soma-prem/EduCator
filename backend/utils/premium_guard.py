import time

from fastapi import HTTPException, Request

from services.entitlement_service import get_user_entitlement
from services.firestore_service import ensure_firestore_initialized

try:
    from firebase_admin import auth as firebase_auth
except Exception:  # pragma: no cover
    firebase_auth = None


PLAN_ORDER = ["free", "silver", "gold", "platinum"]

FEATURE_MIN_PLAN = {
    "fill_blanks": "silver",
    "audio_summary": "silver",
    "knowledge_gap": "silver",
    "true_false": "gold",
    "mock_exam": "platinum",
    "youtube_guide": "platinum",
}


def _rank(plan: str) -> int:
    raw = str(plan or "free").strip().lower()
    try:
        return PLAN_ORDER.index(raw)
    except ValueError:
        return 0


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def require_user(request: Request) -> tuple[str, str]:
    if firebase_auth is None:
        raise HTTPException(status_code=502, detail="Firebase auth is not configured on backend")

    ensure_firestore_initialized()

    token = _bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")

    decoded = firebase_auth.verify_id_token(token)
    uid = str(decoded.get("uid") or "").strip()
    email = str(decoded.get("email") or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token")

    return uid, email


def require_feature(request: Request, feature_key: str) -> str:
    feature_key = str(feature_key or "").strip()
    required_plan = FEATURE_MIN_PLAN.get(feature_key)
    if not required_plan:
        return ""

    uid, _ = require_user(request)
    entitlement, message = get_user_entitlement(uid)
    if message:
        raise HTTPException(status_code=502, detail=message)
    plan = str((entitlement or {}).get("plan") or "free").strip().lower()
    active = bool((entitlement or {}).get("active", False))
    expires_at = int((entitlement or {}).get("expiresAtEpoch") or 0)
    if not active or expires_at <= int(time.time()):
        plan = "free"

    if _rank(plan) < _rank(required_plan):
        raise HTTPException(status_code=403, detail=f"Upgrade required: {required_plan}+")
    return uid
