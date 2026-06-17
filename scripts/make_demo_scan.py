"""Generate a synthetic 'scanned' document (PNG image of text) for the demo corpus.

This gives the demo corpus an image-only document so OCR is exercised end-to-end
(ingest → OCR → chunk → retrieve → answer), not just in a unit test. Content is
synthetic. Run once; the PNG is committed (small, synthetic — no copyright).

    python -m scripts.make_demo_scan
"""
from __future__ import annotations

import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEST = Path("demo_data/scanned/thinkpad_z13_service_bulletin.png")
LINES = [
    "ThinkPad Z13 Gen 2 - Field Service Bulletin",
    "",
    "Recommended thermal paste reapplication interval: 24 months.",
    "Intermittent fan noise is resolved in BIOS version 1.42 or later.",
    "Replacement keyboard service is covered under depot warranty.",
    "Battery health calibration should be run every three months.",
]


def font_path() -> str:
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"):
        if Path(p).exists():
            return p
    hits = glob.glob("/usr/share/fonts/**/NotoSansCJK*", recursive=True)
    if hits:
        return hits[0]
    raise FileNotFoundError("Noto CJK font not found (install fonts-noto-cjk).")


def main() -> None:
    fp = font_path()
    title = ImageFont.truetype(fp, 34)
    body = ImageFont.truetype(fp, 26)
    width = 1100
    height = 70 + sum(50 if line else 22 for line in LINES)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 30
    for i, line in enumerate(LINES):
        if not line:
            y += 22
            continue
        draw.text((40, y), line, fill=(20, 20, 20), font=title if i == 0 else body)
        y += 52 if i == 0 else 44
    DEST.parent.mkdir(parents=True, exist_ok=True)
    img.save(DEST)
    print(f"wrote {DEST} ({DEST.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
