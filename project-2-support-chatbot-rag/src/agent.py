"""RAG answer generation (simulated Claude responses for demo).

Synthesizes a support answer from the retrieved chunks and reports a
confidence score plus source citations. In production, replace the body
of `_synthesize_answer` with a real Claude API call: pass the query and
the retrieved chunk texts as context and let Claude write the answer.
"""

from __future__ import annotations

import re

from loguru import logger

from .config import Settings
from .exceptions import AgentError
from .models import AgentResponse, RetrievedChunk

_FALLBACK_ANSWER = (
    "I don't have enough information in the AcmeCRM knowledge base to answer "
    "that confidently. Could you rephrase the question, or would you like me "
    "to escalate this to a human support agent?"
)


def _select_context(chunks: list[RetrievedChunk], max_chunks: int = 3) -> list[RetrievedChunk]:
    """Pick the strongest, most diverse chunks to ground the answer in.

    Keeps at most one chunk per source document (adjacent overlapping
    chunks from the same doc otherwise repeat the same sentences) and
    drops chunks that trail the top match by more than 0.25 similarity,
    so a single strong hit doesn't get diluted by weak, unrelated ones.
    """
    if not chunks:
        return []

    top_score = chunks[0].score
    selected: list[RetrievedChunk] = []
    seen_sources: set[str] = set()

    for chunk in chunks:
        if chunk.source in seen_sources:
            continue
        if selected and (top_score - chunk.score) > 0.25:
            continue
        selected.append(chunk)
        seen_sources.add(chunk.source)
        if len(selected) == max_chunks:
            break

    return selected


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_SENTENCE_END = (".", "!", "?", ":")


def _clean_excerpt(text: str, max_sentences: int = 2) -> str:
    """Trim a retrieved chunk down to whole sentences.

    Chunks are fixed-width word windows, so they routinely start and end
    mid-sentence. Splicing them in raw produces answers that open halfway
    through a thought ("...you want to reactivate. Can I export my data?").
    Dropping the partial fragments at both ends costs a little context and
    buys an answer a human can actually read.
    """
    stripped = text.strip()
    if not stripped:
        return ""

    sentences = _SENTENCE_SPLIT.split(stripped)

    # A window that doesn't begin at a sentence or a markdown heading opens
    # with the tail of the previous sentence — drop it.
    if len(sentences) > 1 and not (stripped[0].isupper() or stripped[0] in "#*-"):
        sentences = sentences[1:]

    # Likewise, drop a dangling final fragment when something remains.
    if len(sentences) > 1 and not sentences[-1].rstrip().endswith(_SENTENCE_END):
        sentences = sentences[:-1]

    return " ".join(sentences[:max_sentences]).strip()


def _synthesize_answer(query: str, context: list[RetrievedChunk]) -> str:
    """Build an extractive answer from the selected context chunks.

    Swap for `anthropic.Anthropic().messages.create(...)` with the chunks
    as context in production.
    """
    excerpts = [excerpt for chunk in context if (excerpt := _clean_excerpt(chunk.text))]
    body = " ".join(excerpts) or " ".join(chunk.text.strip() for chunk in context)
    sources = ", ".join(sorted({chunk.source for chunk in context}))
    return (
        f"Based on the AcmeCRM documentation ({sources}): {body}"
    )


def generate_answer(
    query: str,
    chunks: list[RetrievedChunk],
    settings: Settings,
) -> AgentResponse:
    """Generate a support answer with citations and a confidence score.

    Falls back to a canned "not enough information" answer when no chunks
    were retrieved or the best match is below `min_confidence_threshold`.
    Raises AgentError on unexpected failures.
    """
    logger.info(f"Generating answer for query: '{query[:60]}'")

    try:
        if not chunks or chunks[0].score < settings.min_confidence_threshold:
            confidence = chunks[0].score if chunks else 0.0
            logger.warning(
                f"Low-confidence retrieval (best score={confidence:.2f}) — "
                "returning fallback answer"
            )
            return AgentResponse(
                query=query,
                answer=_FALLBACK_ANSWER,
                sources=[],
                confidence=confidence,
            )

        context = _select_context(chunks)
        answer = _synthesize_answer(query, context)
        confidence = sum(c.score for c in context) / len(context)
        sources = sorted({chunk.source for chunk in context})

        logger.info(f"Answer generated — confidence={confidence:.2f}, sources={sources}")
        return AgentResponse(
            query=query,
            answer=answer,
            sources=sources,
            confidence=confidence,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(f"Answer generation failed for query '{query[:60]}': {exc}")
        raise AgentError(f"Answer generation failed: {exc}") from exc
