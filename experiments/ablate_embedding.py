"""M1 ablation: dense embedding model (PROJECT_PLAN.md §3.4).

Re-embeds the corpus with each candidate (changing the vector dimension, so the
collection is rebuilt), holds chunking + reranker fixed, and scores retrieval plus
the size-neutral coverage-at-budget metric. Index time (model load/download
excluded) is reported as a cost proxy: on a saturated corpus, equal quality means
the decision is cost — don't pay for a bigger model without a measured gain.

Restores the index to the config-default model at the end so the live system stays
consistent.

Usage:
    python -m experiments.ablate_embedding
    python -m experiments.ablate_embedding --models BAAI/bge-small-en-v1.5 BAAI/bge-large-en-v1.5
"""
from __future__ import annotations

import argparse
import time

from fastembed import TextEmbedding

from config import settings
from evaluation.run_eval import evaluate_retrieval, load_golden
from ingestion import embeddings as emb
from ingestion.corpus import reindex
from ingestion.indexer import get_client

CANDIDATES = [
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "BAAI/bge-large-en-v1.5",
    "BAAI/bge-m3",
]


def _swap(model: str) -> None:
    settings.dense_model = model
    emb._dense.cache_clear()


def main() -> None:
    ap = argparse.ArgumentParser(description="Embedding-model ablation")
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--budget", type=int, default=1000)
    ap.add_argument("--models", nargs="*", default=None)
    args = ap.parse_args()

    default_model = settings.dense_model
    supported = {m["model"] for m in TextEmbedding.list_supported_models()}
    requested = args.models or CANDIDATES
    models = [m for m in requested if m in supported]
    skipped = [m for m in requested if m not in supported]
    if skipped:
        print(f"(skipping models unsupported by fastembed: {skipped})\n")

    golden = load_golden()
    client = get_client()

    print(f"Embedding ablation (top_k={args.top_k}, budget={args.budget}, "
          f"strategy={settings.chunk_strategy}, rerank on)\n")
    header = (f"{'model':>26} {'dim':>5} {'idx_s':>6} {'Recall':>7} {'MRR':>6} "
              f"{'nDCG':>6} {'cov@k':>6} {'cov@bud':>8}")
    print(header)
    print("-" * len(header))

    rows = []
    try:
        for name in models:
            _swap(name)
            dim = emb.dense_dim()  # forces load/download — excluded from idx time
            t0 = time.monotonic()
            reindex(client)
            idx_s = time.monotonic() - t0
            m = evaluate_retrieval(golden, no_rerank=False, top_k=args.top_k, budget_chars=args.budget)
            rows.append((name, dim, idx_s, m))
            print(f"{name.split('/')[-1]:>26} {dim:>5} {idx_s:>6.1f} "
                  f"{m['recall']:>7.3f} {m['mrr']:>6.3f} {m['ndcg']:>6.3f} "
                  f"{m['coverage']:>6.3f} {m['budget_coverage']:>8.3f}")
    finally:
        # Restore the index to the default model so the live system is consistent.
        _swap(default_model)
        reindex(client)
        print(f"\nRestored index to default model: {default_model}")

    if rows:
        best = max(rows, key=lambda r: (r[3]["budget_coverage"], r[3]["ndcg"], r[3]["mrr"], -r[2]))
        print(f"Best (quality, then lower index cost): {best[0].split('/')[-1]} (dim={best[1]})")


if __name__ == "__main__":
    main()
