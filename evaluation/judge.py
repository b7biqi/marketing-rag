"""LLM-as-judge for generation quality (faithfulness / relevancy / abstention).

NOTE on bias: for a first pass the judge reuses the generation model (DeepSeek).
Judge == generator risks self-preference bias (PROJECT_PLAN.md §3.12); the target
is to point the judge at a stronger, different model (Claude). The judge model is
therefore isolated here so it can be swapped without touching the runner.
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llm.generator import get_llm

JUDGE_SYSTEM = "You are a strict RAG evaluation judge. Respond with ONLY a JSON object, no prose."


def judge_answer(question: str, context: str, answer: str) -> dict:
    prompt = f"""Evaluate the ANSWER using the CONTEXT and QUESTION.
Return a JSON object with exactly these fields:
- "faithfulness": number from 0 to 1 = fraction of the answer's factual claims \
directly supported by the CONTEXT (1 if fully grounded, 0 if unsupported).
- "relevancy": number from 0 to 1 = how well the answer addresses the QUESTION.
- "abstained": boolean = true if the answer declines, or states the information \
is not available in the provided context.

QUESTION: {question}

CONTEXT:
{context}

ANSWER:
{answer}

Return only the JSON object."""
    resp = get_llm().invoke(
        [SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=prompt)]
    )
    return _parse(resp.content)


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except Exception:
        return {"faithfulness": None, "relevancy": None, "abstained": None}
    return {
        "faithfulness": _num(data.get("faithfulness")),
        "relevancy": _num(data.get("relevancy")),
        "abstained": bool(data.get("abstained")),
    }


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
