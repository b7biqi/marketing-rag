"""Evaluation harness — the instrument behind every retrieval/generation decision.

Retrieval metrics (default, fast, free, deterministic):
  Recall@k, MRR, nDCG@k over the golden set, plus answer-keyword coverage.
Generation metrics (--generation, uses the LLM judge, costs API calls):
  faithfulness, answer relevancy, and abstention accuracy on negative questions.

The metric computations are exposed as functions (evaluate_retrieval /
evaluate_generation) so experiment scripts (experiments/) can reuse them.

Usage:
  python -m evaluation.run_eval --reindex                 # rebuild index, then eval
  python -m evaluation.run_eval --no-rerank               # ablation: rerank off
  python -m evaluation.run_eval --generation              # add LLM-judged metrics
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import settings
from evaluation.metrics import (
    keyword_coverage,
    mean,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from ingestion.corpus import reindex
from ingestion.indexer import get_client
from retrieval.retriever import hybrid_search, retrieve

GOLDEN = Path("evaluation/golden_set.jsonl")


def load_golden() -> list[dict]:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def get_points(question: str, no_rerank: bool, top_k: int):
    if no_rerank:
        return hybrid_search(question)[:top_k]
    return retrieve(question, top_k=top_k)


def evaluate_retrieval(golden: list[dict], no_rerank: bool, top_k: int) -> dict:
    """Compute retrieval metrics over the answerable questions. Returns a dict."""
    answerable = [g for g in golden if g["type"] != "negative"]
    recalls, rrs, ndcgs, covs = [], [], [], []
    for g in answerable:
        points = get_points(g["question"], no_rerank, top_k)
        flags = [p.payload.get("source") in g["relevant_sources"] for p in points]
        recalls.append(recall_at_k(flags))
        rrs.append(reciprocal_rank(flags))
        ndcgs.append(ndcg_at_k(flags, top_k))
        context = " ".join(p.payload.get("text", "") for p in points)
        cov = keyword_coverage(context, g.get("answer_keywords"))
        if cov is not None:
            covs.append(cov)
    return {
        "n": len(answerable),
        "recall": mean(recalls),
        "mrr": mean(rrs),
        "ndcg": mean(ndcgs),
        "coverage": mean(covs),
    }


def evaluate_generation(golden: list[dict], no_rerank: bool, top_k: int) -> dict:
    """Generate answers and score them with the LLM judge. Returns a dict."""
    from evaluation.judge import judge_answer
    from llm.generator import generate

    answerable = [g for g in golden if g["type"] != "negative"]
    negatives = [g for g in golden if g["type"] == "negative"]

    faiths, rels, abst_ok = [], [], []
    for g in answerable:
        points = get_points(g["question"], no_rerank, top_k)
        context = "\n\n".join(p.payload.get("text", "") for p in points)
        answer = generate(g["question"], points)
        verdict = judge_answer(g["question"], context, answer)
        if verdict["faithfulness"] is not None:
            faiths.append(verdict["faithfulness"])
        if verdict["relevancy"] is not None:
            rels.append(verdict["relevancy"])
    for g in negatives:
        points = get_points(g["question"], no_rerank, top_k)
        context = "\n\n".join(p.payload.get("text", "") for p in points)
        answer = generate(g["question"], points)
        verdict = judge_answer(g["question"], context, answer)
        abst_ok.append(1.0 if verdict["abstained"] else 0.0)

    return {
        "faithfulness": mean(faiths),
        "relevancy": mean(rels),
        "abstention": mean(abst_ok),
        "n_neg": len(negatives),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG evaluation harness")
    ap.add_argument("--reindex", action="store_true", help="Rebuild the index from manifest first")
    ap.add_argument("--no-rerank", action="store_true", help="Ablation: hybrid only, skip reranker")
    ap.add_argument("--generation", action="store_true", help="Also run LLM-judged generation metrics")
    ap.add_argument("--top-k", type=int, default=settings.top_k)
    args = ap.parse_args()

    if args.reindex:
        n = reindex(get_client())
        print(f"Reindexed {n} chunks from manifest.\n")

    golden = load_golden()

    print("=== Config ===")
    print(f"  dense={settings.dense_model}  sparse={settings.sparse_model}")
    print(f"  rerank={'OFF' if args.no_rerank else settings.reranker_model}")
    print(f"  top_k={args.top_k}  chunk_size={settings.chunk_size}/{settings.chunk_overlap}\n")

    r = evaluate_retrieval(golden, args.no_rerank, args.top_k)
    print(f"=== Retrieval (n={r['n']}) ===")
    print(f"  Recall@{args.top_k}:            {r['recall']:.3f}")
    print(f"  MRR:                  {r['mrr']:.3f}")
    print(f"  nDCG@{args.top_k}:              {r['ndcg']:.3f}")
    print(f"  Answer-kw coverage:   {r['coverage']:.3f}")

    if args.generation:
        g = evaluate_generation(golden, args.no_rerank, args.top_k)
        print(f"\n=== Generation (LLM judge: {settings.llm_model}; judge==generator, bias caveat) ===")
        print(f"  Faithfulness:         {g['faithfulness']:.3f}")
        print(f"  Answer relevancy:     {g['relevancy']:.3f}")
        print(f"  Abstention (neg n={g['n_neg']}): {g['abstention']:.3f}")


if __name__ == "__main__":
    main()
