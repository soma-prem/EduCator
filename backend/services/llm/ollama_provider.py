import json
import os
import time
from typing import Any, Dict, Generator, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from services.llm.base import BaseLLMProvider
from services.llm.config import get_base_url, get_model_for_provider, get_retry_count, get_timeout_seconds
from services.llm.provider import LLMProviderMixin, ProviderError


class OllamaProvider(BaseLLMProvider, LLMProviderMixin):
    name = "ollama"

    def __init__(self, model: Optional[str] = None):
        super().__init__(model or get_model_for_provider("ollama"))
        self.base_url = get_base_url("ollama")
        self.timeout_seconds = get_timeout_seconds("ollama")
        self.max_retries = get_retry_count("ollama")
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", os.getenv("LLM_TEMPERATURE", "0.3")) or 0.3)

    def _build_payload(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json", stream: bool = False) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "prompt": self.format_prompt(prompt, response_mime_type=response_mime_type),
            "max_tokens": max_output_tokens,
            "temperature": self.temperature,
            "stream": stream,
        }
        if response_mime_type == "application/json":
            payload["response_format"] = "json"
        return payload

    def _extract_text(self, data: Any) -> str:
        if isinstance(data, dict):
            if "response" in data:
                return str(data.get("response") or "")
            if "results" in data and isinstance(data.get("results"), list):
                items = [str(item.get("response") or "") for item in data.get("results", []) if isinstance(item, dict)]
                return "".join(items)
            return json.dumps(data, ensure_ascii=False)
        return str(data)

    def _send_request(self, payload: Dict[str, Any], stream: bool = False) -> Any:
        endpoint = f"{self.base_url}/api/generate"
        payload_bytes = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(endpoint, data=payload_bytes, headers={"Content-Type": "application/json"}, method="POST")
        if stream:
            response = urlrequest.urlopen(req, timeout=self.timeout_seconds)
            return response
        with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def _is_retryable(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(key in message for key in ["timeout", "timed out", "temporarily", "connection reset", "connection refused", "internal server error"])

    def _request(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        payload = self._build_payload(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type, stream=False)
        last_error = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                data = self._send_request(payload, stream=False)
                text = self._extract_text(data)
                self._log(
                    "provider=%s model=%s status=ok latency_ms=%.0f",
                    self.name,
                    self.model,
                    (time.perf_counter() - started) * 1000,
                )
                return text
            except (urlerror.URLError, ConnectionError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries and self._is_retryable(exc):
                    time.sleep(1.0)
                    continue
                raise self._build_error(
                    f"Ollama provider request failed: {exc}",
                    status_code=503,
                    details={"raw_error": str(exc)},
                ) from exc
        raise self._build_error("Ollama provider request failed", status_code=503, details={"raw_error": str(last_error)})

    def generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> str:
        return self._request(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type)

    def stream_generate(self, prompt: str, *, max_output_tokens: int = 800, response_mime_type: str = "application/json") -> Generator[str, None, None]:
        payload = self._build_payload(prompt, max_output_tokens=max_output_tokens, response_mime_type=response_mime_type, stream=True)
        req = urlrequest.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
                for raw_line in response:
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line in {"[DONE]", "done"}:
                        break
                    try:
                        chunk = json.loads(line)
                        text = self._extract_text(chunk)
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        yield line
        except (urlerror.URLError, ConnectionError) as exc:
            raise self._build_error(
                f"Ollama streaming unavailable: {exc}",
                status_code=503,
                details={"raw_error": str(exc)},
            ) from exc

    def health_check(self) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/models"
        started = time.perf_counter()
        try:
            req = urlrequest.Request(endpoint, headers={"Content-Type": "application/json"})
            with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                models = data if isinstance(data, list) else data.get("models", [])
                has_model = any(str(item).strip().lower() == self.model.lower() for item in models)
                latency_ms = round((time.perf_counter() - started) * 1000)
                return {
                    "ok": bool(has_model),
                    "provider": self.name,
                    "model": self.model,
                    "base_url": self.base_url,
                    "latency_ms": latency_ms,
                    "model_available": bool(has_model),
                    "model_list": models,
                }
        except Exception as exc:
            return {
                "ok": False,
                "provider": self.name,
                "model": self.model,
                "base_url": self.base_url,
                "error": str(exc),
            }

    def get_model_name(self) -> str:
        return self.model

    def format_prompt(self, prompt: str, response_mime_type: str = "application/json") -> str:
        normalized = str(prompt or "").strip()
        if response_mime_type == "application/json":
            suffix = "\n\nReturn only valid JSON without markdown fences, comments, or extra explanation."
        else:
            suffix = ""
        if any(key in self.model.lower() for key in ["gemma", "qwen", "llama", "mistral", "deepseek"]):
            return f"{normalized}{suffix}".strip()
        return normalized
