# 0004 — Chunking strategies + de-biased metric (M1)

- **Commit:** (feat): chunking strategy comparison + section citations (M1)
- **Date:** 2026-06-17
- **Milestone:** M1 (chunking strategy decision)

## What
Implemented six chunking strategies behind one interface (fixed, recursive,
sentence, paragraph, structure, semantic), added a size-neutral evaluation metric
(coverage at a fixed context budget), compared them on the golden set, and set the
default to the hybrid `structure` strategy — which also gives section-level
citations.

## Why
Different real sources need different chunking: clean headed sections, long
unbroken prose, tables. No single splitter is best everywhere, and the user
correctly anticipated needing a *mix*. But comparing strategies first required
fixing the metric: keyword coverage is biased toward bigger chunks, so it would
have rewarded whatever strategy happens to produce large chunks rather than the
one that retrieves the answer most efficiently.

## Key decisions
- **De-bias before comparing — `coverage_at_budget`:** fill an equal *context
  budget* (chars) with whole chunks in rank order, then measure coverage. Bigger
  chunks fill it with fewer/contiguous chunks; smaller with more/diverse — same
  budget for all, so it's a fair "answer per token of context" test. This is the
  precision-aware metric the M0/0003 entries flagged as missing.
- **`structure` made a real hybrid, not one-chunk-per-heading:** the first version
  emitted a chunk per heading and *over-fragmented* (47 tiny chunks, cov@budget
  0.750 — worst). Fixed by (a) recursive fallback for over-long sections and (b)
  packing small adjacent sections up to the size budget. Result: 15 chunks,
  cov@budget 0.981 — now competitive.
- **Added a long-section stress doc** (`deployment_guide.md`) with one ~3.5k-char
  section and three facts buried at different depths — the "long section" case the
  user raised, which the short, uniform demo docs couldn't exercise.
- **Default = `structure`:** tied on retrieval with recursive/paragraph, but
  uniquely supplies `section` metadata (claim → file + section, requirement #6)
  and adapts to both long and short sections; degrades to recursive on un-headed
  PDFs, so it's a safe superset default. `fixed` (worst) and `semantic` (no gain,
  highest compute) are ruled out by measurement.
- **Section-aware citations wired through** generation + the query CLI.

## Validation
Strategy ablation (rerank on, `top_k=3`, budget=1000 chars, 8-doc corpus incl. the
long-section doc):

| strategy | chunks | nDCG | cov@k | cov@budget |
|---|---|---|---|---|
| fixed | 18 | 0.980 | 1.000 | 0.926 |
| recursive | 20 | 0.988 | 1.000 | 0.981 |
| sentence | 18 | 0.980 | 1.000 | 0.981 |
| paragraph | 18 | 0.988 | 1.000 | 0.981 |
| structure | 15 | 0.983 | 0.981 | 0.981 |
| semantic | 25 | 0.988 | 0.833 | 0.833 |

Smoke test: a fact buried deep in the long section ("minimum BIOS … 1.38") is
retrieved and answered, with the citation showing the section:
`deployment_guide.md (p.1, Deployment Considerations, support)`.

## Honesty caveats
- Strategy ranking is corpus-dependent. On these short synthetic docs structure's
  advantage is mostly the citation metadata, not a retrieval win; on real
  heterogeneous PDFs with long uneven sections it should pull further ahead.
  Re-run the ablation on the real corpus before locking.
- `structure` relies on markdown headings; PDF heading detection (font-size
  heuristics) is future work — until then it falls back to recursive on PDFs.
- The LLM judge still reuses the generator (DeepSeek) — judge==generator bias.

## Follow-ups
- PDF heading detection to make `structure` effective on real PDFs.
- Embedding-model ablation (`bge-small` vs `bge-m3` vs `bge-large`).
- M2: fusion (RRF vs weighted) + reranker model ablations.
