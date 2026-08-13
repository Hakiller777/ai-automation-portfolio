"""Tests for src/retrieval.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import pytest

from src.exceptions import RetrievalError
from src.ingestion import get_chroma_collection, ingest_documents
from src.retrieval import retrieve


class TestRetrieve:
    def test_happy_path_returns_ranked_chunks(self, test_settings):
        ingest_documents(test_settings)
        results = retrieve("How do I update my payment method for billing?", test_settings)

        assert len(results) > 0
        assert results[0].score >= results[-1].score  # sorted descending
        assert any(r.source == "billing.md" for r in results)

    # Edge case 1: empty query
    def test_empty_query_returns_no_results(self, test_settings):
        ingest_documents(test_settings)
        assert retrieve("", test_settings) == []
        assert retrieve("   ", test_settings) == []

    # Edge case 2: querying before ingestion (empty collection)
    def test_empty_collection_returns_no_results(self, test_settings):
        results = retrieve("What is the onboarding process?", test_settings)
        assert results == []

    # Error case: underlying vector store query raises
    def test_query_failure_raises_retrieval_error(self, test_settings, monkeypatch):
        ingest_documents(test_settings)
        collection = get_chroma_collection(test_settings)

        def _boom(*args, **kwargs):
            raise RuntimeError("chroma down")

        # Collection is a pydantic model — patch the class method, not the instance.
        monkeypatch.setattr(type(collection), "query", _boom)
        with pytest.raises(RetrievalError):
            retrieve("onboarding", test_settings, collection=collection)
