# 0007 — Real corpus (public Lenovo PSREF PDFs)

- **Commit:** (feat): real corpus — fetch + ingest public PSREF PDFs (M0 corpus)
- **Date:** 2026-06-17
- **Milestone:** Real corpus bootstrap

## What
Added the real corpus: a manifest of public Lenovo PSREF spec-sheet PDF URLs
(X1 Carbon Gen 13, T14 Gen 6 Intel, P16 Gen 3), an on-demand fetch script, a
real-content golden set, and corpus-location parameterization so the harness runs
against either the demo or the real corpus. Then ran the full evaluation on real
PDFs for the first time.

## Why
Every metric so far saturated on the synthetic demo corpus, so the decisions
(chunking, embedding) were validated but not stress-tested. Real spec sheets are
the actual target and the only way to see where the pipeline really stands.

## Key decisions
- **Don't redistribute copyrighted PDFs:** `corpus/pdfs/` is gitignored; the repo
  commits the **manifest of public URLs** + a `fetch_corpus.py` script. Reproducible
  without checking in Lenovo's files. Demo/eval use only.
- **Parameterize the corpus, don't fork the harness:** `MANIFEST_PATH` /
  `GOLDEN_PATH` settings (env-overridable) select demo vs real. `reindex()` resolves
  file paths relative to the manifest dir. One code path, two corpora.
- **Default stays the demo corpus:** a fresh clone has no PDFs, so demo (zero-setup)
  is the default; real is opt-in (`fetch_corpus` + env vars).
- **Golden set built from verified facts:** every answer keyword was confirmed to
  appear in the parsed PDF text (e.g. X1 "1006 g", P16 "128GB", "2.54 kg",
  "HX Series"), so the labels are real, not assumed.

## Validation
Real-corpus eval (3 PDFs, **85 chunks** — finally non-saturating), `top_k=5`:

| metric | demo (synthetic) | real (PSREF PDFs) |
|---|---|---|
| Recall@5 | 1.000 | 1.000 |
| nDCG@5 | ~0.99 | 0.946 |
| answer-kw coverage | 1.000 | **0.556** |
| faithfulness | 1.000 | 0.778 |
| abstention | 1.000 | 0.500 |

**The headline finding:** real multi-column PSREF PDFs are much harder. The
two-column key/value layout interleaves under naive text extraction, fragmenting
field→value pairs, so the specific answer often misses top-k (coverage 0.556) and
section attribution is scrambled (a weight answer cited section "UltraNav"). A
sample query for P16 max memory + weight returned the weight correctly and
**abstained** on memory rather than inventing it from a retrieved *X1* "Max Memory"
chunk — grounding holds even when retrieval fails.

## Honesty caveats
- Recall@5 is still 1.0 (the right *document* is always found); the failure is
  intra-document — the right *value* isn't in the top-k chunks. Coverage/faithfulness
  are the metrics that caught it.
- The golden set is small (11 Qs) and English-only; expand and add multilingual to
  exercise `bge-m3`.
- Fetched PDF content can change over time (PSREF updates); the golden set is tied
  to the version fetched.

## Follow-ups (now evidence-backed priorities)
- **Column/table-aware PDF extraction** (pdfplumber / Docling / PyMuPDF column
  detection) — the #1 gap the real corpus exposed (PROJECT_PLAN §3.1). Should lift
  coverage and fix section attribution.
- Re-run the chunking/embedding ablations on the real corpus now that metrics move.
- Expand the golden set; add a multilingual doc to test `bge-m3`.
