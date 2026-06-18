# Handoff — for the next agent/LLM continuing this project

Read this first. It tells you what this project is, the rules it's built under, what
is **done vs not**, how to run it, and what to do next. Pair it with:
- [PROJECT_PLAN.md](PROJECT_PLAN.md) — the design + the justification (and the
  *confirming experiment*) behind every technical decision.
- [docs/](docs/) — the per-commit decision log (what was done and **why**, commit by
  commit). Start at `docs/README.md`.

## The one non-negotiable rule

**No technical decision ships without evidence.** Embedding model, chunking,
fusion, reranker, OCR engine — each is chosen because it scored better on the
evaluation harness on *our* data, not because it's popular. Public benchmarks only
narrow the candidate set; `evaluation/run_eval.py` picks the winner. If you change a
component, run the harness and record the number. If you can't measure it, say so.

Corollary conventions:
- **Diagnose before building.** When something underperforms, find the actual cause
  first (`evaluation/diagnose.py`, targeted scripts) — twice already the obvious
  guess was wrong (real-corpus failure was boilerplate+product-confusion, not column
  interleaving; "scanned" pages were actually all-boilerplate, not images).
- **Every commit adds a `docs/NNNN-slug.md` decision-log entry** (what + why),
  staged in the same commit. Follow the template in `docs/README.md`. Update its index.
- **Commit messages:** `(feat): ...` / `(fix): ...`, end with the
  `Co-Authored-By: Claude Opus 4.8 (1M context)` trailer. (The human sometimes edits
  the message at commit time — that's fine, don't fight it.)
- **Be honest about caveats** in docs and the README (small eval set, judge bias,
  synthetic data). The project's credibility is the honesty.

## Current state (one paragraph)

A runnable, **torch-free** RAG pipeline: ingest (PDF incl. heading detection + OCR
for scanned/image, DOCX, TXT/MD, image files) → chunk (strategy-pluggable) → hybrid
embed (dense `bge-small` + sparse BM25) → Qdrant → hybrid retrieval (RRF) →
cross-encoder rerank → grounded generation (DeepSeek via LangChain `init_chat_model`)
with claim→file/section citations and abstention. An evaluation harness drives every
decision. Validated on a synthetic demo corpus *and* real public Lenovo PSREF PDFs.
**Not yet built:** LangGraph agent, VLM/multimodal image understanding, FastAPI
service, reliability layer (retry/breaker/Claude fallback), GraphRAG.

## How to run (dev container is the environment)

Everything runs in the dev container — nothing local. The container also runs Qdrant
+ Redis. `QDRANT_URL=http://qdrant:6333` and `DEEPSEEK_API_KEY` (from `.env`,
gitignored) are available inside it.

```bash
# exec into the running container (or VSCode "Reopen in Container")
docker compose -f .devcontainer/docker-compose.yml up -d
docker compose -f .devcontainer/docker-compose.yml exec app bash

# --- inside the container ---
python -m scripts.reindex                              # build index from demo corpus
python -m scripts.query "..."                          # retrieve + grounded answer
python -m evaluation.run_eval --reindex --generation   # full eval
```

**Corpus switch (important):** demo vs real corpus is selected by env var. Default is
the demo corpus. For the real PSREF corpus:
```bash
python -m scripts.fetch_corpus      # downloads gitignored PDFs into corpus/pdfs/
MANIFEST_PATH=corpus/manifest.json GOLDEN_PATH=corpus/golden_set.jsonl \
  python -m evaluation.run_eval --reindex --generation --top-k 5
```

**When you change deps:** edit `requirements.txt` / `.devcontainer/Dockerfile`, then
`docker compose -f .devcontainer/docker-compose.yml up -d --build app`.

## Architecture map

| Path | Responsibility |
|---|---|
| `config.py` | All knobs (pydantic-settings; every field overridable by `UPPER_CASE` env var). Read this to see current defaults. |
| `ingestion/parser.py` | PDF (font-size heading detection → markdown, boilerplate filtering), DOCX, TXT/MD, **image files → OCR**, **no-text PDF pages → OCR**. |
| `ingestion/ocr.py` | RapidOCR wrapper (ONNX, no torch, Chinese-capable). |
| `ingestion/chunkers.py` | The 6 strategies (fixed/recursive/sentence/paragraph/structure/semantic). `chunking.py` just delegates per `settings.chunk_strategy`. Chunks get a `product — section` context prefix (contextual chunking). |
| `ingestion/embeddings.py` | fastembed dense + sparse (lazy, cached). |
| `ingestion/indexer.py` | Qdrant collection (named dense+sparse vectors, IDF, payload indexes), upsert. |
| `ingestion/corpus.py` | `reindex(client, manifest_path)` — drop+rebuild from a manifest (paths relative to the manifest dir → same code for demo & real). |
| `retrieval/retriever.py` | `hybrid_search` (dense+sparse, RRF) → `rerank` (cross-encoder) → `retrieve`. |
| `llm/generator.py` | Grounded generation; system prompt forbids outside knowledge → abstains; resolves `[n]` citations to file/section. Model-agnostic (no vendor citation API). |
| `evaluation/run_eval.py` | Harness: `evaluate_retrieval` (Recall@k, MRR, nDCG@k, kw coverage, **cov@budget**) + `evaluate_generation` (faithfulness/relevancy/abstention via LLM judge). Reusable functions for experiments. |
| `evaluation/metrics.py` | Pure metrics incl. `coverage_at_budget` (size-neutral, de-biases chunk-size comparisons). |
| `evaluation/judge.py` | LLM-as-judge (currently DeepSeek — bias caveat; target Claude). |
| `evaluation/diagnose.py` | Per-question retrieval diagnostic (why a question fails). |
| `experiments/*` | Ablation scripts (chunking, strategy, embedding) + OCR/PDF validation scripts. These produce the numbers in the README. |
| `scripts/*` | CLIs: `reindex`, `query`, `ingest`, `fetch_corpus`, `make_demo_scan`. |
| `demo_data/`, `corpus/` | Demo (synthetic, committed incl. a scanned PNG) and real (PDF URLs + fetch; PDFs gitignored). |

