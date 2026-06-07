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
Intelligence* (ingested to corpus, `doi_10_48550_arxiv_2606_01444`, marker-modal).
It gives a category-theoretic account of agentic discovery: system state is a
copresheaf `It : Sb → Set`, provenance is the category of elements `∫ It`, a
fixed-regime update `Φb` is endofunctorial only when provenance-preserving, and
**discovery** is a *verified regime transition* `u : Sb → Sb′` — old artifacts are
preserved and transported by left Kan extension `Lanu It`, then compared to the
post-transition state; the **residual content beyond functorial transport is the
measure of discovery** (Prop. 4; when a new type receives no morphism from old
types the Kan extension is empty, forcing residual). Two instantiations:
Builder/Breaker (symbolic protein-mechanics model revised under an MDL gate) and
CategoryScienceClaw (a proof-carrying categorical layer over the ScienceClaw ×
Infinite multi-agent platform).

Question posed: *how do we implement this in agent-infra?*

## Decision (summary)

**Recognize, don't rebuild.** agent-infra already runs the *conservative
engineering substrate* the paper describes — and, importantly, runs it at the
**same fidelity the paper's own flagship system claims for itself**. Build **one**
small, ground-truth, no-operator-tax thing (a *computed* move-type classifier in
`buildthenundo.py`). Explicitly **do not** build three things (CategoryScienceClaw
wholesale; an MDL-graded governance gate; a standalone schema-residual audit).

## Alternatives considered

1. **Build a CategoryScienceClaw analog** (categorical/proof-carrying layer over
   our corpus). — *Rejected.* CategoryScienceClaw lifts the **ScienceClaw ×
   Infinite** substrate (distributed typed-skill execution + a public discourse
   platform: posts, votes, reputation, moderation). We don't run ScienceClaw,
   we're single-operator with no discourse layer, no consumer. Pre-Build-Check /
   [[consumption-over-autonomy]] violation; same class as the Autobrowse veto.
2. **Build an MDL-graded governance gate** (Builder/Breaker for our own rules:
   accept a scaffold only if it lowers total description length `Lmodel + Ldata`
   on the accumulated error ledger). — *Rejected* — see corrected reasoning below.
3. **Recognize the substrate, record the honest fidelity map, build one computed
   discriminator, not-build the rest.** — **CHOSEN.**
4. **Do nothing — it's a theory paper.** — *Rejected.* The fidelity map forecloses
   a rebuild of what we have (our #1 failure mode), and the discriminator gap is
   backed by ground-truth recurrence (build-then-undo, below).

## Counterevidence sought

- *Falsify "we already built most of it"?* **Found, and it downgraded the claim.**
  A first draft asserted "~80% of `Kbt`." Cross-model review (Gemini 3.5 Flash +
  GPT-5.5, 2026-06-07) showed the dictionary forced category-theoretic fits onto
  database affordances; honest weighted coverage is **~35–45%**, not 80%. The
  paper's *own* §2.6/§4.7 make the same hedge about CategoryScienceClaw: it is
  "weaker than a software-enforced schema category … should not be overclaimed,"
  realizing only "a typed artifact family and an acyclic provenance hypergraph,
  whose path-category shadow gives the category-of-elements-style structure."
  So the defensible claim is: **we have the same conservative engineering
  substrate the paper's flagship claims — and neither we nor the paper implement
  the full categorical formalism (functorial `It(f)`, typed morphisms with
  composition, Kan transport across schema maps). The formalism is
  specificational, not built.**
- *Reverse "don't build CategoryScienceClaw"?* A distributed multi-agent discovery
  + discourse workload. None exists; recurring sources here graduate into *tools*,
  not a discourse graph (Autobrowse / consumption-over-autonomy assessments).
- *Is the discriminator gap real?* `scripts/buildthenundo.py` → **46 findings / 31
  high-confidence in 30d**. It flags add-then-delete but **cannot distinguish
  "rebuilt something that already existed" (waste) from "superseded old structure
  with surviving residual" (a legitimate regime transition, e.g. `scripts/papers/`
  → `corpus`)**. The paper's transport-vs-residual split is exactly that
  discriminator. Gap confirmed against ground truth.

## Decision

