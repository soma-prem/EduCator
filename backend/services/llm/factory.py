import logging
from typing import Optional

from services.llm.base import BaseLLMProvider
from services.llm.config import (
    get_active_provider_name,
    get_fallback_provider_name,
    get_model_for_provider,
    normalize_provider,
    get_supported_providers,
)
from services.llm.gemini_provider import GeminiProvider
from services.llm.groq_provider import GroqProvider
from services.llm.ollama_provider import OllamaProvider
from services.llm.openai_provider import OpenAIProvider
from services.llm.provider import ProviderError


_PROVIDER_CACHE: dict = {}
_logger = logging.getLogger("services.llm")

PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "groq": GroqProvider,
}


class LLMProviderManager(BaseLLMProvider):
    name = "llm_provider_manager"

    def __init__(self, primary: BaseLLMProvider, fallback: Optional[BaseLLMProvider] = None):
        super().__init__(primary.model)
        self.primary = primary
        self.fallback = fallback
        self.primary_name = normalize_provider(primary.name)
        self.fallback_name = normalize_provider(fallback.name) if fallback else None

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        try:
            return self.primary.generate(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)
        except Exception as primary_exc:
            _logger.warning(
                "Primary provider failed: provider=%s model=%s error=%s",
                self.primary.name,
                self.primary.get_model_name(),
                str(primary_exc),
            )
            if not self.fallback:
                raise
            try:
                return self.fallback.generate(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)
            except Exception as fallback_exc:
                raise ProviderError(
                    f"Both primary ({self.primary.name}) and fallback ({self.fallback.name}) providers failed.",
                    provider=self.primary.name,
                    status_code=getattr(fallback_exc, "status_code", None),
                    details={
                        "primary_error": str(primary_exc),
                        "fallback_error": str(fallback_exc),
                    },
                ) from fallback_exc

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> any:
        started = False
        try:
            for chunk in self.primary.stream_generate(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type):
                started = True
                yield chunk
            return
        except Exception as primary_exc:
            if started or not self.fallback:
                raise
            _logger.warning(
                "Primary provider streaming failed before output; falling back to %s: %s",
                self.fallback.name,
                str(primary_exc),
            )
            yield from self.fallback.stream_generate(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)

    def health_check(self) -> dict:
        primary_status = self.primary.health_check()
        fallback_status = self.fallback.health_check() if self.fallback else None
        ok = bool(primary_status.get("ok")) or bool(fallback_status and fallback_status.get("ok"))
        return {
            "ok": ok,
            "provider": self.name,
            "selected_provider": self.primary.name,
            "fallback_provider": self.fallback.name if self.fallback else None,
            "primary": primary_status,
            "fallback": fallback_status,
            "available_providers": get_supported_providers(),
        }

    def get_model_name(self) -> str:
        return self.primary.get_model_name()


def _instantiate_provider(provider_name: str, model: Optional[str] = None) -> BaseLLMProvider:
    provider_key = normalize_provider(provider_name)
    provider_class = PROVIDER_CLASSES.get(provider_key)
    if not provider_class:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
    effective_model = model or get_model_for_provider(provider_key)
    return provider_class(effective_model)


def create_provider(provider_name: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
    global _PROVIDER_CACHE

    selected_provider = normalize_provider(provider_name or get_active_provider_name())
    selected_model = model or get_model_for_provider(selected_provider)
    fallback_name = get_fallback_provider_name()
    cache_key = (selected_provider, selected_model, fallback_name)

    if provider_name is None and model is None and cache_key in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[cache_key]

    primary = _instantiate_provider(selected_provider, selected_model)
    fallback = None
    if fallback_name and fallback_name != selected_provider:
        fallback = _instantiate_provider(fallback_name)

    provider = LLMProviderManager(primary, fallback) if fallback else primary

    if provider_name is None and model is None:
        _PROVIDER_CACHE[cache_key] = provider
    return provider


def get_provider(provider_name: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
    return create_provider(provider_name=provider_name, model=model)


def verify_provider_startup() -> list[str]:
    provider = create_provider()
    warnings = []
    try:
        status = provider.health_check()
        if not status.get("ok"):
            if isinstance(provider, LLMProviderManager):
                primary = status.get("primary", {})
                fallback = status.get("fallback", {})
                if not primary.get("ok"):
                    warnings.append(
                        f"Primary provider '{primary.get('provider')}' is unavailable or misconfigured. "
                        f"Model={primary.get('model')} base_url={primary.get('base_url', 'unknown')}"
                    )
                if fallback and not fallback.get("ok"):
                    warnings.append(
                        f"Fallback provider '{fallback.get('provider')}' is unavailable or misconfigured. "
                        f"Model={fallback.get('model')}"
                    )
                if status.get("fallback_provider") and status.get("ok"):
                    warnings.append(
                        f"Using fallback provider '{status.get('fallback_provider')}' because primary provider is unavailable."
                    )
            else:
                warnings.append(
                    f"LLM provider '{provider.name}' is unavailable or misconfigured. Model={provider.get_model_name()}"
                )
    except Exception as exc:
        warnings.append(f"Failed to validate LLM provider startup: {exc}")
    return warnings
