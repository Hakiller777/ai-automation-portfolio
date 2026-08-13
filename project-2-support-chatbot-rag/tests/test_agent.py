"""Tests for src/agent.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import pytest

import src.agent as agent_module
from src.agent import generate_answer
from src.exceptions import AgentError


class TestGenerateAnswer:
    def test_happy_path_returns_cited_answer(self, relevant_chunks, test_settings):
        response = generate_answer("How do refunds work for failed payments?", relevant_chunks, test_settings)
        assert response.answer
        assert response.sources == ["billing.md"]
        assert response.confidence > test_settings.min_confidence_threshold

    # Edge case 1: no chunks retrieved at all
    def test_no_chunks_returns_fallback(self, test_settings):
        response = generate_answer("What is the meaning of life?", [], test_settings)
        assert response.confidence == 0.0
        assert response.sources == []
        assert "don't have enough information" in response.answer.lower()

    # Edge case 2: chunks retrieved but below confidence threshold
    def test_low_confidence_chunks_return_fallback(self, weak_chunks, test_settings):
        response = generate_answer("Something obscure", weak_chunks, test_settings)
        assert response.sources == []
        assert "don't have enough information" in response.answer.lower()

    # Error case: unexpected failure during synthesis is wrapped in AgentError
    def test_synthesis_failure_raises_agent_error(self, relevant_chunks, test_settings, monkeypatch):
        monkeypatch.setattr(
            agent_module, "_synthesize_answer", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        with pytest.raises(AgentError):
            generate_answer("query", relevant_chunks, test_settings)
