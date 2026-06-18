# 0012 — Handoff doc + capabilities checklist

- **Commit:** (docs): handoff guide + capabilities checklist
- **Date:** 2026-06-18
- **Milestone:** Continuity / project meta

## What
Added **HANDOFF.md** — a single entry point for a future agent/LLM to continue the
work: the project's non-negotiable rule (decisions need evidence), current state,
how to run (dev container + corpus env-var switch), an architecture map, the
decisions already made (with evidence + doc refs), a done/partial/todo feature
checklist, open caveats/tech debt, and a prioritized backlog. Added a matching
**Capabilities checklist** table to the README and refreshed the stale "Next" list.

## Why
The work spans 11 commits with non-obvious context (corpus env-var switching, the
diagnose-first rule, judge-bias caveat, why `structure` is the default, OCR scoping).
A new agent picking this up should not have to re-derive that from the diff. One
authoritative status+conventions doc + a visible checklist makes "what's done vs not"
and "how do I continue correctly" immediate.

## Key decisions
- **HANDOFF.md at repo root** for discoverability (linked from README and this log).
- **Checklist mirrors idea.md's MVP** so progress maps directly to the original spec;
  honest ✅/🟡/⬜ (e.g. evaluation is 🟡 — custom harness, not the RAGAS library;
  Docker is 🟡 — no API image yet).
- Corrected a stale README "Next" item ("OCR the no-text pages") — those pages were
  diagnosed as all-boilerplate (docs/0010), and OCR is now implemented (0010/0011).

## Validation
Docs only. Cross-checked the checklist and architecture map against the actual file
tree, `config.py` defaults, and the commit history so the handoff matches reality.

## Follow-ups
- Keep HANDOFF.md and the README checklist updated as features land — treat them as
  living, like the decision log.
