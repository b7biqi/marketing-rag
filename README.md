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

## Layout

```
config.py            # central, swappable configuration
ingestion/           # parser, chunking, embeddings, indexer
retrieval/           # hybrid search (RRF) + cross-encoder rerank
llm/                 # DeepSeek generation + model-agnostic grounding
scripts/             # ingest.py, query.py CLIs
demo_data/           # placeholder docs (replace with real corpus — M0)
evaluation/          # (next) golden set + run_eval.py
```

## Next

- **M0:** assemble the public demo corpus + golden eval set + `evaluation/run_eval.py`.
- **M1–M2:** run the chunking / embedding / fusion / rerank ablations and lock the
  winning configs with measured numbers.
