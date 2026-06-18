---
concept: unified cross-domain RSI/research-loop infrastructure (scaffold + manifest + skills + cookbook)
decision_date: 2026-06-18
status: accepted
relates_to:
  - research/2026-06-18-loop-core-probe-v2-algorithm-layer.md
  - research/2026-06-18-hutter-anim-rsi-comparative-report.md
  - decisions/2026-06-16-loop-core-rsi-ledger-factoring.md
  - decisions/2026-06-09-shared-extraction-proven-common-test.md
  - decisions/2026-06-07-verifier-conditional-autonomy.md
affects: [agent-infra, research, phenome, hutter, anim-workbench, intel, skills]
---

# Unified loop infra — scaffold + per-domain MANIFEST + skills + COOKBOOK (no runtime library)

> `/decide` arc, 2026-06-18. Ratified `accepted` after a cross-model panel (2× Gemini + 2× GPT) and
> two repo-grounded scouts produced **zero architecture-spine reversals** — only invariant refinements
> and HOWs. Audit trail: `.model-review/…-4175d6/`, scout outputs `/tmp/scout-{factcheck,arch}.md`.

## Context

hutter, anim, intel + the research generator collection each hand-roll the same
propose→verify→rank→accept→ledger skeleton. The operator wants 3–5 new domain loops soon (immigration
first, then phenome…) that "find new things, rank them, build better theses" with declining
supervision. What shared infra makes starting one *easy* without repeating the build-then-undo this
repo has died of (the `outer-loop` skill shipped zero-caller and was killed; `loop-core` resolved to a
cookbook)?

## Real axis

Not "what infra to design" but **build ahead-of-need vs prove-then-extract.** Resolved: probe v2 killed
the runtime *library* (adopt-by-deletion fails 3/3 — a shared schema is lossy); the operator's roadmap
+ a *prove-then-extract* sequence justify the rest, **provided each layer is derived from a LIVE
instance, not theorized.**

## Decision — four layers, the manifest is the interface

```
L1  SCAFFOLD  /loop-new <domain>  → stamps loop.yaml (manifest) + LOOP.md/OUTER-LOOP.md/HERETIC.md/
              GENERATORS.md + a per-domain ledger FILE + the verifier slot.   (TO BE BUILT — does not exist yet)
L2  MANIFEST  loop.yaml  → the typed per-domain contract: domain id · warehouse/store path · ledger
              schema+version · verifier command + output schema · candidate schemas · verdict→status
              vocab map · autonomy regime · lifecycle rules · cookbook-shapes used.
              DESCRIPTOR / validation target — NOT an executed config. Skills READ it; nothing `run()`s it.
L3  SKILLS (consume the manifest; NO shared runtime):   (ALL TO BE BUILT)
    /loop-generators  diverge → candidates → verifier-RANK (regime-segmented) → ledger → park-dry
    /loop-outer  tri-lab review   ─┐ thin pointers to EXISTING hutter/anim ports
    /loop-health  ledger views + manifest↔ledger drift-test  ─┘ (outer-loop-review.sh, loop_health.py)
L4  COOKBOOK (docs, copy-stamp): role pattern + 6 algorithm SHAPES, implemented as pure parameterized
              functions inside /loop-generators (not inline SQL copies).
```

**The one domain-specific fill is the verifier — and it sets the autonomy regime, segmented per claim-class.**

## Autonomy regime — FOUR statuses, segmented (refined from the cold-panel's 4th-status proposal + measured)

| Regime | Meaning | Action |
|---|---|---|
| **clean** | deterministic verifier covers the generated claim class | auto-rank + auto-ratchet |
| **partial** | verifier covers a declared subset | bounded autonomy *inside* the subset |
| **coverage-poor** | verifier exists but most candidates are unmappable | discovery allowed; ranking **not truth-like** outside the core |
| **amplify** | no ground-truth adjudication | heretic-heavy, human-judged, no auto-ratchet |

