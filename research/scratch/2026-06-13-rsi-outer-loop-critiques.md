---
title: RSI outer-loop ADR — raw cross-lab critiques (Gemini 3.5 Flash + GPT-5.5)
date: 2026-06-13
tags: [rsi, cross-model-review, evidence]
status: active
---

Evidence for decisions/2026-06-13-rsi-outer-loop-skill.md §Phase 4. Verdicts: GPT-5.5 SHIP-WITH-CHANGES, Gemini RECONSIDER. Context packet: /tmp/rsi-outer-loop-critique-context.md (ADR+plan draft 1 + adversarial task).

# ===== GEMINI 3.5 FLASH =====

Here is an adversarial architectural review of the proposed RSI outer-loop migration.

---

### 1. OVER-ENGINEERING: The Declarative Interpreter Fallacy
**Reference:** *ADR Alternatives considered (#2 vs #1); Migration Plan Phase 0.*

The choice of **Decision #2** (Policy-skill + `LOOP.md` contract + shared ledger schema) over **#1** (single skill with a `regime` flag) is a classic architect’s trap: building an interpreter instead of writing parameterizable code.

*   **The Flaw in the Reversal Test:** Your Phase 0 test ("do they differ in $\ge 2$ load-bearing fields?") is the wrong metric for justifying an interpreter. Of course they will differ. But difference does *not* justify declarative parsing. If `hutter` and `intel` differ wildly in schema and bus structure, writing a YAML/Markdown parser in the `outer-loop` skill that safely dynamically configures itself without hallucinating or breaking is *harder* and more prone to runtime failure than simple, hardcoded code paths in the skill itself.
*   **The LLM-as-Interpreter Risk:** If the "interpreter" is just an LLM reading `LOOP.md` as context to decide its next action, you are inviting **instruction drift**. A markdown contract is a soft constraint. If the interpreter is hardcoded code (e.g., Python parsing `LOOP.md`), you are writing a custom parser for a bespoke domain-specific language (DSL) across 5 heterogeneous repos.
*   **Prediction:** `hutter` (local file queue, bit-exact checks) and `intel` (freshness beacons, reporting) will differ so fundamentally in execution context (VM vs. corporate network/API) that your parser will quickly degenerate into a mess of regexes and try-catch blocks. 

*Recommendation:* Revert to **#1**. Keep the loop-driving logic inside the code of a single parameterized skill. Use standard environment variables or a simple, typed JSON config file—not a free-form Markdown `LOOP.md` document that agents must parse and interpret.

---

### 2. LEAKY PARAMETERIZATION: Regime vs. Topology
**Reference:** *ADR "The five instances" Table; "Alternatives considered" (#5).*

You are treating "verifier regime" as a mere parameter. In reality, the verifier regime changes the **topology (the directed graph)** of the loop, not just its variables.

*   **The Loop-Shape Leak:** 
    *   In a **clean+cheap** regime (`hutter`), the loop is a straight line: `Propose -> Gate -> Commit`. 
    *   In a **clean+expensive** regime (`arc-agi`), the loop is a nested dual-loop: `Propose -> Proxy Gate -> [If high: True Gate] -> Budget Check -> Correlation Sync -> Commit`. 
    *   In a **partial** regime (`science`), it is an open-loop generator: `Propose -> Draft -> Human Intercept -> Execute`.
*   **The Leaky Abstraction:** If you try to force these three wildly different topological graphs into one "parameterized" skill, your skill's codebase will be littered with structural branches:
    `if regime == expensive: run_proxy_nested_loop()`. 
    This is not a single parameterized skill; it is three different skills wearing a trench coat. You have missed the true discriminator: **Control Flow Topology**, not Verifier Quality.

---

### 3. THE SPINE: The Missing Rollback & Feedback Loops
**Reference:** *ADR "The invariant core"; Migration Plan Phase 1 ("Accept-gate contract").*

While you correctly identified "consumed, not reported" as the load-bearing invariant for the accept-gate, your "invariant core" is missing the two most critical failure recovery components:

*   **State Rollback (The Undo):** An RSI loop is an automatic mutation engine. If a proposal passes the proposer, is committed to the git bus, but fails a post-deployment verification gate or causes a silent regression discovered 3 cycles later, how does the loop backtrack? If your shared ledger schema (`proposal, lineage, dead_end`) doesn't explicitly track **reversible system states (git SHAs or environment snapshots)**, a single bad accept-gate pass will permanently poison the workspace.
*   **Negative Feedback Loop (The "Why"):** In your model, the proposer is treated as a "swappable, non-load-bearing input." This is wrong. If the accept-gate rejects a proposal, how is the *failure reason* fed back to the proposer? If the proposer doesn't consume the ledger's rejection history, it will generate the same class of failure repeatedly, burning compute in a tight loop. The proposer and the gate must share a tight semantic feedback loop.

---

### 4. MIGRATION RISK: The "No-Shim" Cliff-Edge
**Reference:** *Migration Plan Phase 2 ("delete-as-you-go").*

Your plan mandates a breaking, full migration with "no compat shims" and "delete-as-you-go" commits. This is highly irresponsible for a production system running across multiple repos with active agents (specifically `intel` with ~5 live agents and `hutter` running on a VM).

*   **The Conductor Lockout:** Migrating `/improve maintain` (the agent-infra conductor) *last* while deleting old loop docs *first* means that if your intermediate migrations (e.g., `science` or `genomics`) fail or reveal a schema mismatch, your main conductor is left in an un-runnable state, or worse, running on stale instructions.
*   **Blast Radius:** A bug in the newly unified `outer-loop` skill deployed to fix an issue in `arc-agi` could instantly corrupt the active database/ledger of the `hutter` run or cause the `intel` healthcheck beacon to silent-fail, leaving critical infrastructure unmonitored.

---

### 5. STRONGEST CASE AGAINST: The Jevons Paradox of Abstraction
**Reference:** *ADR Context; Alternatives considered (#4).*

The single strongest argument for **NOT** doing this extraction is that **the runtime environments of these 5 repos are completely incompatible.**

*   `hutter` runs long-lived loops on a dedicated, isolated VM.
*   `genomics` runs on Modal (highly distributed, serverless, ephemeral).
*   `arc-agi` runs in restricted Kaggle environments or local evaluation harnesses.
*   `agent-infra` runs locally in your workspace.

The moment you unify their outer loops into a single shared skill, that skill must become an **orchestration behemoth**. It will need to handle Modal authentication, VM SSH handshakes, local git execution, and Kaggle-like container boundaries. 

By keeping the loops separate and writing a strong, shared **specification doc (Alternative #4)**, you allow each repo's loop to remain extremely lightweight (~100-200 lines of idiomatic local bash/python) while maintaining conceptual alignment. Unification creates an external dependency lockstep across five codebases that have no other reason to be coupled.

---

### Verdict

**RECONSIDER**

*You have correctly identified the structural flaws of the current loops (specifically the "report-not-gate" failure). However, forcing these loops into a single shared skill driven by a declarative Markdown interpreter is a severe case of over-engineering that ignores fundamentally different runtimes and loop topologies. You should pivot to a strong, shared specification document (Alternative #4) with a shared SQLite/TSV ledger schema file, but keep the loop execution local and native to each repo's unique runtime environment.*

# ===== GPT-5.5 (high) =====

## Short read

The good parts are real: the ADR correctly identifies that the proposer is not the load-bearing component, that gates must be consumed rather than merely reported, and that externalized state/ledger is the transferable layer. But the proposed extraction is still too confident. The plan’s falsification gate is weak, the “verifier regime” parameter is too coarse, and the migration sequence creates common-mode failure risk across exactly the repos whose autonomy boundaries you are trying to harden.

---

# 1. OVER-ENGINEERING

### Would #1 deliver ~90% of the value at ~30% of the complexity?

Probably yes for the first migration wave.

ADR **Alternatives considered**, option #1, says:

> “One `/outer-loop` skill with verifier-regime as an inline mode. Skill carries all machinery; regime picked by a flag.”

The ADR rejects this because:

> “the per-repo gate/bus/proxy config lives in prose forks → drift; ‘structure that transfers’ stays trapped in prose.”

That objection is directionally right, but it does not prove you need a declarative `LOOP.md` interpreter plus shared ledger schema now. A lighter version could be:

- one `outer-loop` skill;
- a required `LOOP.md` template, not an interpreted contract;
- a small checklist for gate/bus/human-boundary/schedule;
- no shared ledger implementation yet;
- no “contract interpreter” until two or three repos prove data-only instantiation.

That gets most of the anti-drift benefit without turning this into a mini platform.

The ADR’s preferred #2 says:

> “extract the outer loop into one shared skill that is the policy, reading a per-repo declarative `LOOP.md` contract … backed by a minimal shared ledger + accept-gate schema.”

That is a lot of machinery for a system where several “instances” are not actually running outer loops yet.

### The reversal test is the wrong test

Migration Plan **Phase 0** says:

> “Decision gate: do the two contracts differ in ≥2 load-bearing fields … YES → #2 holds, proceed. NO … fall back to #1.”

This is not a meaningful falsification test.

You chose hutter and intel, i.e. opposite ends of the space:

- hutter: clean-cheap deterministic compression gate, running autonomous loop.
- intel: partial freshness/completeness checks, currently “report-not-gate.”

They will obviously differ in more than two load-bearing fields: regime, gate shape, schedule, human gate, bus semantics, and probably ledger semantics. That proves they are different. It does **not** prove that an interpreted declarative contract is the right abstraction.

A better test would be:

> Can a third repo instantiate the loop by changing only `LOOP.md`, with zero skill edits and zero hidden bespoke prose?

Or:

> Does the contract prevent an invalid autonomy configuration that the prose version previously allowed?

Or:

> Does the shared ledger schema exactly match existing writers in at least two repos, without inventing fields for desired future behavior?

The proposed test is biased to pass.

### Prediction for hutter-vs-intel

The hutter-vs-intel probe will pass the ADR’s test, but for the wrong reason.

It will find ≥2 differing load-bearing fields. But that will mostly reflect the fact that intel does **not** currently have the same kind of loop.

The ADR’s instance table says for **intel**:

> “Outer loop today: none formalized; healthcheck reports, doesn’t gate.”

But the migration plan **Phase 0** says:

> “Author two real `LOOP.md` contracts … by hand, from their actual loop docs … a consumed freshness-beacon gate for intel.”

That is internally inconsistent. For intel, you are not extracting from an actual existing loop doc. You are designing a new consumed gate to fix the report-not-gate failure. That may be valuable, but it weakens the “proven common” claim.

So: hutter-vs-intel will appear to validate #2, but the validation is contaminated by new design work.

---

# 2. LEAKY PARAMETERIZATION

### The four operating points are useful, but not sufficient

ADR **The five instances** defines four regimes:

1. clean + cheap;
2. clean + expensive/rate-limited;
3. partial/noisy;
4. principal/taste.

This taxonomy is helpful, but it bundles several independent axes:

- verifier reliability;
- verifier cost;
- verifier latency;
- reversibility of the action;
- blast radius;
- whether the action mutates code, data, infra, research claims, user-facing output, or governance;
- gate independence/decorrelation from the proposer;
- whether the gate itself is editable by the loop;
- human scarcity/SLA;
- whether failures should block, quarantine, escalate, or only annotate.

The ADR treats “verifier regime” as the central parameter:

> “The parameter that varies: the verifier regime.”

That is too narrow. The real central axis is closer to:

> What action may be taken unattended, under what verifier, with what blast radius, reversibility, budget, and gate independence?

“Verifier regime” is one input into that policy. It should not be the single organizing field.

### Clean/partial/principal is not the same thing as attended/unattended

The ADR says for partial/noisy:

> “generate-only unattended; the gate is a setpoint/differential check that MUST be consumed … execution attended.”

That is too absolute.

Some partial domains may safely execute low-blast-radius operational repairs unattended if the action is reversible and the setpoint is narrow. Conversely, some clean domains should not auto-ratchet if the action is irreversible, expensive, or likely to Goodhart the benchmark.

So the policy should be based on an autonomy matrix, not just a regime enum.

Example fields:

```yaml
actions:
  enqueue_proposal:
    autonomy: unattended
    gate: none
    blast_radius: low

  run_candidate:
    autonomy: unattended
    gate: smoke_test
    blast_radius: medium
    reversible: true

  accept_candidate:
    autonomy: gated
    gate: accept_gate
    gate_independence: decorrelated
    reversible: true

  change_verifier:
    autonomy: human_required
    reason: "gate boundary is protected"

  publish_discovery:
    autonomy: human_required
    reason: "irreversible / principal judgment"
```

Without something like this, “partial-regime” is too blunt.

### “Mixed regime” already breaks the single-regime model

ADR **Decision / Data** says a per-repo `LOOP.md` includes:

> “`verifier.regime` clean-cheap | clean-expensive | partial | principal”

But the instance table says **agent-infra** is:

> “mixed per-finding — tests=clean, governance=partial, taste=principal”

And Phase 2 says:

> “agent-infra: `/improve maintain` two-lane routing → mixed-regime contract.”

That is a schema smell. If `verifier.regime` is a single top-level enum, agent-infra cannot be represented faithfully. If you add nested per-action/per-finding regimes, then “verifier regime” is no longer the central simple parameter; it becomes one field inside an autonomy/action matrix.

### Auto-ratchet leakage risk is not eliminated by a field

ADR **Counterevidence sought** claims:

> “design #2 structurally prevents it: the `accept_gate.regime` field gates which machinery runs, so a partial repo's contract never instantiates auto-ratchet.”

That is too strong.

A markdown contract does not structurally prevent leakage unless the interpreter has a hard safety matrix, tests, and fail-closed behavior. Otherwise an agent can set the wrong regime, or a future edit to the skill can accidentally apply clean-cheap behavior to partial domains.

Also, Migration Plan **Phase 1** says:

> “Where greedy: wire the PACE e-process anytime-valid gate as the default for `regime: partial` auto-accept…”

That sentence is a leakage alarm. “Partial” plus “auto-accept” is exactly where you need the most caution. PACE-style anytime-valid statistics may help with sequential testing under well-defined metrics; it does not magically create semantic ground truth for research synthesis, freshness, clinical genomics, or governance taste.

At minimum, partial auto-accept should be opt-in per action, not defaulted by regime.

---

# 3. THE SPINE

### “Consumed, not reported” is correct

This is the strongest part of the ADR.

ADR **Decision** says:

> “The accept-gate is the spine. Its verdict MUST be consumed (gate), never reported.”

And the evidence cites the intel/genomics failure:

> “both repos' uniform failure is report-not-gate / not-consumed.”

That is right. A healthcheck nobody reads is not a control loop. If the system continues unchanged after a failed gate, the gate is decorative.

### But the invariant core is missing several load-bearing pieces

ADR **The five instances** defines the invariant as:

> “proposer → accept-gate → ledger(lineage) → git bus → human-gate at the discovery/irreversible boundary → scheduling.”

This is close, but incomplete.

Missing invariants:

#### 1. Protected verifier boundary

In an RSI loop, the loop must not be able to silently edit its own accept gate.

The ADR says the accept-gate is load-bearing, but does not say:

- gate code/config is protected;
- gate changes require human approval;
- gate version is recorded in the ledger;
- candidates that modify the gate are routed to human review;
- proposer and verifier have separate trust boundaries.

Without this, the loop can p-hack by changing the verifier rather than improving the object system.

This is especially important because the ADR cites PACE and false commits, but does not explicitly protect the gate from self-modification.

#### 2. Action boundary

The contract must define what is being gated.

“Accept candidate” is not one thing. Possible actions include:

- enqueue idea;
- run experiment;
- commit code;
- deploy service;
- modify dataset;
- modify verifier;
- spend expensive submissions;
- publish/recommend/report;
- update GOALS or strategy.

Each has different autonomy rules. A single accept-gate spine is insufficient unless every action has a declared gate and authority boundary.

#### 3. Structured verdict, not just shell exit

Migration Plan **Phase 1** says:

> “the skill NEVER self-scores an outcome — it shells the repo's `accept_gate` command and consumes its exit/verdict.”

Good principle, but underspecified.

The gate output needs a structured, versioned verdict, e.g.:

```json
{
  "verdict": "accept",
  "gate_version": "2026-06-13.1",
  "metrics": {"compression_bits": 12345},
  "baseline": "commit abc123",
  "candidate": "commit def456",
  "data_snapshot": "sha256:...",
  "reason": "bit-exact improvement",
  "warnings": []
}
```

Exit code alone is not enough. Otherwise the ledger cannot audit why a decision happened.

#### 4. Reproducibility fields in the ledger

ADR **Decision / State** proposes ledger fields:

> “proposal/candidate, lineage(parent), tags, dead_end, proxy_score, ground_truth_score, accept/reject + reason.”

That is too thin.

Needed fields include:

- candidate artifact hash;
- parent commit;
- gate command;
- gate version;
- gate input data snapshot;
- environment/tool version;
- proposer identity/version;
- skill version;
- timestamp;
- human approver when relevant;
- budget consumed;
- failure mode / quarantine state;
- rollback pointer.

Lineage and score are not enough for cross-repo auditability.

#### 5. Rollback/quarantine

The invariant loop should include:

> propose → run/sandbox → gate → accept/quarantine/reject → ledger → bus/schedule

The current spine jumps from gate to ledger/bus but does not explicitly model quarantine or rollback. In partial domains especially, “accepted but later found wrong” must be first-class.

#### 6. Gate independence/decorrelation

The ADR mentions decorrelated checks for high stakes, but the invariant does not make verifier independence mandatory where needed.

Genomics already has the cited failure:

> “canary is same-lineage green-and-wrong.”

That should be represented structurally. For high-stakes or Goodhart-prone regimes, the contract should say whether the gate is same-lineage, differential, decorrelated, human, or external.

#### 7. Scheduler budget and rate limits

For arc-agi, the expensive clean gate is central:

> “~5 subs/day → needs a proxy + dual-gate.”

Budget is not a side detail. It belongs in the invariant/control loop, not just in the regime prose.

#### 8. Concurrency/locking

The plan notes:

> “intel ~5 live [agents].”

If multiple agents are writing queues, ledgers, and bus paths, the invariant needs locks or transaction semantics. Otherwise “consumed gate” can still race.

---

# 4. MIGRATION RISK

### Deleting old loop docs immediately is unnecessarily dangerous

Migration Plan **Phase 2** says:

> “each deletes the old loop doc in the same commit (no parallel paths).”

This is too aggressive.

“No compat shims” is fine for user-facing commands. But deleting the old docs before burn-in destroys the comparison oracle. You need at least an archived, explicitly non-authoritative snapshot until the migrated loop has passed trace-equivalence checks.

Recommended distinction:

- no active parallel control paths;
- but keep old docs under `docs/archive/` or as a commit-linked reference until migration validation completes.

Otherwise, when behavior changes, reviewers will have to spelunk git history to determine whether the new skill preserved the old boundary.

### The hutter vertical slice needs a stronger validation than “one tick”

Migration Plan **Phase 1** says:

> “Verify: a hutter Dreamer tick via `/outer-loop` produces the same queue refill + human-gate behavior.”

One tick is not enough. The hutter loop has scheduling, queue refill, human-gate predicates, restart logic, and stall triage. You need trace equivalence over representative scenarios:

- idea-starved;
- grinder stalled;
- candidate accepted;
- candidate rejected;
- human-gated discovery;
- dead-end lineage restart;
- gate command failure;
- ledger write failure.

Without that, you may preserve the happy path and break the loop semantics.

### Arc-agi is scheduled too late

Migration Plan **Phase 3** puts arc-agi after the running loop migrations:

> “arc-agi `HANDOFF.md` sketch → clean-expensive-regime `LOOP.md`…”

That is backwards architecturally.

Arc-agi is the strongest test of whether the abstraction handles clean-but-expensive gates, proxy correlation, budget, and dual-gate semantics. If you discover schema changes there after deleting hutter/science/agent-infra loop docs, you will churn all migrated contracts.

Arc-agi should be part of Phase 0 or Phase 1 as a design probe, even if it does not run yet.

### Intel is not a migration; it is a behavior change

The ADR says intel currently has:

> “healthcheck reports, doesn't gate.”

Phase 2 says intel will gain a contract whose accept gate is consumed:

> “intel + genomics: author contracts whose `accept_gate` is consumed — this is the fix for report-not-gate.”

That is not just extraction. It changes operational semantics from observability to blocking control.

That may be the right fix, but it needs staged rollout:

- dry-run gate;
- record would-block decisions;
- define fail-open vs fail-closed per action;
- alert owner;
- only then enforce blocking.

Otherwise you risk deadlocking ingestion/resolution pipelines or generating alert fatigue in a system that already had unread reports.

### Migrating `/improve maintain` is meta-circular risk

Phase 2 says:

> “agent-infra: `/improve maintain` two-lane routing → mixed-regime contract. This is the most delicate (it's THE conductor) — do last among running loops…”

Doing it last is not sufficient. This is the loop that governs maintenance. It should not self-migrate under the new abstraction until the abstraction has survived burn-in elsewhere.

You need an explicit rule:

> The new `outer-loop` skill may not be the authority for migrating or approving its own conductor migration.

Use manual review or an independent process for that migration.

### Global skill versioning is missing

The skill lives at:

> `~/Projects/skills/outer-loop/SKILL.md`

If multiple repos depend on a global mutable skill, then a skill edit can silently change the behavior of all loops without a repo-local commit.

That is a serious governance bug.

Each repo contract needs to record:

```yaml
outer_loop_skill:
  name: outer-loop
  version: 2026-06-13
  expected_schema: 1
```

And the ledger should stamp the skill version used for each decision.

If the skill is intentionally unversioned, then deleting repo-local loop docs is even riskier because behavior becomes centralized and historically ambiguous.

### Ledger home ambiguity is a migration hazard

Plan **Phase 1** says:

> “Decide home: a tiny schema file the repos copy vs a tiny shared module. Default: schema file…”

A copied schema avoids premature library coupling but invites drift. A shared module avoids drift but creates dependency coupling.

Do not leave this unresolved during migration. At minimum, use:

- schema spec;
- conformance tests/linter;
- version field;
- migration rules.

A copied TSV definition with no conformance check will recreate the same drift the extraction is supposed to fix.

### PACE is scope creep

Plan **Phase 1** says:

> “read PACE full text first — flagged … as a pre-design must-read.”

That is wise. But wiring PACE into partial auto-accept during the initial migration is too much.

Do not combine:

1. loop extraction;
2. ledger schema creation;
3. consumed-gate enforcement;
4. partial-domain auto-accept;
5. PACE adoption.

That is five changes at once. Keep PACE out of the critical migration path unless a specific repo has a measured false-commit problem requiring it.

---

# 5. STRONGEST CASE AGAINST EXTRACTION

The strongest argument against this extraction is:

> The commonality across these repos is mostly conceptual vocabulary, not executable loop semantics.

The ADR says there are five live instances, but the table itself weakens that claim:

- **hutter**: real running clean-cheap loop.
- **arc-agi**: designed, “not yet running.”
- **intel**: running healthchecks, but “gate not consumed” and “none formalized.”
- **genomics**: has canaries/gates, but “none formalized” as an outer loop.
- **science**: research-ops cycle exists, but partial synthesis has no ground truth.
- **agent-infra**: mixed governance/taste/test loop.

That is not five proven implementations of the same outer loop. It is one mature loop, one designed loop, one partial research workflow, and several adjacent control/healthcheck mechanisms.

The ADR’s **Counterevidence sought** says:

> “Five instances + a shared invariant clears it.”

I think that overstates the evidence. The invariant is broad enough that many control systems fit it:

> proposer → gate → ledger → bus → human-gate → schedule

At that level, you may have identified a useful spec pattern, not necessarily an executable shared skill.

A shared spec doc plus `LOOP.md` template could capture the lessons while avoiding:

- common-mode failure across repos;
- central skill drift;
- overgeneralized policy;
- incorrect autonomy transfer from hutter into partial domains;
- deletion of domain-specific operational knowledge;
- meta-circular risk in agent-infra.

That case is stronger than the ADR admits.

The extraction may still be justified, but only if the first vertical slices prove that the skill can operate from repo data without hidden domain logic and without weakening autonomy boundaries.

---

# Required changes before I would accept this

1. Replace the Phase 0 reversal test.  
   Do not use “hutter vs intel differ in ≥2 fields.” Require a third repo, preferably arc-agi or agent-infra, to instantiate with data-only changes and no skill edits.

2. Change the schema from single `verifier.regime` to an action-level autonomy matrix.  
   Regime can be one field, not the central abstraction.

3. Add protected verifier-boundary rules.  
   Gate code/config changes require human review. Ledger records gate version and skill version.

4. Make gate verdicts structured and auditable.  
   No bare exit-code semantics.

5. Expand the ledger schema.  
   Include artifact hashes, parent commit, gate version, data snapshot, proposer/skill version, budget, timestamp, human approver, rollback/quarantine state.

6. Do not delete old loop docs immediately.  
   Archive them as non-authoritative references until trace-equivalence/burn-in passes.

7. Move arc-agi earlier as a design probe.  
   Clean-expensive proxy/dual-gate/budget semantics are too important to discover after migrations.

8. Treat intel/genomics consumed gates as behavior changes, not simple migrations.  
   Use dry-run/would-block measurement before enforcement.

9. Postpone `/improve maintain` migration until after burn-in and require independent review.  
   Do not let the new loop approve its own conductor migration.

10. Remove PACE adoption from the initial migration critical path.  
    Keep it as an optional later enhancement after measured need.

**Verdict: SHIP-WITH-CHANGES.**
