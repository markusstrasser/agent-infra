---
id: 2026-06-07-categorical-discovery-framework-mapping
concept: categorical-discovery-substrate
repo: agent-infra
decision_date: 2026-06-07
recorded_date: 2026-06-07
provenance: contemporaneous
status: accepted
initial_leaning: "build a categorical layer (CategoryScienceClaw analog) over our corpus"
relations:
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-06-07: Buehler/Wang categorical discovery framework — recognize, don't rebuild

## Context

Read arXiv **2606.01444** (Wang & Buehler, MIT LAMM), *Self-Revising Discovery
Systems for Science: A Categorical Framework for Agentic Artificial
Intelligence* (ingested to corpus via marker-modal). It gives a category-theoretic
account of agentic discovery: system state is a copresheaf `It : Sb → Set`,
provenance is the category of elements `∫ It`, a fixed-regime update `Φb` is
endofunctorial only when provenance-preserving, and **discovery** is a *verified
regime transition* `u : Sb → Sb′` — old artifacts are preserved and transported
by left Kan extension `Lanu It`, then compared to the post-transition state; the
**residual content beyond functorial transport is the measure of discovery**
(Prop. 4). Two instantiations: Builder/Breaker (symbolic protein-mechanics model
revised under an MDL gate) and CategoryScienceClaw (a proof-carrying categorical
layer over the ScienceClaw × Infinite multi-agent platform).

Question posed: *how do we implement this in agent-infra?*

The finding is that **agent-infra has already independently built most of the
paper's computational substrate** under different names. The implementation of a
theory paper into a running system is, here, primarily *recognition* (record the
isomorphism so we don't rebuild it) plus two small genuine gaps — not
construction.

## Alternatives considered

1. **Build a CategoryScienceClaw analog** (a categorical/proof-carrying layer over
   our corpus). — *Rejected.* CategoryScienceClaw is explicitly a wrapper that
   lifts the **ScienceClaw × Infinite** substrate (distributed typed-skill
   execution + a public discourse platform: posts, votes, reputation, moderation)
   into typed objects. We don't run ScienceClaw, we're a single operator with no
   discourse layer, and there's no consumer. Pure Pre-Build-Check /
   [[consumption-over-autonomy]] violation; same class as the Autobrowse
   skill-graduation veto.
2. **Build an MDL-graded governance gate** (Builder/Breaker for our own
   rules/hooks: accept a new scaffold only if it reduces total description length
   `Lmodel + Ldata` on the accumulated error ledger). — *Rejected.* Beautiful fit,
   but **veto-adjacent to the twice-killed `session_quality` scored gate**
   (`.claude/rules/vetoed-decisions.md`), and our binary `gov-shrink` (re-run the
   verifier with the scaffold removed; retire if it still passes) plus the prose
   governance rule already do this job on ground truth. By its own MDL logic it
   doesn't pay for its bits yet.
3. **Recognize the substrate as an existing instantiation, record the dictionary,
   fill the two real gaps (move-type typing; residual-as-discovery-measure), and
   explicitly not-build the rest.** — **CHOSEN.**
4. **Do nothing — it's a theory paper.** — *Rejected.* The dictionary itself is
   load-bearing (it forecloses a rebuild of what we have — our #1 documented
   failure mode), and at least one gap is backed by ground-truth recurrence
   (build-then-undo, below), not hypothetical.

## Counterevidence sought

- *What would falsify "we already built ~80%"?* The discourse layer `Dt` and
  publication map `πt`. We **genuinely lack these** — single-operator, no
  posts/votes/reputation; the decision journal + git log are a thin proxy at best.
  So the honest claim is "≈80% of the **computational** substrate `Kbt` minus
  `(Dt, πt)`," not 100%. Recorded as a limitation, not papered over.
- *What would reverse "don't build CategoryScienceClaw"?* A real distributed
  multi-agent discovery + discourse workload. Searched: none exists here; the
  consumption-over-autonomy and Autobrowse-graduation assessments already
  established that recurring sources graduate into *tools*, not a discourse graph.
- *Is the move-type gap real or hypothetical?* `uv run python3
  scripts/buildthenundo.py` → **46 findings / 31 high-confidence in 30d**. That
  detector cannot distinguish "rebuilt something that already existed" (bad —
  retrieval mislabeled as a build) from "superseded old structure with genuine new
  residual" (good — a discovery/regime transition, e.g. the `scripts/papers/` →
  `corpus` consolidation). The paper's transport-vs-residual split is exactly that
  missing discriminator. Gap confirmed against ground truth.

## Decision

### The dictionary (paper `Kbt = (Sb, Γb, It, Provt, Vb, Lb, Dt, πt)` ↔ our substrate)

