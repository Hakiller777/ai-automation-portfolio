"""End-to-end retrieval quality gates against the real knowledge base.

The rest of the suite exercises each module in isolation with hand-built
fixtures. That left a hole: `test_agent.py` proves the low-confidence
fallback works when handed weak chunks, but nothing proved that real
retrieval can ever *produce* weak chunks. It could not — the score
conversion had a floor of 0.5 against a threshold of 0.15, so the fallback
was unreachable in production while the unit test stayed green.

These tests close that hole by running the real pipeline over the real
knowledge base, and they double as the evaluation set that justifies
`min_confidence_threshold`.

The two failure modes are deliberately not weighted equally:

  * Answering a question the knowledge base does not cover is a hard
    failure — it produces a confident, cited, wrong answer. Asserted at 100%.
  * Escalating a question we could have answered is a soft failure — a human
    picks up the ticket. Asserted as a coverage floor, not perfection.
"""

import re
from pathlib import Path

import pytest

from src.agent import generate_answer
from src.config import Settings
from src.ingestion import ingest_documents
from src.retrieval import retrieve

PROJECT_DIR = Path(__file__).resolve().parent.parent
REAL_KB_DIR = PROJECT_DIR / "data" / "knowledge_base"

# The configuration users actually run: the quickstart copies it to .env,
# docker compose injects it, and DEPLOYMENT.md mirrors it.
SHIPPED_ENV_FILE = PROJECT_DIR / ".env.example"

# Questions the bundled AcmeCRM knowledge base genuinely covers.
IN_SCOPE_QUESTIONS = [
    "How do I export my contacts from AcmeCRM?",
    "Why is my calendar not syncing?",
    "How do I create a custom field?",
    "What permissions does an admin role have?",
    "How do I enable two-factor authentication?",
    "How do I import contacts from a CSV file?",
    "How do I change my billing plan?",
    "What does the mobile app support offline?",
    "How do I build a report or dashboard?",
    "How do I set up an automation workflow?",
    "What are the stages in the deal pipeline?",
    "How do I connect a third-party integration?",
    "What is the support response time?",
    "How do I get started onboarding my team?",
    "Why are my email notifications not arriving?",
]

# Questions the knowledge base does not cover. The agent must escalate on
# every one of these rather than assembling an answer out of loose matches.
OUT_OF_SCOPE_QUESTIONS = [
    "What is your refund policy for enterprise contracts in Japan?",
    "zxqw plutonium bicycle quarterly",
    "How do I bake a chocolate cake?",
    "What is the capital of Mongolia?",
    "Can I book a flight through your platform?",
    "Do you offer legal advice on employment contracts?",
    "What is the weather forecast for tomorrow?",
    "How do I train a neural network on my laptop?",
]

# Share of in-scope questions that must clear the threshold. Below 1.0 on
# purpose: a bag-of-words retriever will always miss some phrasings, and
# forcing 100% here would mean lowering the threshold until out-of-scope
# questions start getting answered — trading a safe failure for a dangerous one.
MIN_IN_SCOPE_COVERAGE = 0.80


@pytest.fixture(scope="module")
def live_settings(tmp_path_factory) -> Settings:
    """Shipped settings (`.env.example`) against the real KB, in a throwaway vector store.

    Evaluating the file users copy, not the code defaults, is deliberate: the
    retrieval rewrite once moved `embedding_dim` and `min_confidence_threshold`
    in `src/config.py` while `.env.example` kept the old values, and anyone who
    followed the quickstart got an agent that answered every out-of-scope
    question. Loading the shipped file makes that drift fail here.
    """
    assert SHIPPED_ENV_FILE.is_file(), "the gate must evaluate the shipped .env.example"
    store = tmp_path_factory.mktemp("chroma_live")
    return Settings(
        _env_file=SHIPPED_ENV_FILE,
        chroma_persist_dir=str(store),
        collection_name="retrieval_quality_eval",
        knowledge_base_dir=str(REAL_KB_DIR),
    )


@pytest.fixture(scope="module")
def ingested(live_settings: Settings) -> Settings:
    """Index the real knowledge base once for the whole module."""
    result = ingest_documents(live_settings)
    assert result.total_chunks > 0
    return live_settings


def _top_score(question: str, settings: Settings) -> float:
    chunks = retrieve(question, settings)
    return chunks[0].score if chunks else 0.0


class TestRetrievalQuality:
    def test_out_of_scope_questions_never_clear_the_threshold(self, ingested: Settings):
        """Hard gate: the KB does not cover these, so none may be answered."""
        leaks = [
            (q, score)
            for q in OUT_OF_SCOPE_QUESTIONS
            if (score := _top_score(q, ingested)) >= ingested.min_confidence_threshold
        ]
        assert not leaks, (
            "Out-of-scope questions scored above the confidence threshold "
            f"({ingested.min_confidence_threshold}) and would receive a "
            f"confident, cited answer: {leaks}"
        )

    def test_in_scope_questions_mostly_clear_the_threshold(self, ingested: Settings):
        """Coverage gate: the KB covers these, so most must be answered."""
        scores = {q: _top_score(q, ingested) for q in IN_SCOPE_QUESTIONS}
        answered = [q for q, s in scores.items() if s >= ingested.min_confidence_threshold]
        coverage = len(answered) / len(IN_SCOPE_QUESTIONS)

        assert coverage >= MIN_IN_SCOPE_COVERAGE, (
            f"Only {coverage:.0%} of in-scope questions cleared the threshold "
            f"(floor is {MIN_IN_SCOPE_COVERAGE:.0%}). Misses: "
            f"{ {q: round(s, 4) for q, s in scores.items() if q not in answered} }"
        )

    def test_scores_can_fall_below_the_threshold(self, ingested: Settings):
        """Regression guard for the score-conversion bug.

        `_distance_to_similarity` once mapped cosine distance as
        `1 - distance/2`, which floors non-negative vectors at 0.5 and made
        every threshold below 0.5 unreachable. Any conversion that cannot
        produce a low score for obvious nonsense fails here.
        """
        score = _top_score("zxqw plutonium bicycle quarterly", ingested)
        assert score < 0.5, (
            f"Nonsense query scored {score:.4f}. Retrieval scores appear to be "
            "compressed into a narrow high range, which makes the low-confidence "
            "fallback unreachable."
        )


class TestFallbackEndToEnd:
    def test_out_of_scope_question_escalates_through_the_real_pipeline(
        self, ingested: Settings
    ):
        """The fallback must be reachable from a real query, not just unit tests."""
        question = "What is your refund policy for enterprise contracts in Japan?"
        chunks = retrieve(question, ingested)
        response = generate_answer(question, chunks, ingested)

        assert response.sources == []
        assert "don't have enough information" in response.answer.lower()

    def test_in_scope_question_answers_with_citations(self, ingested: Settings):
        """The happy path still works end to end after the fallback fix."""
        question = "How do I change my billing plan?"
        chunks = retrieve(question, ingested)
        response = generate_answer(question, chunks, ingested)

        assert response.sources, "Expected at least one cited source document"
        assert response.confidence >= ingested.min_confidence_threshold
        assert "don't have enough information" not in response.answer.lower()
        assert not re.search(r"(^|\s)#{1,6}\s", response.answer), "Markdown headings leaked into the answer"
