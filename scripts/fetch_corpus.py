"""Download the real corpus PDFs listed in corpus/manifest.json.

The PDFs themselves are gitignored (we don't redistribute Lenovo's copyrighted
files); this script re-fetches them on demand so the corpus is reproducible from
the committed manifest of public PSREF URLs. Demo/evaluation use only.

Usage:
    python -m scripts.fetch_corpus
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

CORPUS = Path("corpus")
MANIFEST = CORPUS / "manifest.json"
UA = "Mozilla/5.0 (compatible; marketing-rag/0.1; +https://github.com/b7biqi/marketing-rag)"


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in entries:
        url = entry.get("url")
        dest = CORPUS / entry["file"]
        if not url:
            print(f"  (no url for {entry['file']} — skip)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  exists: {dest} ({dest.stat().st_size} bytes)")
            continue
        print(f"  fetching: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  saved: {dest} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
