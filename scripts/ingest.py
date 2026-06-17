"""Ingest a file or directory into the vector store.

Usage:
    python -m scripts.ingest demo_data/ --doc-type spec
    python -m scripts.ingest demo_data/thinkpad_x1_spec.md \
        --doc-type spec --product "ThinkPad X1" --region APAC --version 2025
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.chunking import chunk_pages
from ingestion.indexer import ensure_collection, get_client, index_chunks
from ingestion.parser import parse_file

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def iter_files(path: Path):
    if path.is_dir():
        yield from (p for p in sorted(path.rglob("*")) if p.suffix.lower() in SUPPORTED)
    else:
        yield path


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest documents into Qdrant.")
    ap.add_argument("path", help="File or directory to ingest")
    ap.add_argument("--doc-type", default="unknown", help="spec | brand | compliance | ...")
    ap.add_argument("--product", default="unknown")
    ap.add_argument("--region", default="global")
    ap.add_argument("--version", default="unknown")
    args = ap.parse_args()

    client = get_client()
    ensure_collection(client)

    total_chunks = 0
    for file in iter_files(Path(args.path)):
        print(f"Parsing {file} ...")
        pages = parse_file(file)
        if not pages:
            print("  (no extractable text — skipped)")
            continue
        base_metadata = {
            "doc_id": file.stem,
            "source": file.name,
            "doc_type": args.doc_type,
            "product": args.product,
            "region": args.region,
            "version": args.version,
        }
        chunks = chunk_pages(pages, base_metadata)
        n = index_chunks(client, chunks)
        total_chunks += n
        print(f"  indexed {n} chunks")

    print(f"\nDone. {total_chunks} chunks in collection.")


if __name__ == "__main__":
    main()
