"""Pure retrieval metrics (no external deps, deterministic).

Each function takes `relevant_flags`: a list of booleans in retrieved-rank order,
where True means the chunk at that rank is relevant to the query.
"""
from __future__ import annotations

import math


def recall_at_k(relevant_flags: list[bool]) -> float:
    """1.0 if any relevant chunk was retrieved in the top-k, else 0.0."""
    return 1.0 if any(relevant_flags) else 0.0


def reciprocal_rank(relevant_flags: list[bool]) -> float:
    """1 / rank of the first relevant chunk (0 if none)."""
    for i, rel in enumerate(relevant_flags, start=1):
        if rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(relevant_flags: list[bool], k: int) -> float:
    """Binary-relevance nDCG over the top-k."""
    flags = relevant_flags[:k]
    dcg = sum(1.0 / math.log2(i + 2) for i, rel in enumerate(flags) if rel)
    n_rel = sum(1 for rel in relevant_flags if rel)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(n_rel, k)))
    return dcg / ideal if ideal > 0 else 0.0


def keyword_coverage(context: str, keywords: list[str]) -> float | None:
    """Fraction of expected answer keywords present in the retrieved context.

    Measures whether the *specific* answer text made it into context (a sharper
    signal than source-level recall on a small corpus). None if no keywords.
    """
    if not keywords:
        return None
    ctx = context.lower()
    hits = sum(1 for kw in keywords if kw.lower() in ctx)
    return hits / len(keywords)


def coverage_at_budget(
    texts_in_rank_order: list[str], keywords: list[str], budget_chars: int
) -> float | None:
    """Keyword coverage within a fixed *context budget*, not a fixed chunk count.

    Fills the budget greedily with whole chunks in rank order, then measures
    coverage. This de-biases chunk-size/strategy comparison: bigger chunks fill the
    budget with fewer, more-contiguous chunks; smaller chunks fit more, more-diverse
    chunks. Same budget for all → a fair "how much answer per token of context" test.
    """
    if not keywords:
        return None
    acc: list[str] = []
    total = 0
    for t in texts_in_rank_order:
        acc.append(t)
        total += len(t)
        if total >= budget_chars:
            break
    return keyword_coverage(" ".join(acc), keywords)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0