### Fidelity map (paper `Kbt = (Sb, Γb, It, Provt, Vb, Lb, Dt, πt)` ↔ our substrate)

Legend: **✓** structural match (the engineering affordance genuinely exists) ·
**≈** affordance only (storage/labels, not the categorical structure) · **✗** gap.

| Paper construct | agent-infra mechanism | Fidelity |
|---|---|---|
| `It : Sb → Set` copresheaf | annotations keyed by `scope`/type | ≈ storage only; **no functorial `It(f)`** between scopes |
| `∫ It` category of elements | `claim_relation_endpoints` + lineage | ≈ provenance links, not realized `It(f)(x)=y` operations |
| morphism `f:A→B` (typed op) | `claim_relations` (`support/extend/qualify/refute/background`) | ≈ **semantic edge labels**, no typed src/tgt signatures or composition law → not a schema category |
| refinement `δt` (provenance-preserving) | append-only **supersession** (`supersedes_annotation_id`, tombstones, status) | ✓ genuine — Props 5/7 (refinement lifts to a faithful functor on provenance; old evidence inspectable) |
| gate / verifier `Vb` | verdicts + `gov-id` `verifier:` (ground-truth grader) + source-grade hooks | ✓ genuine |
| desc-length functional `Lb` | binary `gov-shrink` + `support_balance` scalar | ≈ binary, not graded MDL (deliberate) |
| regime transition `u:Sb→Sb′` | decision-journal `relations` + bitemporal migration | ≈ human-readable history, not a schema functor on objects/morphisms |
| Kan transport `Lanu It` | — | ✗ supersession is *fixed-regime* preservation, **not** cross-schema colimit transport |
| residual content (discovery measure) | — | ✗ the `buildthenundo` discriminator (gap, building below) |
| rejected alternatives as first-class objects | `vetoed-decisions.md` + `Rejected:` trailer | ✓ genuine |
| Builder/Breaker + gate loop | `/observe`+session-analyst → improvement-log → `gov-id`/`gov-shrink` | ✓ structurally (binary gate, not MDL) |
| discourse `Dt`, publication map `πt` | — | ✗ absent (single operator, deliberate) |

Tally: **4 genuine / 5 affordance-only / 3 gaps.** The two facts worth keeping:
our append-only-with-supersession ledger genuinely realizes the paper's
refinement-morphism story (Props 5/7), and our `gov-id → gov-shrink` loop is
structurally Builder/Breaker — binary where the paper is MDL-graded.

### What is NOT implemented (and isn't by the paper either)

A real `Sb` (typed morphisms with source/target signatures and composition),
functorial action `It(f)`, and Kan transport across a schema map. These are the
paper's *specification* layer. Treat them as a design vocabulary for auditing our
substrate, **not** as something to go build — the paper's own flagship doesn't.

### The build (corrected after cross-model review): a *computed* move-type classifier

The original plan was a hand-typed `move_type: retrieval|search|discovery`
frontmatter field. **Rejected** (both reviewers, convergent): a self-reported tag
is gameable, rots, and adds operator tax — the exact "instructions over
architecture" anti-pattern the constitution forbids, and it taxes the
declining-supervision objective. Instead, **compute** the discriminator inside
`buildthenundo.py` from ground-truth git structure (zero operator tax):

- `discovery` — the churn touched the schema/rule/hook vocabulary (`*.sql`,
  `migrations/`, `.claude/rules/`, hooks): a regime transition, residual = the
  changed vocabulary element. *De-emphasize* (legitimate).
- `superseded` — a tracked file still carries the deleted file's identity
  (basename/symbol overlap): the work moved/consolidated, residual survives.
  *De-emphasize* (advisory; full AST/symbol fingerprinting deferred — review #20
  flags single-signal similarity as noisy).
- `churn` — default: no regime surface, no surviving twin → the genuinely-suspect
  pure build-then-undo. *Surface loudest.*

This turns the report-only detector into a re-ranking one and delivers gaps 1 + 2
(move-type typing **and** residual-as-measure) in one ground-truth artifact.

### Verdicts

- ✅ **DO** — this memo (honest fidelity map; prevents rebuild).
- ✅ **BUILD** — computed move-type classifier in `buildthenundo.py` (above);
  report-only, deterministic, no operator tax.
