"""Chunking strategies (PROJECT_PLAN.md §3.3).

Each strategy maps page text -> chunks with metadata. They share a size budget
(settings.chunk_size) so they're comparable in the ablation. Pick by measurement,
not by default — see experiments/ablate_strategy.py.

Why several, and why a "mix": real sources (PDFs) have wildly uneven structure —
some docs are clean headed sections, some are long unbroken prose, some are tables.
No single splitter is best everywhere:
  - fixed:      predictable size, but splits mid-sentence/mid-fact (worst coherence)
  - recursive:  good general default; respects separators up to the size budget
  - sentence:   never splits a sentence; packs sentences to the budget
  - paragraph:  splits on blank lines; merges small, recursively splits huge paras
  - structure:  splits on headings, keeps a section together, attaches the section
                title (best citations); over-long sections fall back to recursive
                -> this is the hybrid "mix"
  - semantic:   splits where topic shifts (sentence-embedding similarity drops);
                best for unstructured prose, at higher compute cost
"""
from __future__ import annotations

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


# --- helpers ---------------------------------------------------------------

def _emit(texts: list[str], page: dict, base: dict, extra: dict | None = None) -> list[dict]:
    out = []
    for t in texts:
        t = t.strip()
        if not t:
            continue
        md = {**base, "page": page["page"]}
        if extra:
            md.update(extra)
        out.append({"text": t, "metadata": md})
    return out


def _recursive_splitter(overlap: int | None = None) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap if overlap is None else overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _pack(units: list[str], size: int, sep: str = " ") -> list[str]:
    """Greedily pack units (sentences/paragraphs) into <=size chunks."""
    chunks: list[str] = []
    cur = ""
    for u in units:
        if cur and len(cur) + len(sep) + len(u) > size:
            chunks.append(cur)
            cur = u
        else:
            cur = u if not cur else cur + sep + u
    if cur:
        chunks.append(cur)
    return chunks


# --- strategies ------------------------------------------------------------

def fixed(pages: list[dict], base: dict) -> list[dict]:
    size, overlap = settings.chunk_size, settings.chunk_overlap
    step = max(1, size - overlap)
    out: list[dict] = []
    for pg in pages:
        text = pg["text"]
        out += _emit([text[i : i + size] for i in range(0, len(text), step)], pg, base)
    return out


def recursive(pages: list[dict], base: dict) -> list[dict]:
    splitter = _recursive_splitter()
    out: list[dict] = []
    for pg in pages:
        out += _emit(splitter.split_text(pg["text"]), pg, base)
    return out


def sentence(pages: list[dict], base: dict) -> list[dict]:
    out: list[dict] = []
    for pg in pages:
        sents = [s for s in _SENTENCE.split(pg["text"]) if s.strip()]
        out += _emit(_pack(sents, settings.chunk_size), pg, base)
    return out


def paragraph(pages: list[dict], base: dict) -> list[dict]:
    splitter = _recursive_splitter(overlap=0)
    out: list[dict] = []
    for pg in pages:
        paras = [p for p in re.split(r"\n\s*\n", pg["text"]) if p.strip()]
        units: list[str] = []
        for p in paras:
            units += splitter.split_text(p) if len(p) > settings.chunk_size else [p]
        out += _emit(_pack(units, settings.chunk_size, sep="\n\n"), pg, base)
    return out


def structure(pages: list[dict], base: dict) -> list[dict]:
    """Hybrid "mix": split on headings, but right-size the result —
      - over-long sections fall back to a recursive split (so a huge section
        doesn't become one giant chunk), and
      - small adjacent sections are packed together up to the size budget (so a
        doc of short sections doesn't shatter into many tiny chunks).
    Each chunk keeps its (leading) section title for citations. (Markdown headings
    here; PDF heading detection via font-size heuristics is future work.)"""
    splitter = _recursive_splitter()
    out: list[dict] = []
    for pg in pages:
        section_pieces: list[tuple[str, str]] = []
        for title, body in _split_sections(pg["text"]):
            body = body.strip()
            if not body:
                continue
            if len(body) > settings.chunk_size:
                section_pieces += [(title, piece) for piece in splitter.split_text(body)]
            else:
                section_pieces.append((title, body))
        for title, text in _pack_sections(section_pieces, settings.chunk_size):
            out += _emit([text], pg, base, extra={"section": title})
    return out


def _pack_sections(items: list[tuple[str, str]], size: int, sep: str = "\n\n") -> list[tuple[str, str]]:
    """Pack consecutive (title, text) pieces up to `size`, keeping the first title."""
    out: list[tuple[str, str]] = []
    cur_title: str | None = None
    cur = ""
    for title, text in items:
        if cur and len(cur) + len(sep) + len(text) > size:
            out.append((cur_title or "", cur))
            cur_title, cur = title, text
        elif not cur:
            cur_title, cur = title, text
        else:
            cur = cur + sep + text
    if cur:
        out.append((cur_title or "", cur))
    return out


def _split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [("", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        pre = text[: matches[0].start()].strip()
        if pre:
            sections.append(("", pre))
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((title, text[start:end]))
    return sections


def semantic(pages: list[dict], base: dict) -> list[dict]:
    """Split where consecutive-sentence embedding similarity drops below the 25th
    percentile (topic shift). Reuses the dense embedder; higher compute cost."""
    import numpy as np

    from ingestion.embeddings import _dense

    model = _dense()
    out: list[dict] = []
    min_len = settings.chunk_size * 0.3
    for pg in pages:
        sents = [s for s in _SENTENCE.split(pg["text"]) if s.strip()]
        if len(sents) <= 1:
            out += _emit(sents, pg, base)
            continue
        embs = [e / (np.linalg.norm(e) + 1e-9) for e in model.passage_embed(sents)]
        sims = [float(np.dot(embs[i], embs[i + 1])) for i in range(len(embs) - 1)]
        threshold = float(np.percentile(sims, 25))
        chunks: list[str] = []
        cur = [sents[0]]
        for i, sim in enumerate(sims):
            joined = " ".join(cur)
            if sim < threshold and len(joined) > min_len:
                chunks.append(joined)
                cur = [sents[i + 1]]
            else:
                cur.append(sents[i + 1])
        if cur:
            chunks.append(" ".join(cur))
        out += _emit(chunks, pg, base)
    return out


STRATEGIES = {
    "fixed": fixed,
    "recursive": recursive,
    "sentence": sentence,
    "paragraph": paragraph,
    "structure": structure,
    "semantic": semantic,
}


def chunk_pages(pages: list[dict], base_metadata: dict) -> list[dict]:
    strategy = STRATEGIES.get(settings.chunk_strategy)
    if strategy is None:
        raise ValueError(
            f"Unknown chunk_strategy '{settings.chunk_strategy}'. "
            f"Options: {', '.join(STRATEGIES)}"
        )
    return strategy(pages, base_metadata)
