"""Semantic menu search using TF-IDF for Vietnamese food queries.

Simple RAG pipeline: precompute TF-IDF vectors for all restaurant menus,
then cosine-match against user query at request time. Zero external deps.
"""

import logging
import math
import re
import unicodedata
from collections import Counter

from src.schemas import Restaurant

logger = logging.getLogger("vindine.menu_search")

_idf: dict[str, float] = {}
_doc_vectors: dict[str, Counter] = {}
_built = False


def _normalize(text: str) -> str:
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def _tokenize(text: str) -> list[str]:
    text = _normalize(text)
    tokens = re.findall(r"[a-z0-9]+", text)
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return tokens + bigrams


def _build_menu_text(r: Restaurant) -> str:
    parts = [
        r.name,
        " ".join(r.cuisine_types),
        " ".join(r.menu_tags),
        " ".join(r.dietary_tags),
        " ".join(r.best_for),
    ]
    return " ".join(parts)


def build_index(restaurants: list[Restaurant]) -> None:
    """Precompute TF-IDF index for all restaurant menus."""
    global _idf, _doc_vectors, _built
    if _built:
        return

    doc_freq: Counter = Counter()
    n = len(restaurants)

    for r in restaurants:
        text = _build_menu_text(r)
        tokens = _tokenize(text)
        tf = Counter(tokens)
        _doc_vectors[r.id] = tf
        for token in set(tokens):
            doc_freq[token] += 1

    _idf = {token: math.log(n / df) for token, df in doc_freq.items()}
    _built = True
    logger.info("Built TF-IDF index for %d restaurants, %d terms", n, len(_idf))


def _tfidf_vector(tf: Counter) -> dict[str, float]:
    return {token: count * _idf.get(token, 0) for token, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_search(
    query: str,
    restaurants: list[Restaurant],
    top_k: int = 10,
) -> dict[str, float]:
    """Return restaurant_id -> similarity score (0.0-1.0) for a food query.

    Uses TF-IDF cosine similarity against precomputed menu index.
    """
    if not query.strip():
        return {}

    if not _built:
        build_index(restaurants)

    query_tf = Counter(_tokenize(query))
    query_vec = _tfidf_vector(query_tf)

    scores: list[tuple[str, float]] = []
    for rid, doc_tf in _doc_vectors.items():
        doc_vec = _tfidf_vector(doc_tf)
        sim = _cosine(query_vec, doc_vec)
        if sim > 0:
            scores.append((rid, sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    result = {rid: score for rid, score in scores[:top_k]}

    if scores:
        logger.info("Menu search '%s': top=%s (%.3f), %d matches", query[:40], scores[0][0], scores[0][1], len(scores))
    return result
