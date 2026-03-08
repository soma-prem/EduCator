from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {"status": "ok", "message": "Backend is running"}


@router.get("/api/message")
def get_message():
    return {"message": "Hello from Python Backend"}
