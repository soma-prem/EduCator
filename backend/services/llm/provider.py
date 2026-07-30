import json
import os
import time
from typing import Any, Dict, Optional

from services.llm.base import BaseLLMProvider


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, provider: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}


class ProviderResult(Dict[str, Any]):
    pass


class LLMProviderMixin:
    def _build_error(self, message: str, *, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None) -> ProviderError:
        return ProviderError(message, provider=self.name, status_code=status_code, details=details or {})

    def _log(self, message: str, **kwargs: Any) -> None:
        import logging

        logger = logging.getLogger("services.llm")
        logger.info(message, **kwargs)

    def _format_response(self, text: str, *, provider: str, model: str, latency_ms: int, prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None) -> Dict[str, Any]:
        return {
            "provider": provider,
            "model": model,
            "text": text,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
