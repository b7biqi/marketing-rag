"""Central configuration. Every component reads from here so choices are swappable.

Env vars (see .env.example) override any field; field name upper-cased is the env key.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Qdrant ---
    # If qdrant_url is set, connect to the server; otherwise use embedded local mode.
    qdrant_url: str | None = None
    qdrant_path: str = "./qdrant_data"
    collection_name: str = "marketing_rag"

    # --- Embedding / retrieval models (fastembed = ONNX, no torch) ---
    # These are dev defaults chosen for speed. The embedding/reranker choice is an
    # M1/M2 experiment (see PROJECT_PLAN.md §3.4, §3.8) — swap and re-measure.
    dense_model: str = "BAAI/bge-small-en-v1.5"      # 384-dim, fast
    sparse_model: str = "Qdrant/bm25"                # lexical arm of hybrid
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # --- Chunking ---
    # Strategy chosen by experiment (experiments/ablate_strategy.py). On the demo
    # corpus structure/recursive/paragraph tie on coverage; "structure" (hybrid:
    # heading split + recursive fallback + small-section packing) is the default
    # because it adds `section` metadata for citations and degrades to recursive
    # on un-headed PDFs. Options: fixed | recursive | sentence | paragraph |
    # structure | semantic.
    chunk_strategy: str = "structure"
    chunk_size: int = 1000     # ~250 tokens (size budget per chunk)
    chunk_overlap: int = 150

    # --- Retrieval ---
    top_n: int = 30            # hybrid candidates fed to the reranker
    top_k: int = 5             # reranked chunks handed to the LLM

    # --- LLM (LangChain init_chat_model) ---
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    deepseek_api_key: str | None = None


settings = Settings()
