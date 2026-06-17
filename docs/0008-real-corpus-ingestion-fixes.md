# 0008 — Real-corpus ingestion fixes (boilerplate + contextual chunking)

- **Commit:** (feat): fix real-PDF retrieval — boilerplate filter + contextual chunks
- **Date:** 2026-06-18
- **Milestone:** Real-corpus retrieval quality

## What
Diagnosed why real-PDF answer coverage was only 0.556, then fixed the actual root
causes: dropped repeated page-header/footer boilerplate in the PDF parser, and
prepended product+section context to each chunk. Coverage on the real corpus went
**0.556 → 0.944**, faithfulness **0.778 → 0.944**.

## Why
The plan (and my own earlier guess) assumed the real-PDF problem was multi-column
/ table extraction. **A per-question diagnostic (`evaluation/diagnose.py`) proved
otherwise:** in every failing question the correct *document* was retrieved
(Recall@5 = 1.0), but the specific value chunk was outranked by (a) repeated
boilerplate ("ThinkPad … Gen X" page titles, "PSREF", "N of N") and (b) the *wrong
product's* same-field chunk (X1's "Max Memory" beat P16's for a P16 query, because
the chunk text didn't name the product). Column extraction would have fixed
neither. Diagnose first, then fix what's actually broken.

## Key decisions
- **Boilerplate filtering in the parser:** a line repeated on ≥ half the pages, or
  matching a header/footer pattern (`N of N`, "PSREF", "Product Specifications
  Reference"), is dropped. Body font size is computed from non-boilerplate lines.
- **Contextual chunking:** every chunk's text is prefixed with `product — section`
  (falling back to the doc title when product is generic). A bare value becomes
  self-describing and product-disambiguated. Applied in the chunker's `_emit`, so
  it benefits all strategies and both corpora.
- **Did NOT add column/table extraction:** the diagnostic showed it wasn't the
  bottleneck. Kept as a possible future refinement, not built speculatively.

## Validation
Real corpus (3 PDFs, 85 chunks), `top_k=5`:

| metric | naive ingest | + fixes |
|---|---|---|
| Recall@5 | 1.000 | 1.000 |
| nDCG@5 | 0.946 | 0.977 |
| answer coverage | 0.556 | **0.944** |
| faithfulness | 0.778 | **0.944** |
| abstention (neg) | 0.500 | 0.500 |

Diagnostic: 4/9 → **1/9** questions miss a keyword. Demo corpus unchanged
(coverage 1.000) — no regression.

## Honesty caveats
- 1/9 real questions still misses; abstention is still 0.5 (one negative is
  answered instead of declined) — generation-side, follow-up.
- Boilerplate detection is frequency/pattern heuristic; an unusual layout could
  drop a real line or keep a header. Tune per corpus.
- Contextual prefix slightly inflates chunk text; negligible here.

## Follow-ups
- Tighten abstention (prompt / threshold) for the remaining negative.
- Investigate the last coverage miss.
- Re-run chunking/embedding ablations on the real corpus (metrics now move).
- Column/table extraction only if a future corpus shows it's the bottleneck.
