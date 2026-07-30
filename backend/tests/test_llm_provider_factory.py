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


class LlmProviderFactoryTests(unittest.TestCase):
    def test_factory_returns_gemini_provider_by_default(self):
        from services.llm.factory import create_provider

        with patch.dict(os.environ, {"LLM_PROVIDER": "", "GEMINI_API_KEY": "test-key"}, clear=False):
            provider = create_provider()

        self.assertEqual(provider.__class__.__name__, "GeminiProvider")

    def test_factory_returns_ollama_provider_when_selected(self):
        from services.llm.factory import create_provider

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "LLM_MODEL": "gemma3"}, clear=False):
            provider = create_provider()

        self.assertEqual(provider.__class__.__name__, "OllamaProvider")


if __name__ == "__main__":
    unittest.main()
