"""Chunking entry point — delegates to the strategy selected by config.

The actual strategies (fixed / recursive / sentence / paragraph / structure /
semantic) live in `chunkers.py`. `settings.chunk_strategy` picks one. Strategy is
chosen by experiment (experiments/ablate_strategy.py), not by default
(PROJECT_PLAN.md §3.3).
"""
from __future__ import annotations

from ingestion.chunkers import chunk_pages

__all__ = ["chunk_pages"]
