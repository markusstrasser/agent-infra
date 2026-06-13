---
id: 2026-06-13-rsi-outer-loop-skill
concept: rsi-outer-loop
repo: agent-infra
decision_date: 2026-06-13
recorded_date: 2026-06-13
provenance: contemporaneous
status: accepted
initial_leaning: "Defer extraction — hutter(clean) vs science(partial) differ, proven-common test unmet. REVERSED when ≥3 live instances surfaced (hutter, arc-agi, intel) + the verifier-regime axis turned out to be a PARAMETER, not a blocker."
relations:
  - type: depends_on
    target: 2026-06-03-verifier-bound-autonomy
  - type: depends_on
    target: 2026-06-07-state-externalization-lens
  - type: branches_from
    target: 2026-06-04-consumption-over-autonomy
---

# 2026-06-13: Extract the RSI outer-loop into one shared, verifier-regime-parameterized skill

## Context

RSI (recursive self-improvement) is not a one-off in hutter. It is **the main loop that
matters**, and it is already instantiated — in different states of completeness — across at
least five repos. The same shape was being re-authored as prose in each repo's loop docs, with
the divergence engine just merged into `/leverage` and a partial-verifier instance living in
`research-ops cycle`. The user directed: extract the pattern into one shared skill (breaking,
full migration, no compat shims), optimized for the longest-term best architecture and deepest
representation; consumer = AI agent developers/maintainers; SWE cost ≈ 0 (gate on maintenance,
not effort).

This decision was run through the full `/decide` arc at max effort, grounded in five live
instances + the 2026-06-12 RSI-gap literature sweep.

## The real axis (Phase 0)

The first framing — "should we extract a shared loop skill?" — is the wrong axis; the user
already decided yes. The **real decision axis** is:

> **What is the invariant core of an RSI loop across verifier regimes, and what representation
> lets one skill drive all instances without leaky wrappers or per-regime forks?**

The load-bearing reframe (from the literature, not invented here): **the accept-gate (verifier)
is the load-bearing component of any RSI loop — not the proposer** (PACE, arXiv:2606.08106:
greedy "keep if score up" is self-p-hacking, 30–42% false commits). And **the layer that
actually transfers cross-model is structure** — ledger/tool/memory/externalized state — **not
weights and not prompt-text** (`2026-06-12-agents-rsi-gap-sweep.md`; `state-externalization-lens`).
So the abstraction must put the *gate* and the *externalized ledger* at the center, and treat
the proposer (`/leverage` et al.) as a swappable, non-load-bearing input.

### Hidden assumptions made explicit
1. The five loops share enough structure to unify — **verified below** (instance table), not assumed.
2. The clean/partial verifier difference is the *blocker* to extraction — **REVERSED**: it is the
   central *parameter*. The OUTER-LOOP's own warning ("do NOT port auto-ratchet to partial domains")
   becomes a regime-gated branch, not a reason to keep loops separate.
3. "Deepest representation" = more abstraction. **Tested against** the maintenance gate (constitution
   P8, Jevons): the declarative contract earns its keep only because the consumer instantiates the
   loop in *new* repos — otherwise it would be complexity sprawl.

## The five instances (Phase 3 grounding — read, not remembered)

| Repo | Inner loop (the grind) | Accept-gate / verifier regime | Outer loop today | Status |
|---|---|---|---|---|
| **hutter** | GPT-5.5 grinder, NEVER-STOP on VM | **clean + cheap** — bit-exact compression gate, free/infinite/deterministic | `OUTER-LOOP.md` Dreamer (`/loop /dream`): leverage+research+brainstorm → queue/; discovery human-gated | RUNNING |
| **arc-agi** | `agent.py` plays a game, env-state verifier (clean per-game) | **clean + expensive/rate-limited** — RHAE on hidden Kaggle 55-set, ~5 subs/day → needs a **proxy** + **dual-gate** (proxy↑ AND ground-truth↑); Goodhart-risk | designed in `HANDOFF.md`, **not yet running** ("after hutter proves the loop") | DESIGNED |
| **intel** | source ingestion / resolve loops | **partial** — freshness/completeness setpoints; failure mode = **report-not-gate** (resolve-heartbeat FAILed daily ~50d into a log nobody read) | none formalized; healthcheck reports, doesn't gate | RUNNING (gate not consumed) |
| **genomics** | Modal pipelines, canary_gate (70 sentinels) | **partial→clean-able** — differential count-delta gates possible & deterministic; clinical render = decorrelated / human | none formalized; canary is same-lineage (green-and-wrong) | RUNNING |
| **science** (genomics/phenome research) | research synthesis / discovery | **partial** — synthesis has no ground truth | `research-ops cycle` Lane A/B (generate-only unattended, attended execute) | RUNNING |
| **agent-infra** | `/improve maintain` | **mixed** per-finding (tests=clean, governance=partial, taste=principal) | `/improve maintain` two-lane Generate/Execute | RUNNING |

