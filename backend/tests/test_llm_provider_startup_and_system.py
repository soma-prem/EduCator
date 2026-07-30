import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class LlmProviderStartupTests(unittest.TestCase):
    def test_primary_ollama_with_gemini_fallback_is_instantiated(self):
        from services.llm.factory import create_provider

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "FALLBACK_PROVIDER": "gemini", "OLLAMA_MODEL": "gemma3"}, clear=False):
            provider = create_provider()

        self.assertEqual(provider.primary.name, "ollama")
        self.assertEqual(provider.fallback.name, "gemini")

    def test_provider_health_endpoint_returns_status(self):
        from routes.system import get_providers_status

        result = get_providers_status()
        self.assertIn("current_provider", result)
        self.assertIn("current_model", result)
        self.assertIn("status", result)

    def test_verify_provider_startup_reports_warning_for_missing_provider(self):
        from services.llm.factory import verify_provider_startup

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_BASE_URL": "http://localhost:1"}, clear=False):
            warnings = verify_provider_startup()

        self.assertTrue(any("unavailable or misconfigured" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
