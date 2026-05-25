import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.entitlement_service import get_user_entitlement, set_user_entitlement
from services.firestore_service import get_firestore_db

try:
    import stripe
except Exception:  # pragma: no cover
    stripe = None

try:
    from firebase_admin import auth as firebase_auth
except Exception:  # pragma: no cover
    firebase_auth = None


router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _get_frontend_base_url(request: Request) -> str:
    """
    Prefer configured FRONTEND_BASE_URL (Render/Vercel).
    Fallback to request Origin/Referer (helps when env is missing/misconfigured).
    """
    configured = os.getenv("FRONTEND_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured

    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin.startswith("http"):
        return origin

    referer = (request.headers.get("referer") or "").strip()
    if referer.startswith("http"):
        try:
            # Very small parser to avoid importing urllib just for this.
            # Keep scheme + host only.
            parts = referer.split("/")
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
        except Exception:
            pass

    return "http://localhost:3000"

# Best-effort idempotency for local/dev: avoid re-processing the same Stripe event repeatedly.
_PROCESSED_EVENTS = {}


PLAN_CATALOG = {
    "silver": {"amount_minor": 20000, "currency": "inr", "label": "Silver", "features": ["fill_blanks", "audio_summary", "knowledge_gap"]},
    "gold": {
        "amount_minor": 50000,
        "currency": "inr",
        "label": "Gold",
        "features": ["fill_blanks", "audio_summary", "knowledge_gap", "true_false"],
    },
    "platinum": {
        "amount_minor": 100000,
        "currency": "inr",
        "label": "Platinum",
        "features": ["fill_blanks", "audio_summary", "knowledge_gap", "true_false", "mock_exam", "youtube_guide"],
    },
}


def _require_stripe():
    if stripe is None:
        raise RuntimeError("stripe package is not installed on backend")
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe checkout is not configured. Add STRIPE_SECRET_KEY to backend/.env and restart the backend.")
    stripe.api_key = STRIPE_SECRET_KEY


def _get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def _require_firebase_user(request: Request):
    if firebase_auth is None:
        raise RuntimeError("firebase_admin is not installed/configured on backend")
    get_firestore_db()
    token = _get_bearer_token(request)
    if not token:
        raise ValueError("Missing Authorization Bearer token")
    decoded = firebase_auth.verify_id_token(token)
    uid = str(decoded.get("uid") or "").strip()
    email = str(decoded.get("email") or "").strip()
    if not uid:
        raise ValueError("Invalid token (uid missing)")
    return uid, email


def _plan_for_entitlement(entitlement: dict | None):
    if not isinstance(entitlement, dict):
        return "free", False, 0
    plan = str(entitlement.get("plan") or "").strip().lower()
    active = bool(entitlement.get("active", False))
    try:
        expires_at = int(entitlement.get("expiresAtEpoch") or 0)
    except Exception:
        expires_at = 0
    now_epoch = int(time.time())
    if not active or expires_at <= now_epoch or plan not in PLAN_CATALOG:
        return "free", False, expires_at
    return plan, True, expires_at


@router.get("/api/billing/me")
def billing_me(request: Request):
    try:
        uid, _email = _require_firebase_user(request)
        entitlement, message = get_user_entitlement(uid)
        if message:
            return JSONResponse(content={"error": message}, status_code=502)
        plan, active, expires_at = _plan_for_entitlement(entitlement)
        features = PLAN_CATALOG.get(plan, {}).get("features", []) if plan != "free" else []
        return {
            "userId": uid,
            "plan": plan,
            "active": active,
            "expiresAtEpoch": expires_at,
            "features": features,
        }
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=401)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/billing/checkout")
async def create_checkout(request: Request):
    try:
        uid, email = _require_firebase_user(request)
        body = await request.json()
        plan = str((body or {}).get("plan") or "").strip().lower()
        if plan not in PLAN_CATALOG:
            return JSONResponse(content={"error": "plan must be one of: silver, gold, platinum"}, status_code=400)

        _require_stripe()
        item = PLAN_CATALOG[plan]
        frontend_base_url = _get_frontend_base_url(request)
        success_url = f"{frontend_base_url}/premium?success=1&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_base_url}/premium?canceled=1"

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": str(item.get("currency") or "inr"),
                        "unit_amount": int(item["amount_minor"]),
                        "product_data": {"name": f"EduCator {item['label']} (1 year)"},
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=uid,
            customer_email=email or None,
            metadata={"uid": uid, "plan": plan},
        )
        return {
            "checkoutUrl": session.get("url"),
            "sessionId": session.get("id"),
            "frontendBaseUrl": frontend_base_url,
        }
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=401)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/billing/confirm")
async def confirm_checkout(request: Request):
    """
    Fallback activation endpoint for success redirects.
    Verifies the Stripe checkout session belongs to the current Firebase user and was paid,
    then stores entitlement in Firestore.

    This helps when webhooks are not configured/reachable in production.
    """
    try:
        uid, _email = _require_firebase_user(request)
        _require_stripe()

        payload = await request.json()
        session_id = str((payload or {}).get("sessionId") or (payload or {}).get("session_id") or "").strip()
        if not session_id:
            return JSONResponse(content={"error": "sessionId is required"}, status_code=400)

        session = stripe.checkout.Session.retrieve(session_id)
        if not isinstance(session, dict):
            return JSONResponse(content={"error": "Invalid session"}, status_code=400)

        if str(session.get("payment_status") or "").lower() != "paid":
            return JSONResponse(content={"error": "Payment not completed"}, status_code=400)

        meta = session.get("metadata") or {}
        session_uid = str(meta.get("uid") or session.get("client_reference_id") or "").strip()
        if not session_uid or session_uid != uid:
            return JSONResponse(content={"error": "Session does not belong to current user"}, status_code=403)

        plan = str(meta.get("plan") or "").strip().lower()
        if plan not in PLAN_CATALOG:
            return JSONResponse(content={"error": "Invalid plan on session"}, status_code=400)

        expires_at = int(time.time()) + 365 * 24 * 60 * 60
        ok, _message = set_user_entitlement(
            uid,
            plan,
            expires_at,
            email=str((session.get("customer_details") or {}).get("email") or ""),
            stripe_customer_id=str(session.get("customer") or ""),
            stripe_checkout_session_id=str(session.get("id") or ""),
            stripe_payment_intent_id=str(session.get("payment_intent") or ""),
        )
        if not ok:
            return JSONResponse(content={"error": "Failed to store entitlement"}, status_code=502)

        return {"ok": True, "plan": plan, "expiresAtEpoch": expires_at}
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=401)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    try:
        if stripe is None:
            return JSONResponse(content={"error": "stripe package is not installed on backend"}, status_code=502)
        if not STRIPE_SECRET_KEY:
            return JSONResponse(content={"error": "STRIPE_SECRET_KEY is missing"}, status_code=502)
        if not STRIPE_WEBHOOK_SECRET:
            return JSONResponse(content={"error": "STRIPE_WEBHOOK_SECRET is missing"}, status_code=502)
        stripe.api_key = STRIPE_SECRET_KEY

        payload = await request.body()
        sig = request.headers.get("stripe-signature")
        if not sig:
            return JSONResponse(content={"error": "Missing stripe-signature header"}, status_code=400)

        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig, secret=STRIPE_WEBHOOK_SECRET)
        event_id = str(event.get("id") or "").strip()
        now_epoch = int(time.time())
        if event_id:
            # purge older than 2 hours
            for key, ts in list(_PROCESSED_EVENTS.items()):
                if now_epoch - int(ts or 0) > 2 * 60 * 60:
                    _PROCESSED_EVENTS.pop(key, None)
            if event_id in _PROCESSED_EVENTS:
                return {"received": True, "deduped": True}
            _PROCESSED_EVENTS[event_id] = now_epoch
        event_type = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}

        if event_type == "checkout.session.completed":
            if str(obj.get("payment_status") or "").lower() != "paid":
                return {"received": True}
            meta = obj.get("metadata") or {}
            uid = str(meta.get("uid") or obj.get("client_reference_id") or "").strip()
            plan = str(meta.get("plan") or "").strip().lower()
            if not uid or plan not in PLAN_CATALOG:
                return {"received": True}

            expires_at = int(time.time()) + 365 * 24 * 60 * 60
            ok, _message = set_user_entitlement(
                uid,
                plan,
                expires_at,
                email=str(obj.get("customer_details", {}).get("email") or ""),
                stripe_customer_id=str(obj.get("customer") or ""),
                stripe_checkout_session_id=str(obj.get("id") or ""),
                stripe_payment_intent_id=str(obj.get("payment_intent") or ""),
            )
            if not ok:
                return JSONResponse(content={"error": "Failed to store entitlement"}, status_code=502)

        return {"received": True}
    except stripe.error.SignatureVerificationError:
        return JSONResponse(content={"error": "Invalid signature"}, status_code=400)
    except Exception as exc:
        return JSONResponse(content={"error": f"Webhook error: {exc}"}, status_code=500)
