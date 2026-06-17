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

**Measured baseline** (4-doc / 8-chunk demo corpus, `bge-small` + `bm25` RRF):

| Config | Recall@1 | MRR@1 | nDCG@1 |
|---|---|---|---|
| hybrid + rerank | **1.000** | **1.000** | **1.000** |
| hybrid only (no rerank) | 0.933 | 0.933 | 0.933 |

Generation (`top_k=3`): faithfulness **1.000**, answer relevancy **1.000**,
abstention on negatives **1.000** (3/3 unanswerable questions correctly declined).

> ⚠️ The demo corpus is tiny, so metrics saturate at `top_k≥3`. The point of M0
> is the *instrument* and the first measured signal (reranking lifts precision@1
> 0.933→1.000); the discriminating numbers come with the real/larger corpus and
> the M1–M2 ablations. The LLM judge currently reuses the generator (DeepSeek) —
> bias caveat noted; target is a Claude judge.

## Layout

```
config.py            # central, swappable configuration
ingestion/           # parser, chunking, embeddings, indexer, corpus (manifest)
retrieval/           # hybrid search (RRF) + cross-encoder rerank
llm/                 # DeepSeek generation + model-agnostic grounding
evaluation/          # golden_set.jsonl, metrics, judge, run_eval.py
scripts/             # ingest.py, query.py, reindex.py CLIs
demo_data/           # placeholder docs + manifest.json (replace with real corpus)
```

## Next

- **Corpus:** swap placeholder demo docs for the real public corpus (incl. scanned
  PDFs + images); update `golden_set.jsonl` accordingly.
- **M1:** chunking (size × overlap × strategy) and embedding-model ablations,
  measured with `run_eval.py`; lock the winners.
- **M2:** fusion (RRF vs weighted) and reranker (`bge-reranker-v2-m3` vs ms-marco)
  ablations; record the headline retrieval table.
