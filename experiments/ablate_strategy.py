"""M1 ablation: chunking strategy, measured on the golden set (PROJECT_PLAN.md §3.3).

Holds chunk_size fixed (the M1 size winner) and varies the strategy
(fixed / recursive / sentence / paragraph / structure / semantic). The index is
rebuilt per strategy so only the strategy changes.

Headline metric is **coverage @ fixed context budget** — size-neutral, so a
strategy isn't rewarded just for producing bigger chunks. Ranking metrics
(Recall/MRR/nDCG) and raw coverage@k are reported alongside.

Usage:
    python -m experiments.ablate_strategy
    python -m experiments.ablate_strategy --top-k 3 --budget 1000
"""
from __future__ import annotations

import argparse

from config import settings
from evaluation.run_eval import evaluate_retrieval, load_golden
from ingestion.chunkers import STRATEGIES
from ingestion.corpus import reindex
from ingestion.indexer import get_client


def main() -> None:
    ap = argparse.ArgumentParser(description="Chunking strategy ablation")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--budget", type=int, default=1000, help="context budget in chars")
    args = ap.parse_args()

    golden = load_golden()
    client = get_client()

    print(f"Strategy ablation (top_k={args.top_k}, budget={args.budget} chars, "
          f"size={settings.chunk_size}/{settings.chunk_overlap}, rerank on, "
          f"dense={settings.dense_model})\n")
    header = (f"{'strategy':>10} {'chunks':>7} {'Recall':>7} {'MRR':>6} "
              f"{'nDCG':>6} {'cov@k':>6} {'cov@budget':>11}")
    print(header)
    print("-" * len(header))

    rows = []
    for name in STRATEGIES:
        settings.chunk_strategy = name
        n = reindex(client)
        m = evaluate_retrieval(golden, no_rerank=False, top_k=args.top_k, budget_chars=args.budget)
        rows.append((name, n, m))
        print(f"{name:>10} {n:>7} {m['recall']:>7.3f} {m['mrr']:>6.3f} "
              f"{m['ndcg']:>6.3f} {m['coverage']:>6.3f} {m['budget_coverage']:>11.3f}")

    best = max(rows, key=lambda r: (r[2]["budget_coverage"], r[2]["ndcg"], r[2]["mrr"]))
    print(f"\nBest (by cov@budget, then nDCG, MRR): {best[0]}  "
          f"(cov@budget={best[2]['budget_coverage']:.3f}, nDCG={best[2]['ndcg']:.3f}, "
          f"MRR={best[2]['mrr']:.3f})")


if __name__ == "__main__":
    main()
