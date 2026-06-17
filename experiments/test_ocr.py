"""Validate the OCR path on a controlled "scanned" page.

The real corpus is all-digital, so to exercise OCR we take a known digital PSREF
page, rasterize it into an image-only PDF (no text layer — a simulated scan), then
run it through parse_file (which routes image pages to OCR) and compare the
recovered text against the original digital text.

    MANIFEST_PATH=corpus/manifest.json python -m experiments.test_ocr
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import fitz

from config import settings
from ingestion.corpus import load_manifest
from ingestion.parser import parse_file

PAGE_INDEX = 2  # a content-rich spec page
SAMPLE_TERMS = ["memory", "processor", "display", "battery", "weight",
                "thinkpad", "carbon", "intel"]


def _make_image_pdf(src_pdf: Path, page_index: int, out_pdf: Path, dpi: int = 200) -> None:
    with fitz.open(src_pdf) as doc:
        pix = doc[page_index].get_pixmap(dpi=dpi)
    out = fitz.open()
    page = out.new_page(width=pix.width * 72 / dpi, height=pix.height * 72 / dpi)
    page.insert_image(page.rect, pixmap=pix)
    out.save(str(out_pdf))
    out.close()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def main() -> None:
    base = Path(settings.manifest_path).parent
    src = base / load_manifest()[0]["file"]  # X1 spec
    with fitz.open(src) as doc:
        original = doc[PAGE_INDEX].get_text("text")

    tmp = Path(tempfile.mkdtemp())
    img_pdf = tmp / "scanned_page.pdf"
    _make_image_pdf(src, PAGE_INDEX, img_pdf)

    with fitz.open(img_pdf) as d:
        assert not d[0].get_text("text").strip(), "expected an image-only page (no text layer)"

    pages = parse_file(img_pdf)
    ocr_text = pages[0]["text"] if pages else ""

    recovered = [t for t in SAMPLE_TERMS if t in _norm(ocr_text)]
    print(f"Source: {src.name} page {PAGE_INDEX + 1}")
    print(f"Original text chars: {len(original)}   OCR text chars: {len(ocr_text)}")
    print(f"Sample terms recovered: {len(recovered)}/{len(SAMPLE_TERMS)} -> {recovered}")
    print("\n--- OCR output (first 700 chars) ---")
    print(ocr_text[:700])


if __name__ == "__main__":
    main()
