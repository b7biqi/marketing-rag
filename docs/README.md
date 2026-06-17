# Decision Log

One entry per commit, explaining **what changed** and **the reasoning behind it** —
not just the diff (git already has that), but *why* the choices were made and what
was considered. This is the narrative companion to [PROJECT_PLAN.md](../PROJECT_PLAN.md):
the plan states the intended decisions and experiments; these entries record what
was actually done, measured, and learned in each commit.

## Convention

- One Markdown file per commit: `NNNN-short-slug.md` (zero-padded, sequential).
- Add the entry **in the same commit** as the change it describes.
- Keep the structure below so entries are skimmable and comparable.

### Entry template

```markdown
# NNNN — <title>

- **Commit:** <subject line> (`<short hash>` — fill after committing if needed)
- **Date:** YYYY-MM-DD
- **Milestone:** <e.g. Phase-0 / M0 / M1>

## What
<one-paragraph summary of the change>

## Why
<the reasoning: the problem, options considered, why this approach>

## Key decisions
<bullet list of decisions + justification (link to PROJECT_PLAN.md sections)>

## Validation
<how it was checked: tests run, metrics, smoke tests — with results>

## Follow-ups
<what this enables or defers next>
```

## Index

- [0001 — Initial RAG pipeline](0001-initial-rag-pipeline.md)
- [0002 — Evaluation harness + demo corpus (M0)](0002-evaluation-harness.md)
- [0003 — Corpus expansion + chunking ablation (M1)](0003-chunking-ablation.md)
