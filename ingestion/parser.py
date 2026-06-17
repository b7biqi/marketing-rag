"""Document parsing → page-level text.

Returns a list of {"page": int, "text": str}. Page is 1 for non-paginated
formats.

PDFs: text is reconstructed as lightweight markdown — headings are detected from
font size/weight and prefixed with `#` — so the `structure` chunker (which keys
on `#` headings) works on real PDFs the same as on markdown docs. Heading
detection is a tunable heuristic (PROJECT_PLAN §3.1/§3.3). Pages with no text
layer are skipped (scanned → OCR is an M-later task).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
import docx

_BOLD_FLAG = 1 << 4  # PyMuPDF span flag bit for bold


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


# --- PDF with heading detection -------------------------------------------

def _parse_pdf(path: Path) -> list[dict]:
    pages: list[dict] = []
    skipped = 0
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            markdown = _page_to_markdown(page)
            if markdown.strip():
                pages.append({"page": i, "text": markdown})
            else:
                skipped += 1  # likely scanned → needs OCR (later milestone)
    if skipped:
        print(f"  [parser] {path.name}: {skipped} page(s) had no text layer "
              f"(scanned? OCR pending)")
    return pages


def _span_is_bold(span: dict) -> bool:
    return bool(span.get("flags", 0) & _BOLD_FLAG) or "bold" in span.get("font", "").lower()


def _page_to_markdown(page) -> str:
    """Reconstruct page text as markdown, prefixing detected headings with `#`."""
    data = page.get_text("dict")
    lines: list[dict] = []
    sizes: list[int] = []
    for block_idx, block in enumerate(data.get("blocks", [])):
        if block.get("type", 0) != 0:  # 0 = text block; skip images
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            max_size = max((s.get("size", 0) for s in spans), default=0)
            bold = any(_span_is_bold(s) for s in spans)
            lines.append({"text": text, "size": max_size, "bold": bold, "block": block_idx})
            sizes.append(round(max_size))

    if not sizes:
        return ""

    body_size = Counter(sizes).most_common(1)[0][0]  # modal size = body text

    out: list[str] = []
    prev_block = None
    for ln in lines:
        if prev_block is not None and ln["block"] != prev_block:
            out.append("")  # blank line between blocks → paragraph boundary
        prev_block = ln["block"]
        level = _heading_level(ln, body_size)
        out.append(("#" * level + " " + ln["text"]) if level else ln["text"])
    return "\n".join(out)


def _heading_level(line: dict, body_size: int) -> int:
    """0 = body; 1-3 = heading level. Heuristic: short lines that are larger than
    body text (or bold at body size) are headings; bigger → higher level."""
    words = len(line["text"].split())
    if words > 14:  # too long to be a heading
        return 0
    ratio = line["size"] / body_size if body_size else 1.0
    if ratio >= 1.5:
        return 1
    if ratio >= 1.25:
        return 2
    if ratio >= 1.12 or (line["bold"] and ratio >= 0.98 and words <= 10):
        return 3
    return 0


# --- other formats ---------------------------------------------------------

def _parse_docx(path: Path) -> list[dict]:
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return [{"page": 1, "text": text}] if text.strip() else []


def _parse_text(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [{"page": 1, "text": text}] if text.strip() else []
