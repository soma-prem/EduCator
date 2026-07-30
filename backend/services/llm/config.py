import os
from typing import List, Optional

SUPPORTED_PROVIDERS = ["gemini", "ollama", "openai", "groq"]

PROVIDER_ALIASES = {
    "gemini": "gemini",
    "google": "gemini",
    "g": "gemini",
    "ollama": "ollama",
    "local": "ollama",
    "localai": "ollama",
    "openai": "openai",
    "oai": "openai",
    "groq": "groq",
}


def normalize_provider(provider: Optional[str]) -> str:
    if not provider:
        return ""
    value = str(provider).strip().lower()
    return PROVIDER_ALIASES.get(value, value)


def get_env_provider(name: str, default: str = "") -> str:
    return normalize_provider(os.getenv(name, default))


def get_active_provider_name() -> str:
    provider = get_env_provider("LLM_PROVIDER")
    if provider:
        return provider
    provider = get_env_provider("PRIMARY_PROVIDER")
    if provider:
        return provider
    return "ollama"


def get_fallback_provider_name() -> Optional[str]:
    fallback = get_env_provider("FALLBACK_PROVIDER")
    if not fallback:
        return None
    if fallback == get_active_provider_name():
        return None
    if fallback not in SUPPORTED_PROVIDERS:
        return None
    return fallback


def get_model_for_provider(provider_name: str, explicit_model: Optional[str] = None) -> str:
    provider = normalize_provider(provider_name) or get_active_provider_name()
    if explicit_model:
        return str(explicit_model).strip()
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "gemma3")) or "gemma3"
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", "gemini-2.5-flash")) or "gemini-2.5-flash"
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini")) or "gpt-4o-mini"
    if provider == "groq":
        return os.getenv("GROQ_MODEL", os.getenv("LLM_MODEL", "llama-3.1-8b-instant")) or "llama-3.1-8b-instant"
    return os.getenv("LLM_MODEL", "") or ""


def get_timeout_seconds(provider_name: str) -> int:
    provider_key = normalize_provider(provider_name).upper()
    return int(os.getenv(f"{provider_key}_TIMEOUT_SECONDS", os.getenv("LLM_TIMEOUT_SECONDS", "30")) or 30)


def get_retry_count(provider_name: str) -> int:
    provider_key = normalize_provider(provider_name).upper()
    return int(os.getenv(f"{provider_key}_MAX_RETRIES", os.getenv("LLM_MAX_RETRIES", "1")) or 1)


def get_temperature(provider_name: str) -> float:
    provider_key = normalize_provider(provider_name).upper()
    return float(os.getenv(f"{provider_key}_TEMPERATURE", os.getenv("LLM_TEMPERATURE", "0.3")) or 0.3)


def get_max_output_tokens(provider_name: str) -> int:
    provider_key = normalize_provider(provider_name).upper()
    return int(os.getenv(f"{provider_key}_MAX_TOKENS", os.getenv("LLM_MAX_TOKENS", "800")) or 800)


def get_base_url(provider_name: str) -> str:
    provider_key = normalize_provider(provider_name).upper()
    return str(os.getenv(f"{provider_key}_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))).rstrip("/")


def get_supported_providers() -> List[str]:
    return list(SUPPORTED_PROVIDERS)
