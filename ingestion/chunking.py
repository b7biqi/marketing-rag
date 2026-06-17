"""Chunking: page text → overlapping chunks carrying metadata.

Recursive character splitting for now (respects paragraph/sentence boundaries).
Structure-aware splitting (by heading/section) and token-bounded sizing are the
M1 ablation (PROJECT_PLAN.md §3.3) — this is the measurable baseline.
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings


def chunk_pages(pages: list[dict], base_metadata: dict) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[dict] = []
    for pg in pages:
        for piece in splitter.split_text(pg["text"]):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append({
                "text": piece,
                "metadata": {**base_metadata, "page": pg["page"]},
            })
    return chunks