- ❌ **DON'T** — MDL-graded `gov-shrink`. *Corrected reasoning:* the original
  "veto-adjacent to `session_quality`" argument was a **category error** (review
  #28) — the vetoed `session_quality` was a *model-judged composite score*; an MDL
  gate would be *ground-truth bit-counting on the error ledger*, a genuinely
  different mechanism. The real reason to hold: **binary `gov-shrink` works with
  zero incidents where it failed to retire a scaffold it should have**; MDL adds
  maintenance for unproven gain. Revisit on a real `gov-shrink` miss.
- ❌ **DON'T** — CategoryScienceClaw wholesale (Alt 1).
- ❌ **DON'T (yet)** — standalone schema-residual audit, outbox diagrammatic-
  coherence gate, isolated-node lint. See "Acknowledged, not built."

### Acknowledged, not built (real-but-speculative gaps from review)

- **Outbox diagrammatic coherence** (review #2, HIGH): a txn can write
  `A support B, B support C, A refute C` since each edge validates individually.
  Real structural gap, but **zero contradiction incidents on record ever** and the
  cross-repo contradiction layer was already vetoed (2026-06-01). SPECULATIVE → no
  incident → don't build. Revisit only on a first observed contradiction.
- **Isolated-node / empty-Kan lint** (review #8/#18): a new scope/type/relation-
  class with no link to existing nodes = a silent regime addition. Folded *lightly*
  into the classifier's `discovery` signal; a standalone **blocking** lint risks
  bootstrap false-positives (review #22) → not a hook.
- **Proof-carrying claim-path lint** (review #12): report-only provenance links
  (claim → source hash → verifier receipt). Plausible but unproven need; the
  `gov-id` `verifier:` field already carries most of this. Backlog.

## Evidence

- Paper: arXiv 2606.01444 — Defs 1–6, Props 4–8; §2.6/§4.7 conservative-reading
  hedge; Builder/Breaker MDL case (Eq. 5–8). Ingested via marker-modal.
- Cross-model review (2026-06-07): `.model-review/2026-06-07-categorical-discovery-mapping-5ec743/`
  (Gemini 3.5 Flash arch + GPT-5.5 formal, 28 findings). Drove the 80%→35-45%
  downgrade, the tag→computed-classifier pivot, and the MDL-reasoning fix.
- Substrate survey (this session): `corpus_core` schema, supersession/tombstone
  semantics, transactional outbox, `gov-id.md`/`gov-shrink`, `vetoed-decisions.md`.
- Ground-truth recurrence: `scripts/buildthenundo.py` 46/30d.
- Non-duplication: complements `2026-05-26-cross-attestation-substrate-v2` and
  [[science-graph-positioning-2026-05]].

## Revisit if

- A distributed multi-agent discovery + discourse workload emerges (reopens
  `Dt`/CategoryScienceClaw).
- `gov-shrink` ever fails to retire a scaffold it should (reopens MDL gate).
- A real cross-repo/intra-corpus contradiction is observed (reopens coherence gate).
- The classifier's `superseded` heuristic proves too noisy → upgrade to AST/symbol
  fingerprinting (review #20).

## Revisions

**2026-06-07 (cross-model review):** Downgraded the headline claim from "~80% of
`Kbt`" to "~35–45%; the same conservative substrate the paper's own flagship
claims, not the categorical formalism" — the dictionary had forced fits
(annotations-as-functor without `It(f)`; relation_class edge-labels as morphisms;
supersession mislabeled "literally" Kan transport). Pivoted the build from a
hand-typed `move_type` frontmatter tag to a **computed** classifier in
`buildthenundo.py` (self-reported tags are gameable + operator-taxing). Corrected
the MDL don't-build *reasoning* (veto-adjacency was a category error; the real
reason is "binary suffices, zero incidents"), conclusion unchanged. *Why:* a
cross-model panel had less project context but caught genuine over-claiming the
authoring model was blind to. Held against the reviewers on building more
categorical machinery (coherence gate, invariant enforcement, discourse layer) —
those are speculative / no-incident, and the memo's thesis is don't-over-build.

## Supersedes

None. Depends on the corpus substrate (`2026-05-26-cross-attestation-substrate-v2`).
