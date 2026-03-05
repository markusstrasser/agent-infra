# Skill Provenance Controls

**Date:** 2026-03-05
**Question:** What would skill provenance controls actually do, and how do we add them without turning the skills library into a package-management project?
**Status:** Recommendation memo

## TL;DR

Treat `SKILL.md` files as a **mutable instruction supply chain**.

Do not solve this with signatures, central registries, or heavy policy engines first.

Start with three things:
- inventory every skill and its origin
- hash the exact skill version used in each session
- warn when a skill changed without review

That gives visibility, rollback, and scoped trust without much machinery.

## Why This Matters

Recent work changes the threat model:

- **SKILL-INJECT** shows that skill files themselves are a realistic attack surface.
- Our own setup has shared skills that mutate in place.
- The skills audit already noted that the library has **no version pinning**.

This is not hypothetical. In this repo family, a changed skill can silently alter:
- research method
- review method
- verification rules
- tool routing

If we cannot answer "which exact skill text influenced this run?", then we have weak provenance for agent behavior.

## What This Would Actually Do

### 1. Explain behavior changes

If a workflow suddenly becomes worse or different, provenance tells you whether:
- the model changed
- the environment changed
- the skill changed

Without that, skills are hidden confounders.

### 2. Make failures diffable

If `researcher` or `model-review` regresses, you can compare:
- old hash / old content
- new hash / new content
- sessions before and after the change

That turns "the agent feels worse" into an auditable diff.

### 3. Support selective trust

Not all skills should be treated equally.

Examples:
- local authored + reviewed
- imported from another repo but reviewed
- imported and unreviewed
- experimental local override

High-stakes projects can allow only the first two.

### 4. Create usable forensics

Session receipts and transcript analysis become much more valuable if they can say:
- model
- project
- tools used
- skill hashes loaded

That is the minimum viable "behavior provenance" chain.

## Minimal Design

### A. Skill inventory

Maintain a machine-readable registry, for example:

```json
[
  {
    "name": "researcher",
    "path": "/Users/alien/Projects/skills/researcher/SKILL.md",
    "origin": "local-authored",
    "owner": "shared",
    "review_status": "reviewed",
    "sha256": "..."
  }
]
```

The registry is not a package manager. It is an inventory.

### B. Session-time hash logging

Whenever a skill is invoked:
- resolve the file path
- compute hash
- log it into the session receipt or sidecar JSONL

This is cheap and gives immediate observability.

### C. Changed-since-review warning

If the current skill hash differs from the last reviewed hash:
- warn in-session
- mark the skill as `changed_unreviewed`

Do not block by default.

### D. Project allowlists for high-stakes repos

For `intel` or similar projects:
- allow `local-authored`
- allow `imported-reviewed`
- warn or block `imported-unreviewed`

This is where the control becomes useful, not just descriptive.

## What Not To Build Yet

- public key signing
- remote trust service
- semantic diff classifier for every skill edit
- strict pinning for every low-stakes project
- a new installer ecosystem

Those are easy ways to burn time before proving value.

## Why This Is Not Yak Shaving

It stays sane if we keep the scope tight:

1. **Log first, block later.**
   If the control does not produce useful observations, stop there.

2. **Track only invoked skills.**
   Do not build provenance for unused files.

3. **Treat provenance as debugging infrastructure.**
   The first win is better forensics, not airtight security.

4. **Use coarse trust classes.**
   Four states are enough: `local-reviewed`, `local-unreviewed`, `imported-reviewed`, `imported-unreviewed`.

## Recommended Rollout

### Phase 1: Logging only

- add skill hash + path logging to session receipts
- generate a skill inventory snapshot

### Phase 2: Review state

- add `review_status`
- warn when a high-impact skill changed since last review

### Phase 3: High-stakes gating

- per-project allowlist for `intel`
- warn or block unreviewed imported skills

### Phase 4: Correlate with failures

- when session-analyst logs a regression, include skill-hash changes in the analysis

At that point, provenance is paying rent.

## Where This Helps Most

### `meta`

- shared skills mutate in place
- cross-project propagation makes behavior drift harder to diagnose

### `researcher`

- high-impact because it shapes evidence gathering and claim verification

### `intel`

- highest stakes
- local overrides and persistent analyst workflows make silent drift more dangerous

## Bottom Line

Skill provenance controls are not mainly about hard security.

They are about making skill changes:
- visible
- attributable
- reversible
- project-scoped

That is enough to materially improve trust in the skills layer without building a bureaucracy around `SKILL.md`.

## Sources

- [SOURCE: arXiv:2602.20156] `SKILL-INJECT`
- [SOURCE: skills-audit-2026-02-28.md]
