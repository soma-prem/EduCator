from fastapi import APIRouter

from services.llm.factory import create_provider, get_active_provider_name, get_fallback_provider_name
from services.rag.vectordb import health_check as get_rag_health

router = APIRouter()


@router.get("/api/system/providers")
def get_providers_status():
    provider = create_provider()
    status = provider.health_check()
    return {
        "current_provider": get_active_provider_name(),
        "current_model": provider.get_model_name(),
        "fallback_provider": get_fallback_provider_name(),
        "available_providers": ["gemini", "ollama", "openai", "groq"],
        "status": status,
    }


@router.get("/api/system/rag")
def get_rag_status():
    status = get_rag_health()
    return {
        "status": status,
    }
