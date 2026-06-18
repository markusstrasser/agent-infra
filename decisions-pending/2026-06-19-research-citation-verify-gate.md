> **RESOLVED 2026-06-19 — APPROVED & IMPLEMENTED** (`/execute`). Shipped in `skills@a529547`
> (`research/scripts/verify_citations.py` + SKILL.md Phase 3 + verification-procedure.md).
> Kept as the decision record; no longer awaiting a human gate.

# Pending decision — citation-verify rate-gate for `/research`

**Boundary:** shared — edits `~/Projects/skills/research/` (used in all projects, 3+ blast radius)
+ adds one thin checker. **Reversible** (skill prose + one script; git).
**User-directed:** "1 2 3 /decide" → chose *Grounding only* → "OK just do that" (2026-06-19).
Goes through sign-off per constitution hard-limit #4 (shared infra = EXPLICIT human approval).
**ADR:** `decisions/2026-06-19-autoresearch-grounding-imports.md`.

## The ask (one yes/no)

Approve adding a **citation-verification rate-gate** to `/research`'s finalize step.

## What it is (reuses existing machinery — does NOT rebuild resolution)

A thin checker `verify_citations` (script, later a `just` verb per the dispatch-brief schema) that
takes a finalized memo's citations and, **reusing `corpus` (`references_resolved`/`crossref`),
research-mcp `verify_claim`, and scite stance**, emits a coverage report:

| Field | Meaning | Gate |
|---|---|---|
| `resolved_rate` | % citations resolving to a real paper (DOI/PMID/title match) | ≥80% (advisory) |
| `hallucinated` | citations resolving to NOTHING or a DIFFERENT paper | **0 (blocking)** |
| `arxiv_only_ratio` | % preprint-only (no accepted venue) | flag if >60% (advisory) |
| `venue_upgrade` | arXiv cites that DBLP/OpenReview show as accepted | report list |

Skill prose change: `/research` "Finalize" step gains — *"run `verify_citations`; report the rate;
`hallucinated > 0` is blocking, the rest advisory."*

## Why this shape (grounded in the ADR)

- **Gate, not prose:** checkable predicate → architecture (constitution P1). Scattered
  "verify before citing" rules already exist in the skill but aren't enforced or measured.
- **Reuse, not build:** `corpus` already resolves references (Pre-Build #1; vetoed speculative
  extraction). The gate is the missing ~10% (the rate metric + arxiv-cap + venue-upgrade), not
  the resolution.
- **Advisory first:** per constitution P3 (measure before enforcing) — log the rate per memo;
  promote `arxiv_only`/`resolved_rate` from advisory→blocking only if a real miss recurs.
  Only `hallucinated > 0` blocks from day one (it is the dangerous, citable-slop case).

## Open micro-fork (yours, low stakes)

#1's weakness→component **routing table** for `/improve`: adopt as output-formatting (route each
surfaced finding to its fixing component) **or** skip as already-covered by `review_gate.py rank`?
**Recommend: skip now**, revisit only if `/improve` outputs read as non-actionable in practice.

## Rejected here (see ADR + deferred-and-open) — do not re-propose

- #3 phase-gated 6.0→8.5 score · #1 calibration ladder — LLM-judge-as-gate proxy; no host loop;
  the verifier-regime operating points already serve the role.

## On approval

Implement in `~/Projects/skills/research/` (the checker + the finalize-step prose + a
`references/verification-procedure.md` section), measure the rate over the next N memos, report.
