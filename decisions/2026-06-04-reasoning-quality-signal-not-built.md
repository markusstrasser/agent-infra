---
id: 2026-06-04-reasoning-quality-signal-not-built
concept: reasoning-quality-fitness-signal
repo: agent-infra
decision_date: 2026-06-04
recorded_date: 2026-06-04
provenance: contemporaneous
status: accepted
initial_leaning: build a calibrated, outcome-orthogonal "reasoning soundness" scorer (TAA + perturbation + enforcer-regression) in evals/, gated by a power spike
relations:
  - type: depends_on
    target: 2026-06-01-cross-repo-contradiction-layer-not-built
  - type: branches_from
    target: 2026-06-01-genomic-phenotype-support-linking
---

# 2026-06-04: Reasoning-Quality Signal (RQS) — kill the build, keep report-only

## Context
The thesis-verifier work (intel-harness) re-derived a rule: *grade the orthogonal
reasoning signal, not the noisy outcome* (the placebo came back NULL — residual
direction is chance at N=15). The question was whether that generalizes to **agent
sessions**: build a calibrated, outcome-orthogonal "reasoning soundness" fitness
signal to rank enforcer proposals / A-B rulesets / eventually evolve rules. Homed
in `evals/`. Brainstorm (25 ideas → 5 clusters) + cross-model `/critique` (Gemini
3.5 Flash + GPT-5.5) shrank a grand "LLM-judged fitness engine" to a deterministic,
report-only v2: **Tool-Action Alignment (TAA)** + perturbation-sensitivity +
enforcer-regression-suite, gated by **VALIDITY BEFORE SCORER** — a Phase 0a kill-test
that builds the cheapest possible TAA scorer and checks it separates known-flagged
from clean sessions *before* anything is built in `evals/`.

This decision records the Phase 0a outcome: **kill the build.**

## Alternatives considered
1. **Build the RQS scorer in `evals/`** (the plan) — calibrated TAA + perturbation +
   enforcer-regression behind a `BaseSessionScorer`. *Rejected* — see Decision.
