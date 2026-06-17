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

### OCR (scanned PDFs / image files)

Image files (`.png/.jpg/...`) and PDF pages with no text layer are OCR'd with
RapidOCR (ONNX, no torch; Chinese-capable) and flow through the same chunking →
retrieval → generation path. Validate the path (rasterizes a digital page to an
image-only PDF, OCRs it, ~90% char recovery):

```bash
MANIFEST_PATH=corpus/manifest.json python -m experiments.test_ocr
```

The current PSREF corpus is all-digital (nothing to OCR); this is a validated
capability for scanned documents. Toggle with `OCR_ENABLED`.

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

### M1 — chunking ablations

**Size × overlap** (`python -m experiments.ablate_chunking`, `top_k=3`):

| chunk_size | overlap | chunks | nDCG | kw coverage |
|---|---|---|---|---|
| 300 | 0 / 45 | 47 | 0.981 | 0.792 |
| 500 | 0 / 75 | 26 | 0.987 | 0.833 |
| **1000** | **150** | 14 | **0.993** | 1.000 |

→ Larger chunks keep related facts together; overlap is negligible. **Keep `1000/150`.**

**Strategy** (`python -m experiments.ablate_strategy`) — judged on **coverage at a
fixed context budget** (size-neutral, so a strategy isn't rewarded for bigger
chunks), on an 8-doc corpus that includes a deliberate **long-section** stress doc:

| strategy | nDCG | cov@budget | note |
|---|---|---|---|
| fixed | 0.980 | 0.926 | blind splits clip facts — **worst** |
| recursive | 0.988 | 0.981 | strong, simple |
| sentence | 0.980 | 0.981 | never splits a sentence |
| paragraph | 0.988 | 0.981 | |
| **structure** (hybrid) | 0.983 | 0.981 | **+ `section` metadata for citations**; degrades to recursive on un-headed PDFs |
| semantic | 0.988 | 0.833 | topic-split lost coverage; highest compute |

→ recursive / paragraph / structure **tie** on retrieval; `fixed` and `semantic`
lose. **Decision: default to `structure`** — tied on quality but uniquely supplies
section-level citations (claim → file + section) and handles long *and* short
sections in one adaptive strategy (heading split + recursive fallback for long
sections + small-section packing). `recursive` is the automatic fallback when no
headings are detected (e.g. raw PDFs).

> The size-bias caveat from the first pass is now addressed by the `cov@budget`
> metric. Remaining caveat: the LLM judge reuses the generator (DeepSeek) — target
> is a Claude judge. Strategy choice is corpus-dependent; re-run on the real PDF
> corpus (where structure-aware should pull further ahead) before locking.

### M1 — embedding model (`python -m experiments.ablate_embedding`)

Re-embed the corpus per model (collection rebuilt for the new dim), chunking +
reranker fixed, `top_k=2`:

| model | dim | index time | nDCG | cov@budget |
|---|---|---|---|---|
| **bge-small-en-v1.5** | 384 | **0.9 s** | 0.986 | 0.981 |
| bge-base-en-v1.5 | 768 | 2.5 s | 0.986 | 0.981 |
| bge-large-en-v1.5 | 1024 | 6.6 s | 0.986 | 0.981 |

→ **Identical quality, very different cost.** On a saturated corpus the bigger
models buy nothing, so the decision is cost: **keep `bge-small`** (~7× faster
indexing, 2.7× smaller vectors). `bge-m3` (multilingual, native sparse) is the
candidate to revisit for the **Mandarin/multilingual** requirement and a harder
corpus — measured then, not paid for speculatively now.

## Real corpus (public Lenovo PSREF PDFs)

Real spec sheets are **fetched on demand** (gitignored — we don't redistribute
copyrighted PDFs); the repo commits the manifest of public URLs + a fetch script.

```bash
python -m scripts.fetch_corpus            # download PDFs listed in corpus/manifest.json
MANIFEST_PATH=corpus/manifest.json GOLDEN_PATH=corpus/golden_set.jsonl \
  python -m evaluation.run_eval --reindex --generation --top-k 5
```

Real-corpus eval (3 PDFs, **85 chunks** — finally non-saturating). The first pass
exposed real-world failures; a per-question diagnostic (`evaluation/diagnose.py`)
located the cause, and the fix (boilerplate filtering + contextual chunking,
docs/0008) recovered most of the gap:

| metric | naive PDF ingest | + boilerplate filter & contextual chunks |
|---|---|---|
| Recall@5 | 1.000 | 1.000 |
| nDCG@5 | 0.946 | 0.977 |
| answer-kw coverage | **0.556** | **0.944** |
| faithfulness | 0.778 | 0.944 |
| abstention (neg) | 0.500 | **1.000** |

→ The failure was **not** column interleaving (a tempting guess). Diagnosis showed
the right *document* was always retrieved, but repeated boilerplate (page titles,
"PSREF") and the *wrong product's* same-field chunk outranked the real value. Fix:
drop cross-page boilerplate in the parser, and prefix each chunk with
`product — section` so "Max Memory: 128GB" is product-disambiguated. Coverage
0.556 → 0.944. Abstention 0.5 → 1.0 came from tightening the prompt to forbid
outside-knowledge inference. Grounding holds throughout (abstains rather than
inventing). This is the kind of finding synthetic data hides — and why diagnosing
beats guessing.

**Ablations re-run on the real corpus** (docs/0009) confirm the demo-corpus
decisions hold — with honest nuance: `bge-small` still ties bigger models on
de-biased metrics; `structure`'s *retrieval* edge disappears on real PDFs (cov@budget
tied, nDCG marginally behind fixed/recursive), so its kept-default justification is
now purely **section-level citations**. The real golden set is small (9 answerable),
so these are directional, not statistically strong — expanding it is a follow-up.

## Layout

```
config.py            # central, swappable configuration
ingestion/           # parser (+ OCR), chunking, embeddings, indexer, corpus (manifest)
retrieval/           # hybrid search (RRF) + cross-encoder rerank
llm/                 # DeepSeek generation + model-agnostic grounding
evaluation/          # golden_set.jsonl, metrics, judge, run_eval.py
experiments/         # ablation scripts (ablate_chunking.py, ...)
scripts/             # ingest.py, query.py, reindex.py, fetch_corpus.py CLIs
demo_data/           # synthetic demo docs + manifest.json (zero-setup default)
corpus/              # real corpus: manifest of public PDF URLs (PDFs gitignored)
docs/                # per-commit decision log
```

## Next (evidence-backed priorities)

- **Expand the real golden set** — 9 answerable Qs gives only directional signal;
  more questions would make the strategy/embedding calls statistically confident.
- **OCR the no-text pages** — each PSREF PDF has 1 page with no text layer (skipped);
  the OCR/multimodal milestone.
- **M2:** fusion (RRF vs weighted) and reranker (`bge-reranker-v2-m3` vs ms-marco);
  add multilingual content to exercise `bge-m3`.
