# Enterprise Marketing Content Agent — Project Plan

A production-shaped, multimodal RAG system that generates grounded marketing
content from internal product/brand/compliance documents, with hybrid retrieval,
reranking, an agentic workflow, OCR + vision ingestion, and a real evaluation
harness.

This plan exists to make **every technical decision justifiable**. For each
component we state the candidate options, the decision, *why*, and the
**experiment that will confirm or overturn the decision against our own data** —
not just leaderboard reputation.

---

## 0. Guiding principles

1. **Decisions are hypotheses until measured on our corpus.** Public benchmarks
   (MTEB, BEIR) narrow the candidate set; the in-domain eval set picks the
   winner. No component ships on vibes.
2. **Build the evaluation harness first.** It is the instrument every other
   decision is measured with. If we can't measure retrieval quality, we can't
   justify a chunking or embedding choice.
3. **Cheap, reversible, observable.** Prefer components that are Docker-native,
   swappable behind an interface, and emit metrics.
4. **Demonstrate breadth the JD asks for** (RAG, hybrid search, rerank,
   agentic, OCR, multimodal, eval, FastAPI, Docker, reliability) **without
   sacrificing correctness** of the core retrieval path.

---

## 1. System architecture (target)

```
                          ┌────────────────────────────────────────────┐
                          │                FastAPI service               │
                          │  /ingest /query /generate /upload-image /health│
                          └───────────────┬──────────────────────────────┘
                                          │
                 ┌────────────────────────┼─────────────────────────────┐
                 │                        │                              │
        ┌────────▼────────┐     ┌─────────▼──────────┐        ┌──────────▼─────────┐
        │ Ingestion        │     │ LangGraph Agent     │        │ Reliability layer  │
        │ pipeline         │     │ (orchestration)     │        │ retry + breaker +  │
        │                  │     │                     │        │ fallback LLM       │
        │ parse→OCR?→chunk │     │ plan → retrieve×N →  │        └──────────┬─────────┘
        │ →embed→index     │     │ draft → fact-check   │                   │
        └────────┬─────────┘     └─────────┬───────────┘          ┌─────────▼────────┐
                 │                         │                       │ LLM (primary +  │
                 │                ┌────────▼─────────┐             │ fallback) + VLM │
                 │                │ Retrieval engine  │             └──────────────────┘
                 │                │ hybrid → rerank   │
                 ▼                └────────┬──────────┘
        ┌──────────────────┐              │
        │ Qdrant (vectors  │◄─────────────┘
        │ + sparse + meta) │
        └──────────────────┘
        ┌──────────────────┐
        │ Redis (cache,    │
        │ rate, idempotency)│
        └──────────────────┘
```

Each box is a Python module behind an interface so the underlying choice can be
swapped and A/B-measured.

---

## 2. The corpus & evaluation backbone (do this first)

Every downstream justification depends on having (a) a representative document
set and (b) a labeled question set.

### 2.1 Demo corpus
Assemble ~30–60 documents across the three knowledge domains the product needs:
- **Product specs** (e.g. ThinkPad-style spec sheets) — digital PDFs, tables.
- **Brand / marketing guidelines** — prose + visual rules.
- **Compliance / security whitepapers** — dense prose, claims, disclaimers.
- **A handful of scanned/image PDFs and product images** — to exercise OCR + VLM.

Mix is deliberate: digital text, tables, scanned pages, and images, so the
ingestion decisions are tested against all modalities they must handle.

### 2.2 Golden evaluation set (the instrument)
Build a question→(answer, supporting chunks) set, ~80–150 items:
1. **Auto-generate** candidate QA pairs from each chunk with Claude (question +
   grounded answer + the source chunk id).
2. **Manually curate / correct** ~100 of them into a trusted golden set.
3. Tag each by type: factual lookup, table value, cross-document, paraphrase,
   "negative" (answer not in corpus → system should abstain).

This set drives **retrieval metrics** (Recall@k, nDCG@10, MRR) and
**generation metrics** (RAGAS: faithfulness, answer relevancy, context
precision/recall). Without it, no chunking/embedding/rerank claim is defensible.

**Deliverable:** `evaluation/golden_set.jsonl` + `evaluation/run_eval.py` that
takes any retrieval/generation config and prints a metrics table. This is
milestone 0 and gates everything else.

