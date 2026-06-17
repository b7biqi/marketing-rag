"""Query the RAG system: hybrid retrieve → rerank → grounded generation.

Usage:
    python -m scripts.query "What is the battery life of the ThinkPad X1?"
    python -m scripts.query "Write a LinkedIn post on security for CIOs" \
        --task --doc-type compliance
    python -m scripts.query "..." --no-generate     # retrieval only
"""
from __future__ import annotations

import argparse

from llm.generator import generate, sources_table
from retrieval.retriever import retrieve


def main() -> None:
    ap = argparse.ArgumentParser(description="Query the marketing RAG system.")
    ap.add_argument("query", help="Question or content request")
    ap.add_argument("--task", action="store_true",
                    help="Treat the query as a content-generation instruction")
    ap.add_argument("--doc-type", default=None, help="Filter by doc_type")
    ap.add_argument("--product", default=None, help="Filter by product")
    ap.add_argument("--region", default=None, help="Filter by region")
    ap.add_argument("--no-generate", action="store_true",
                    help="Show retrieved chunks only, skip the LLM")
    ap.add_argument("--top-k", type=int, default=None, help="Number of chunks to retrieve")
    args = ap.parse_args()

    filters = {k: v for k, v in {
        "doc_type": args.doc_type,
        "product": args.product,
        "region": args.region,
    }.items() if v}

    points = retrieve(args.query, filters=filters or None, top_k=args.top_k)

    if not points:
        print("No results. Have you ingested any documents?")
        return

    if args.no_generate:
        print("\n=== Retrieved chunks ===")
        for i, p in enumerate(points, start=1):
            md = p.payload or {}
            print(f"\n[{i}] {md.get('source')} (p.{md.get('page')}, {md.get('doc_type')})")
            print(md.get("text", "")[:500])
        return

    answer = generate(args.query, points, task=args.query if args.task else None)
    print("\n=== Answer ===\n")
    print(answer)
    print("\n=== Sources ===")
    for s in sources_table(points):
        sec = f", {s['section']}" if s["section"] else ""
        print(f"  [{s['index']}] {s['source']} (p.{s['page']}{sec}, {s['doc_type']})")


if __name__ == "__main__":
    main()
