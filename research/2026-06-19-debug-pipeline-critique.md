---
title: Debug pipeline critique synthesis (skills/critique cross2)
date: 2026-06-19
tags: [critique, debug, execute]
status: implemented-v1
review: .model-review/2026-06-19-debug-pipeline-090ce4/disposition.md
---

# Debug pipeline — critique synthesis

**Method:** `Projects/skills/critique` — `review_gate.py triage` + `model-review.py --axes cross2 --context-scope packet --no-scout`

**Verdict:** Ship with guards. Supersedes ad-hoc `research/2026-06-19-debug-pipeline-critique.md`.

## Accepted (implemented in v1)

- `import sys` + multiline/block FINDING parser + parse warnings
- Scout output contract validation (`NO_FINDINGS` or `## FINDING`)
- Run-id in filenames (no same-day overwrite)
- `--workers` / `--max-scouts` ≥ 1 guards
- `commit-prep --write` → target repo `artifacts/commit-prep/`
- Staged + unstaged diff stat; untracked in file list
- Optional JSON fence in scout prompt for machine parse
- `just debug`, `just debug-triage`, `just commit-prep`
- `skills/debug/SKILL.md` orchestrator-model contract

## Deferred (v2)

- JSONL as primary transport (shared with code-review-scout)
- Shared fan-out library extraction
- Injected file contents for grounding
- Auto-trigger on canary/contract lint failure

## Operator flow

```bash
just debug ~/Projects/genomics recent
just debug-triage ~/Projects/genomics/docs/audit
# read *-debug-handoff.md in orchestrator-model session (frontier parent)
just commit-prep --repo ~/Projects/genomics --write
```
