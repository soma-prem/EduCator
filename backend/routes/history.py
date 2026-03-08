from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from services.firestore_service import (
    clear_history,
    delete_history_item,
    list_history,
    save_session_history,
)

router = APIRouter()


@router.get("/api/history")
def get_history(limit: str = Query(default="20")):
    try:
        try:
            limit_value = max(1, min(100, int(limit)))
        except ValueError:
            limit_value = 20

        items, message = list_history(limit=limit_value)
        if message:
            return {"items": [], "message": f"Firebase error: {message}"}
        return {"items": items}
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/history/clear")
def clear_history_route():
    try:
        cleared, message = clear_history()
        if message:
            return {"cleared": 0, "message": f"Firebase error: {message}"}
        return {"cleared": cleared}
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.delete("/api/history/{doc_id}")
def delete_history_route(doc_id):
    try:
        deleted, message = delete_history_item(doc_id)
        if not deleted:
            return {"deleted": False, "message": f"Firebase error: {message}"}
        return {"deleted": True}
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)


@router.post("/api/history/session")
def save_session_history_route(payload: dict = Body(default=None)):
    try:
        payload = payload or {}
        session_id = save_session_history(payload)
        return {"sessionId": session_id, "stored": session_id is not None}
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
