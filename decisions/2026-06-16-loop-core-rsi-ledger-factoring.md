---
concept: cross-project RSI loop factoring (loop-core as composable roles)
decision_date: 2026-06-16
status: proposed
relates_to:
  - research/2026-06-15-critique-slow-and-unreliable.md
  - research/2026-06-14-leverage-hunt-rsi-system.md
  - research/2026-06-12-agents-rsi-gap-sweep.md
  - decisions/2026-06-07-state-externalization-lens.md
affects: [hutter, anim-workbench, substrate/corpus-core, substrate/ledger-core, intel, genomics, agent-infra]
---

# loop-core — composable RSI loop roles over a shared append-only ledger

> **Breaking refactor / full migration. No compat shims, wrappers, or legacy paths.**
> Maintained by AI agents; optimize for the deepest, most inspectable representation,
> NOT for SWE cost. Phase-2 ADR (deep revision — supersedes the coarse field-list draft).
> Sibling decision **A** (dispatch surface) is settled separately: `just <verb>` recipes for
> **templated** work, subagents for **artisanal** work; execution coordinates with the
> concurrent surface-governance session.

## Context

Every advanced project hand-rolls the same propose→verify→accept→ledger loop: hutter
(Grinder/Dreamer, compression), anim-workbench (grow/shrink, render-gates), agent-infra
`/improve` + prediction-ledger. They have already **drifted on the load-bearing component** —
the accept-gate (hutter greedy vs anim-workbench auditor) — which is the proof that an
un-factored invariant silently diverges. Factor the common substrate **deeply, as composable
roles**, not a coarse field-list.

## The real axis

Which parts of the loop are common **roles** (factor as swappable, inspectable interfaces) vs
domain mechanics (plug). Established by reading the two most-advanced instances (Explore digs,
2026-06-16) and the `corpus_core` ledger writer — not by theorizing.

## History constraint — heed the outer-loop build-then-undo (CRITICAL)

A near-identical extraction was ALREADY built and KILLED: `decisions/2026-06-13-rsi-outer-loop-skill.md`
extracted a shared `outer-loop` skill + typed LOOP.md + ledger schema — then FINDING 5 killed
deployment (**zero external callers**; hutter and `/improve maintain` already encoded the pattern
natively; durable output was knowledge + `route.py`, not a platform). FINDING 4: **verifier regime
decides whether a standalone loop is even possible** — only hutter (clean + cheap verifier)
auto-ratchets; intel/genomics/science are conductor-driven *partial* regimes. Build-then-undo of
shared platforms is the repo's recurring meta-failure.

**Consequence:** the roles below transfer as a **documented PATTERN (knowledge)**, NOT as a shared
runtime that dictates one control flow (that overfits hutter — the only standalone loop). The ONLY
package extraction permitted is `ledger-core`, and ONLY after a **loader probe** proves ≥2 real
callers of the *same* contract (the proven-common bar). The per-project win (hutter Heretic auditor)
is the real deliverable; a `loop-core` runtime is gated, not assumed.

## Decision — loop-core ROLES are a documented pattern; the only package is a proven `ledger-core`

```
        ┌────────── ledger (append-only · DuckDB · shared mechanics w/ corpus_core) ──────────┐
        │  every role appends its output → the run is fully replayable / debuggable           │
        ↓                                                                                      │
 Proposer ──→ Runner ──→ Verifier ──→ Auditor ──→ Accept-gate ──→ (append verdict) ────────────┘
 (Dreamer)   (Grinder)               (Heretic)
```

| Role | What it is | Generic (loop-core ships this) | Plug (per-project) |
|---|---|---|---|
| **Proposer** (Dreamer) | ledger-signal → candidates | queue-drain · self-gen via **clade-yield** (rank parents by descendant-acceptance, not own-score) · beam-K fan-out | candidate representation; domain hypothesis generation |
| **Runner** (Grinder) | candidate → raw measurement | dispatch/execute harness; resource caps | build/run mechanics |
| **Verifier** | measurement → score + hard pass/fail gate | interface contract: **deterministic only, never LLM-judged** | the scorer (compression bytes / render-gate) |
| **Auditor** (Heretic) | adversarial pre-accept check | oracle-ratio · real-reject-rate · idea-fuel-exhaustion | domain oracle-bias checks |
| **Accept-gate** | (verifier, auditor) → ACCEPT / REJECT | policy interface | greedy \| conjunctive \| PACE e-process |
| **Ledger** | append-only durable memory + inspection surface | `ledger-core` DuckDB mechanics (below) | domain columns |

