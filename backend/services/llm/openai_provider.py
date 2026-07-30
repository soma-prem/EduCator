import json
import os
import time
from typing import Any, Dict, Optional

from services.llm.base import BaseLLMProvider
from services.llm.provider import LLMProviderMixin


class OpenAIProvider(BaseLLMProvider, LLMProviderMixin):
    name = "openai"

    def __init__(self, model: Optional[str] = None):
        super().__init__(model or os.getenv("LLM_MODEL", "gpt-4o-mini"))
        self.api_key = str(os.getenv("OPENAI_API_KEY", "") or "").strip()

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        if not self.api_key:
            raise self._build_error("OPENAI_API_KEY is missing in backend environment", status_code=500)

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise self._build_error("openai package is not installed", status_code=500, details={"raw_error": str(exc)}) from exc

        client = OpenAI(api_key=self.api_key)
        started = time.perf_counter()
        response = client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=max_output_tokens,
        )
        text = getattr(response, "output_text", "") or ""
        self._log("provider=%s model=%s status=ok latency_ms=%.0f", self.name, self.model, (time.perf_counter() - started) * 1000)
        return str(text)

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Any:
        raise NotImplementedError("Streaming is not implemented for OpenAI provider")

    def health_check(self) -> Dict[str, Any]:
        return {"ok": bool(self.api_key), "provider": self.name, "model": self.model}

    def get_model_name(self) -> str:
        return self.model
