"""OCR via RapidOCR (PP-OCR models on onnxruntime — no torch; supports Chinese).

Used for the two ingestion paths that have no text layer: image files and
scanned/image PDF pages. The engine is lazily loaded and cached.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def ocr_image_bytes(data: bytes) -> str:
    """Run OCR on raw image bytes (PNG/JPEG/...). Returns recognized text, top-to-
    bottom, or '' if nothing was found."""
    result, _ = _engine()(data)
    if not result:
        return ""
    # result rows are [box, text, score]; keep reading order.
    return "\n".join(row[1] for row in result)