**A loop carries a regime PER CLAIM-CLASS, not one blanket label.** A narrow true-verifier must NOT
license corpus-wide auto-ranking — that is the PACE self-p-hack (Invariant 6).

**Immigration is measured COVERAGE-POOR:** ~10% of 189 numeric claims have independent cross-source
adjudication (the `<HS` NPV triangulation NAS+NRC+Clemens + SIPP/MEPS microdata cells), ~35%
banding/consistency-only, ~56% orphan; 33% of claims sit in clusters with no data table. → auto-rank
ONLY the ~10% core; the rest is amplify/heretic-only. (`/tmp/scout-factcheck.md`)

## Invariants

1. **Verifier is ground-truth, never LLM-judged**, AND **ranking is regime-segmented** — auto-rank only
   the adjudicable claim-class; never let one true cell license corpus-wide truth-ranking.
2. **Cookbook is copy-stamp, not shared code** (probe v2 — lossy schema). Shapes are pure parameterized
   functions in `/loop-generators`; the shared-helper-lib re-opens only at a 2nd same-contract caller.
3. **Born-with-a-caller, by layer:** `/loop-generators` extracts from the LIVE immigration sweep (caller
   #1 real). **`/loop-new` extraction is gated on immigration being LIVE + surviving ≥2 sweeps**;
   dry-stamping phenome is a non-overfit check, NOT caller #2. (Don't ship a stamper proven only by one
   stamp — the `outer-loop` death.)
4. **Manifest is the typed interface** — descriptor/validation target, never an executed config; a
   `/loop-health` **manifest↔ledger drift-test** enforces it.
5. **Ledger is append-only, a PER-DOMAIN FILE** (not one shared sidecar — DuckDB single-writer ⇒ lock
   contention under concurrent launchd loops). Normalized `status` (accepted|rejected|parked|error|
   unverifiable) + domain `verdict_detail`; content-hash `candidate_id`; `schema_version`. Supersede,
   never mutate.
6. **Auditor (heretic) is mandatory even when the accept-gate is greedy** (PACE: greedy alone =
   self-p-hacking); typed output (`heretic_verdict`, `failure_modes[]`, `blocking`).

## Rejected alternatives

- **`loop-core` runtime LIBRARY (shared schema/views)** — probe v2: adopt-by-deletion fails 3/3, LOSSY
  (can't hold anim prose verdicts / hutter's 12-value taxonomy). Correctness, not effort → survives
  "depth over effort." (`research/2026-06-18-loop-core-probe-v2-algorithm-layer.md`)
- **Shared generic-typed PROTOCOL ENGINE** (`DiscoveryEngine.run(Diverge→Verify→Rank→Ledger→Park)`,
  Gemini arch) — **category error**: the loops do NOT share control flow (hutter NEVER-STOP auto-ratchet;
  anim paused gated stepper; intel bash-cron fan-out with no propose/ratchet/park). An engine would
  re-impose the auto-ratchet intel deleted 2026-05-19 and the autonomy anim HOLD'd. The "patch-N-codebases"
  drag is hypothetical (clade-yield has 1 consumer). (`/tmp/scout-arch.md`)
- **Defer `/loop-new` to a LIVE 2nd caller (phenome)** — over-corrects past the roadmap; gate on
  immigration-live+≥2-sweeps instead (Invariant 3).
- **Pure-docs cookbook only** · **central orchestrator** (eradicated 2026-06-07) · **MCP `loop-ops`**
  (knowledge-substrate MCP retired) · **rebuild `/loop-outer`+`/loop-health`** (point at hutter/anim ports).

## Grounded facts (this arc)

`lifetime_generators`=104, `parameter_claims`=563 (189 numeric), **21 data tables** (not 25), `theories_tested`=58,
`sweep_experiments` not yet created. Probe-0 "match" was CIRCULAR (claim + benchmark both NAS-2017). Generator
drift = exactly 2 MD-only (`G-LIF-Q06`, `G-LIF-S15`); reconcile by INSERT (DB is source of truth) before new rows.
