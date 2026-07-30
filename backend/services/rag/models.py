from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionAnswer(BaseModel):
    question: str
    answer: str


class Summary(BaseModel):
    summary: str


class MCQ(BaseModel):
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    answer: str
    explanation: str
    topic: str


class Flashcard(BaseModel):
    front: str
    back: str
    topic: str


class TrueFalseQuestion(BaseModel):
    question: str
    answer: bool
    explanation: str
    topic: str


class FillBlankQuestion(BaseModel):
    prompt: str
    answer: str
    explanation: str
    topic: str


class GenerationResult(BaseModel):
    feature: str
    data: Any
    retrieved_chunk_count: int = 0
    scores: List[float] = Field(default_factory=list)
    retrieval_time: float = 0.0
    llm_time: float = 0.0
    total_time: float = 0.0
    error: Optional[str] = None
