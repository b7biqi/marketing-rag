"""Manifest-driven corpus ingestion.

The manifest pins each document's enterprise metadata (doc_type/product/region/
version) so ingestion is reproducible and the evaluation harness can rebuild the
index deterministically. This is what makes re-running ablations honest.
"""
from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import QdrantClient

from config import settings
from ingestion.chunking import chunk_pages
from ingestion.indexer import ensure_collection, index_chunks
from ingestion.parser import parse_file

DEMO_DIR = Path("demo_data")
MANIFEST = DEMO_DIR / "manifest.json"


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def reindex(client: QdrantClient) -> int:
    """Drop and rebuild the collection from the manifest. Returns chunk count."""
    if client.collection_exists(settings.collection_name):
        client.delete_collection(settings.collection_name)
    ensure_collection(client)

    total = 0
    for entry in load_manifest():
        file = DEMO_DIR / entry["file"]
        pages = parse_file(file)
        if not pages:
            continue
        base_metadata = {
            "doc_id": Path(entry["file"]).stem,
            "source": entry["file"],
            "doc_type": entry["doc_type"],
            "product": entry["product"],
            "region": entry.get("region", "global"),
            "version": entry.get("version", "unknown"),
        }
        chunks = chunk_pages(pages, base_metadata)
        total += index_chunks(client, chunks)
    return total
