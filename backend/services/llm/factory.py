import os
from typing import Optional

from services.llm.base import BaseLLMProvider
from services.llm.gemini_provider import GeminiProvider
from services.llm.groq_provider import GroqProvider
from services.llm.ollama_provider import OllamaProvider
from services.llm.openai_provider import OpenAIProvider


_PROVIDER_CACHE: Optional[BaseLLMProvider] = None


def create_provider(provider_name: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
    global _PROVIDER_CACHE

    selected_provider = (provider_name or os.getenv("LLM_PROVIDER", "gemini") or "gemini").strip().lower()
    selected_model = model or os.getenv("LLM_MODEL", "") or ""

    if provider_name is None and model is None and _PROVIDER_CACHE is not None:
        current_provider = _PROVIDER_CACHE.__class__.__name__.lower()
        current_env = selected_provider
        if current_provider.startswith(current_env) or current_env in {"gemini", "ollama", "openai", "groq"}:
            if current_provider.replace("provider", "") == current_env:
                return _PROVIDER_CACHE

    if selected_provider == "ollama":
        provider = OllamaProvider(selected_model or None)
    elif selected_provider == "openai":
        provider = OpenAIProvider(selected_model or None)
    elif selected_provider == "groq":
        provider = GroqProvider(selected_model or None)
    else:
        provider = GeminiProvider(selected_model or None)

    if provider_name is None and model is None:
        _PROVIDER_CACHE = provider
    return provider


def get_provider(provider_name: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
    return create_provider(provider_name=provider_name, model=model)
