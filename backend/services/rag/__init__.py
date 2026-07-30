from services.rag.chunking import chunk_text
from services.rag.embeddings import embed_documents, embed_query, embed_text, load_model
from services.rag.generation import generate_answer, generate_fill_blanks, generate_flashcards, generate_mcqs, generate_summary, generate_true_false
from services.rag.ingestion import ingest_document
from services.rag.parser import parse_fill_blanks, parse_flashcards, parse_json, parse_mcqs, parse_true_false
from services.rag.prompts import (
    FILL_BLANK_PROMPT_TEMPLATE,
    FLASHCARD_PROMPT_TEMPLATE,
    MCQ_PROMPT_TEMPLATE,
    QA_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
    TRUE_FALSE_PROMPT_TEMPLATE,
)
from services.rag.retriever import retrieve_chunks
from services.rag.vectordb import add_documents, delete_document, get_collection, initialize, list_documents, search

__all__ = [
    "chunk_text",
    "embed_documents",
    "embed_query",
    "embed_text",
    "load_model",
    "ingest_document",
    "generate_answer",
    "generate_summary",
    "generate_mcqs",
    "generate_flashcards",
    "generate_true_false",
    "generate_fill_blanks",
    "parse_json",
    "parse_mcqs",
    "parse_flashcards",
    "parse_true_false",
    "parse_fill_blanks",
    "QA_PROMPT_TEMPLATE",
    "SUMMARY_PROMPT_TEMPLATE",
    "MCQ_PROMPT_TEMPLATE",
    "FLASHCARD_PROMPT_TEMPLATE",
    "TRUE_FALSE_PROMPT_TEMPLATE",
    "FILL_BLANK_PROMPT_TEMPLATE",
    "retrieve_chunks",
    "initialize",
    "get_collection",
    "add_documents",
    "delete_document",
    "search",
    "list_documents",
]
