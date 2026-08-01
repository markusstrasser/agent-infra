---
concept: prior-context-turn-retrieval
decision_date: 2026-08-01
status: decided
---

# Turn-level prior-context retrieval — SHADOW on

**Decision:** Wire `scripts/prior-context-index search` behind INTENT/REDISCOVERY in
`skills/hooks/userprompt-prior-context.py` in **shadow only** (log, do not inject).

**Log:** `~/.claude/prior-context-shadow.jsonl`  
**Timeout:** 2s hard; fail-open  
**Promote later when:** ≥30 intent-matched prompts logged, answer-bearing precision ≥70%,
source-handle validity 100%, warm p95 ≤2s (per pending plan steps 3–4).

**Supersedes pending step 2–3:** `decisions-pending/2026-07-16-turn-retrieval-hook-activation.md`

**Evidence:** operator AskUserQuestion 2026-08-01 yes-shadow; ablation gate closed 2026-07-25.
