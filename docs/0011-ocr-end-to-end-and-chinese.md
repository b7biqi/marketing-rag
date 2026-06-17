# 0011 — OCR end-to-end through retrieval + Chinese OCR

- **Commit:** (feat): OCR end-to-end demo + Chinese OCR test
- **Date:** 2026-06-18
- **Milestone:** OCR validation (full pipeline + multilingual)

## What
Added a synthetic **scanned document** (a PNG of a service bulletin) to the demo
corpus plus a golden question whose answer exists only in that image, so OCR is
exercised through the full pipeline (ingest → OCR → chunk → retrieve → answer).
Added a **Chinese-language OCR test** for the Mandarin requirement.

## Why
docs/0010 proved OCR *extraction* in a unit test. This proves OCR content is
actually retrievable and answerable end-to-end, and that the engine handles
Chinese — the two things that make OCR a real feature rather than a parsing detail.

## Key decisions
- **Answer lives only in the image:** the golden question ("thermal paste
  reapplication interval … 24 months") is answerable *only* from the scanned PNG, so
  a correct answer is genuine proof OCR text reached retrieval — not a lucky match
  against a text doc.
- **Synthetic scanned doc, committed:** generated with Pillow (`scripts/make_demo_scan.py`),
  36 KB, synthetic content — safe to commit, keeps the demo zero-setup.
- **Chinese via Noto CJK + RapidOCR default model:** RapidOCR's default PP-OCR model
  recognizes Chinese + English, so no engine change was needed; added `fonts-noto-cjk`
  only to *render* the test image.

## Validation
- **End-to-end:** query "recommended thermal paste reapplication interval for the
  ThinkPad Z13?" → "**24 months [1]**", cited to `thinkpad_z13_service_bulletin.png`.
  The PNG was OCR'd, chunked, and indexed (demo corpus now 16 chunks).
- **Chinese:** all four lines recovered (联想ThinkPad维护公告 / 电池续航时间最长可达18小时 /
  推荐的固件基线版本为2.4.1 / 保修期为三年) — **5/5** expected tokens.
- **No regression:** demo eval (n=28 incl. the OCR question) Recall@5 1.000,
  coverage 1.000, nDCG@5 0.959.

## Honesty caveats
- The scanned doc is a *clean* synthetic render. Real scans add skew, rotation,
  noise, and compression artifacts that lower accuracy — robustness on real scans is
  untested here.
- One Chinese sample; no quantitative Chinese accuracy benchmark yet.

## Follow-ups
- **Multimodal/VLM** milestone: describe product *images* (image understanding, not
  text reading) — the idea.md image-ingestion feature.
- Robustness pass on noisier/rotated scans; OCR-output boilerplate filtering.
- Engine/accuracy comparison (RapidOCR vs Tesseract vs VLM) if needed.
