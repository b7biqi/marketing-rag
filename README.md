# Enterprise Marketing Content Agent

Multimodal RAG system that generates **grounded** marketing content from internal
product / brand / compliance documents — hybrid retrieval, cross-encoder
reranking, source citations, and (incrementally) an agentic workflow, OCR +
vision ingestion, and an evaluation harness.

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full design and the justification
(+ confirming experiment) behind every technical decision.

## Status

Phase-0 vertical slice is runnable: **ingest → chunk → hybrid embed → Qdrant →
hybrid + rerank retrieve → grounded DeepSeek generation with citations.**

Dev stack is deliberately lightweight (torch-free): `fastembed` (ONNX dense +
sparse + reranker), Qdrant in embedded local mode, DeepSeek via LangChain
`init_chat_model`. Self-hosted vLLM and the Claude fallback are deferred.

## Quickstart (VSCode Dev Container)

Nothing is installed locally — everything runs in the dev container, which also
brings up Qdrant and Redis.

1. `cp .env.example .env` and add your `DEEPSEEK_API_KEY`.
2. VSCode → **Reopen in Container** (or `Dev Containers: Rebuild and Reopen`).
   This builds the image (Python 3.12 + deps) and starts `app` + `qdrant` + `redis`.
3. In the container terminal:

```bash
# Ingest the placeholder demo docs (replace with the real corpus later)
python -m scripts.ingest demo_data/thinkpad_x1_spec.md --doc-type spec --product "ThinkPad X1"
python -m scripts.ingest demo_data/brand_guidelines.md --doc-type brand

# Retrieval only (no API key needed)
python -m scripts.query "What is the battery life of the ThinkPad X1?" --no-generate

# Full RAG answer with citations (needs DEEPSEEK_API_KEY)
python -m scripts.query "What is the battery life of the ThinkPad X1?"

# Content generation, respecting brand guidance
python -m scripts.query "Write a LinkedIn post on ThinkPad X1 security for CIOs" --task
```

First run downloads the ONNX embedding/reranker models (cached in a named volume).
Inside the container `QDRANT_URL=http://qdrant:6333` is preset, so retrieval uses
the Qdrant server (full BM25/IDF), not embedded mode.

> The root `docker-compose.yml` is a standalone services-only alternative if you
> prefer not to use the dev container.

## Evaluation (M0)

The eval harness is the instrument behind every retrieval/generation decision —
nothing is "chosen" without a number. Retrieval metrics are deterministic and
free; generation metrics use an LLM judge (API calls).

```bash
# Rebuild the index from the manifest, then score retrieval
python -m evaluation.run_eval --reindex

# Ablation: reranker on vs off
python -m evaluation.run_eval --no-rerank

# Sharper operating point (small corpus saturates at top_k=5)
python -m evaluation.run_eval --top-k 1

# Add LLM-judged generation metrics (faithfulness / relevancy / abstention)
python -m evaluation.run_eval --generation
```

**Measured baseline** (7-doc / 14-chunk demo corpus, 28-question golden set,
`bge-small` + `bm25` RRF, `1000/150` chunks):

Reranking ablation at `top_k=1` (n=24 answerable):

| Config | Recall@1 | MRR@1 | nDCG@1 |
|---|---|---|---|
| hybrid + rerank | **1.000** | **1.000** | **1.000** |
| hybrid only (no rerank) | 0.917 | 0.917 | 0.917 |

→ the cross-encoder reranker corrects ~2/24 questions hybrid mis-ranks. **Decision:
keep the reranker.**

Generation (`top_k=3`): faithfulness **1.000**, answer relevancy **1.000**,
abstention on negatives **1.000** (4/4 unanswerable questions correctly declined).

### M1 — chunking ablation (`python -m experiments.ablate_chunking`)

`chunk_size` × `overlap`, index rebuilt per config, scored at `top_k=3`:

| chunk_size | overlap | chunks | Recall | MRR | nDCG | kw coverage |
|---|---|---|---|---|---|---|
| 300 | 0 / 45 | 47 | 1.000 | 0.979 | 0.981 | 0.792 |
| 500 | 0 / 75 | 26 | 1.000 | 1.000 | 0.987 | 0.833 |
| **1000** | **150** | **14** | 1.000 | 1.000 | **0.993** | **1.000** |

→ Larger chunks keep related facts together, so a retrieved chunk holds the whole
answer; small chunks split facts. Overlap is negligible at these sizes.
**Decision: keep `1000/150`.**

> ⚠️ Two honesty caveats. (1) On this small corpus, ranking metrics (Recall/MRR/
> nDCG) are near-saturated; the moving signal is keyword coverage, which is *partly
> biased* toward larger chunks (more text mechanically contains more keywords). So
> this validates the default but isn't a clean win — a precision-normalized metric
> (context precision) and the real corpus are needed for a strong call. (2) The LLM
> judge currently reuses the generator (DeepSeek) — bias caveat; target is a Claude
> judge.

## Layout

```
config.py            # central, swappable configuration
ingestion/           # parser, chunking, embeddings, indexer, corpus (manifest)
retrieval/           # hybrid search (RRF) + cross-encoder rerank
llm/                 # DeepSeek generation + model-agnostic grounding
evaluation/          # golden_set.jsonl, metrics, judge, run_eval.py
experiments/         # ablation scripts (ablate_chunking.py, ...)
scripts/             # ingest.py, query.py, reindex.py CLIs
demo_data/           # placeholder docs + manifest.json (replace with real corpus)
docs/                # per-commit decision log
```

## Next

- **Corpus:** swap placeholder demo docs for the real public corpus (incl. scanned
  PDFs + images); update `golden_set.jsonl` accordingly.
- **M1 (cont.):** embedding-model ablation (`bge-small` vs `bge-m3` vs `bge-large`)
  through the harness; add a token-budget-normalized context-precision metric to
  de-bias the chunking call.
- **M2:** fusion (RRF vs weighted) and reranker (`bge-reranker-v2-m3` vs ms-marco)
  ablations; record the headline retrieval table.
