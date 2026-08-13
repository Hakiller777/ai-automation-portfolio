"""Shared pytest fixtures for the project-2 RAG chatbot test suite."""

from pathlib import Path

import pytest

from src.config import Settings
from src.models import RetrievedChunk

_SAMPLE_DOCS = {
    "billing.md": (
        "AcmeCRM billing plans starter growth enterprise. Invoices are "
        "available as a PDF under settings billing invoice history. "
        "Failed payments are retried automatically after three days."
    ),
    "onboarding.md": (
        "AcmeCRM onboarding guide week one create your workspace and "
        "invite your team import existing contacts and deals define your "
        "sales pipeline stages to match your process."
    ),
    "security.md": (
        "AcmeCRM data protection encryption TLS AES two factor "
        "authentication audit logs SOC 2 compliance GDPR data residency."
    ),
}


@pytest.fixture
def kb_dir(tmp_path: Path) -> Path:
    """A temporary knowledge base directory with a handful of markdown docs."""
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    for filename, text in _SAMPLE_DOCS.items():
        (kb / filename).write_text(text, encoding="utf-8")
    return kb


@pytest.fixture
def empty_kb_dir(tmp_path: Path) -> Path:
    """An existing but empty knowledge base directory."""
    kb = tmp_path / "empty_kb"
    kb.mkdir()
    return kb


@pytest.fixture
def test_settings(tmp_path: Path, kb_dir: Path) -> Settings:
    """Settings pointed at an isolated chroma store + temp knowledge base."""
    return Settings(
        chroma_persist_dir=str(tmp_path / "chroma_store"),
        collection_name="test_collection",
        knowledge_base_dir=str(kb_dir),
        chunk_size=20,
        chunk_overlap=5,
        embedding_dim=64,
        top_k=3,
        min_confidence_threshold=0.15,
    )


@pytest.fixture
def relevant_chunks() -> list[RetrievedChunk]:
    """High-confidence retrieval results for agent happy-path tests."""
    return [
        RetrievedChunk(
            chunk_id="c1",
            source="billing.md",
            text="Invoices are available as a PDF under Settings, Billing, Invoice History.",
            score=0.82,
        ),
        RetrievedChunk(
            chunk_id="c2",
            source="billing.md",
            text="Failed payments are retried automatically after three days and again after seven.",
            score=0.71,
        ),
    ]


@pytest.fixture
def weak_chunks() -> list[RetrievedChunk]:
    """Low-confidence retrieval results for agent fallback tests."""
    return [
        RetrievedChunk(chunk_id="c9", source="faq.md", text="Unrelated snippet.", score=0.04),
    ]
