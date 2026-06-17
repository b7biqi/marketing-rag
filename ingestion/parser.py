"""Document parsing → page-level text.

Returns a list of {"page": int, "text": str}. Page is 1 for non-paginated
formats. OCR for scanned PDFs (no text layer) is an M1 task — for now pages
with no extractable text are skipped and reported.
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import docx


def parse_file(path: str | Path) -> list[dict]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".docx":
        return _parse_docx(path)
    if ext in {".txt", ".md"}:
        return _parse_text(path)
    raise ValueError(f"Unsupported file type: {ext} ({path})")


def _parse_pdf(path: Path) -> list[dict]:
    pages: list[dict] = []
    skipped = 0
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                pages.append({"page": i, "text": text})
            else:
                skipped += 1  # likely scanned → needs OCR (M1)
    if skipped:
        print(f"  [parser] {path.name}: {skipped} page(s) had no text layer "
              f"(scanned? OCR pending — M1)")
    return pages


def _parse_docx(path: Path) -> list[dict]:
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return [{"page": 1, "text": text}] if text.strip() else []


def _parse_text(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [{"page": 1, "text": text}] if text.strip() else []
