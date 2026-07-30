import json
import os
import time
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from services.llm.base import BaseLLMProvider
from services.llm.provider import LLMProviderMixin, ProviderError


class OllamaProvider(BaseLLMProvider, LLMProviderMixin):
    name = "ollama"

    def __init__(self, model: Optional[str] = None):
        super().__init__(model or os.getenv("LLM_MODEL", "gemma3"))
        self.base_url = str(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def _request(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_output_tokens},
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(endpoint, data=payload_bytes, headers={"Content-Type": "application/json"}, method="POST")
        started = time.perf_counter()
        try:
            with urlrequest.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                text = str(data.get("response", "") or "")
                self._log("provider=%s model=%s status=ok latency_ms=%.0f", self.name, self.model, (time.perf_counter() - started) * 1000)
                return text
        except (urlerror.URLError, ConnectionError, json.JSONDecodeError) as exc:
            raise self._build_error(f"Ollama provider unavailable: {exc}", status_code=503, details={"raw_error": str(exc)}) from exc

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        return self._request(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Any:
        raise NotImplementedError("Streaming is not implemented for Ollama provider")

    def health_check(self) -> Dict[str, Any]:
        return {"ok": False, "provider": self.name, "model": self.model, "base_url": self.base_url}

    def get_model_name(self) -> str:
        return self.model