2. **Kill the build; keep existing report-only detectors** (chosen) — `trace-faithfulness.py`
   (+ `reasoning-audit.py`, `tool-trajectory.py`, `pushback-index.py`, `thesis-challenge.py`,
   `fold-detector.py`) already exist and run; route decision-level reasoning soundness to
   cross-model `/critique` (the constitution's named mitigation for semantic failure).
3. **Wire/consume the existing detector fleet into the session-loop's missing
   per-enforcer metric** — deferred, not killed. The real latent gap is *consumption*
   ([[consumption-over-autonomy]]), not a new scorer. Recorded under "Revisit if."

## Counterevidence sought
Before killing, I searched for evidence the build is justified:
- **A documented "reasoning-action mismatch" the existing detectors miss but TAA would
  catch.** Found ~1-2 instances ever (the canonical one, `07231221`, Gemini-dispatch
  "removed capability instead of fixing transport"); the log is otherwise dominated by
  **build-then-undo** (out of RQS scope, already report-only via `buildthenundo.py`) and
  **semantic/coherent-wrong** failures. The mismatch class TAA targets is nearly empty.
- **Any separation on the surviving labels.** Ran the probe (below). The two signals RQS
  proposed (faithfulness, entity-TAA) show **zero/inverted** separation.
- **A durable gold set to ever calibrate against.** 4 of the 5 cleanest human-labeled
  sessions (Run-25, 2026-04-09) are rotated off disk AND absent from `agentlogs.db`.
  Calibration on rotating JSONLs is infeasible without snapshotting features at label-time.
Searched for the case that reverses the kill; did not find it.

## Decision
**Do not build RQS.** Phase 0a met its pre-registered KILL criterion empirically and
structurally. The kill rests on three independent legs (the first two are N-independent):

1. **Pre-Build duplication.** `scripts/trace-faithfulness.py` already computes the
   TAA-equivalent (`faithfulness_score`), `fabrication_rate` (ground-truth-bound
   provenance check), and TRACER trajectory signals. A new scorer rebuilds what exists.
2. **Ephemeral calibration substrate.** The labeled gold set the validity gate needs does
   not durably exist; session JSONLs rotate and were not all indexed.
3. **Structural + empirical falsification of TAA.** Entity-level thought↔action alignment
   is flat/inverted on the surviving labels, AND *cannot in principle* catch the dominant
   documented failure — **coherent rationalization**, where the thought AGREES with the
   wrong action (alignment is HIGH on a bad decision, not low). That class is **semantic**;
   the constitution already names cross-model review as its only mitigation.

The one signal that survived length-normalization (repeated-tool *rate*, pos 7.97 vs neg
3.86 per 100 tools) is the **existing** TRACER trajectory detector tracking thrashing /
build-then-undo — out of RQS scope, already covered report-only, and resting on N=2.
It does not justify a new calibrated scorer.

This is **low-irreversibility**: if a real incident ever shows a reasoning-soundness gap
the existing report-only fleet + `/critique` miss, we build then. Absence of a feature ≠
presence of a problem.

## Evidence
Phase 0a probe (`.scratch/taa_probe.py`, throwaway; reuses `trace-faithfulness.py`
functions over DB-reconstructed traces since source JSONLs rotated). Labeled positives =
documented quality findings; negatives = recent completed sessions (assumed-clean, NOT
verified — a deliberate weakness, reported).

```
   pk  lbl turns  faith  fab    taa  rep/100  errIgn  note
  356  pos   249   1.00    3  0.071      8.8     292  07231221 reasoning-action mismatch + build-then-undo
  123  pos   592   1.00    8  0.085      7.1     455  3d4a2d99 build-then-undo + hook contention
 3547  neg    15    n/a    2  0.068      0.0      16  agent-infra 05-19
 3747  neg    69   1.00    0  0.065      4.9      93  intel 05-29
 3751  neg   104   1.00   10  0.044      3.3     156  intel 05-25   (more fabrications than either positive)
 3725  neg    37   1.00    4  0.061      2.7      57  intel 05-25
 3713  neg    71   1.00    2  0.038      4.6     108  intel 05-27
 3717  neg    46   1.00    3  0.037      3.9      60  intel 05-24
 3441  neg    36    n/a    0  0.039      5.2      59  intel 05-15
 3560  neg    19    n/a    7  0.047      6.2      27  intel 05-21

separation (length-normalized):
  faith            : pos=1.000 neg=1.000  no separation
  taa (alignment)  : pos=0.078 neg=0.050  INVERTED (positives more aligned)
  fab / turn       : pos=0.013 neg=0.100  INVERTED (positives better)
  errIgn / turn    : pos=0.971 neg=1.418  INVERTED (positives better)
  repeated / 100tc : pos=7.968 neg=3.864  pos worse — but = existing TRACER signal, out of scope
```

Caveats (reported, not hidden): N=2 positives; negatives assumed-clean not verified;
one "clean" session (3751) has the highest fabrication count of all. These weaken the
empirical leg but do not touch the Pre-Build or substrate legs.

Provenance: brainstorm `.brainstorm/2026-06-04-reasoning-quality-signal-7eabbe74/`;
critique `.model-review/2026-06-04-reasoning-quality-fitness-signal-rqs-pro-b6578f/`;
plan `.claude/plans/7eabbe74-reasoning-quality-fitness-signal.md` (now KILLED).

## Revisit if
- A real incident shows a reasoning-soundness failure that the existing report-only fleet
  (`trace-faithfulness` et al.) AND cross-model `/critique` both miss, with the session
  data still on hand. Then build narrowly for *that* class.
- Someone wants session-level calibration enough to first solve the substrate problem
  (snapshot labeled session features at label-time, since JSONLs rotate).
- The session-loop's missing **per-enforcer success metric** becomes a measured pain — the
  fix is *consuming* existing detector output ([[consumption-over-autonomy]]), not a new scorer.

## Supersedes
Supersedes the build intent in `.claude/plans/7eabbe74-reasoning-quality-fitness-signal.md`.
Aligned with the earlier "outcome is the noise" lesson — but that lesson does NOT transfer:
agents get cheap deterministic environment ground truth (pytest/compiler/diff), so the
right move is deterministic env-grounded checks (which already exist), not an LLM-judged
reasoning scorer.
