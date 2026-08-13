"""Tests for src/ingestion.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

from pathlib import Path

import pytest

from src.exceptions import IngestionError
from src.ingestion import chunk_text, get_chroma_collection, ingest_documents, load_knowledge_base


class TestChunkText:
    def test_happy_path_produces_overlapping_windows(self):
        """A long text is split into multiple chunks that overlap by `overlap` words."""
        text = " ".join(f"word{i}" for i in range(50))
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1
        # last words of chunk N should reappear at the start of chunk N+1
        first_tail = chunks[0].split()[-5:]
        second_head = chunks[1].split()[:5]
        assert first_tail == second_head

    # Edge case 1: empty input
    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("", chunk_size=20, overlap=5) == []
        assert chunk_text("   ", chunk_size=20, overlap=5) == []

    # Edge case 2: overlap >= chunk_size must not infinite-loop
    def test_overlap_greater_than_chunk_size_terminates(self):
        text = " ".join(f"word{i}" for i in range(30))
        chunks = chunk_text(text, chunk_size=10, overlap=15)
        assert len(chunks) > 0  # completes without hanging


class TestLoadKnowledgeBase:
    def test_happy_path_loads_all_markdown_docs(self, kb_dir: Path):
        docs = load_knowledge_base(kb_dir)
        assert len(docs) == 3
        assert all(text for _, text in docs)

    # Error case: missing directory
    def test_missing_directory_raises_ingestion_error(self, tmp_path: Path):
        with pytest.raises(IngestionError):
            load_knowledge_base(tmp_path / "does-not-exist")

    def test_empty_directory_raises_ingestion_error(self, empty_kb_dir: Path):
        with pytest.raises(IngestionError):
            load_knowledge_base(empty_kb_dir)


class TestIngestDocuments:
    def test_happy_path_stores_chunks_in_collection(self, test_settings):
        result = ingest_documents(test_settings)
        assert result.total_documents == 3
        assert result.total_chunks > 0

        collection = get_chroma_collection(test_settings)
        assert collection.count() == result.total_chunks

    def test_reingestion_replaces_existing_chunks(self, test_settings):
        """Running ingestion twice must not duplicate chunks in the collection."""
        first = ingest_documents(test_settings)
        second = ingest_documents(test_settings)
        collection = get_chroma_collection(test_settings)
        assert first.total_chunks == second.total_chunks
        assert collection.count() == second.total_chunks
