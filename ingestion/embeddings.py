"""Embeddings via fastembed (ONNX, no torch).

Provides the dense and sparse vectors that power hybrid retrieval. Models are
lazily loaded and cached. bge dense models get the correct query/passage prefix
automatically through fastembed's query_embed/passage_embed.
"""
from __future__ import annotations

from functools import lru_cache

from fastembed import SparseTextEmbedding, TextEmbedding

from config import settings


@lru_cache(maxsize=1)
def _dense() -> TextEmbedding:
    return TextEmbedding(settings.dense_model)


@lru_cache(maxsize=1)
def _sparse() -> SparseTextEmbedding:
    return SparseTextEmbedding(settings.sparse_model)


def dense_dim() -> int:
    return len(next(iter(_dense().passage_embed(["dimension probe"]))))


def embed_passages_dense(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _dense().passage_embed(texts)]


def embed_query_dense(text: str) -> list[float]:
    return next(iter(_dense().query_embed([text]))).tolist()


def embed_passages_sparse(texts: list[str]):
    """Yields fastembed SparseEmbedding objects (.indices, .values)."""
    return list(_sparse().embed(texts))


def embed_query_sparse(text: str):
    return next(iter(_sparse().query_embed([text])))
