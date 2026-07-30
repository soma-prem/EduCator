import unittest
from unittest.mock import patch

from services.rag import generation, parser


class RagGenerationTests(unittest.TestCase):
    def test_parse_mcqs_validates_schema(self):
        payload = '[{"question":"What is Python?","options":["A","B","C","D"],"answer":"A","explanation":"It is a language.","topic":"Programming"}]'
        result = parser.parse_mcqs(payload)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "What is Python?")

    def test_parse_mcqs_rejects_missing_fields(self):
        payload = '[{"question":"What is Python?","options":["A","B","C","D"],"answer":"A"}]'
        with self.assertRaises(ValueError):
            parser.parse_mcqs(payload)

    @patch("services.rag.generation.retrieve_chunks", return_value=[])
    def test_generate_answer_returns_fallback_without_retrieval(self, mock_retrieve):
        answer, metadata = generation.generate_answer(question="What is in the document?", document_id="doc-1")
        self.assertIn("couldn't find this information", answer)
        self.assertEqual(metadata["retrieved_chunk_count"], 0)
        mock_retrieve.assert_called_once()


if __name__ == "__main__":
    unittest.main()