**Dreamer = the Proposer role; Heretic = the Auditor role** — separate from the Accept-gate it
feeds. The coarse draft that buried both inside "accept-gate policy" is explicitly rejected below.

**The ledger is the inspection surface.** Every role appends its output (proposal · measurement ·
verifier-score · auditor-verdict · accept-decision), so any loop run is fully replayable and
debuggable from the ledger alone. Each role is an independently testable interface; loop-core
ships reference implementations of the generic strategies (clade-yield proposer, heretic auditor,
e-process gate) that projects compose and override. This is the classic propose-evaluate-select
loop (genetic / active-learning) decomposed into its natural roles, with durable memory.

## Ledger — corpus stays separate; the real `ledger-core` is loop↔loop (re-scoped 2026-06-16)

The Phase-4 critique correctly killed a **`corpus_core ↔ loop`** ledger-core: corpus is a belief GRAPH
(recursive resolution, claim-relations, `support_balance` traversals — confirmed in `graph_schema.sql`);
a loop ledger is a LINEAR timeseries of trials. Divergent access patterns → no shared package across
*that* boundary; corpus keeps its own ledger. They share only a *discipline* (append-only ·
content-addressed · supersession · JSONL→rebuildable-DuckDB · derived-scalars-as-views).

**But the critique and the draft mis-scoped the extraction (Markus, 2026-06-16).** The real `ledger-core`
opportunity is **loop ↔ loop ↔ loop** — hutter, anim-workbench, and intel (+ more RSI loops coming) are
all the SAME shape: append-only timeseries trial logs with `predicted/actual/verdict/lineage`. The
architectural-mismatch objection does **not** apply among same-shape loops, and their lockstep coupling
is *appropriate* (they should co-evolve). With ≥2 existing callers (hutter SQLite + anim JSONL) and more
arriving, the proven-common bar is plausibly met. The only open question is the empirical 50-line-wrapper
one — does the shared append/content-id/supersession/rebuild/schema-guard exceed a trivial wrapper — and
**more consumers make the probe more favorable, not less.**

**DELETION-PROBE RESULT (2026-06-16 — ran it, read both ledgers' code): NO package.** hutter is a SQLite
`experiments` table with **autoincrement int ids** + ~13 domain-specific views (calibration, clade-yield,
probe-transfer), explicitly **gitignored + rederived-by-rerun**. anim is a **~10-line** JSONL append
(`appendFileSync` + `JSON.parse`) + a domain coverage view. **The "ledger-core mechanics"
(content-addressing · supersession · JSONL→rebuildable-projection · schema-version-guard) were
`corpus_core`'s — the loops have NONE of them.** What the loops share is ~10 lines of stdlib + domain
views that do NOT share — the 50-line wrapper, confirmed by code. **Markus's reframe was right (loops ARE
same-shape; the corpus-mismatch reasoning was wrong) — but same-shape ≠ shared mechanics: a PATTERN, not
a library.**

**Forward-standard caveat:** a shared *mature* ledger lib (bringing corpus's content-id/supersession/
replayability TO the loops) is a separate, SPECULATIVE bet — it imposes machinery the current loops don't
use or need (hutter gitignored-rederivable; anim raw JSONL). Per the repo's no-speculative-shared-utils
rule, revisit ONLY when ≥3 loops concretely NEED a replayable/supersession ledger. Today: no.

## Invariants to preserve

1. **Verifier is ground-truth, never LLM-judged** (a bad eval is worse than none — Goodhart).
2. **The Auditor role is mandatory** even when the Accept-gate policy is greedy (PACE: greedy
   alone = self-p-hacking; the auditor is the anti-self-dealing component).
