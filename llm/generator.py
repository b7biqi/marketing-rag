"""Grounded generation via DeepSeek (LangChain init_chat_model).

The model is constrained to answer ONLY from retrieved context and to cite each
claim by chunk index. Grounding is model-agnostic (PROJECT_PLAN.md §3.11): we
hand the model numbered context blocks and resolve [n] citations back to
file/page from chunk metadata — no vendor-specific citation API.
"""
from __future__ import annotations

import os
from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings

SYSTEM_PROMPT = """You are an enterprise marketing content assistant for a \
hardware company. You write product marketing copy and answer questions using \
ONLY the provided source context.

Rules:
- Use only facts present in the numbered context blocks. Never invent product \
features, specifications, or claims.
- Cite every factual claim with its source index in square brackets, e.g. \
"battery life up to 18 hours [2]".
- If the context does not contain enough information to answer or to support a \
requested claim, say so explicitly instead of guessing.
- Respect brand and compliance guidance found in the context.
"""


@lru_cache(maxsize=1)
def get_llm():
    if settings.deepseek_api_key:
        os.environ.setdefault("DEEPSEEK_API_KEY", settings.deepseek_api_key)
    return init_chat_model(
        settings.llm_model,
        model_provider=settings.llm_provider,
        temperature=0,
    )


def format_context(points) -> str:
    blocks = []
    for i, p in enumerate(points, start=1):
        md = p.payload or {}
        source = md.get("source", "?")
        page = md.get("page", "?")
        blocks.append(f"[{i}] (source: {source}, page {page})\n{md.get('text', '')}")
    return "\n\n".join(blocks)


def generate(query: str, points, task: str | None = None) -> str:
    """task: optional instruction, e.g. 'Write a LinkedIn post for CIOs'.
    If omitted, answer the query directly."""
    context = format_context(points)
    instruction = task or query
    user_prompt = (
        f"CONTEXT:\n{context}\n\n"
        f"TASK:\n{instruction}\n\n"
        f"Write the response now, citing sources by index."
    )
    response = get_llm().invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    return response.content


def sources_table(points) -> list[dict]:
    """Resolve citation indices to their source metadata for display."""
    table = []
    for i, p in enumerate(points, start=1):
        md = p.payload or {}
        table.append({
            "index": i,
            "source": md.get("source", "?"),
            "page": md.get("page", "?"),
            "doc_type": md.get("doc_type", "?"),
        })
    return table
