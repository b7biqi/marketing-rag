"""M1 ablation: chunk size x overlap, measured on the golden set.

For each configuration we mutate the chunking settings, rebuild the index from the
manifest (so only the chunking variable changes), and score retrieval. The goal is
to pick chunk_size/overlap by evidence rather than by default (PROJECT_PLAN.md §3.3).

Usage:
    python -m experiments.ablate_chunking
    python -m experiments.ablate_chunking --top-k 2
"""
from __future__ import annotations

import argparse

from config import settings
from evaluation.run_eval import evaluate_retrieval, load_golden
from ingestion.corpus import reindex
from ingestion.indexer import get_client

CHUNK_SIZES = [300, 500, 1000]
OVERLAP_RATIOS = [0.0, 0.15]


def main() -> None:
    ap = argparse.ArgumentParser(description="Chunk size/overlap ablation")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    golden = load_golden()
    client = get_client()

    print(f"Chunking ablation (top_k={args.top_k}, rerank on, "
          f"dense={settings.dense_model})\n")
    header = f"{'chunk_size':>10} {'overlap':>8} {'chunks':>7} {'Recall':>7} {'MRR':>6} {'nDCG':>6} {'kw_cov':>7}"
    print(header)
    print("-" * len(header))

    rows = []
    for size in CHUNK_SIZES:
        for ratio in OVERLAP_RATIOS:
            overlap = int(size * ratio)
            settings.chunk_size = size
            settings.chunk_overlap = overlap
            n_chunks = reindex(client)
            m = evaluate_retrieval(golden, no_rerank=False, top_k=args.top_k)
            rows.append((size, overlap, n_chunks, m))
            print(f"{size:>10} {overlap:>8} {n_chunks:>7} "
                  f"{m['recall']:>7.3f} {m['mrr']:>6.3f} {m['ndcg']:>6.3f} {m['coverage']:>7.3f}")

    # Pick winner by keyword coverage, then nDCG, then MRR (precision-leaning).
    best = max(rows, key=lambda r: (r[3]["coverage"], r[3]["ndcg"], r[3]["mrr"]))
    print(f"\nBest: chunk_size={best[0]}, overlap={best[1]} "
          f"(kw_cov={best[3]['coverage']:.3f}, nDCG={best[3]['ndcg']:.3f}, MRR={best[3]['mrr']:.3f})")


if __name__ == "__main__":
    main()