3. **Falsifiable contract is non-tautological** (anim's `grow-ledger` already enforces this).
4. **Append-only / supersession-not-mutation** — overwriting destroys the replayable moat.
5. **Every role traces to the ledger** — inspectability is an invariant, not a feature.

## Rejected alternatives

- **Coarse field-list factoring** (the prior draft: propose/auditor buried in "accept-gate
  policy") — rejected: it hides the two roles that most need to be first-class + swappable
  (Dreamer, Heretic). Shallower than the structure that actually exists in the code.
- **Jam experiment trials into corpus_core's `annotations` table** — rejected: different domain;
  pollutes the belief graph (field-compare evidence: `predicted/actual/verdict` vs
  `status/relation_class`).
- **One mega "RSI framework"** owning everything as a monolith — rejected: roles are independently
  swappable interfaces, not a framework that dictates control flow (over-centralization, principle 9).
- **Status quo (hand-rolled per project)** — rejected: it is the consumption-over-autonomy disease;
  the loops already drifted on the accept-gate.
- **Any backward-compat shim / wrapper / dual-path** — rejected by directive: breaking refactor,
  full migration.

## Concrete first win — DONE (2026-06-16, in worktree, awaiting review)

**hutter adopts anim-workbench's Heretic auditor** — IMPLEMENTED in worktree
`~/Projects/hutter-heretic-wt` (branch `heretic-auditor`): `scripts/heretic_audit.py`, a stateless
per-track auditor (unverified-record ratio · zero-REJECT window · tautological-prediction ratio)
wired at the ACCEPT branch in `eval.py`. On FAIL → `ACCEPT_HELD`: the byte win is recorded + bit-exact
but does NOT ratchet (excluded from `v_leaderboard`/`v_accepted`, surfaced in new `v_held` view for
human triage). 12 tests pass; not merged. Proves the Auditor role end-to-end with no loop-core package.
NOTE (scout S2): hutter's exact-byte ratchet is zero-variance and structurally sound — the real hole
is *compute allocation under noisy proxies* and *search-space self-dealing*, not false ACCEPTs; the
auditor flags selection-pressure/calibration drift, it does not fix a broken ratchet.

## Gating sequence — default is NO package

1. **DONE** — hutter Heretic auditor win (above). The one real build; per-project, zero-dependency.
2. **Write the ledger CONTRACT/SPEC + conformance fixtures** (file layout · record envelope · content-ID
   rule · supersession rule · schema-version rule · rebuild semantics). This documented pattern IS the
   shared artifact — zero package.
3. **Brutal deletion-probe on the LOOP ledgers (hutter + anim, both EXISTING).** A `ledger-core` package
   is justified if both migrate onto one API by DELETING their local mechanics (proven by deletion, not
   "could share"). The corpus↔loop pairing is excluded (divergent); loop↔loop is same-shape with ≥2
   callers now + intel/more coming — so this probe is worth running and may well PASS. If the shared
   mechanics exceed a trivial wrapper → extract `ledger-core` (loops only); each loop keeps its domain schema.
4. Build NO shared **runtime** (only hutter is standalone; partial regimes are conductor-driven —
   FINDING 4). The roles stay a documented pattern. The ledger-core **package** is GATED on step 3's
   loop↔loop probe — not pre-rejected, not pre-assumed.

## Global meta-loop tie-in

loop-core ledgers feed the **EXISTING** global promotion loop (`blindspot_miner` → `/observe` →
`improvement-log` → `/improve maintain` → harness), NOT a new mechanism. Upward promotion runs through
the global constitution gate (2+ sessions · checkable predicate · blast_radius tier), **never** the
per-project accept-gate. The per-project accept-gate (PACE anti-self-p-hack) and global gov-shrink
(capability-rising retirement) are **orthogonal** gates with opposite defaults. Auditor rejections
classify to the supervision taxonomy (`GROW_COVERAGE`/`REDUCE_ERROR`) and feed blindspot-miner;
accept-gate policy divergence across projects becomes *visible* in the ledger → a harmonization
proposal for agent-infra to gate. The actuator gaps in that global loop are real and pre-existing
(`gov.py` AUTO_APPLY=False; no prediction-registration trigger; 13× add-vs-retire) — loop-core adds
upstream signal, it does not close them.

## Revisions

- **2026-06-16 — deletion-probe RESULT (supersedes the Gating step-3 "may well PASS"):** the probe was RUN
  (read hutter + anim ledger code). **FAILED → no `ledger-core` package.** hutter = SQLite table +
  autoincrement int ids + ~13 domain views (gitignored/rederived-by-rerun); anim = a ~10-line JSONL
  `appendFileSync` + a coverage view. The content-id / supersession / rebuild / schema-guard mechanics
  that would justify a package are `corpus_core`'s — **absent in the loops.** They share ~10 lines of
  stdlib + non-shared domain views (the 50-line wrapper, confirmed by reading code). Markus's same-shape
  reframe was correct, but same-shape ≠ shared library.
- **Arc shape (this ADR got *more conservative* under pressure — the point of running the arc):**
  deep role-based PLATFORM + ledger-core → (history scout: outer-loop already built+killed, zero callers)
  roles = documented pattern → (cross-model critique: ledger-core = displaced overreach) → (Markus: loops
  are same-shape, re-open) → (deletion-probe: loops share stdlib, not mechanics) **build NOTHING shared.**
  Net build across the whole arc: the hutter Heretic auditor only (DONE, merged `c70e1f1`). The Gating
  section's pre-probe optimism and the body's earlier "ledger-core is a live candidate" are superseded by
  this entry.
