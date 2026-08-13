"""Vector search: embed a query, fetch top-k chunks, rank by similarity."""

from __future__ import annotations

import chromadb
from loguru import logger

from .config import Settings
from .embeddings import embed_text
from .exceptions import RetrievalError
from .ingestion import get_chroma_collection, load_idf
from .models import RetrievedChunk


def _distance_to_similarity(distance: float) -> float:
    """Convert a ChromaDB cosine distance to a 0-1 similarity score.

    ChromaDB reports cosine distance as `1 - cosine_similarity`. Our vectors
    are TF-IDF weights, which are never negative, so the cosine similarity
    lives in [0, 1] and the distance does too — the similarity is simply
    `1 - distance`.

    Note for anyone tempted to "generalise" this to `1 - distance / 2`:
    that maps the full [-1, 1] cosine range onto [0, 1], which is correct
    only for embeddings that can point in opposing directions. Applied to
    non-negative vectors it compresses every score into [0.5, 1.0], so no
    result can ever fall below a sane confidence threshold and the
    low-confidence fallback in agent.py becomes unreachable.
    """
    similarity = 1.0 - distance
    return max(0.0, min(1.0, similarity))


def retrieve(
    query: str,
    settings: Settings,
    collection: chromadb.Collection | None = None,
) -> list[RetrievedChunk]:
    """Return the top-k most relevant chunks for a support query.

    Returns an empty list for blank queries or an empty/unseeded collection
    rather than raising — callers (agent.py) treat that as "no context found".
    Raises RetrievalError if the vector store query itself fails.
    """
    if not query or not query.strip():
        logger.warning("Retrieval called with empty query — returning no results")
        return []

    try:
        coll = collection or get_chroma_collection(settings)

        if coll.count() == 0:
            logger.warning("Knowledge base collection is empty — run ingestion first")
            return []

        # Same IDF weighting the chunks were indexed under — embedding a
        # query without it would compare vectors on two different scales.
        query_embedding = embed_text(query, settings.embedding_dim, load_idf(settings))

        if not any(query_embedding):
            logger.warning(
                f"Query '{query[:60]}' has no indexable terms after tokenization "
                "— returning no results"
            )
            return []

        n_results = min(settings.top_k, coll.count())

        raw = coll.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        ids = raw["ids"][0]
        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0]
        distances = raw["distances"][0]

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    source=metadata.get("source", "unknown"),
                    text=text,
                    score=_distance_to_similarity(distance),
                )
            )

        chunks.sort(key=lambda c: c.score, reverse=True)
        logger.info(f"Retrieved {len(chunks)} chunks for query: '{query[:60]}'")
        return chunks

    except RetrievalError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Retrieval failed for query '{query[:60]}': {exc}")
        raise RetrievalError(f"Retrieval failed: {exc}") from exc
