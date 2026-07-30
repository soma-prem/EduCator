from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMProvider(ABC):
    name = "base"

    def __init__(self, model: Optional[str] = None):
        self.model = model or ""

    @abstractmethod
    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        raise NotImplementedError

    @abstractmethod
    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Any:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError

    def format_prompt(self, prompt: str, response_mime_type: str = "application/json") -> str:
        return str(prompt or "").strip()
