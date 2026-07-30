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


class RagGenerationRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_route_uses_the_rag_generation_engine(self):
        from backend.routes import generate as generate_routes

        async def fake_get_source_text_from_request(request):
            return "source text", {"difficulty": "medium"}

        with patch.object(generate_routes, "get_source_text_from_request", side_effect=fake_get_source_text_from_request), patch.object(
            generate_routes, "generate_summary_from_rag", return_value=({"summary": "RAG summary"}, {"feature": "summary"})
        ) as mock_generate_summary:
            response = await generate_routes.generate_summary(object())

        self.assertEqual(response, {"summary": "RAG summary"})
        mock_generate_summary.assert_called_once_with("source text")

    async def test_tool_route_uses_the_rag_generation_engine_for_summary(self):
        from backend.routes import tools as tools_routes

        class DummyForm(dict):
            def get(self, key, default=None):
                return super().get(key, default)

            def getlist(self, key):
                return [self.get(key)]

        class DummyRequest:
            async def form(self):
                return DummyForm({"tool": "summary", "count": "5"})

        async def fake_get_source_text_from_request(request):
            return "source text", {"difficulty": "medium"}

        with patch.object(tools_routes, "get_source_text_from_request", side_effect=fake_get_source_text_from_request), patch.object(
            tools_routes, "generate_summary_from_rag", return_value=({"summary": "RAG summary"}, {"feature": "summary"})
        ) as mock_generate_summary:
            response = await tools_routes.tool_generate(DummyRequest())

        self.assertEqual(response["tool"], "summary")
        self.assertEqual(response["summary"], "RAG summary")
        mock_generate_summary.assert_called_once_with("source text")


if __name__ == "__main__":
    unittest.main()
