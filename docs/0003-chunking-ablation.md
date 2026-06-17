# 0003 — Corpus expansion + chunking ablation (M1)

- **Commit:** (feat): chunking ablation + corpus expansion (M1)
- **Date:** 2026-06-17
- **Milestone:** M1 (first justified-by-experiment retrieval decision)

## What
Expanded the demo corpus from 4 to 7 documents and the golden set from 18 to 28
questions, refactored the eval into reusable functions, and added the first real
ablation (`experiments/ablate_chunking.py`) that picks `chunk_size`/`overlap` by
measurement rather than by default.

## Why
The M0 corpus (8 chunks) saturated every metric, so any ablation on it would be
inconclusive (PROJECT_PLAN §3.3). An ablation is only meaningful if the metric can
move. Expanding the corpus with more *fact-rich, partially-overlapping* documents
(a P16 workstation, warranty terms, sustainability/regulatory) gives retrieval more
to discriminate and lets chunk granularity actually affect the score.

## Key decisions
- **Expand for discrimination, not just size:** new docs add distinct, queryable
  facts (P16 = only discrete NVIDIA GPU; 3-year warranty; EPEAT Gold; RoHS/REACH)
  and new `doc_type`s (`support`), so questions force real choices.
- **Refactor `run_eval` into `evaluate_retrieval()` / `evaluate_generation()`** so
  experiment scripts reuse the exact same scoring as the CLI — no metric drift
  between ad-hoc experiments and the canonical harness.
- **Ablate by in-process settings mutation + manifest reindex:** each config
  rebuilds the index from the manifest so only chunking changes — the determinism
  `corpus.py` was built for.
- **Winner picked by (coverage, nDCG, MRR):** precision-leaning tie-breaking.

## Validation
Chunking ablation (rerank on, `top_k=3`, 7-doc corpus):

| chunk_size | overlap | chunks | Recall | MRR | nDCG | kw cov |
|---|---|---|---|---|---|---|
| 300 | 0/45 | 47 | 1.000 | 0.979 | 0.981 | 0.792 |
| 500 | 0/75 | 26 | 1.000 | 1.000 | 0.987 | 0.833 |
| 1000 | 150 | 14 | 1.000 | 1.000 | 0.993 | 1.000 |

Refreshed reranker baseline (`top_k=1`, n=24): Recall@1 **1.000** with rerank vs
**0.917** without (reranker corrects ~2/24). Generation (`top_k=3`): faithfulness
1.000, relevancy 1.000, abstention 4/4.

**Decision:** keep `chunk_size=1000, overlap=150` and keep the reranker — both now
backed by numbers, not defaults.

## Honesty caveats
- Ranking metrics are still near-saturated on this corpus; the moving signal is
  keyword coverage, which is **partly biased toward larger chunks** (more text
  mechanically contains more keywords). So the chunking result validates the default
  but is not a clean win. A token-budget-normalized **context-precision** metric and
  the real corpus are needed to make a strong, de-biased call.
- The LLM judge still reuses the generator (DeepSeek) — judge==generator bias.

## Follow-ups
- Add a context-precision metric to de-bias chunk-size comparison.
- Embedding-model ablation (`bge-small` vs `bge-m3` vs `bge-large`).
- M2: fusion (RRF vs weighted) and reranker model ablations.
