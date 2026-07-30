import time
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from services.firestore_service import (
    load_revision_plan,
    load_user_profile,
    list_revision_plans,
    save_revision_plan,
    save_user_profile,
)
from utils.premium_guard import require_user

router = APIRouter()


@router.get("/api/profile")
def get_profile(request: Request):
    try:
        user_id, _ = require_user(request)
        profile, message = load_user_profile(user_id)
        if message:
            return JSONResponse(content={"error": message}, status_code=502)
        return profile or {"userId": user_id, "displayName": "", "preferredSubjects": [], "learningGoals": [], "recentActivity": [], "weakTopics": [], "strengthTopics": [], "sessionStats": {}, "revisionPlans": []}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/profile")
def update_profile(request: Request, payload: dict = Body(default=None)):
    try:
        user_id, email = require_user(request)
        payload = payload or {}
        profile = {
            "displayName": str(payload.get("displayName", "")).strip(),
            "email": str(payload.get("email", email)).strip(),
            "preferredSubjects": payload.get("preferredSubjects") if isinstance(payload.get("preferredSubjects"), list) else [],
            "learningGoals": payload.get("learningGoals") if isinstance(payload.get("learningGoals"), list) else [],
            "recentActivity": payload.get("recentActivity") if isinstance(payload.get("recentActivity"), list) else [],
            "weakTopics": payload.get("weakTopics") if isinstance(payload.get("weakTopics"), list) else [],
            "strengthTopics": payload.get("strengthTopics") if isinstance(payload.get("strengthTopics"), list) else [],
            "sessionStats": payload.get("sessionStats") if isinstance(payload.get("sessionStats"), dict) else {},
            "revisionPlans": payload.get("revisionPlans") if isinstance(payload.get("revisionPlans"), list) else [],
            "lastSeenAt": str(payload.get("lastSeenAt", "")).strip(),
            "lastSeenAtEpoch": int(payload.get("lastSeenAtEpoch", 0) or 0),
        }
        ok, message = save_user_profile(user_id, profile)
        if not ok:
            return JSONResponse(content={"error": message}, status_code=400)
        return {"saved": True}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.get("/api/profile/revision-plans")
def get_revision_plans(request: Request):
    try:
        user_id, _ = require_user(request)
        plans, message = list_revision_plans(user_id)
        if message:
            return JSONResponse(content={"error": message}, status_code=502)
        return {"revisionPlans": plans}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.get("/api/profile/revision-plans/{plan_id}")
def get_revision_plan(request: Request, plan_id: str):
    try:
        user_id, _ = require_user(request)
        plan_id = str(plan_id or "").strip()
        if not plan_id:
            return JSONResponse(content={"error": "planId is required"}, status_code=400)
        plan, message = load_revision_plan(user_id, plan_id)
        if message:
            return JSONResponse(content={"error": message}, status_code=502)
        if plan is None:
            return JSONResponse(content={"error": "Revision plan not found"}, status_code=404)
        return plan
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/profile/revision-plans")
def create_revision_plan(request: Request, payload: dict = Body(default=None)):
    try:
        user_id, _ = require_user(request)
        payload = payload or {}
        plan_id = str(payload.get("planId", "")).strip()
        name = str(payload.get("name", "")).strip()
        description = str(payload.get("description", "")).strip()
        topics = payload.get("topics") if isinstance(payload.get("topics"), list) else []
        steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []

        if not plan_id:
            return JSONResponse(content={"error": "planId is required"}, status_code=400)
        if not name:
            return JSONResponse(content={"error": "name is required"}, status_code=400)

        ok, message = save_revision_plan(user_id, plan_id, name, description, topics, steps)
        if not ok:
            return JSONResponse(content={"error": message}, status_code=400)
        return {"saved": True, "planId": plan_id}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
