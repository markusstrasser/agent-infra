---
id: 2026-06-21-decision-currency-whitelist
concept: decision-currency
repo: agent-infra
decision_date: 2026-06-21
recorded_date: 2026-06-21
provenance: contemporaneous
status: proposed
relations:
  - type: branches_from
    target: 2026-06-18-lifecycle-graph-spine
  - type: relates_to
    target: 2026-06-18-planning-lifecycle-contract
  - type: relates_to
    target: 2026-06-07-state-externalization-lens
---

# 2026-06-21: Executing a superseded ADR is a CURRENTNESS-whitelist gap, not a missing currency system — surface + status-gate, defer the machinery

## Context — the incident

Substrate ADR `0003` ("absorb verification machinery onto claimcore") still reads
`**Status:** PROPOSED`; its premise was reversed by `0007`/`0010`/`0011` ("reconcile, don't
absorb; do NOT lift `CanonicalStageHash`"). An agent opened `0003` in isolation and executed the
dead "absorb" plan; the operator had to correct it. Asked: *how do we architecturally stop agents
executing superseded ADRs?*

## The real axis (reframed — cold cross-lab R1)

First framing: "how do we mark an ADR superseded" (a **blacklist**). The real axis is
**"what makes an ADR EXECUTABLE" (a whitelist).** Execution eligibility requires **positive
currentness**, not the *absence* of supersession. `0003` is `PROPOSED` — never accepted — so it is
non-executable *regardless* of any supersession edge. This subsumes three sub-gaps (forward-only
supersession, semantic-not-structured reversal, PROPOSED/dead conflation) in one rule, and
**fail-closed-on-`unknown` is the structural forcing-function** that an opt-in mechanism never gets.

## Decision

**The binding constraint is SURFACING + a status-whitelist, NOT a missing currency system.** Verified
(repo-grounded Composer round): for the actual incident the reversal record **already exists**
(`deferred-and-open.md:24-26`, `0011:26`) — it is a discoverability failure. `0003` is **not**
edge-superseded (no `supersedes: 0003`; killers are soft verbs), and **substrate ADRs carry no YAML
frontmatter**, so the lifecycle graph skips them (`lifecycle.py:206`) — a structured-edge currency
view would measure ~0 coverage on the real incident today.

**Phase 1 (prevent recurrence — 2 edits + 1 cheap shadow, NO new machinery):**
1. Append a backward marker to `0003` (`Reframed-by [[0007]]/[[0010]]/[[0011]] — reconcile-not-absorb;
   do NOT lift CanonicalStageHash`). Append-only-safe.
2. A `REFRAMINGS.md` entry keyed to absorb/`0003` (compaction-surviving; already SessionStart-surfaced).
3. A **whitelist status-read SHADOW** — a report-only script on the *existing* global
   `PostToolUse:Read` matcher that parses the **already-present** `**Status:**`/`status:` field and
   logs when a read decision/ADR is non-`ACCEPTED`. No edge-graph, no prose-parser, no vocab change.

**Verb ruling** (for when the machinery IS built): flip currency ONLY on `supersedes`/`retires`/
`reverses_premise`. `merged_from`/`unifies`/`subsumes`/`concretizes`/`extends` = **weaken /
read-with-context, NOT kill** — substrate's own recompute-on-read thesis (`0008:35-52`); "Unifies
0003" cites absorption *gates*, not deletion.

## Rejected / deferred alternatives

- **Build a decision-currency system now** (vocab `reverses_premise` + prose-relation parser +
  ADR-frontmatter migration + cross-repo index + currency-eval view + active read-gate). **DEFERRED**
  — the record already exists (surfacing gap), and `0003` is unindexable today. Resurrect on a 2nd
  prevented-regression OR the shadow showing measured demand on structured `supersedes`/
  `reverses_premise` in agent-infra `decisions/` first. (Pre-Build #1; mirrors
  `2026-06-18-planning-lifecycle-contract` v0.4.4: a universal contract collapsed to 3 edits because
  adoption, not machinery, was the constraint.)
- **ADRs onto plan-core's state machine** — rejected: plan-core is plans-only by design; ADRs ≠
  plans (HC: 3-layer boundary; `2026-06-18-lifecycle-graph-spine`).
- **A new persistent currency store** — rejected (veto-adjacent; lifecycle-graph-spine: rederivable
  view + vocab, never a store).
- **Semantic detection (LLM "premise reversed") as the GATE** — rejected as authority; permitted only
  as a SCOUT that populates a review queue (recall for un-flip-verbed reversals). Never auto-retire
  from a commit message; only `operator_confirmed_*` gates (provenance-separated from `suspected_*`).
- **Another prose rule** ("agents: check backlinks") — rejected: substrate CLAUDE.md already says
  "read REFRAMINGS" and it doesn't fire (Constitution P1).

## Invariants this preserves

No new store · decisions append-only (backward marker is an *append*) · architecture-over-prose
(the gate, not a rule) · operator-confirmation stays principal (only confirmed currency gates) ·
advisory-first (fail-closed is the promotion target, not Phase 1 — `2026-06-18-...` v0.4.3: a red
blocking gate is worse than advisory).

## Evidence / audit trail

`/decide` arc, this session (`70c686a8`). Plan: `.claude/plans/70c686a8-adr-decision-currency.md`.
Probes: 3 read-only Explore agents (lifecycle currency / staleness gates / substrate practice) +
verification greps (substrate ADRs: 0 YAML frontmatter; `supersedes: 0003`: 0 hits;
`PostToolUse:Read` matcher present). Cross-model: cold gpt-5.5 (R1 whitelist reframe, folded) +
repo-grounded Composer (collapse-to-2-edits + verb ruling, folded). **Spine held — zero architecture
reversals across both rounds; resolution was deeper (blacklist→whitelist) + smaller (machinery
deferred), not overturned.**

## Apply note

The two `0003`/REFRAMINGS edits are **substrate** edits (live substrate session `018ee7c8` owns that
checkout — coordinate, don't clobber). The status-shadow is an **agent-infra global hook** (apply
when the agent-infra peer session settles). Neither applied in-session due to live peers.

## Revisions

### 2026-06-22 — v2: operator push corrected shadow→ACTIVE; mechanism is the gate, not the one-off
Operator: *"how will this avoid stuff in the future if you're just fixing a one-off ADR?"* — valid
(the original ask was architectural *prevention*; rule #21: don't one-off-patch a class). The v1
collapse over-deferred: stamping `0003` is **backfill**, and a *report-only shadow* measures but
doesn't prevent. **New argument (not capitulation):** an *advisory injection* is not a hard block, so
"measure-before-enforce" (which guards blocking) does not forbid shipping it **active**. So the
general prevention ships now, not after a 2nd regression.
- **BUILT (agent-infra-first, this session):** `scripts/hooks/posttool-decision-currency.sh` — an
  active `PostToolUse:Read` advisory that fires on read of ANY decision/ADR whose status ∉
  {accepted,active,current,implemented,done,ratified}, keyed on the **existing** status field
  (YAML `status:` or prose `**Status:**`; no edge-graph, no parser-migration — works on
  frontmatter-less substrate ADRs). Once per (session,file). Wired in `.claude/settings.json`;
  hooks-smoke 269→270. Tested: fires on 0003 (proposed) + 0005 (superseded), silent on 0011 (accepted).
- **The one-off `0003` stamp + REFRAMINGS entry** are now explicitly **backfill** (the *why*), routed
  as a substrate apply-handoff (`decisions-pending/2026-06-22-substrate-0003-currency-backfill.md`).
- **Phase 2 (the 2nd general mechanism — proposed, not built):** a **producer-side auto-back-stamp** —
  when a new ADR declares a flip-verb (`supersedes`/`retires`/`reverses_premise`), a Write hook appends
  the backward marker to the target, so **supersession always marks its target** (generalizes the
  one-off stamp; closes G1 forward-only at the source).
- **Sign-off-gated:** propagating the active gate GLOBALLY (so it fires in substrate/genomics/phenome,
  incl. the actual 0003 read) is a 3+-repo shared-hook change → invariant #4. agent-infra-first is the
  autonomous slice + the measure surface; global is the proposal.
Current version = this entry, v2.
