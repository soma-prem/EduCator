from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from routes.exam import create_mock_exam
from routes.qa import answer_question_from_upload
from routes.tools import tool_generate

router = APIRouter()


def _normalize_type(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "mock_test": "mocktest",
        "mock-test": "mocktest",
        "mock": "mocktest",
        "text_ai": "textai",
        "text-ai": "textai",
    }
    return aliases.get(raw, raw)


@router.post("/api/ai/generate")
async def ai_generate(request: Request):
    try:
        form = await request.form()
        request_type = _normalize_type(form.get("type") or form.get("tool"))
        if request_type in {"mocktest"}:
            return await create_mock_exam(request)
        if request_type in {"textai"}:
            return await answer_question_from_upload(request)
        return await tool_generate(request)
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse(content={"error": f"Unexpected server error: {exc}"}, status_code=500)
