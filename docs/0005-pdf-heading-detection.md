# 0005 — PDF heading detection

- **Commit:** (feat): PDF heading detection for structure-aware chunking
- **Date:** 2026-06-17
- **Milestone:** M1 follow-up (makes `structure` usable on real PDFs)

## What
Upgraded the PDF parser to detect headings from font size/weight and emit them as
markdown `#` headings, so the `structure` chunker works on real PDFs the same as
on markdown. Added a self-contained validation that generates a spec-sheet PDF and
checks the full path.

## Why
The M1 decision (docs/0004) made `structure` the default chunker, but it keys on
markdown `#` headings — which real PDFs don't have. Without heading detection,
`structure` silently degraded to recursive on every PDF, losing the section
metadata that justified choosing it. This closes that gap (PROJECT_PLAN §3.1).

## Key decisions
- **Detect in the parser, not the chunker:** the parser reconstructs PDF text as
  lightweight markdown (headings → `#`). The chunker stays format-agnostic — one
  heading convention works for `.md`, `.docx`-derived, and PDF sources.
- **Heuristic from `get_text("dict")`:** modal span size = body text; a short line
  (≤14 words) that is larger than body (or bold at body size) is a heading; bigger
  ratio → higher level. Tunable thresholds.
- **Graceful by construction:** a PDF with no size contrast yields no headings →
  `structure` falls back to recursive. No special-casing needed.

## Validation
`python -m experiments.test_pdf_headings` generates a PDF (18pt title, 13pt bold
section heads, 11pt body, one long section) and confirms:
- title → `#`, section heads → `###`, body plain;
- `structure` chunker emits chunks with the right `section` titles;
- the over-long "Deployment Considerations" section is handled (recursive fallback).

## Honesty caveats
- Heuristic — real-world PDFs (multi-column, tables, inconsistent typography) will
  need threshold tuning and possibly column/table handling.
- Detection is per-page, so a section spanning a page break loses its title on the
  continuation page.
- Small sections packed together take the first section's title (minor citation
  imprecision); could be extended to record all merged titles.

## Follow-ups
- Tune on real PDFs once the real corpus lands.
- Table-aware extraction (pdfplumber/Docling) for spec tables (PROJECT_PLAN §3.1).