| Paper construct | agent-infra mechanism |
|---|---|
| `It : Sb → Set` typed artifact state | corpus `annotations` keyed by `scope`/type (`scripts/corpus/.../store.py`, `graph_schema.sql:61`) |
| `∫ It` category of elements (provenance) | `claim_relation_endpoints` (subject/object/anchor) + parent lineage |
| morphism `f:A→B` (typed operation) | `claim_relations`, closed schema, `relation_class ∈ {support,extend,qualify,refute,background}` + `detector` |
| refinement `δt` (provenance-preserving update) | append-only **supersession**: `supersedes_annotation_id`, `status∈{active,superseded,retracted}`, tombstones — *literally* Props 5 & 7 |
| gate / verifier `Vb` | verdicts + source-grade hooks + **`gov-id` `verifier:` (ground-truth grader)** + `audit_corpus_sync` drift gate |
| desc-length functional `Lb` | **partial** — binary `gov-shrink` + `support_balance` scalar; not graded MDL (deliberately, see Alt 2) |
| regime transition `u:Sb→Sb′` | decision-journal `relations: supersedes/branches_from/reopens` + bitemporal schema migration |
| Kan transport `Lanu It` | supersedes chain + `valid_from` bitemporal replay/projection |
| residual content (discovery measure) | **GAP** (see gap 2) |
| rejected alternatives as first-class objects | `vetoed-decisions.md` + decision "Alternatives considered" + `Rejected:` commit trailer |
| Builder/Breaker + gate loop | `/observe`+session-analyst (Breaker) → improvement-log (Builder) → `gov-id`/`gov-shrink` (gate) |
| discourse `Dt`, publication map `πt` | **absent** (single operator); decision journal + git log are a thin proxy |

Two structural facts stand out: our **append-only-with-supersession ledger is
exactly the paper's "preserve old artifacts, never silently delete"** (Prop. 7 /
Remark 4), and our **`gov-id → gov-shrink` loop is Builder/Breaker** — binary
(verifier passes/fails) where the paper is MDL-graded (bits).

### The two real gaps

1. **Move-type typing (retrieval / search / discovery — Fig. 1).** We conflate
   "found that X already exists" (retrieval → *stop, reuse it*), "recombined
   existing rules/tools" (search), and "added a new hook/relation-class/verifier
   category" (discovery → *name the residual*). The distinction is already
   pervasive practice (Pre-Build Checks, probe-before-build, `no_vetoed_rebuild`
   grader) but **untyped**.
2. **Residual-as-discovery-measure (Prop. 4).** When we make a regime transition
   we don't compute *what it added beyond transporting old structure*. This is the
   discriminator `buildthenundo.py` lacks (a pure-transport change with zero
   residual is the suspect class).

### Verdicts

- ✅ **DO** — this memo (the dictionary; near-zero maintenance; prevents rebuild).
- 🟡 **BUILD (minimal, evidence-backed)** — `move_type: retrieval|search|discovery`
  field on decisions + improvement-log, where a `discovery` entry **must name its
  residual** (the new type/hook/verifier/relation-class). Checkable predicate;
  verifier-bound (a `gov-id` grader). Design pending cross-model review.
- ❌ **DON'T** — MDL-graded `gov-shrink` (Alt 2: veto-adjacent, binary suffices).
- ❌ **DON'T** — CategoryScienceClaw wholesale (Alt 1: no consumer, single-operator).
- ❌ **DON'T (yet)** — a standalone residual-content audit on schema transitions;
  `bitemporal-migrate` + `audit_corpus_sync` cover migration safety and schema
  evolution is rare. Fold the residual idea into `move_type` (gap 1) instead of a
  separate system.

## Evidence

- Paper: arXiv 2606.01444, Defs 1–6, Props 4–8, Builder/Breaker MDL case (Eq. 5–8),
  CategoryScienceClaw fiber-network case. Ingested to corpus (marker-modal).
- Substrate survey (this session): `corpus_core` schema, supersession/tombstone
  semantics, transactional outbox, `gov-id.md` / `gov-shrink`, `vetoed-decisions.md`.
- Ground-truth recurrence: `scripts/buildthenundo.py` 46/30d; improvement-log
  recent entries dominated by retrieval-class "already exists" findings.
- Prior art / non-duplication: complements
  `decisions/2026-05-26-cross-attestation-substrate-v2.md` and
  [[science-graph-positioning-2026-05]] (corpus = within-repo belief ledger, not a
  cross-repo claim graph).

## Revisit if

- A distributed multi-agent discovery + discourse workload emerges (reopens the
  `Dt`/CategoryScienceClaw question).
- Schema evolution becomes frequent enough that a dedicated residual audit pays for
  itself.
- The `move_type` discriminator proves insufficient and build-then-undo triage
  genuinely needs the full Kan-residual computation.

## Supersedes

None. Depends on the corpus substrate (`2026-05-26-cross-attestation-substrate-v2`).
