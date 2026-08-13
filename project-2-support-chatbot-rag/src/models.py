"""Pydantic data models for the RAG support chatbot pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A single chunk produced from a source knowledge base document."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str                     # filename, e.g. "faq.md"
    text: str
    chunk_index: int
    embedding: Optional[list[float]] = None


class IngestionResult(BaseModel):
    """Summary of a knowledge base ingestion run."""

    total_documents: int
    total_chunks: int
    collection_name: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievedChunk(BaseModel):
    """A single chunk returned by the retrieval step, with its similarity score."""

    chunk_id: str
    source: str
    text: str
    score: float = Field(ge=0.0, le=1.0)


class AgentResponse(BaseModel):
    """Final answer produced by the RAG agent for a support query."""

    query: str
    answer: str
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