---

## 3. Technical decisions (option → decision → why → experiment)

### 3.1 Document parsing / text extraction

| Option | Strengths | Weaknesses |
|---|---|---|
| **PyMuPDF (fitz)** | Fast; returns text blocks with **bbox, page, font** → enables layout-aware chunking and precise citations | Not built for OCR or complex table reconstruction |
| `unstructured` | One API for PDF/DOCX/HTML/images; element typing | Heavy deps; slower; coarser layout fidelity |
| `pdfplumber` | Excellent table extraction | Slower; text-only |
| `Docling` (IBM) | Layout + table model, reading order, markdown export | Heavier; model download |

**Decision:** **PyMuPDF** as the primary PDF text/layout extractor, `python-docx`
for DOCX, `pdfplumber` invoked *only* for pages detected to contain tables.
Evaluate **Docling** as a challenger on the table-heavy spec docs.

**Why:** Source grounding (requirement #6) needs page + section + bounding box;
PyMuPDF provides these cheaply and deterministically. Tables in spec sheets are
where naive extraction fails, so we route those pages to a table-aware tool
rather than paying that cost everywhere.

**Experiment:** On 10 manually-transcribed pages (incl. 3 table pages), measure
character-level extraction fidelity and table-cell accuracy: PyMuPDF vs
PyMuPDF+pdfplumber-for-tables vs Docling. Pick by accuracy at acceptable latency.

### 3.2 OCR (scanned PDFs & images)

| Option | Notes |
|---|---|
| Tesseract | Ubiquitous baseline; weak on layout/tables; lower accuracy on noisy scans |
| **PaddleOCR (PP-OCRv4 / PP-StructureV2)** | Strong detection+recognition, table & layout structure, **multilingual incl. Chinese** |
| docTR / Surya | Modern DL OCR, good accuracy |
| VLM OCR (Claude vision / Qwen2.5-VL) | Best on messy/handwritten/contextual; higher cost/latency |

**Decision:** **PaddleOCR** as the default OCR engine, with a VLM (Claude vision)
escalation path for pages where PaddleOCR confidence is low. **Scanned-vs-digital
is auto-detected** via text-layer coverage (ratio of extractable characters to
page area); OCR runs only when coverage is below threshold.

**Why:** PaddleOCR balances accuracy, table/layout awareness, and self-hostability
(JD: open-source, HF, local inference). Chinese support is a direct nod to the
Mandarin-preferred requirement. Running OCR only on scanned pages avoids
corrupting clean digital text.

**Experiment:** Label ~15 scanned pages. Measure **CER/WER**: Tesseract vs
PaddleOCR vs VLM-OCR. Also validate the digital/scanned classifier
(precision/recall of "needs OCR") so we never OCR a clean page.

### 3.3 Chunking strategy

| Option | Trade-off |
|---|---|
| Fixed-size token windows | Simple, cache-friendly; ignores structure, splits mid-sentence |
| **Recursive character/token split w/ overlap** | Good default; respects separators |
| Semantic (embedding-breakpoint) chunking | Topic-coherent; compute cost, variable sizes |
| **Layout/structure-aware** (split on headings/sections, keep tables intact) | Best citations & coherence; needs reliable structure |

**Decision:** **Structure-aware splitting** (by detected headings/sections, tables
kept whole) **with a recursive token-bounded fallback** and overlap. Each chunk
carries `{doc_id, page, section, bbox, doc_type, product, region, version}`.

**Why:** Marketing claims must cite a section; coherent, section-scoped chunks
improve both citation precision and retrieval. But chunk size/overlap materially
move retrieval metrics, so the exact parameters are chosen empirically, not
assumed.

**Experiment (ablation grid):** chunk size {256, 512, 1024 tokens} × overlap
{0%, 15%} × strategy {recursive, semantic, layout-aware}. Metric: Recall@10 and
nDCG@10 on the golden set, plus RAGAS context precision on a generation subset.
Lock the winning configuration and record the table in the README.

**Result (M1, demo corpus):** implemented 6 strategies (fixed / recursive /
sentence / paragraph / structure / semantic) + a size-neutral **coverage-at-budget**
metric to de-bias the comparison. Findings: `fixed` is worst (clips facts),
`semantic` gives no gain at higher compute, and recursive/paragraph/structure tie
on retrieval. Default set to **`structure`** (hybrid: heading split + recursive
fallback for long sections + small-section packing) for its `section` citation
metadata; `recursive` is the auto-fallback on un-headed PDFs. Size locked at
`1000/150`. Re-confirm on the real PDF corpus. See README §M1 and docs/0004.

### 3.4 Embedding model

| Option | Notes |
|---|---|
| `BAAI/bge-large-en-v1.5` | Strong English, well-understood, needs query instruction prefix |
| **`BAAI/bge-m3`** | Multilingual (incl. Chinese), **produces dense + sparse + ColBERT vectors from one model** → natural fit for hybrid |
| `intfloat/e5-large-v2`, `gte-large` | Competitive English bi-encoders |
| Proprietary (Voyage / Cohere / OpenAI) | Often top accuracy; external dependency, cost, no local hosting |

**Decision:** **`BAAI/bge-m3`** as primary embedding model (self-hosted via
sentence-transformers / HF), with `bge-large-en-v1.5` as an English-only
challenger.

**Why:** (1) Open-source + HF + local inference hits three JD bullets directly.
(2) bge-m3 emits dense **and** learned-sparse vectors, so one model powers the
hybrid index — fewer moving parts. (3) Multilingual covers the Mandarin angle.
MTEB places it among the strong open models, but we still confirm in-domain.

**Experiment:** Index the corpus with each candidate; measure Recall@10 / nDCG@10
/ MRR on the golden set. Also record embedding latency and dimension (storage
cost). Choose by in-domain retrieval quality, breaking ties on latency.

**Result (M1, demo corpus):** `bge-small` / `bge-base` / `bge-large` score
*identically* (quality saturated on the small corpus); they differ only in cost
(index time 0.9 / 2.5 / 6.6 s; dim 384 / 768 / 1024). **Decision: keep `bge-small`**
(equal quality, ~7× faster, 2.7× smaller). `bge-m3` deferred to the multilingual /
real corpus where it can differentiate (Mandarin requirement). See README §M1 and
docs/0006.

### 3.5 Vector store

| Option | Verdict for this project |
|---|---|
| **Qdrant** | Native dense **+ sparse** vectors, server-side **fusion (RRF)**, rich payload filtering with indexes, HNSW + quantization, Docker-native, mature Python client |
| Chroma | Simplest DX; weaker hybrid/filtering at scale |
| FAISS | Fast library, but no metadata filtering/persistence/service out of the box |
| pgvector | Great if already on Postgres; hybrid+rerank ergonomics weaker |
| Pinecone/Weaviate | Capable; managed (Pinecone) or heavier (Weaviate) |

**Decision:** **Qdrant.**

**Why:** It is the only candidate that natively gives us *all* of: hybrid
(dense+sparse) retrieval, server-side RRF fusion, first-class metadata filtering
(the enterprise `product/doc_type/region/version` use case in idea.md), HNSW
tuning + quantization, and one-command Docker deployment. This collapses several
custom components into the database and is the defensible "production" choice.

**Experiment:** Validate metadata-filtered retrieval correctness (e.g.
`doc_type=compliance AND region=APAC`) and confirm hybrid recall ≥ dense-only on
the golden set (see 3.7). Sanity-check p95 query latency under concurrent load.

### 3.6 Indexing strategy

**Decisions & rationale:**
- **HNSW** index; distance = **cosine** (embeddings L2-normalized). HNSW is the
  standard recall/latency sweet spot for this corpus size.
- **Payload indexes** on `product`, `doc_type`, `region`, `version` so filtered
  queries stay fast and use the keyword index, not a brute scan.
- **Sparse vector index** alongside dense for the lexical arm of hybrid.
- **Quantization (scalar/int8)**: *not enabled initially* — corpus is small
  enough to keep full-precision vectors in RAM; revisit only if memory becomes a
  constraint (document the trade-off, don't pay it speculatively).

**Experiment:** Sweep `hnsw_ef` (search) and confirm the Recall@10 vs latency
curve; pick the knee. Measure recall delta if int8 quantization is enabled to
quantify the memory/accuracy trade-off for the README.

### 3.7 Hybrid search & fusion

| Lexical arm | Fusion method |
|---|---|
| BM25 (rank_bm25) or learned-sparse (bge-m3 / SPLADE) | **Reciprocal Rank Fusion (RRF)** — parameter-light, scale-invariant |
| | Weighted score normalization (min-max / z-score) — needs calibration |

**Decision:** **Hybrid = dense (bge-m3) + sparse, fused with RRF** via Qdrant's
Query API. Keep weighted fusion as a measured alternative.

**Why:** Dense retrieval misses exact tokens that matter in this domain — model
numbers ("X1 Carbon Gen 13"), spec figures ("18 hours"), compliance clause IDs.
Lexical retrieval nails those but misses paraphrase. Hybrid captures both. **RRF**
is chosen over weighted fusion because it needs no per-corpus score calibration
and is robust to the dense/sparse score-scale mismatch — fewer magic numbers to
justify.

**Experiment (headline result):** Compare on the golden set —
**dense-only vs BM25-only vs hybrid-RRF vs hybrid-weighted** — reporting
Recall@10, nDCG@10, MRR. Tune RRF `k` and (for weighted) the dense/sparse weight.
Expect hybrid > either alone; the table is a centerpiece of the README.

### 3.8 Reranking

| Option | Notes |
|---|---|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Light, fast, English |
| **`BAAI/bge-reranker-v2-m3`** | Strong, multilingual, open-source cross-encoder |
| `bge-reranker-large` | Strong English |
| Cohere Rerank | High quality, external API |
| LLM-as-reranker | Flexible, expensive/slow |

**Decision:** Two-stage retrieval — hybrid returns **top-N (≈30)**, a
**`bge-reranker-v2-m3` cross-encoder** rescues precision and returns **top-k (≈5)**
to the LLM.

**Why:** Bi-encoders embed query and doc independently; a cross-encoder attends to
the pair jointly and is consistently more precise at the top — exactly what a
generator needs (5 clean chunks beat 20 noisy ones). It is open-source and
multilingual, consistent with the rest of the stack.

**Experiment:** Measure nDCG@5 and RAGAS **context precision** with rerank ON vs
OFF, and `bge-reranker-v2-m3` vs `ms-marco-MiniLM`. Record the **added latency**
per query so the precision gain is weighed against cost. Decide N and k from the
recall(N)→precision(k) curve.

### 3.9 Multimodal / Vision-Language Model

| Option | Notes |
|---|---|
| **Claude Opus 4.8 (vision)** | High-resolution image support, strong reasoning, integrates with the same generation client |
| GPT-4o / Gemini | Capable; different vendor |
| **Qwen2.5-VL** (open-source) | Self-hostable; demonstrates OSS VLM skill |
| LLaVA | Older OSS baseline |

**Decision (per OSS-primary posture):** **Qwen2.5-VL** (self-hosted) as the primary
VLM, **Claude Opus 4.8 vision** as the quality-ceiling/escalation path. Flow:
product image → VLM extracts visual features/attributes → those become a
retrieval query into the KB → grounded marketing copy is generated (never
invented from the image alone).

**Why:** OSS-primary foregrounds self-hostable multimodal + GPU-inference skills
(JD). Qwen2.5-VL is a strong open VLM; Claude's high-res vision is the escalation
when the open model is uncertain, mirroring the text generation posture so the
reliability layer is consistent across modalities.

**Experiment:** On ~10 product images, check that VLM-extracted attributes
retrieve the correct product's KB chunks (retrieval hit rate), and that generated
copy contains no claim absent from retrieved context (faithfulness via RAGAS /
LLM-judge).

### 3.10 Agent orchestration framework

**Decision:** **LangGraph** (not vanilla LangChain chains).

Graph: `plan → retrieve_product → retrieve_brand → retrieve_compliance →
draft → fact_check → (conditional) revise → finalize`, with conditional edges
(e.g. fact-check failure routes back to revise) and per-node retries.

**Why:** The workflow is inherently a state machine with branching and loops
(fact-check can send the draft back). LangGraph models this explicitly with
typed state, conditional edges, checkpointing, and observability — vanilla
sequential chains hide control flow and make the fact-check loop awkward. This is
also the differentiated, enterprise-looking choice the JD rewards.

**Experiment:** Ablate the agent — single-shot RAG vs full graph (separate
brand/compliance retrieval + fact-check loop) — on faithfulness and a
brand/compliance-violation rate scored by an LLM judge. The graph should reduce
violations; quantify it.

### 3.11 Generation LLM + reliability

**Phase-0 starting point (current):** to start building RAG immediately without
GPU/serving infra, the generator is **DeepSeek (open-weight) via LangChain
`init_chat_model("deepseek-chat", model_provider="deepseek")`**. This keeps the
OSS-primary posture (DeepSeek is open-weight) while the model sits behind LangChain's
provider abstraction, so swapping to self-hosted vLLM or adding the Claude
fallback later is a config change, not a rewrite. **Self-host (vLLM) is deferred.**

**Target (OSS-primary + Claude ceiling):** **Primary = a self-hosted
open-source model** (e.g. Qwen2.5-72B-Instruct or Llama-3.3-70B served via
**vLLM**); **Fallback/ceiling = Claude Opus 4.8** (`claude-opus-4-8`). Reliability
layer: `tenacity` (timeout + exponential-backoff retry) → `pybreaker` (circuit
breaker) → Claude fallback.

**Source grounding is model-agnostic** (it must be — the open primary has no
native citation feature): the generator is constrained via **structured output**
to emit `{claim, source_chunk_ids[]}`, and a post-step **validates every claim's
chunk ids exist in the retrieved context** and resolves them to
`file + page + section` from chunk metadata. Claude's native document citations
are used as a *cross-check oracle* in evaluation and on the escalation path, not
as the load-bearing mechanism.

**Why:**
- OSS-primary directly foregrounds the JD's open-source LLM, Hugging Face, GPU
  inference, and self-hosting requirements — the default request path runs on a
  model we control.
- Claude Opus 4.8 as the **fallback/ceiling** makes the reliability layer real
  (primary vLLM down/slow → breaker opens → hosted Claude serves a grounded
  answer instead of a 500) *and* gives a strong reference for the quality gap.
- Decoupling grounding from any one vendor's citation API is more honest
  engineering and keeps the system swappable.

**Experiment:** (1) Compare OSS-primary vs Claude on faithfulness/answer-relevancy
on the golden set — quantify the quality gap accepted on the default path. (2)
Validate the structured-citation mechanism: % of claims with resolvable, in-context
chunk ids, and rate of unsupported claims caught. (3) Fault-injection: force vLLM
timeouts/5xx, assert the breaker opens and Claude serves a grounded answer.

### 3.12 Evaluation pipeline

**Decision:** **RAGAS** (faithfulness, answer relevancy, context precision,
context recall) + classic **retrieval metrics** (Recall@k, nDCG@10, MRR) + a
**golden set** + LLM-as-judge for brand/compliance-violation and abstention
("don't answer when unsupported"). One command: `python evaluation/run_eval.py`.

**Why:** Evaluation is the instrument behind every §3 experiment and is itself a
JD "good-to-have" (eval pipelines / hallucination detection). Retrieval metrics
isolate the retriever; RAGAS measures the end-to-end answer; the judge catches
the domain-specific failure (hallucinated features, brand/compliance breaches).

**Judge ≠ generator (bias control):** since the *generator* is the open-source
model, the **LLM judge and synthetic-QA generation use Claude Opus 4.8**. Keeping
the evaluator stronger than and distinct from the system-under-test avoids
self-preference bias and gives a credible upper-reference for quality.

**Targets (initial, to be reported honestly):** faithfulness ≥ 0.90, context
precision ≥ 0.80, answer relevancy ≥ 0.85, and **abstention** on negative
questions ≥ 0.90. Numbers are reported as measured, not asserted.

---

## 4. Decision summary table

| Step | Decision | Primary justification | Confirming experiment |
|---|---|---|---|
| Parse | PyMuPDF (+pdfplumber for tables) | Layout/bbox → citations; table fidelity | Extraction fidelity vs Docling |
| OCR | PaddleOCR (+VLM escalation), auto-detect scanned | Accuracy + tables + Chinese + local | CER/WER vs Tesseract/VLM |
| Chunk | Structure-aware + token-bounded + overlap | Citation precision + coherence | Size×overlap×strategy ablation |
| Embed | bge-m3 (vs bge-large) | OSS/local, multilingual, dense+sparse | In-domain Recall@10/nDCG |
| Store | Qdrant | Native hybrid + filtering + Docker | Filtered-retrieval correctness, latency |
| Index | HNSW, cosine, payload indexes, no quant (yet) | Recall/latency knee; filter speed | ef sweep; quant trade-off |
| Search | Hybrid dense+sparse, RRF fusion | Exact-term + semantic; calibration-free | dense/BM25/hybrid comparison |
| Rerank | bge-reranker-v2-m3, top-30→top-5 | Cross-encoder precision at top-k | nDCG@5 + latency, rerank on/off |
| VLM | Qwen2.5-VL primary + Claude vision ceiling | OSS/self-host breadth; Claude escalation | Image→KB retrieval hit rate |
| Agent | LangGraph | Branching + fact-check loop, observability | Agent-on/off violation rate |
| LLM | OSS primary (vLLM) + Claude fallback | OSS/GPU/self-host + reliability ceiling | Quality gap + citation validity + fault injection |
| Grounding | Structured `{claim, chunk_ids}` + validation | Model-agnostic; not vendor-locked to citations | % resolvable, in-context claims |
| Eval | RAGAS + retrieval metrics + golden set; Claude judge | Instrument for all decisions; bias-controlled judge | (is the instrument) |

---

## 5. Milestones

- **M0 — Eval backbone (gate):** demo corpus assembled; golden set built;
  `run_eval.py` runs end-to-end on a trivial baseline retriever.
- **M1 — Ingestion:** parse + OCR + structure-aware chunk + embed + index into
  Qdrant with metadata. Run §3.1–3.4 experiments; lock parse/OCR/chunk/embed.
- **M2 — Retrieval:** hybrid search + RRF + reranker behind a `Retriever`
  interface. Run §3.6–3.8 experiments; lock indexing/fusion/rerank. **Headline
  retrieval table produced.**
- **M3 — Generation + grounding:** Claude generation with native citations
  (claim→source). RAGAS targets met on golden set.
- **M4 — Agent:** LangGraph plan→retrieve×3→draft→fact-check→revise. Run agent
  ablation.
- **M5 — Multimodal:** image upload → VLM → KB retrieval → marketing copy.
- **M6 — Reliability + API + Docker:** tenacity/pybreaker fallback; FastAPI
  endpoints; `docker-compose up` (api + qdrant + redis). Fault-injection test.
- **M7 — Polish:** README with all decision tables and measured numbers; CI;
  optional GraphRAG/Neo4j stretch.

Sequencing rule: **no component is declared "done" until its confirming
experiment has run and the result is recorded in the README.**

---

## 6. Resolved scope decisions

Confirmed with the user:

1. **LLM posture → OSS-primary + Claude ceiling.** Default request path runs a
   self-hosted open model via vLLM; Claude Opus 4.8 is the reliability fallback,
   the eval judge/QA generator, and the multimodal escalation. Grounding is
   model-agnostic (structured claims + chunk-id validation), not tied to Claude's
   native citations. (See §3.9, §3.11, §3.12.)
2. **Corpus → assemble a public demo corpus.** Gather ThinkPad-style spec sheets,
   brand guidelines, and security whitepapers, plus a few scanned PDFs and
   product images so every ingestion path (digital text, tables, OCR, vision) is
   exercised. (See §2.1.)
3. **GraphRAG/Neo4j → deferred to the M7 stretch milestone.** Ship the measured
   hybrid + rerank + agent + eval baseline first; add a graph-search arm only
   after the baseline numbers are solid.

---

## 7. Repository structure (target)

```
enterprise-marketing-agent/
├── api/              # FastAPI app + endpoints
├── ingestion/        # parse, ocr, chunking, embed, index
├── retrieval/        # vector_search, bm25/sparse, hybrid, reranker (interfaces)
├── agents/           # LangGraph graph + nodes (plan/retrieve/draft/factcheck)
├── llm/              # provider abstraction + reliability (tenacity/pybreaker)
├── evaluation/       # golden_set.jsonl, run_eval.py, experiment scripts
├── experiments/      # ablation scripts + results tables (reproducible)
├── tests/
├── demo_data/
├── docker-compose.yml
└── README.md         # architecture + decision tables WITH measured numbers
```
