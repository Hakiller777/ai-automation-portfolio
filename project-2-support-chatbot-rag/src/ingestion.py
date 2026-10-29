"""Knowledge base ingestion: load docs → chunk → embed → store in ChromaDB.

No external API calls — embeddings are produced by the deterministic
TF-IDF vectorizer in `embeddings.py`, so ingestion runs fully offline.

Ingestion also computes the corpus IDF weights and persists them next to the
vector store. Retrieval loads the same weights, so a query and the indexed
chunks are always embedded under one consistent weighting.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import chromadb
from loguru import logger

from .config import Settings
from .embeddings import build_idf, embed_batch
from .exceptions import IngestionError
from .models import DocumentChunk, IngestionResult

IDF_FILENAME = "idf.json"

_WORD = re.compile(r"\S+")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word-count windows.

    Word counts decide where each window starts and ends, but the window keeps
    the source's own line breaks, so markdown structure (headings, list items)
    survives into the chunk and the answer step can tell a heading from prose.

    Returns an empty list for blank input. `overlap` must be smaller than
    `chunk_size` or the sliding window never advances.
    """
    spans = [match.span() for match in _WORD.finditer(text)]
    if not spans:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size - 1)

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(spans):
        window = spans[start : start + chunk_size]
        chunks.append(text[window[0][0] : window[-1][1]])
        start += step

    return chunks


def load_knowledge_base(kb_dir: Path) -> list[tuple[str, str]]:
    """Load every `.md` file in `kb_dir` as (filename, text) pairs.

    Raises IngestionError if the directory does not exist or contains no
    markdown documents.
    """
    if not kb_dir.exists() or not kb_dir.is_dir():
        raise IngestionError(f"Knowledge base directory not found: {kb_dir}")

    docs: list[tuple[str, str]] = []
    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append((path.name, text))
        else:
            logger.warning(f"Skipping empty knowledge base document: {path.name}")

    if not docs:
        raise IngestionError(f"No markdown documents found in {kb_dir}")

    logger.info(f"Loaded {len(docs)} knowledge base documents from {kb_dir}")
    return docs


def get_chroma_collection(settings: Settings) -> chromadb.Collection:
    """Get or create the persistent ChromaDB collection used for retrieval.

    We pass our own embeddings on every add/query call, so no embedding
    function is registered on the collection.
    """
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def idf_path(settings: Settings) -> Path:
    """Location of the persisted corpus IDF weights."""
    return Path(settings.chroma_persist_dir) / IDF_FILENAME


def save_idf(settings: Settings, idf: list[float]) -> None:
    """Persist corpus IDF weights alongside the vector store."""
    path = idf_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(idf), encoding="utf-8")
    logger.info(f"Saved IDF weights ({len(idf)} buckets) to {path}")


def load_idf(settings: Settings) -> list[float] | None:
    """Load corpus IDF weights, or None if the index has not been built.

    Returns None rather than raising so retrieval degrades to plain term
    frequency instead of failing outright on an unbuilt index.
    """
    path = idf_path(settings)
    if not path.exists():
        logger.warning(f"No IDF weights at {path} — run ingestion to build the index")
        return None

    try:
        idf = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error(f"Could not read IDF weights from {path}: {exc}")
        return None

    if not isinstance(idf, list) or len(idf) != settings.embedding_dim:
        logger.error(
            f"IDF weights at {path} have length {len(idf) if isinstance(idf, list) else '?'}, "
            f"expected {settings.embedding_dim} — re-run ingestion"
        )
        return None

    return idf


def ingest_documents(settings: Settings, kb_dir: Path | None = None) -> IngestionResult:
    """Chunk, embed, and store every document in the knowledge base.

    The collection is cleared and rebuilt on each run so re-ingestion is
    idempotent. Raises IngestionError on failure.
    """
    target_dir = kb_dir or Path(settings.knowledge_base_dir)
    logger.info(f"Starting knowledge base ingestion from {target_dir}")

    try:
        docs = load_knowledge_base(target_dir)
        collection = get_chroma_collection(settings)

        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)

        all_chunks: list[DocumentChunk] = []
        for filename, text in docs:
            pieces = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            for idx, piece in enumerate(pieces):
                all_chunks.append(
                    DocumentChunk(source=filename, text=piece, chunk_index=idx)
                )

        if not all_chunks:
            raise IngestionError("Chunking produced zero chunks from the knowledge base")

        # IDF is computed over the chunks that are actually indexed, so the
        # weights match exactly what retrieval searches over.
        chunk_texts = [c.text for c in all_chunks]
        idf = build_idf(chunk_texts, settings.embedding_dim)
        save_idf(settings, idf)

        embeddings = embed_batch(chunk_texts, settings.embedding_dim, idf)

        collection.add(
            ids=[c.id for c in all_chunks],
            embeddings=embeddings,
            documents=[c.text for c in all_chunks],
            metadatas=[{"source": c.source, "chunk_index": c.chunk_index} for c in all_chunks],
        )

        result = IngestionResult(
            total_documents=len(docs),
            total_chunks=len(all_chunks),
            collection_name=settings.collection_name,
        )
        logger.info(
            f"Ingestion complete — {result.total_documents} docs, "
            f"{result.total_chunks} chunks stored in '{result.collection_name}'"
        )
        return result

    except IngestionError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Ingestion failed: {exc}")
        raise IngestionError(f"Ingestion failed: {exc}") from exc


if __name__ == "__main__":
    from .config import settings, setup_logging

    setup_logging(settings.log_level)
    ingest_documents(settings)