**The invariant core (present in all) — REVISED after Phase-4 critique:**
proposer (consumes ledger: dedup vs dead_ends) → **accept-gate (consumed, structured verdict,
protected from self-modification)** → ledger(lineage + reproducibility + rollback pointer) → git
bus (isolate-per-agent, merge-via-git) → human-gate at the discovery/irreversible boundary →
budget/rate-limit → scheduling, with **accept/quarantine/reject** (not just accept/reject) and a
declared **gate-independence** level (same-lineage | differential | decorrelated | human |
external). The 8 additions over the first draft are folded from the cross-lab critique (§Phase 4).

**The central representation is an action × autonomy MATRIX, not a single regime enum** (both
labs; my own agent-infra "mixed per-finding" instance is unrepresentable under a top-level enum —
that was a contradiction in draft 1). Each *action* (enqueue idea | run candidate | accept
candidate | commit code | spend expensive submission | modify the gate | publish/recommend |
update GOALS) declares its own `{autonomy, gate, gate_independence, blast_radius, reversible,
budget}`. **Verifier regime is ONE input** to that policy, with four operating points it commonly
selects — but it is not the organizing field:

1. **clean + cheap** → low-blast actions auto-ratchet unattended; discovery human-gated. (hutter)
2. **clean + expensive/rate-limited** → **proxy** + **dual-gate** (proxy↑ AND truth↑), budget the gate, track proxy↔truth correlation. (arc-agi)
3. **partial / noisy** → default **generate-only**; the gate is a **consumed differential** check; execute attended UNLESS an action is narrow-blast + reversible (then per-action unattended is allowed — "partial = always attended" was too absolute). (intel, genomics, science)
4. **principal / taste** → **amplify**: reversible drafts; the human is the gate. (agent-infra taste, GOALS)

## Alternatives considered (Phase 1 diverge — 6 mechanisms)

1. **One `/outer-loop` skill with verifier-regime as an inline mode.** Skill carries all
   machinery; regime picked by a flag. — Simple, but the per-repo gate/bus/proxy config lives in
   prose forks → drift; "structure that transfers" stays trapped in prose.
2. **Skill (policy) + per-repo declarative `LOOP.md` contract (data) + minimal shared
   ledger/gate schema (structure).** ★ The loop becomes *declarative* per repo; the skill is the
   interpreter; the ledger schema is shared code. — Cleanest policy/data/state split; highest
   transfer; one home for the accept-gate (the load-bearing field). More moving parts.
3. **Shared `rsi_loop` Python library (ledger, gate primitives, proxy-correlation, bus
   helpers) + thin skill.** — Real reusable code, but a runtime lib across 5 heterogeneous repos
   risks the vetoed "speculative shared-utility extraction" unless the contract is proven common
   (it now is, but the differences are real → a fat lib would over-fit).
4. **Spec-only: a constitution-level RSI-loop pattern doc + vocabulary, no shared skill.** —
   This is the rejected "defer". No shared machinery → re-authoring continues.
5. **Two skills split by inner/outer: `/grind` + `/dream`.** — Mirrors hutter's LOOP/OUTER-LOOP,
   but the inner loop is irreducibly repo-specific (compression vs game vs Modal) — a shared
   `/grind` would be a hollow wrapper. The *outer* loop is the shareable half.
