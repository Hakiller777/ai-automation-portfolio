"""Deterministic, offline text embeddings (hashed TF-IDF vectorizer).

No network calls and no model download — keeps the demo fully self-hosted
and dependency-light. In production, swap `embed_text` for a real embedding
model (e.g. an embeddings API or a local sentence-transformers model); every
other module only depends on the `embed_text` / `embed_batch` signatures.

Why TF-IDF and not plain term frequency: with raw term frequencies, common
English words dominate every vector, so *every* query looks moderately
similar to *every* chunk. That makes the retrieval scores useless for
deciding whether the knowledge base actually covers a question. Weighting
each term by its inverse document frequency — and dropping stopwords
outright — lets rare, meaningful terms drive the similarity instead.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Vector width. Must comfortably exceed the corpus vocabulary, otherwise
# unrelated terms collide into the same bucket and manufacture similarity
# between documents that share nothing.
DEFAULT_DIM = 4096

# Dropped before hashing. These carry no topical signal but appear in every
# document, so they inflate similarity between unrelated texts.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a about all also am an and any are as at be because been before being
    between both but by can cannot could did do does doing done down during
    each few for from further get got had has have having he her here hers
    him his how i if in into is it its itself just me more most my no nor not
    of off on once only or other our out over own s same she should so some
    such t than that the their them then there these they this those through
    to too under until up very was we were what when where which while who
    whom why will with would you your yours
    """.split()
)


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on alphanumerics, and drop stopwords."""
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]


def _token_index(token: str, dim: int) -> int:
    """Deterministic hash → vector index (stable across processes/runs)."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % dim


def build_idf(documents: list[str], dim: int = DEFAULT_DIM) -> list[float]:
    """Compute a smoothed inverse-document-frequency weight per hash bucket.

    Called once at ingestion over the whole corpus; the result is persisted
    and reused for every query so documents and queries share one weighting.
    Buckets never seen in the corpus keep the maximum weight, which means an
    out-of-vocabulary query term adds to the query's magnitude without
    matching anything — correctly pushing its similarity down.
    """
    total_docs = len(documents)
    if total_docs == 0:
        return [1.0] * dim

    doc_freq = [0] * dim
    for document in documents:
        for index in {_token_index(token, dim) for token in _tokenize(document)}:
            doc_freq[index] += 1

    return [
        math.log((1.0 + total_docs) / (1.0 + freq)) + 1.0
        for freq in doc_freq
    ]


def embed_text(
    text: str,
    dim: int = DEFAULT_DIM,
    idf: list[float] | None = None,
) -> list[float]:
    """Embed a single string as an L2-normalized, hashed TF-IDF vector.

    Uses sublinear term frequency (1 + log tf) so a word repeated ten times
    does not count ten times as much as one mentioned once. When `idf` is
    omitted the vector falls back to plain term frequency, which is only
    appropriate when no corpus statistics exist yet.

    Empty or whitespace-only text (or text that is all stopwords) returns a
    zero vector.
    """
    vector = [0.0] * dim
    tokens = _tokenize(text)

    if not tokens:
        return vector

    counts: dict[int, int] = {}
    for token in tokens:
        index = _token_index(token, dim)
        counts[index] = counts.get(index, 0) + 1

    for index, count in counts.items():
        weight = 1.0 + math.log(count)
        if idf is not None and index < len(idf):
            weight *= idf[index]
        vector[index] = weight

    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector


def embed_batch(
    texts: list[str],
    dim: int = DEFAULT_DIM,
    idf: list[float] | None = None,
) -> list[list[float]]:
    """Embed a batch of strings. Order-preserving."""
    return [embed_text(text, dim, idf) for text in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors of equal length.

    Returns 0.0 for zero-magnitude vectors instead of raising.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
