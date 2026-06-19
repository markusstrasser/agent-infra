---
concept: reproducible-fact-contract
decision_date: 2026-06-19
status: proposed
relates_to:
  - substrate ADR 0009 (fat substrate + thin adapters)
  - 2026-06-19-rsi-sota-synthesis-what-to-integrate.md
  - 2026-06-19-behavioral-eval-feasibility.md
supersedes: []
---

# Reproducible-fact contract — verdicts become citable facts

## Telos
Every testground/eval verdict ("X does/doesn't work") becomes a **reproducible, citable
fact** — re-derivable by anyone and publishable to a KG/paper — instead of a one-off
observation that evaporates. Driver: operator, 2026-06-19 ("so reproducible it can go into a
public knowledge graph or a paper").

## The real axis (Phase 0)
NOT "which carrier shape" — the probes settled that. The governing axis is:
**the reproducibility TIER is the fact's epistemic grade.** A bit-exact verdict (hutter
round-trip) and a weak-tier verdict (behavioral model-sampling) are different epistemic
objects; the contract's core duty is to make the guarantee first-class and **forbid
tier-laundering** (a distributional/weak verdict presenting as a hard fact). Corollary axes
the evidence forced: a fact is a *verdict*, not a run (sim); corpus stores a *pointer*, not
the fact (probe-corpus); the home is *fixed* to the substrate (ADR 0009 R5), not chosen.

## Decision (the principle)

**P1 — Tier is the reproducibility MODE; epistemic grade is COMPUTED, multi-axis.** [REFINED
by Phase-4 cold critique: reproducibility ≠ validity.] The envelope carries `reproducibility
{tier ∈ bit-exact|distributional|weak, guarantee, evidence}` — but **tier is ONE axis, not the
grade.** What "re-derivable" means is tier-specific: bit-exact → identical output hash @SHA;
distributional → same verdict at the pre-registered z over recorded CRN seeds+n; weak → verdict
CI overlaps at the threshold over n samples. **Publishable epistemic grade = f(reproducibility,
pre-registration, statistical strength (power/MDE), scope validity, oracle validity,
independence)** — computed by a validator, NOT producer-declared. A bit-exact-reproducible
result that is underpowered or scope/oracle-invalid is *reproducible but not a citable fact.*
No laundering: a fact may not claim a stronger tier than its verifier supports, AND honest
tier-labeling alone does not confer citability — the computed grade gates that.

**P2 — Emit at the verdict, on a clean tree.** The envelope is emitted at the VERDICT
(ratchet/aggregation), not per-run (a raw row is 6/15 of a fact — sim). `harness_sha + dirty`
is required; **`dirty=True` ⇒ not a publishable fact** (un-re-derivable).

**P3 — Carrier = S6 hybrid (manifest + corpus pointer).** The producing repo emits the
envelope as a provenance **manifest**; corpus-core attests a support/refute `claim_relation`
+ a hash-pinned pointer (`output_uri` + `output_hash`). Corpus is index+attestation, NOT the
fact-store (probe-corpus: closed relation holds only the edge + grade_weight; 16 KiB ceiling).
**`run_id` = manifest content hash = corpus `output_hash`** — one hash, three roles (run
identity, manifest integrity, corpus pointer).

