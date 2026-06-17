"""Evaluation harness — the instrument behind every retrieval/generation decision.

Retrieval metrics (default, fast, free, deterministic):
  Recall@k, MRR, nDCG@k over the golden set, plus answer-keyword coverage.
Generation metrics (--generation, uses the LLM judge, costs API calls):
  faithfulness, answer relevancy, and abstention accuracy on negative questions.

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


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG evaluation harness")
    ap.add_argument("--reindex", action="store_true", help="Rebuild the index from manifest first")
    ap.add_argument("--no-rerank", action="store_true", help="Ablation: hybrid only, skip reranker")
    ap.add_argument("--generation", action="store_true", help="Also run LLM-judged generation metrics")
    ap.add_argument("--top-k", type=int, default=settings.top_k)
    args = ap.parse_args()

    client = get_client()
    if args.reindex:
        n = reindex(client)
        print(f"Reindexed {n} chunks from manifest.\n")

    golden = load_golden()
    answerable = [g for g in golden if g["type"] != "negative"]
    negatives = [g for g in golden if g["type"] == "negative"]

    print("=== Config ===")
    print(f"  dense={settings.dense_model}  sparse={settings.sparse_model}")
    print(f"  rerank={'OFF' if args.no_rerank else settings.reranker_model}")
    print(f"  top_k={args.top_k}  chunk_size={settings.chunk_size}/{settings.chunk_overlap}\n")

    # --- Retrieval metrics ---
    recalls, rrs, ndcgs, covs = [], [], [], []
    for g in answerable:
        points = get_points(g["question"], args.no_rerank, args.top_k)
        flags = [p.payload.get("source") in g["relevant_sources"] for p in points]
        recalls.append(recall_at_k(flags))
        rrs.append(reciprocal_rank(flags))
        ndcgs.append(ndcg_at_k(flags, args.top_k))
        context = " ".join(p.payload.get("text", "") for p in points)
        cov = keyword_coverage(context, g.get("answer_keywords"))
        if cov is not None:
            covs.append(cov)

    print(f"=== Retrieval (n={len(answerable)}) ===")
    print(f"  Recall@{args.top_k}:            {mean(recalls):.3f}")
    print(f"  MRR:                  {mean(rrs):.3f}")
    print(f"  nDCG@{args.top_k}:              {mean(ndcgs):.3f}")
    print(f"  Answer-kw coverage:   {mean(covs):.3f}")

    # --- Generation metrics (optional) ---
    if args.generation:
        from evaluation.judge import judge_answer
        from llm.generator import generate

        faiths, rels, abst_ok = [], [], []
        print(f"\n=== Generation (LLM judge: {settings.llm_model}; judge==generator, bias caveat) ===")
        for g in answerable:
            points = get_points(g["question"], args.no_rerank, args.top_k)
            context = "\n\n".join(p.payload.get("text", "") for p in points)
            answer = generate(g["question"], points)
            verdict = judge_answer(g["question"], context, answer)
            if verdict["faithfulness"] is not None:
                faiths.append(verdict["faithfulness"])
            if verdict["relevancy"] is not None:
                rels.append(verdict["relevancy"])
        for g in negatives:
            points = get_points(g["question"], args.no_rerank, args.top_k)
            context = "\n\n".join(p.payload.get("text", "") for p in points)
            answer = generate(g["question"], points)
            verdict = judge_answer(g["question"], context, answer)
            abst_ok.append(1.0 if verdict["abstained"] else 0.0)

        print(f"  Faithfulness:         {mean(faiths):.3f}")
        print(f"  Answer relevancy:     {mean(rels):.3f}")
        print(f"  Abstention (neg n={len(negatives)}): {mean(abst_ok):.3f}")


if __name__ == "__main__":
    main()