## Decisions already made (with evidence)

| Area | Decision | Why / evidence | Doc |
|---|---|---|---|
| Stack | fastembed (ONNX) + Qdrant + LangChain; **torch-free** | runs full hybrid+rerank+gen without GPU/torch | 0001 |
| LLM | DeepSeek (open-weight) via `init_chat_model` | OSS-primary posture; vLLM self-host deferred | 0001 |
| Vector store | Qdrant | native hybrid + RRF + metadata filtering + Docker | 0001 |
| Search | dense+sparse, **RRF** | calibration-free; catches exact terms dense misses | 0001 |
| Rerank | cross-encoder, keep it | precision@1 0.917→1.000 on real corpus | 0002/0009 |
| Chunk size | `1000/150` | best nDCG/coverage in ablation | 0003 |
| Chunk strategy | `structure` (heading split + recursive fallback + packing) | ties on retrieval; **uniquely gives section citations**; degrades gracefully on un-headed PDFs | 0004 |
| PDF headings | font-size detection → markdown `#` | makes `structure` work on real PDFs | 0005 |
| Embedding | `bge-small` | ties bge-base/large on de-biased metrics at 3–7× lower cost | 0006/0009 |
| Real-corpus fixes | boilerplate filter + contextual `product — section` prefix | coverage 0.556→0.944 | 0008 |
| Abstention | prompt forbids outside-knowledge inference | abstention 0.5→1.0 | 0009 |
| OCR | RapidOCR; trigger on true image pages + image files | torch-free, Chinese; ~90% char recovery; 5/5 Chinese tokens; e2e through retrieval | 0010/0011 |

## Feature checklist (idea.md MVP + plan)

Done ✅ / partial 🟡 / todo ⬜ — see the README "Capabilities" table for the same list.

- ✅ Document ingestion (PDF/DOCX/TXT/MD/images)
- ✅ OCR pipeline (scanned PDFs, image files, Chinese)
- ✅ Vector DB + metadata filtering (Qdrant)
- ✅ Hybrid search (BM25 + vector, RRF)
- ✅ Reranking (cross-encoder)
- ✅ Source grounding / citations (claim → file + section) + abstention
- 🟡 Evaluation pipeline — custom harness (retrieval metrics + LLM-judge
  faithfulness/relevancy/abstention). **Not** the RAGAS library; equivalent metrics.
- 🟡 Docker — dev container + services compose exist; no single `docker compose up`
  that also serves the API (because there's no API yet).
- ⬜ Agentic workflow (LangGraph: plan → retrieve×N → draft → fact-check)
- ⬜ Multimodal / VLM (describe a product **image** → retrieve → marketing copy).
  Note: OCR ≠ VLM. OCR reads text; this is image *understanding*.
- ⬜ FastAPI service (`/ingest`, `/query`, `/generate-marketing-content`, `/upload-image`, `/health`)
- ⬜ Reliability layer (tenacity retry + pybreaker + **Claude fallback**)
- ⬜ M2: fusion ablation (RRF vs weighted) + reranker-model ablation (`bge-reranker-v2-m3` vs ms-marco)
- ⬜ GraphRAG / Neo4j (nice-to-have, deferred)

## Open caveats / tech debt (be honest about these)

- **LLM judge == generator (DeepSeek)** → self-preference bias. Target: Claude judge.
  `evaluation/judge.py` is isolated for exactly this swap.
- **Real golden set is small** (9 answerable) → strategy/embedding deltas are
  *directional*, not statistically strong. Expanding it is the highest-leverage next step.
- **No reliability/fallback** — a DeepSeek outage currently fails the request.
- **OCR validated on clean synthetic renders only** — real scans (skew/noise/rotation)
  untested; OCR'd pages still include their own boilerplate.
- **Fusion is RRF only** — weighted fusion not yet compared (M2).
- **`bge-m3` not adopted** — Chinese *OCR* works, but Chinese *embedding/retrieval*
  end-to-end is untested; `bge-m3` is the multilingual candidate to measure.
- Self-hosted vLLM primary + Claude ceiling (the plan's target posture) is deferred;
  current generation is DeepSeek API.

## Prioritized backlog (pick up here)

1. **Expand the real golden set** (→ statistical confidence). Add ~20–40 questions to
   `corpus/golden_set.jsonl` across the real PDFs; re-run the real-corpus ablations.
2. **Multimodal / VLM** — add an image→description path (Qwen2.5-VL self-host, or a
   vision model via API), feed the description into retrieval, generate copy. This is
   the biggest missing JD capability and pairs with the existing OCR work.
3. **FastAPI service** — wrap ingest/query/generate/upload-image/health; then a single
   `docker compose up` that serves it. Then the reliability layer (tenacity + pybreaker
   + Claude fallback) around the LLM call.
4. **M2 ablations** — fusion (RRF vs weighted) + reranker model; and measure `bge-m3`
   for the multilingual requirement on a corpus that includes Chinese docs.
5. **LangGraph agent** — plan → retrieve(product/brand/compliance) → draft → fact-check
   loop, using the existing retriever + generator as nodes.

Whatever you pick: change one thing, run `evaluation/run_eval.py`, record the number,
write the `docs/` entry, commit.
