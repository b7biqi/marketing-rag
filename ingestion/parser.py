"""Document parsing → page-level text.

Returns a list of {"page": int, "text": str}. Page is 1 for non-paginated
formats.

PDFs: text is reconstructed as lightweight markdown — headings detected from font
size/weight and prefixed with `#` — so the `structure` chunker works on PDFs the
same as on markdown. Repeated page headers/footers (doc title, "PSREF", "N of N",
etc.) are detected across pages and dropped as boilerplate, since on real spec
sheets they otherwise dominate retrieval (diagnosed on the PSREF corpus). Heading
detection + boilerplate filtering are tunable heuristics (PROJECT_PLAN §3.1).
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
import docx

from config import settings

_BOLD_FLAG = 1 << 4
_NOF_RE = re.compile(r"^\d+\s+of\s+\d+$", re.IGNORECASE)
_BOILER_SUBSTRINGS = ("psref", "product specifications reference")
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def parse_file(path: str | Path) -> list[dict]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".docx":
        return _parse_docx(path)
    if ext in {".txt", ".md"}:
        return _parse_text(path)
    if ext in _IMAGE_EXTS:
        return _parse_image(path)
    raise ValueError(f"Unsupported file type: {ext} ({path})")


def _parse_image(path: Path) -> list[dict]:
    """OCR an image file (screenshot, photo, scan)."""
    if not settings.ocr_enabled:
        print(f"  [parser] {path.name}: image file but OCR disabled — skipped")
        return []
    from ingestion.ocr import ocr_image_bytes

    text = ocr_image_bytes(path.read_bytes())
    return [{"page": 1, "text": text}] if text.strip() else []


# --- PDF: line extraction, boilerplate filtering, markdown reconstruction ----

def _span_is_bold(span: dict) -> bool:
    return bool(span.get("flags", 0) & _BOLD_FLAG) or "bold" in span.get("font", "").lower()


def _page_lines(page) -> list[dict]:
    """Extract text lines with size/bold/block, preserving order."""
    out: list[dict] = []
    data = page.get_text("dict")
    for block_idx, block in enumerate(data.get("blocks", [])):
        if block.get("type", 0) != 0:  # skip images
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            out.append({
                "text": text,
                "size": max((s.get("size", 0) for s in spans), default=0),
                "bold": any(_span_is_bold(s) for s in spans),
                "block": block_idx,
            })
    return out


def _parse_pdf(path: Path) -> list[dict]:
    with fitz.open(path) as doc:
        per_page = [_page_lines(page) for page in doc]
        n_pages = len(per_page)

        # A line is boilerplate if it repeats across >= half the pages, or matches
        # a known header/footer pattern (page numbers, PSREF markers).
        freq: Counter[str] = Counter()
        for lines in per_page:
            for text in {ln["text"] for ln in lines}:
                freq[text] += 1
        repeat_threshold = max(2, (n_pages + 1) // 2)

        def is_boiler(text: str) -> bool:
            if n_pages >= 3 and freq[text] >= repeat_threshold:
                return True
            if _NOF_RE.match(text):
                return True
            low = text.lower()
            return any(s in low for s in _BOILER_SUBSTRINGS)

        sizes = [round(ln["size"]) for lines in per_page for ln in lines if not is_boiler(ln["text"])]
        body_size = Counter(sizes).most_common(1)[0][0] if sizes else 11

        pages: list[dict] = []
        image_pages = 0
        for i, lines in enumerate(per_page, start=1):
            kept = [ln for ln in lines if not is_boiler(ln["text"])]
            markdown = _lines_to_markdown(kept, body_size)
            if markdown.strip():
                pages.append({"page": i, "text": markdown})
            elif not lines:
                # True image page (no extractable text). OCR it. All-boilerplate
                # pages (which DO have text, just filtered) are silently skipped —
                # they are not image pages and must not be sent to OCR.
                image_pages += 1
                if settings.ocr_enabled:
                    from ingestion.ocr import ocr_image_bytes

                    pix = doc[i - 1].get_pixmap(dpi=settings.ocr_dpi)
                    text = ocr_image_bytes(pix.tobytes("png"))
                    if text.strip():
                        pages.append({"page": i, "text": text, "ocr": True})

    if image_pages:
        action = "OCR'd" if settings.ocr_enabled else "skipped (OCR disabled)"
        print(f"  [parser] {path.name}: {image_pages} image page(s) with no text layer — {action}")
    return pages


def _lines_to_markdown(lines: list[dict], body_size: int) -> str:
    out: list[str] = []
    prev_block = None
    for ln in lines:
        if prev_block is not None and ln["block"] != prev_block:
            out.append("")  # paragraph boundary between blocks
        prev_block = ln["block"]
        level = _heading_level(ln, body_size)
        out.append(("#" * level + " " + ln["text"]) if level else ln["text"])
    return "\n".join(out)


def _heading_level(line: dict, body_size: int) -> int:
    words = len(line["text"].split())
    if words > 14:
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
