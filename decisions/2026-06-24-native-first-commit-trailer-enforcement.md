# Proposal: enforce Native-First via the commit-check hook (advisory)

**Date:** 2026-06-24 · **Class:** shared-hook change (3+ projects) → human sign-off · **Risk:** low (additive advisory, never blocks)
**Source:** maintain tick — gov-report governance-health read

## Problem (two failing gov invariants, one fix)

`gov-report` (2026-06-24) flags two `✗` invariants:
- **`native-patterns` FAIL** (margin 0.215): **150 of 191** new scripts in the last 90d carry **no `Native-First:` commit trailer** (e.g. `worktree_gc.py`, `behavioral_harness_replay.py`, `over_ask_telemetry_grader.py`, `memory_provenance_check.py`).
- **`P1-rule-hook-balance` CONTRADICTION**: too many instructions relative to enforcement.

These are the SAME defect. The Native-First discipline ("new Python script → a `Native-First:` trailer justifying why a `just` recipe / SQLite view / git hook / launchd plist didn't suffice") lives only as an **instruction** in `.claude/rules/native-patterns.md` + `commit-conventions.md`. An instruction ignored 150/191 times is exactly what Constitution P1 says to convert to architecture — and doing so directly improves the rule-hook-balance invariant.

## Proposed change (concrete, minimal)

Extend `~/Projects/skills/hooks/commit-check-parse.py` — which **already** suggests `Evidence:` for governance files via the same `get_staged_files()` path (lines 160-163) — with one parallel block:

```python
# New .py script staged AND no Native-First: trailer → suggest it
new_py = [f for f in staged if f.endswith(".py") and _is_added(f)]  # git diff --cached --diff-filter=A
if new_py and "Native-First" not in trailers:
    suggestions.append(
        f"{len(new_py)} new script(s) ({', '.join(new_py[:3])}…) — add a `Native-First:` trailer "
        f"(what native tool — just recipe / SQLite view / git hook / launchd — was considered and why a script instead)."
    )
```

**Advisory only** (appends to `suggestions`, never a `warnings`/block) — consistent with measure-before-enforcing (P3) and the hook's existing trailer-suggestion behavior. The `native_first.py` grader (rolling 90d window) then measures whether the missing-trailer rate falls; promote to a warning only if the advisory is measured ineffective.

## Why this is propose-only, not autonomous

`commit-check-parse.py` is a **shared hook** referenced by every repo's commit flow (3+ projects) → the autonomy boundary requires human sign-off even for an additive-advisory change.

## Dedup

- `commit-check-parse.py` does NOT currently check Native-First (grep-confirmed).
- Not already proposed (no native-first entry in decisions-pending/ or steward-proposals/).
- The grader reads a **rolling 90d** window (`--since=90 days --diff-filter=A`), so this is forward-fixable — not dead historical debt; the count falls as new commits carry the trailer and old ones age out.

## Pre-registered falsify (F3)

change_ref: this hook edit · predicted_failure_class: new scripts without Native-First justification · metric: `native_first.py` missing-trailer fraction over rolling 90d · direction: decrease · control: a different trailer's adherence (Evidence: on governance commits) should stay ~flat · rollback: if the fraction doesn't fall within 30d, the advisory is insufficient → escalate to a `warnings`-level nudge or drop.
