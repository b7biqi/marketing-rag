# 0002 — Evaluation harness + demo corpus (M0)

- **Commit:** (feat): evaluation harness + demo corpus (M0)
- **Date:** 2026-06-17
- **Milestone:** M0 (the gate)

## What
Built the evaluation backbone — the instrument that turns every retrieval and
generation choice into a measured decision. Enriched the demo corpus, added a
manifest-driven reproducible reindex, a hand-authored golden question set, and a
runner (`evaluation/run_eval.py`) that reports retrieval metrics (free,
deterministic) and optional LLM-judged generation metrics.

## Why
The project's premise is that no component ships on reputation — it has to score
better on our own data (PROJECT_PLAN §0, §2). That requires (a) a corpus where
retrieval actually has to discriminate and (b) a labeled question set. Without
this, "we chose X" is an assertion; with it, it's a result. M0 is therefore a
gate: later milestones (chunking, embedding, fusion, reranker ablations) all run
through this harness.

## Key decisions
- **Discriminating corpus, not just bigger:** X1 and T14 specs are deliberately
  *similar but differ on specific facts* (X1 1.09 kg / no Ethernet; T14 1.36 kg /
  has RJ45 / 64 GB). A question like "which has Ethernet?" only scores well if
  retrieval picks the right document — that's what exercises hybrid + rerank.
- **Manifest-driven reindex** (`demo_data/manifest.json`, `ingestion/corpus.py`):
  ablations are only honest if the index is rebuilt identically except for the one
  variable under test. `reindex()` gives that determinism (drop → recreate →
  parse/chunk/embed/index per manifest entry).
- **Golden labels by `relevant_sources` + `answer_keywords`:** source labels score
  ranking; keyword presence is a sharper "did the actual answer reach context"
  check that survives re-chunking (important for the M1 chunk-size ablation).
- **3 negative questions** (price, macOS, CEO) to measure *abstention* — the
  anti-hallucination behavior the product needs.
- **Retrieval metrics are dependency-free** (`metrics.py`): Recall@k, MRR, nDCG@k,
  keyword coverage — fast, free, deterministic, so ablations are cheap to run.
- **LLM judge isolated** (`judge.py`) so the judge model is swappable. It currently
  reuses DeepSeek — a known judge==generator bias (PROJECT_PLAN §3.12); target is a
  Claude judge.
- **Skipped RAGAS for now:** a custom JSON-returning judge avoids the heavy
  ragas/torch dependency while giving faithfulness/relevancy/abstention. Can add
  RAGAS later behind the same runner.

## Validation
Ran in the dev container against the rebuilt 4-doc / 8-chunk index:

| Config | Recall@1 | MRR@1 | nDCG@1 |
|---|---|---|---|
| hybrid + rerank | 1.000 | 1.000 | 1.000 |
| hybrid only | 0.933 | 0.933 | 0.933 |

Generation (`top_k=3`, DeepSeek judge): faithfulness 1.000, relevancy 1.000,
abstention 3/3 on negatives.

**First measured decision:** the cross-encoder reranker earns its place — it lifts
precision@1 from 0.933 → 1.000 (fixes the one question hybrid mis-ranked).

**Honest caveat:** the corpus is tiny, so metrics saturate at `top_k ≥ 3` (you
retrieve most of the corpus). The value of M0 is the *instrument* and the first
signal; discriminating numbers arrive with the real/larger corpus and M1–M2.

## Follow-ups
- Swap placeholder docs for a real public corpus (incl. scanned PDFs + images);
  update the golden set.
- M1: chunking (size × overlap × strategy) and embedding-model ablations via the
  harness; lock the winners and record the tables.
- Point the judge at Claude to remove the judge==generator bias.