**P4 — Home = the substrate; consumers are thin adapters (ADR 0009 R5).** The envelope schema
+ emit logic live in **`evalcore`** (the substrate eval fat-library; `run_eval` is already the
proven template). Attestation lives in **`corpus-core`**. arc-agi/hutter/anim/phenome are
THIN ADAPTERS that call `evalcore.emit_fact(...)` — they do NOT reimplement the envelope
(epistemic-principle #9 + R5). One schema, single-sourced.

**P5 — Strictness = core + extended.** Required core: claim + decision_rule + prediction;
harness_sha + dirty; verdict + reproducibility.tier; run_id; heretic.ok. Optional extended:
full metrics (n/SE/effect-size/z), token_cost {reasoning,output,input}, calibration, env.
Low adoption barrier; the core is what makes a fact minimally re-derivable + non-self-dealing.

**Net-new universal fields** (probe-coverage: 0/4 today): token_cost · content-addressed
run_id · corpus_attested · env · in-record decision_rule.

## Invariants the decision must preserve
- tier = epistemic grade (P1); pre-registration is provably-before-results; emit-at-verdict (P2);
- heretic-clean gates publishability (a fact over oracle-unbacked runs is not a fact — the arc-agi
  RHAE=0.0003 class); single schema in evalcore (P4); dirty-tree ⇒ no fact (P2).

## Rejected alternatives
- **S1 flat-only** — no cross-repo KG path (needs a collector); fine as the *manifest body*, not the system.
- **S2 dir-per-run** — heavy; not substrate-native; evals' value (pre-reg enforcement) folds into evalcore.
- **S3 event-sourced** — overkill; a locked pre-reg timestamp + emit-at-verdict suffices.
- **S4 git-native (notes)** — notes are unqueryable / don't sync; SHA-pin is reused (P2) without making notes the carrier.
- **S5 corpus-as-fact-store** — REFUTED by probe-corpus (closed schema + 16 KiB ceiling; grade_weight is the only scalar, "never a probability").
- **A-strict** — adoption barrier across 4 ledgers; core+ext wins.
- **Per-testground schema / agent-infra as home** — violates epistemic-#9 + ADR 0009 R5 (wrong layer).

## Coordination (corpus is MID-REFACTOR — do not fork it)
The canonical schema lands in `evalcore` **coordinated with ADR 0009** (M1 in flight) — proposed
to the substrate, not unilaterally edited. **De-risk path:** prototype `emit_fact` as a THIN
arc-agi adapter call (the just-touched `loop/ratchet.py` verdict, where claim+paired-z+heretic+
calibration already converge — P2's natural site), validate the envelope end-to-end on one repo,
then upstream the canonical schema to `evalcore` when the migration coordinates it.

## Post-critique refinements (Phase 4 — cursor repo-grounded over substrate + cold-gpt frontier)
NO spine reversal (both kept P2–P5). Three evidence-backed refinements + an already-handled map:

1. **P1 reframe (cold-gpt):** tier = reproducibility MODE, not epistemic grade; publishable grade is
   computed multi-axis. reproducibility ≠ validity (a bit-exact but underpowered/scope-invalid result is not a fact).
2. **run_id "one hash, three roles" → MISMATCH, corrected (cursor, file:line):** substrate `run_id` is a
   timestamp (storage.py:52-57); `output_hash` defaults to `relation_content_sha` (the relation SEMANTIC
   core, identity.py:140-148) and enqueues NULL (outbox.py:276-281). Substrate does NOT unify them. FIX:
   `run_id` = a NET-NEW content-addressed field = the manifest content hash, DISTINCT from the relation's
   `output_hash`; the manifest is referenced by `output_uri` (PRESENT). Manifest integrity = a separate `manifest_hash`.
3. **grade_weight ∈ [0,1] is narrative-only (cursor):** unenforced at runtime; regardless it cannot carry an
   effect size — quantitative fields stay in the manifest, never the relation. No change to P3.

**Already-handled (PRESENT — do NOT rebuild) vs OPEN (build):**
- PRESENT: corpus index + claim_relation attestation + repo-URI hash-pinned sidecars (annotate.py, outbox.py,
  uri.py); evalcore run-provenance (run_id/code_commit/model/seed across run.py + storage.py + run_manifest.py).
- OPEN (net-new): `evalcore.emit_fact()`; the envelope fields (tier, harness_sha+dirty, heretic, decision_rule,
  token_cost, corpus_attested, content-addressed run_id); the **multi-axis publishability VALIDATOR** (P1); the
  manifest→corpus wire-up for fact envelopes.

**Deferred design (for the substrate ADR):** cold-gpt's composable model — Claim · DecisionRule · EvidenceBundle ·
Verdict · Attestation (the fact = a Verdict over an EvidenceBundle under a DecisionRule, attested) — "more
composable than treating the manifest as the fact." Evaluate when authoring the substrate ADR.

## Status
REFINED post-critique — spine (P2–P5) survived repo-grounded + cold critique with **zero reversals**; P1
sharpened (tier=mode; grade=computed multi-axis). **Pending operator sign-off.** Substrate-touching standard,
NOT locked here. The canonical substrate ADR (~/Projects/substrate/docs/decisions/, coordinated with ADR 0009)
is the follow-up; this agent-infra record is the principle + the pointer. First build slice: `evalcore.emit_fact()`
+ the publishability validator, prototyped as a thin arc-agi ratchet-verdict adapter, upstreamed when ADR-0009 coordinates.
