# 0009 — Tighten abstention + re-run ablations on the real corpus

- **Commit:** (feat): tighten abstention + re-run ablations on real corpus
- **Date:** 2026-06-18
- **Milestone:** Real-corpus validation

## What
Closed the last abstention gap (one negative was answered via outside-knowledge
inference) by tightening the generation prompt, then re-ran the chunking-size,
strategy, and embedding ablations on the real PSREF corpus to check the
demo-corpus decisions hold on real data.

## Why
The real corpus is the true test. M1's chunking/embedding decisions were made on a
saturated synthetic corpus; the user asked to re-validate them on real PDFs now
that metrics move. And abstention 0.5 was a real grounding leak worth fixing.

## Key decisions
- **Abstention via prompt, not threshold:** the prompt now forbids outside/general
  knowledge and inference ("do not reason about what is 'likely' or 'consistent
  with'"); when the context doesn't address the question, reply that the info isn't
  in the sources. The "macOS" negative went from a reasoned "No … consistent with
  Windows/Linux" to a clean abstention.
- **No default changes — decisions validated on real data**, with honest nuance:
  - Chunk size `1000/150` retained. On real PDFs a genuine trade-off appears (small
    chunks rank better, large cover values better) — neither dominates; 1000 is the
    balanced pick.
  - `structure` kept as default, but its *retrieval* edge is gone on real PDFs
    (nDCG 0.982 vs 0.991 for fixed/recursive; cov@budget tied). Its justification is
    now purely **section-level citations** (contextual chunking already supplies the
    product/section context that structure's metadata used to add). Stated plainly.
  - `bge-small` retained: still ties bge-base/large on de-biased metrics at 3–10×
    lower index cost.

## Validation
Real corpus (3 PDFs, ~76 chunks), `top_k=3`:

Abstention (generation): **0.5 → 1.0**; faithfulness 0.944, relevancy 0.978 (held).

Strategy (cov@budget / nDCG): fixed 0.944/0.991 · recursive 0.944/0.991 ·
paragraph 0.944/0.991 · structure 0.944/0.982 · semantic 0.944/0.991 ·
sentence 0.944/0.973.

Embedding (nDCG / cov@budget / idx_s): bge-small 0.982/0.944/5.7 ·
bge-base 0.982/0.944/16.3 · bge-large 0.982/0.944/54.8.

## Honesty caveats
- The golden set is small (9 answerable), so 0.01-level nDCG gaps are ~1-question
  swings — directional, not statistically strong. Bigger golden set needed for
  confident strategy/embedding calls.
- Each PSREF PDF has **1 page with no text layer** (skipped by the parser) — an OCR
  opportunity that could add content.

## Follow-ups
- Expand the real golden set for statistical confidence.
- OCR the no-text pages (the multimodal/OCR milestone).
- M2: fusion (RRF vs weighted) + reranker-model ablation; add multilingual content
  to exercise `bge-m3`.
