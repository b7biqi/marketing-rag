"""Qdrant collection management + chunk indexing.

Collection holds a named dense vector ("dense", cosine) and a named sparse
vector ("sparse", BM25 with IDF), plus keyword payload indexes on the enterprise
metadata fields used for filtering (PROJECT_PLAN.md §3.5–3.6).
"""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient, models

from config import settings
from ingestion.embeddings import (
    dense_dim,
    embed_passages_dense,
    embed_passages_sparse,
)

FILTER_FIELDS = ["doc_id", "source", "doc_type", "product", "region", "version"]


def get_client() -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=settings.qdrant_path)


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(settings.collection_name):
        return
    client.create_collection(
        collection_name=settings.collection_name,
        vectors_config={
            "dense": models.VectorParams(
                size=dense_dim(), distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )
    for field in FILTER_FIELDS:
        client.create_payload_index(
            collection_name=settings.collection_name,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def index_chunks(client: QdrantClient, chunks: list[dict]) -> int:
    if not chunks:
        return 0
    texts = [c["text"] for c in chunks]
    dense = embed_passages_dense(texts)
    sparse = embed_passages_sparse(texts)

    points = []
    for chunk, dvec, svec in zip(chunks, dense, sparse):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dvec,
                    "sparse": models.SparseVector(
                        indices=svec.indices.tolist(),
                        values=svec.values.tolist(),
                    ),
                },
                payload={"text": chunk["text"], **chunk["metadata"]},
            )
        )
    client.upsert(collection_name=settings.collection_name, points=points)
    return len(points)
