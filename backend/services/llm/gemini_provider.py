import json
import os
import re
import time
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from services.llm.base import BaseLLMProvider
from services.llm.provider import LLMProviderMixin, ProviderError


class GeminiProvider(BaseLLMProvider, LLMProviderMixin):
    name = "gemini"

    def __init__(self, model: Optional[str] = None):
        super().__init__(model or os.getenv("LLM_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")))
        self.api_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
        self.timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))

    def _request(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        if not self.api_key:
            raise self._build_error("GEMINI_API_KEY is missing in backend environment", status_code=500)

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": response_mime_type,
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")

        last_error = None
        tried_global_fallback = False
        current_key = self.api_key
        current_endpoint = endpoint
        for attempt in range(self.max_retries + 1):
            req = urlrequest.Request(current_endpoint, data=payload_bytes, headers={"Content-Type": "application/json"}, method="POST")
            try:
                started = time.perf_counter()
                with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                    self._log("provider=%s model=%s status=ok latency_ms=%.0f", self.name, self.model, (time.perf_counter() - started) * 1000)
                    return body
            except urlerror.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="ignore")
                last_error = f"Gemini HTTP {exc.code}: {error_body}"
                if exc.code == 429 and re.search(r"quota", error_body, flags=re.IGNORECASE):
                    global_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
                    if global_key and global_key != current_key and not tried_global_fallback:
                        tried_global_fallback = True
                        current_key = global_key
                        current_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={current_key}"
                        continue
                    raise self._build_error("Gemini quota exceeded on provided key. Wait for quota reset or use a paid key.", status_code=429, details={"raw_error": last_error}) from exc
                if exc.code == 429 and attempt < self.max_retries:
                    retry_after = 1.5
                    retry_match = re.search(r"retry in ([0-9.]+)s", error_body, flags=re.IGNORECASE)
                    if retry_match:
                        retry_after = float(retry_match.group(1))
                    time.sleep(max(1.0, retry_after))
                    continue
                raise self._build_error(last_error, status_code=exc.code, details={"raw_error": last_error}) from exc
            except Exception as exc:
                raise self._build_error(str(exc), status_code=500, details={"raw_error": str(exc)}) from exc

        raise self._build_error(last_error or "Gemini request failed", status_code=500, details={"raw_error": last_error or "Gemini request failed"})

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        return self._request(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Any:
        raise NotImplementedError("Streaming is not implemented for Gemini provider")

    def health_check(self) -> Dict[str, Any]:
        return {"ok": bool(self.api_key), "provider": self.name, "model": self.model}

    def get_model_name(self) -> str:
        return self.model
