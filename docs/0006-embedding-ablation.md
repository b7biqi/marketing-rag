# 0006 — Embedding-model ablation (M1)

- **Commit:** (feat): embedding-model ablation (M1)
- **Date:** 2026-06-17
- **Milestone:** M1 (embedding model decision)

## What
Compared dense embedding models (`bge-small` / `bge-base` / `bge-large`) through
the harness, holding chunking and reranker fixed. Each model re-embeds the corpus
(rebuilding the collection at the new vector dimension) and is scored on retrieval
+ the size-neutral coverage-at-budget metric, with index time as a cost proxy.

## Why
The embedding model is the single biggest lever on retrieval quality, but also on
cost (latency + storage). The choice should be measured in-domain, not taken from
an MTEB leaderboard (PROJECT_PLAN §3.4). The experiment also demonstrates the
swap-and-remeasure infra (clear the model cache, rebuild at the new dim, restore
the default afterward so the live system stays consistent).

## Key decisions
- **Isolate cost from download:** model load/download is forced *before* the timer,
  so `idx_s` reflects embedding+indexing throughput, not a one-time download.
- **Cost is the deciding axis when quality ties:** on a saturated corpus, a bigger
  model that scores the same is strictly worse (slower, larger). Tie-break is
  explicitly `(quality, then lower index cost)`.
- **Restore-on-exit:** the ablation rebuilds the index with the default model in a
  `finally` block, so a half-run experiment never leaves the live system on a
  mismatched dimension.

## Validation
`top_k=2`, chunking=`structure`, rerank on, 8-doc corpus:

| model | dim | index time | nDCG | cov@budget |
|---|---|---|---|---|
| bge-small-en-v1.5 | 384 | 0.9 s | 0.986 | 0.981 |
| bge-base-en-v1.5 | 768 | 2.5 s | 0.986 | 0.981 |
| bge-large-en-v1.5 | 1024 | 6.6 s | 0.986 | 0.981 |

Identical quality; ~7× index-time spread. **Decision: keep `bge-small-en-v1.5`.**

## Honesty caveats
- Quality is saturated on this corpus, so this does not prove the models are
  *equivalent* in general — only that the smaller one is sufficient *here*. A
  larger/harder corpus could separate them.
- `bge-m3` (multilingual + native sparse) was **not** run: it would saturate the
  same here at much higher download/compute cost. It is the candidate to adopt for
  the Mandarin/multilingual requirement — to be measured on the real/multilingual
  corpus, not paid for speculatively now.

## Follow-ups
- Re-run including `bge-m3` once multilingual content is in the corpus.
- M2: fusion (RRF vs weighted) + reranker model ablations.
