import os
import time
from typing import Any, Dict, Optional

from services.llm.base import BaseLLMProvider
from services.llm.provider import LLMProviderMixin


class GroqProvider(BaseLLMProvider, LLMProviderMixin):
    name = "groq"

    def __init__(self, model: Optional[str] = None):
        super().__init__(model or os.getenv("LLM_MODEL", "llama-3.1-8b-instant"))
        self.api_key = str(os.getenv("GROQ_API_KEY", "") or "").strip()

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        if not self.api_key:
            raise self._build_error("GROQ_API_KEY is missing in backend environment", status_code=500)

        try:
            from groq import Groq
        except ImportError as exc:
            raise self._build_error("groq package is not installed", status_code=500, details={"raw_error": str(exc)}) from exc

        client = Groq(api_key=self.api_key)
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_output_tokens,
        )
        text = response.choices[0].message.content or ""
        self._log("provider=%s model=%s status=ok latency_ms=%.0f", self.name, self.model, (time.perf_counter() - started) * 1000)
        return str(text)

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Any:
        raise NotImplementedError("Streaming is not implemented for Groq provider")

    def health_check(self) -> Dict[str, Any]:
        return {"ok": bool(self.api_key), "provider": self.name, "model": self.model}

    def get_model_name(self) -> str:
        return self.model
