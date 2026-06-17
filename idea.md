Requirements

Must Have
• Hands-on experience with:
• Retrieval-Augmented Generation (RAG)
• Multimodal AI / Vision-Language Models (VLMs)
• LLM application development
• Experience building or deploying:
• document AI systems
• chatbot/agentic workflows
• OCR + LLM pipelines
• semantic search systems
• AI APIs/services
• Strong Python skills
• Experience with at least some of the following:
• LangChain / LangGraph
• Vector databases (ChromaDB, FAISS, Qdrant, Pinecone, etc.)
• Open-source LLMs
• FastAPI / Flask
• Docker
• Hugging Face
• Prompt engineering
• Experience working with:
• PDFs
• images
• OCR
• embeddings
• reranking
• retrieval pipelines
• Mandarin communication skills preferred

Good to Have
• Agentic AI workflows
• GraphRAG / Knowledge Graphs
• Evaluation pipelines / hallucination detection
• GPU inference optimization
• Cloud deployment (AWS/GCP/Azure)
• CI/CD or MLOps exposure

Responsibilities
• Design and develop RAG and multimodal AI applications
• Build scalable AI pipelines for document and knowledge retrieval
• Integrate LLMs with internal systems and APIs
• Optimize retrieval quality, latency, and response accuracy
• Work on production deployment, monitoring, and evaluation of AI systems
• Collaborate with cross-functional teams to deliver enterprise AI solutions


----
AI response:


The project should demonstrate:

* RAG
* Agentic workflow
* Vector database
* OCR
* Multimodal support
* Evaluation
* Production APIs
* Docker deployment

That's almost every keyword in the JD.

# Project Idea

## Enterprise Marketing Content Agent

**Problem:**

Marketing teams need to create product content from company documentation without hallucinating features or violating brand guidelines.

The AI system should:

* Search internal product knowledge
* Search marketing guidelines
* Search compliance documents
* Generate marketing content
* Cite sources
* Support PDF and image ingestion

---

# MVP Requirements

## 1. Document Ingestion Pipeline

Input:

```text
PDF
DOCX
TXT
Images
```

Supported examples:

```text
ThinkPad Product Spec.pdf
Brand Guidelines.pdf
Security Whitepaper.pdf
Product Image.png
```

Pipeline:

```text
Document
 ↓
Extract
 ↓
Chunk
 ↓
Embed
 ↓
Store
```

Skills demonstrated:

* OCR
* chunking
* embeddings
* vector db

Libraries:

```python
unstructured
pymupdf
paddleocr
sentence-transformers
```

---

## 2. Vector Database

Use:

### Option A

```text
Qdrant
```

Best interview choice.

or

### Option B

```text
Chroma
```

Simpler.

Store metadata:

```json
{
  "product": "ThinkPad X1",
  "doc_type": "spec",
  "region": "APAC",
  "version": "2025"
}
```

Demonstrates:

* metadata filtering
* enterprise retrieval

---

# 3. Hybrid Search

Implement:

```text
BM25
+
Vector Search
```

Then merge results.

This is something many candidates don't build.

Architecture:

```text
User Query
    ↓
BM25
    ↓
Vector Search
    ↓
Merge
    ↓
Rerank
```

---

# 4. Reranking

Use:

```python
BAAI/bge-reranker-large
```

or

```python
cross-encoder/ms-marco
```

Pipeline:

```text
Top 20 retrieved
       ↓
Reranker
       ↓
Top 5
       ↓
LLM
```

This immediately makes your project look more production-ready.

---

# 5. Agent Workflow

Use:

### LangGraph

instead of vanilla LangChain.

Workflow:

```text
User Request
      ↓
Planner
      ↓
Retrieve Product Info
      ↓
Retrieve Brand Guidelines
      ↓
Retrieve Compliance Rules
      ↓
Generate Draft
      ↓
Fact Check
      ↓
Final Output
```

Example:

```text
Generate LinkedIn post
for ThinkPad security features
targeting CIOs
```

Agent decides:

```text
Tool 1:
Product Search

Tool 2:
Brand Search

Tool 3:
Compliance Search
```

---

# 6. Source Grounding

Generated output should contain:

```text
Claim:
Battery life up to 18 hours

Source:
ThinkPad_X1_Spec.pdf
Section 3.2
```

This is very impressive in interviews.

---

# 7. Multimodal Component

This directly targets the Lenovo JD.

Input:

```text
Product Image
```

System should:

```text
Image
 ↓
Vision Model
 ↓
Describe Features
 ↓
Search Knowledge Base
 ↓
Generate Marketing Copy
```

Possible models:

* LLaVA
* Qwen-VL
* GPT-4o
* Gemini

Example:

Upload:

```text
ThinkPad laptop image
```

Output:

```text
Product description
Marketing headline
Feature summary
```

---

# 8. OCR Pipeline

Support scanned PDFs.

Flow:

```text
Image PDF
 ↓
PaddleOCR
 ↓
Text Extraction
 ↓
Chunking
 ↓
Embedding
```

This checks another Lenovo requirement.

---

# 9. Evaluation Pipeline

Almost nobody includes this.

Add:

```text
evaluation/
```

Use:

### RAGAS

Metrics:

```text
faithfulness
context_precision
answer_relevancy
```

Example:

```bash
python evaluate.py
```

Generates:

```json
{
  "faithfulness": 0.91,
  "relevancy": 0.88
}
```

Interviewers love seeing evaluation.

---

# 10. FastAPI Service

Expose endpoints.

```python
POST /ingest

POST /query

POST /generate-marketing-content

POST /upload-image

GET /health
```

Demonstrates production engineering.

---

# 11. Reliability Layer

Since you've already worked on this area, this can become your differentiator.

Add:

```python
tenacity
pybreaker
```

Architecture:

```text
Primary LLM
     ↓
Timeout
     ↓
Retry
     ↓
Circuit Breaker
     ↓
Fallback LLM
```

Most GitHub RAG demos completely ignore this.

---

# 12. Docker

Provide:

```text
docker-compose.yml
```

Services:

```text
api
qdrant
redis
```

One command:

```bash
docker compose up
```

---

# Nice-to-Have (Stand Out)

## GraphRAG

Create:

```text
ThinkPad X1
    |
uses
    |
Intel Processor
```

Store in:

```text
Neo4j
```

Agent decides:

```text
Vector Search
or
Graph Search
```

This maps directly to Lenovo's "Good to Have".

---

# GitHub Structure

```text
enterprise-marketing-agent/
│
├── api/
│   └── fastapi_app.py
│
├── ingestion/
│   ├── pdf_parser.py
│   ├── image_parser.py
│   └── chunking.py
│
├── retrieval/
│   ├── vector_search.py
│   ├── bm25_search.py
│   └── reranker.py
│
├── agents/
│   └── marketing_agent.py
│
├── evaluation/
│   └── ragas_eval.py
│
├── tests/
│
├── docker-compose.yml
│
├── README.md
│
└── demo_data/
```

# What Would Impress a Lenovo Interviewer Most?

If you only have time for a few features, prioritize:

1. Hybrid Search (BM25 + Vector)
2. Reranking
3. LangGraph Agent
4. OCR Support
5. Source Citations
6. FastAPI
7. Docker
8. Evaluation (RAGAS)

That combination looks much closer to a real enterprise AI platform than the typical "upload PDF and chat" project that many candidates bring to interviews.
