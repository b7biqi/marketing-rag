"""Chinese-language OCR test (Mandarin requirement).

Renders a Chinese spec bulletin to an image and runs it through RapidOCR (whose
default PP-OCR model recognizes Chinese + English), verifying the Chinese text and
numbers are recovered.

    python -m experiments.test_ocr_chinese
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from ingestion.ocr import ocr_image_bytes
from scripts.make_demo_scan import font_path

LINES = [
    "联想 ThinkPad 维护公告",
    "电池续航时间最长可达 18 小时",
    "推荐的固件基线版本为 2.4.1",
    "保修期为三年",
]
EXPECT = ["电池", "小时", "18", "2.4.1", "保修"]


def main() -> None:
    fp = font_path()
    title = ImageFont.truetype(fp, 38)
    body = ImageFont.truetype(fp, 30)
    width = 900
    height = 50 + len(LINES) * 60
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 20
    for i, line in enumerate(LINES):
        draw.text((30, y), line, fill=(0, 0, 0), font=title if i == 0 else body)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    text = ocr_image_bytes(buf.getvalue())
    flat = text.replace(" ", "")
    found = [e for e in EXPECT if e in text or e in flat]

    print("--- OCR output ---")
    print(text)
    print(f"\nExpected tokens recovered: {len(found)}/{len(EXPECT)} -> {found}")


if __name__ == "__main__":
    main()
