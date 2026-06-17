"""Diagnose PDF pages the parser skips: are they true image/scanned pages (need
OCR), all-boilerplate pages (a filtering artifact, no OCR needed), or blank?

Reports per page: raw text length, # text lines, # lines kept after boilerplate
filtering. Renders only TRUE image pages (no text lines) to ocr_debug/.

    MANIFEST_PATH=corpus/manifest.json python -m experiments.render_notext_pages
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import fitz

from config import settings
from ingestion.corpus import load_manifest
from ingestion.parser import _NOF_RE, _page_lines, _BOILER_SUBSTRINGS

OUT = Path("ocr_debug")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    base = Path(settings.manifest_path).parent
    for entry in load_manifest():
        f = base / entry["file"]
        if f.suffix.lower() != ".pdf":
            continue
        with fitz.open(f) as doc:
            per_page = [_page_lines(p) for p in doc]
            n = len(per_page)
            freq: Counter[str] = Counter()
            for lines in per_page:
                for t in {ln["text"] for ln in lines}:
                    freq[t] += 1
            thr = max(2, (n + 1) // 2)

            def is_boiler(t: str) -> bool:
                if n >= 3 and freq[t] >= thr:
                    return True
                if _NOF_RE.match(t):
                    return True
                low = t.lower()
                return any(s in low for s in _BOILER_SUBSTRINGS)

            print(f"\n### {f.name} ({n} pages)")
            for i, (page, lines) in enumerate(zip(doc, per_page), start=1):
                raw = page.get_text("text").strip()
                kept = [ln for ln in lines if not is_boiler(ln["text"])]
                if not lines:  # TRUE image page
                    pix = page.get_pixmap(dpi=120)
                    dest = OUT / f"{f.stem}_p{i}.png"
                    pix.save(dest)
                    print(f"  p{i}: IMAGE PAGE (no text lines) -> rendered {dest.name}")
                elif not kept:  # all-boilerplate -> filtering artifact
                    print(f"  p{i}: all-boilerplate (raw_len={len(raw)}, lines={len(lines)}) "
                          f"-> skipped by filter, NOT scanned")


if __name__ == "__main__":
    main()
