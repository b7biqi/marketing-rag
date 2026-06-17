"""Drop and rebuild the vector index from demo_data/manifest.json.

Usage:
    python -m scripts.reindex
"""
from __future__ import annotations

from config import settings
from ingestion.corpus import reindex
from ingestion.indexer import get_client


def main() -> None:
    client = get_client()
    n = reindex(client)
    print(f"Reindexed {n} chunks from {settings.manifest_path}.")


if __name__ == "__main__":
    main()
