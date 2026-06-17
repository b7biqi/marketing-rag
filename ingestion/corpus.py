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

def load_manifest(manifest_path: str | None = None) -> list[dict]:
    path = Path(manifest_path or settings.manifest_path)
    return json.loads(path.read_text(encoding="utf-8"))


def reindex(client: QdrantClient, manifest_path: str | None = None) -> int:
    """Drop and rebuild the collection from the manifest. Returns chunk count.

    File paths in the manifest are resolved relative to the manifest's directory,
    so the same code serves both the demo corpus and the real PDF corpus.
    """
    path = Path(manifest_path or settings.manifest_path)
    base_dir = path.parent

    if client.collection_exists(settings.collection_name):
        client.delete_collection(settings.collection_name)
    ensure_collection(client)

    total = 0
    for entry in load_manifest(str(path)):
        file = base_dir / entry["file"]
        pages = parse_file(file)
        if not pages:
            continue
        base_metadata = {
            "doc_id": Path(entry["file"]).stem,
            "source": Path(entry["file"]).name,
            "doc_type": entry["doc_type"],
            "product": entry["product"],
            "region": entry.get("region", "global"),
            "version": entry.get("version", "unknown"),
        }
        chunks = chunk_pages(pages, base_metadata)
        total += index_chunks(client, chunks)
    return total
