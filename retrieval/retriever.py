"""Two-stage retrieval: hybrid (dense + sparse, RRF fusion) → cross-encoder rerank.

PROJECT_PLAN.md §3.7–3.8. Each stage is separable so the agent can call hybrid
search directly, and so on/off ablations are easy to measure.
"""
from __future__ import annotations

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import QdrantClient, models

from config import settings
from ingestion.embeddings import embed_query_dense, embed_query_sparse
from ingestion.indexer import get_client


@lru_cache(maxsize=1)
def _reranker() -> TextCrossEncoder:
    return TextCrossEncoder(settings.reranker_model)


def _build_filter(filters: dict | None) -> models.Filter | None:
    if not filters:
        return None
    must = [
        models.FieldCondition(key=k, match=models.MatchValue(value=v))
        for k, v in filters.items()
        if v is not None
    ]
    return models.Filter(must=must) if must else None


def hybrid_search(
    query: str,
    top_n: int | None = None,
    filters: dict | None = None,
    client: QdrantClient | None = None,
) -> list[models.ScoredPoint]:
    """Dense + sparse candidates fused with Reciprocal Rank Fusion."""
    top_n = top_n or settings.top_n
    client = client or get_client()
    qfilter = _build_filter(filters)
    sparse = embed_query_sparse(query)

    result = client.query_points(
        collection_name=settings.collection_name,
        prefetch=[
            models.Prefetch(
                query=embed_query_dense(query),
                using="dense",
                limit=top_n,
                filter=qfilter,
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse.indices.tolist(),
                    values=sparse.values.tolist(),
                ),
                using="sparse",
                limit=top_n,
                filter=qfilter,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_n,
        with_payload=True,
    )
    return result.points


def rerank(
    query: str, points: list[models.ScoredPoint], top_k: int | None = None
) -> list[models.ScoredPoint]:
    top_k = top_k or settings.top_k
    if not points:
        return []
    docs = [p.payload["text"] for p in points]
    scores = list(_reranker().rerank(query, docs))
    ranked = sorted(zip(points, scores), key=lambda pair: pair[1], reverse=True)
    return [p for p, _ in ranked[:top_k]]


def retrieve(
    query: str, filters: dict | None = None, top_k: int | None = None
) -> list[models.ScoredPoint]:
    """End-to-end: hybrid search then rerank to the top_k chunks."""
    candidates = hybrid_search(query, filters=filters)
    return rerank(query, candidates, top_k=top_k)
