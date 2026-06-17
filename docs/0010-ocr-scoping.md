# 0010 — OCR: when it's needed + implementation

- **Commit:** (feat): OCR for scanned PDFs and image files (RapidOCR)
- **Date:** 2026-06-18
- **Milestone:** OCR ingestion path

## What
Implemented OCR for the two ingestion paths that have no text layer — **image
files** and **scanned/image PDF pages** — using RapidOCR. Diagnosed first that the
current PSREF corpus has no scanned pages, so validated the path with a controlled
simulated scan (rasterize a digital page → image-only PDF → OCR → compare).

## When is OCR needed?
Not on the current all-digital corpus, but these are core enterprise cases the
system must handle (and a JD requirement):
1. **Scanned PDFs** — images of pages, no text layer (scanned contracts, signed
   compliance forms, faxed/older datasheets).
2. **Image files** — `.png/.jpg/.tiff` with text (screenshots, photographed docs,
   packaging, slide exports).
3. **Image-only pages inside a digital PDF** — scanned appendix, signature page,
   inserted exhibit.

## Key decisions
- **Engine: RapidOCR** (PP-OCR models on onnxruntime) — fits the torch-free stack
  like fastembed (no torch/paddle), bundled models (offline), and **Chinese support**
  for the Mandarin requirement. Tesseract (lighter, weaker) and a VLM (for
  photos/diagrams, not text) are documented alternatives.
- **Trigger only on true image pages** (`not _page_lines(page)`) and image files —
  never on all-boilerplate pages (which have text, just filtered). This is why the
  earlier "OCR pending" message was first corrected (docs scoping) before wiring OCR.
- **OCR output flows through the same pipeline** (chunking → index → retrieve →
  generate) — no special path; an OCR'd page is just another page of text.
- **Config:** `ocr_enabled` (default on) and `ocr_dpi` (render resolution for PDF
  image pages). System deps added to the dev container (`libgl1`, `libglib2.0-0`).

## Validation
`experiments/test_ocr.py` rasterizes a digital PSREF page (X1, page 3) into an
image-only PDF (asserts no text layer), runs it through `parse_file`, and compares:
- **~90% character recovery** (1922 of 2137 chars).
- Content recovered and searchable: "ThinkPad X1 Carbon Gen 13", "Operating System:
  Windows 11 Pro / Fedora Linux / Ubuntu", "Integrated Intel AI Boost up to 48 TOPS".
- Digital corpus reindex unaffected (76 chunks); all-boilerplate pages correctly do
  NOT trigger OCR.

## Honesty caveats
- OCR artifacts: occasional missing spaces ("ProductSpecifications") and misreads
  ("AI"→"Al") — typical; still searchable.
- OCR'd pages bypass the text-layer boilerplate filter, so they include their own
  header/footer text. Minor; contextual chunking still adds product context.
- No scanned pages exist in the current corpus, so this is a validated *capability*
  via a controlled test, not a corpus-level metric. Embedded images inside text
  pages are not yet OCR'd.

## Follow-ups
- Add a scanned/image doc to a demo corpus to show OCR end-to-end through retrieval.
- Engine comparison (RapidOCR vs Tesseract vs VLM) + a Chinese-language test for the
  Mandarin requirement, if/when needed.
- Filter boilerplate from OCR output too.
