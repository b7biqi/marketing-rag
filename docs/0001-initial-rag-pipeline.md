# 0001 — Initial RAG pipeline

- **Commit:** (feat): initial marketing RAG pipeline (`9828acb`)
- **Date:** 2026-06-17
- **Milestone:** Phase-0 vertical slice

## What
First runnable, end-to-end slice of the Enterprise Marketing Content Agent:
ingest → chunk → hybrid embed → Qdrant → hybrid (RRF) + cross-encoder rerank →
grounded DeepSeek generation with source citations. Plus the project plan, a
VSCode dev container, and placeholder demo data.

## Why
Goal was to get a real retrieval→generation path working immediately so later
decisions could be made against a running system, rather than over-planning. The
[PROJECT_PLAN.md](../PROJECT_PLAN.md) captures the justified target architecture;
this commit is the minimal walking skeleton of it.

## Key decisions
- **Lightweight, torch-free dev stack:** `fastembed` (ONNX dense + sparse +
  cross-encoder) + Qdrant + LangChain. Lets the full hybrid+rerank+generate path
  run without GPU/torch, so we can "do RAG right away." Swappable to
  sentence-transformers/`bge-m3` for the M1 embedding experiment.
- **LLM = DeepSeek via `init_chat_model`** (PROJECT_PLAN §3.11, Phase-0 note).
  DeepSeek is open-weight (keeps the OSS-primary posture) and avoids standing up
  vLLM now; the LangChain provider abstraction makes swapping later a config change.
- **Vector store = Qdrant** with named dense + sparse vectors, IDF for BM25, and
  payload indexes on `doc_type/product/region/version` (PROJECT_PLAN §3.5–3.6) —
  native hybrid + metadata filtering in one component.
- **Hybrid = dense + sparse fused with RRF** (PROJECT_PLAN §3.7): calibration-free,
  catches exact terms (model numbers, specs) that dense retrieval misses.
- **Two-stage retrieval:** hybrid top-N → cross-encoder rerank → top-k
  (PROJECT_PLAN §3.8).
- **Model-agnostic grounding:** the generator is given numbered context blocks and
  cites `[n]`, resolved to file/page from chunk metadata — no vendor-specific
  citation API, so the open generator can ground answers (PROJECT_PLAN §3.11).
- **Config centralized** in `config.py` so every choice is swappable and ablatable.

## Validation
Built and ran entirely in the dev container (Docker, nothing local):
- Image build + `app`/`qdrant`/`redis` up; all imports clean.
- Ingested demo docs → chunked → dense+sparse embedded → indexed into the Qdrant
  server.
- Hybrid + rerank returned correctly ranked chunks (spec doc #1 for a battery query).
- Full grounded generation: DeepSeek produced a cited answer that also applied a
  brand rule to a spec claim.

## Follow-ups
- M0: real eval harness + golden set so decisions become measured (next commit).
- Deferred: self-hosted vLLM primary + Claude fallback/reliability layer; OCR for
  scanned PDFs; multimodal (VLM) path; LangGraph agent; FastAPI; GraphRAG (stretch).
