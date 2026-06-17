"""Per-question retrieval diagnostic — shows *why* a question fails coverage.

For each answerable golden question: the missed/hit keywords, and the top-k
retrieved chunks with their source + section and whether each contains a keyword.
Reveals the failure mode (wrong product retrieved? value split across chunks?
column interleaving?) so fixes target the real cause.

Usage:
    MANIFEST_PATH=corpus/manifest.json GOLDEN_PATH=corpus/golden_set.jsonl \
        python -m evaluation.diagnose --reindex
"""
from __future__ import annotations

import argparse

from evaluation.run_eval import get_points, load_golden
from ingestion.corpus import reindex
from ingestion.indexer import get_client


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    if args.reindex:
        n = reindex(get_client())
        print(f"Reindexed {n} chunks.\n")

    golden = [g for g in load_golden() if g["type"] != "negative"]
    fails = 0
    for g in golden:
        pts = get_points(g["question"], no_rerank=False, top_k=args.top_k)
        ctx = " ".join(p.payload.get("text", "") for p in pts).lower()
        kws = g["answer_keywords"]
        miss = [k for k in kws if k.lower() not in ctx]
        status = "FAIL" if miss else "ok"
        if miss:
            fails += 1
        print(f"[{status}] {g['id']}: {g['question'][:64]}")
        if miss:
            print(f"        missed keywords: {miss}")
            for p in pts:
                md = p.payload or {}
                mark = "*" if any(k.lower() in md.get("text", "").lower() for k in kws) else " "
                src = str(md.get("source", "?"))[:32]
                sec = str(md.get("section", ""))[:24]
                print(f"        {mark} {src:32}  sec={sec}")
    print(f"\n{fails}/{len(golden)} questions miss at least one keyword.")


if __name__ == "__main__":
    main()