6. **Workflow script (deterministic fan-out).** — Wrong lifetime: the outer loop is a long-lived
   self-scheduling session; Workflow runs are bounded per-invocation (hutter: "the Dreamer is a
   session, not a subagent").

## Counterevidence sought (against the leading candidate = #2)

- **Searched for a regime that doesn't fit the four operating points** — none across the 5
  instances; arc-agi independently invented operating-point 2 with the same vocabulary, which is
  strong convergent validation rather than a fit-by-construction.
- **Searched the corpus for a prior veto on shared-loop extraction** — found the *opposite*
  bar: `vetoed-decisions` "speculative shared-utility extraction" permits extraction once the
  contract is **proven common across ≥2 repos** (`corpus_core` is the bar). **Honest accounting
  (GPT critique, accepted):** the five are NOT five proven implementations of the same loop — they
  are *one mature running loop* (hutter), *one designed-not-running* (arc-agi), *one partial
  research workflow* (science/research-ops), and *several adjacent control/healthcheck mechanisms*
  (intel/genomics/agent-infra) that fit the invariant but don't yet run it. The invariant
  (proposer→gate→ledger→bus→human-gate→schedule) is broad enough that many control systems fit it —
  so what's proven common today is a **spec pattern**, and *executable* commonality is a hypothesis
  the migration must prove, not assume. That is why the leading candidate is revised (below) to
  **prove executability on a third repo before** committing the interpreter+ledger platform. The
  mutation-gateway veto ("abstractions over divergent logic rejected; share the spec, implement
  per-repo") is the live precedent pulling toward spec-first — it is honored by the prove-first gate,
  not ignored.
- **Searched for the failure the OUTER-LOOP warns about** (auto-ratchet ported to a partial
  domain) — design #2 structurally prevents it: the `accept_gate.regime` field gates which
  machinery runs, so a partial repo's contract never instantiates auto-ratchet.
- **What would still reverse #2:** if the per-repo `LOOP.md` contracts collapse to "one field
  differs" (then #1 is right — don't build an interpreter for a constant), OR if the shared
  ledger schema needs per-repo divergence in >1 load-bearing field (then the contract is not
  actually common and #3/#4 is right). The migration's Phase 1 (author two real contracts —
  hutter + intel — before building the interpreter) is the probe that resolves this.

## Decision

Adopt **#2**: extract the **outer loop** into one shared skill that is the *policy*, reading a
per-repo **declarative `LOOP.md` contract** (the *data*), backed by a **minimal shared ledger +
accept-gate schema** (the *structure* that transfers). Breaking, full migration, no compat shims.

- **Skill name:** `outer-loop` (the user's word; hutter's established term; honest — it drives
  the outer loop and owns the gate; the inner loop stays repo-specific). Alt `rsi-loop` noted.
- **Policy (in the skill, the irreducible LLM decisions):** which divergence move to fire, is a
  proposal buildable, does this cross a human-gate predicate, is the inner loop stalled vs
  idea-starved (the OUTER-LOOP triage), restart-from-fertile-parent selection.
- **Data (per-repo `LOOP.md`, a TYPED+VALIDATED contract — not free-form prose the agent
  soft-parses, which would invite instruction drift):** an **`actions:` matrix** (each action →
  `{autonomy, gate, gate_independence, blast_radius, reversible, budget}`), `verifier.regime` (one
  field), `accept_gate` (exact runnable command emitting a **structured versioned verdict** — not a
  bare exit code), `bus` paths, `schedule`, `proposer`, and `outer_loop_skill: {name, version,
  expected_schema}` so a global-skill edit can't silently change a repo's behavior.
- **State (per-repo ledger):** one shared schema **+ a conformance linter** (a copied schema with no
  check recreates the drift this fixes). Fields (expanded from the thin draft): `candidate, parent_commit,
  artifact_hash, lineage, tags, dead_end, gate_command, gate_version, data_snapshot, env/tool_version,
  proposer_version, skill_version, proxy_score, ground_truth_score, verdict, reason, budget_consumed,
  human_approver, quarantine_state, rollback_pointer, timestamp`. The structure layer — the part the
  literature says actually transfers cross-model.
- **Protected verifier boundary (the canonical RSI safety hole, was missing):** the loop may NOT
  silently edit its own accept-gate. `modify the gate` is a human-gated action; gate_version is
  stamped in every ledger row; proposer and verifier hold separate trust boundaries. Without this the
  loop p-hacks by moving the goalposts, not improving the system.
- **The accept-gate is the spine.** Its verdict MUST be **consumed (gate), never reported** —
  the uniform intel/genomics failure. Where acceptance is greedy, the gate is anytime-valid
  (PACE e-process); where stakes are high, decorrelated/differential (genomics F-1).
- **The proposer is swappable and non-load-bearing** — `/leverage` (now 3-mode) + research +
  brainstorm + critique feed it; none is the bottleneck.

### What this subsumes (full migration — these stop existing as separate loops)
- `research-ops cycle` Lane A/B → becomes the **partial-regime** instantiation of `outer-loop`
  (research-ops keeps `compile`/`diff`/`dispatch`; loses `cycle` to the skill).
- hutter `OUTER-LOOP.md` Dreamer body → **clean-cheap-regime** `LOOP.md` contract + skill.
- `/improve maintain` two-lane routing → agent-infra's **mixed-regime** contract + skill.
- arc-agi `HANDOFF.md` loop sketch → **clean-expensive-regime** contract (unblocks its build).
- intel/genomics → gain a formalized contract whose gate is **consumed** (fixes report-not-gate).

## Evidence
- `2026-06-12-agents-rsi-gap-sweep.md` — accept-gate is load-bearing (PACE); structure transfers,
  weights/prompt-text don't; HGM clade-metaproductivity (restart-from-fertile-parent); Self-Harness
  (self-edit + regression-gate = the Grinder pattern published).
- `intel-genomics-verifier-diagnosis.md` — both repos' uniform failure is report-not-gate /
  not-consumed; F-1 differential count-delta = decorrelated verifier needing no second model.
- arc-agi `HANDOFF.md` + `research/2026-06-08-clean-verifier-loop-targets-arc-aimo.md` — operating
  point 2 (clean-but-rate-limited → proxy + dual-gate) in the wild, same vocabulary.
- hutter `OUTER-LOOP.md` — the reference Dreamer (proposer set, strategic-move generator, git bus,
  human discovery gate, session-not-subagent lifetime).
- `2026-06-03-verifier-bound-autonomy.md`, `state-externalization-lens` — the two principle anchors.

## Phase 4 — Cross-lab critique synthesis (Gemini 3.5 Flash + GPT-5.5, 2026-06-13)

Verdicts: **GPT-5.5 = SHIP-WITH-CHANGES**, **Gemini = RECONSIDER**. Both non-sycophantic; GPT
caught a logical contradiction in draft 1 (mixed-regime vs single-enum), verified against the doc.
Convergent findings (both labs independently) are weighted highest.

**FLIPPED (new fact named) — folded above:**
- *Central axis: regime-enum → action×autonomy matrix.* New fact: agent-infra "mixed per-finding"
  is unrepresentable under a single top-level `verifier.regime` enum (contradiction in my own table).
- *Phase-0 test was biased-to-pass.* New fact (both labs): opposite-end repos trivially differ in
  ≥2 fields, proving difference, not interpreter-fit. Replaced with the third-repo data-only test.
- *Invariant core was incomplete.* New fact (GPT, 8 items): missing protected-verifier-boundary
  (gate self-mod = the canonical RSI p-hack hole), structured versioned verdict, reproducibility
  ledger fields, quarantine/rollback, mandatory gate-independence, budget/rate-limit, concurrency
  (git-isolate per `2026-06-13-multiagent-state-coordination-prior-art`), proposer←ledger dedup edge.
- *"5 proven instances" was an overclaim.* New fact: 1 mature + 1 designed + 1 partial + adjacent.
- *Contract format.* New fact: free-form Markdown the agent parses = instruction drift → typed+validated.

**HELD (with reason):**
- *Gemini "incompatible runtimes → orchestration behemoth" (its strongest-case-against).* HELD —
  rests on conflating inner (runtime-bound: VM/Modal/Kaggle) with outer (git-bus + shell-out to the
  repo's gate, runtime-agnostic; hutter's Dreamer never touches the VM). The rebuttal is now an
  explicit invariant: **the outer loop never embeds runtime auth/transport** — runtime-binding lives
  in the repo's `accept_gate` command, which the skill only shells. Without stating it, an implementer
  *would* build the behemoth, so the HOLD is conditional on making it explicit (done).
- *PACE e-process as the partial auto-accept default.* HELD-and-DEFERRED — GPT correctly flags it as
  scope creep (5 changes at once); matches our own measure-before-enforcing. Out of the critical path;
  adopt only on a measured false-commit incident.

**Revised leading candidate (#2′ — prove-first):** keep the extraction (Plan B survives), but the
first build is the *lighter* form — one `outer-loop` skill + a typed `LOOP.md` **template** +
action-autonomy matrix + the conformance-linted ledger schema — and the **declarative interpreter +
shared-ledger platform are EARNED** by passing the third-repo data-only test, not committed upfront.
This is the bounded-autonomy / reversible-draft discipline the constitution prescribes for
partial-verifier architecture work.

## The one fork left to the principal (constitution P12 — labs disagree with stated Plan B)

**RESOLVED 2026-06-13: B — prove-first** (the principal chose the labs' recommendation over the
literal "full stuff" Plan B). Skill name stays `outer-loop`. The platform (declarative interpreter +
shared-ledger) is earned by the executability proof, not committed upfront.

Both labs lean toward proving executable commonality before building the full platform; the user's
stated Plan B was "the full stuff." Not silently resolving this — it is the user's call:
- **A — Full #2 now** (literal Plan B): build interpreter + shared ledger platform immediately. Risk:
  platform on commonality proven for 1–2 of 5 repos.
- **B — #2′ prove-first** (labs' rec, recommended): extract skill + template + matrix + schema NOW;
  earn the interpreter/platform via the third-repo data-only test. Still a breaking shared extraction.
- **C — spec-only (#4)**: shared spec doc + ledger schema file, keep 5 native loops. Minimal; arguably
  not "a skill"; the mutation-gateway precedent's default.

## Revisit if
- Third-repo data-only instantiation fails (needs skill edits / hidden prose) → the commonality is a
  spec not a skill; fall to **C**.
- The action×autonomy matrix collapses to one differing field across repos → ship **#1** (skill+mode).
- A 6th regime appears outside the four operating points → reopen the parameterization.

## Phase 1 outcome — BUILT + PROVEN (2026-06-13, skills@54707da)

The skill is built and the executability proof passed. Shipped in `~/Projects/skills/outer-loop/`
(4 commits, `08e8654`→`54707da`): `SKILL.md` (policy), `references/loop-contract.md` (typed
`LOOP.md` schema), `references/ledger-schema.sql` (canonical generic schema + `predicted_score` +
`v_calibration`), `scripts/route.py` (the deterministic autonomy router — 6 safety rules as CODE),
`scripts/lint_ledger_conformance.py` (field-map-aware drift guard), `references/examples/hutter-LOOP.md`
(first instance), `tests/test_route_trace_equivalence.py` (the proof).

**Proof:** 10/10 trace-equivalence scenarios reproduce the OUTER-LOOP/eval.py oracle; conformance
linter PASSES against hutter's **live** `experiments` schema with **zero hutter mutation** (every
canonical field mapped to its compression column). A blind fresh-eyes review (1,800-combo router
sweep) confirmed the two RSI-critical fail-closed invariants hold under brute force and the test's
oracle is independently anchored in hutter's code (not circular); it surfaced one latent gap
(errored-accept→reject vs fail_closed) now hardened.

**Two design locks the probe-the-write forced** (folded into the build, not the original draft):
1. **Generic-core schema + per-repo `field_map`**, never forced column renames — hutter conforms today.
2. **`gate_version` is recommended-not-required** — clean deterministic gates defeat silent
   gate-gaming structurally, so the audit field is load-bearing only in soft-gate regimes.

**Scoping tightening:** Phase 1 wrote ONLY to the skills repo (read hutter for ground truth + oracle).
Planting the contract into hutter + archiving `OUTER-LOOP.md` is Phase 2 (archive-then-delete).

## Phase 2 outcome — partial-regime build + 2 ground-truth findings (2026-06-13, skills@e265a66)

Began Phase 2 with science (the partial-regime instance). Two findings reshaped the plan, plus one
design correction:

- **DESIGN CORRECTION — `route.py` partial accept was wrong.** It routed a `partial`-regime accept to
  UNATTENDED (auto-committing on a noisy verifier — the intel/genomics report-not-gate failure
  inverted). hutter's clean-cheap test never exercised the partial branch. Fixed: partial/mixed
  accepts default to ATTENDED; the ADR's "narrow+reversible → unattended" exception is a per-action
  contract literal, never a route() default. Proven by an 8/8 partial trace-equivalence test.
- **FINDING 1 — science is conductor-coupled, not a standalone loop.** `/research-ops cycle` is a
  WORKER the single conductor `/improve maintain` dispatches (since the 2026-06-12 three-conductor
  merge). So science's *deploy* belongs with the conductor migration (Phase 3), not standalone Phase 2.
  Only its contract + fix-proof are done now. The migration order is corrected accordingly.
- **FINDING 2 — science's ledger is git-native** (git history as attempt graph + CYCLE.md + the
  failed-experiments fingerprints), not a SQL table. The shared SQL schema + conformance linter fit the
  4 structured loops (hutter/arc-agi/intel/genomics); the linter now skips `kind: git-native`. A
  structured science ledger is a deferred enhancement (the loop runs on git today — YAGNI).
- **Trace-isomorphic gate (from the /eval survey):** the science gate verifies extracted *claims*
  against external sources (already consumed + decomposed). A noted upgrade is to grade the evidence
  *trace* (phenome KG-verifier pattern; structure-checking verifiers block reward-hacking output checks
  miss). Recommended, not built in Phase 2.

- **CORRECTION (verify-before-fold caught a stale premise in THIS ADR) — intel/genomics gates ARE
  consumed.** The instance table + operating-point-3 called intel/genomics "report-not-gate /
  not-consumed," sourced from `intel-genomics-verifier-diagnosis.md`. Probed at the primary source
  (2026-06-13): **both gates block today.** genomics `canary_gate.py` exit-2-blocks commits on
  classification regression since **2026-03-23**; intel `pretool-tier1-pipeline-liveness-gate.py`
  `exit_block`s Tier-1 writes on a dead pipeline/resolve-loop since **2026-06-03** (its docstring
  literally credits the diagnosis memo as the thing it fixes, and it ships a `shadow|warn|block`
  staging mode defaulted to `block`). The memo was accurate WHEN WRITTEN and DROVE the intel fix; the
  ADR (2026-06-13) cited its premise as current without checking the fix had shipped 10 days earlier.
  **Consequence:** intel + genomics are **faithful ports** (author the contract around the existing
  consumed gate), NOT the high-risk staged behavior change — the "enforce boundary" is moot, both
  already enforce. genomics's real open issue is the one the ADR got right: the canary is
  **same-lineage** (green-and-wrong possible) — a `gate_independence` concern (differential count-delta
  = the deferred upgrade), not a consumption one. Evidence: gate ground-truth probe
  `research/scratch/2026-06-13-intel-genomics-gate-ground-truth.md` + the two hooks read directly.

Revised Phase 2 (de-risked) = intel + genomics **faithful-port contracts** (gates already consumed;
no staged behavior change) + hutter authoritative deploy. Phase 3 = agent-infra conductor + science deploy.

## Deferred / open (tracker)
- ~~Skill name: `outer-loop` vs `rsi-loop`~~ → **RESOLVED: `outer-loop`** (built). | ~~Ledger home:
  schema-file+linter vs module~~ → **RESOLVED: schema-file + conformance linter** (built, field-map-aware).
- PACE adoption: deferred to measured false-commit need (out of critical path). | intel/genomics
  consumed-gate: staged dry-run→enforce (Phase 2).
- Global skill symlink (`~/.claude/skills/outer-loop`): **deferred to Phase 2** — make-discoverable is
  a deploy step; Phase 1 is build+prove only (zero cross-project blast).
- arc-agi clean-expensive contract: re-probe its ledger writer when it lands (Phase-0 used the design doc).
- `/improve maintain` migration: Phase 3, after burn-in elsewhere + independent review (may not self-authorize).
