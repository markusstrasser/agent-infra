# Genomics Self-Improvement Loop Mapping

**Status:** PROBE-IN-PROGRESS — 2026-06-13, mapping the knowledge cycle + canary + accept-gate architecture.

---

## CENTRAL QUESTION VERDICT

**Genomics is a conductor-coupled system, NOT a standalone RSI loop.**

Evidence (three axes):

1. **No autonomous loop operator** — There is no Dreamer/conductor in genomics that PROPOSES improvements and GATES them. The system is entirely a Modal pipeline + knowledge system that gets improved BY agent-infra's `/improve` conductor (MAINTAIN.md, improvement-log.md).

2. **Knowledge cycle is data-driven, not self-improving** — The `knowledge/` subsystem (executor.py, mutation_gateway.py, cascade.py, cycle_ledger.py) is a REACTIVE evidence-pipeline, not a PROACTIVE improvement proposer. It:
   - Listens for source drift (via `rederivation_triggers` table)
   - Executes Direction D quorum on fresh evidence
   - Writes verdicts back to the DB (claim_verdicts, evidence_bindings)
   - Cascades down dependent claims
   - **Does NOT propose** new classification rules, pipeline stages, or architecture changes

3. **Canary gate is acceptance-only, not improvement-only** — `scripts/canary_gate.py` (70 sentinels, exit-2 on regression) is a **regression detector** for committed code (auto_classify changes), not a **verifier-driven loop** that proposes new classification rules or gatekeeps their entry.

4. **MAINTAIN.md governs both projects** — `/improve maintain` conductor runs the same cadence across both agent-infra AND genomics (MAINTAIN.md is the source of truth for both). Genomics has no separate improvement cycle — it IS the pipeline; agent-infra has the conductor.

**Implication:** genomics's contract is Phase 3 conductor-coupled (defer autonomous loop until Phase 3 strategic pivot); Phase 2 is a clean knowledge witness/verification system + data-driven claim mutation (Direction E) within the pipeline.

---

## MAP: 6-ITEM GEOMETRY

### 1. Loop Doc / Driver
**Does NOT exist as a standalone entity.**

- **`CYCLE.md`** (path: `/Users/alien/Projects/genomics/CYCLE.md`) — **What it is:** A research/operational **checkpoint**, not a loop driver. Tracks completed phases (Phase 0–4 shipped; Phase 5/6/E in flight), manual gates (Tier 1 BIO actions, Tier 0.5 SBayesRC probe), queued improvements (R0–R5 rerun waves).
  - **Key quote (line 2):** `## Last tick: 2026-04-28`
  - **Key quote (line 3):** `## Phase: **Bio-verify v3→v7 STRUCTURALLY + OPERATIONALLY COMPLETE.**` — marks operator-gated checkpoints, not auto-proposals.
  - **Verbatim rhythm:** "Completed Since Last Tick", "Next: (1) Drain agent completes Phase E...", "Queue — What's Next" (Tier 0–4 human-actionable lists).
  - **VERDICT:** Checkpoint document, not improvement loop. No conductor, no Dreamer, no auto-gating.

- **`MAINTAIN.md`** (path: `/Users/alien/Projects/genomics/MAINTAIN.md`) — **What it is:** SWE quality ledger (2026-03-29 last tick). Findings, Fixed, Deferred, Open Steward Proposals.
  - **Key quote (line 1):** `## Findings`
  - **Key quote (lines 34–49):** "10 Open Steward Proposals (brainstorm-dedup-precheck, destructive-git-ref-hook, …) — 5 require shared-infra/cross-repo approval, 3 are meta-scope and warrant review first."
  - **VERDICT:** Ledger of findings, not proposer. Proposes things to agent-infra's conductor; receives no auto-gating.

- **No OUTER-LOOP.md, no /dream skill, no launchd loop job** — Genomics has no self-contained improvement driver. Improvements come from agent sessions + the conductor in agent-infra.

### 2. Candidates — What the Loop Actually Improves/Accepts
**Unit of proposal:** Classification rules / canary variants / auto_classify() logic / variant evidence thresholds.

- **Accept boundary:** `auto_classify()` in `generate_review_packets.py` — the central classification function (imported by canary_gate.py line 25).
- **Proposed changes:** New canary variants in `tests/fixtures/canary_variants.json`, threshold edits in `pipeline_config.py` (Pydantic-typed thresholds), classification decision branches in `variant_review_rules.py`.
- **Gate mechanics:** Canary_gate runs 70 variants through auto_classify(), asserts exact label/confidence/reportability (lines 115–155). **Mismatch → exit 1 → blocks commit via pre-commit hook.**
- **The mutation source:** Manual edits by operators + agent-driven fixes during CYCLE closure (e.g., "Fix 22 validator/output-decl mismatches" — D-1, CYCLE.md line 375–376).
- **Verdict:** Genomics does NOT auto-propose classification improvements; humans/agents propose, canary gates them.

### 3. The Accept-Gate: canary_gate.py Independence & Other Gates

**Path:** `/Users/alien/Projects/genomics/scripts/canary_gate.py` (506 lines)

**What it is:**
- **Deterministic** regression tester — no randomness, no model-based grading.
- **Sentinel coverage:** 70 curated variants (line 110 in loop) spanning 28 decision branches (line 9 docstring).
- **Shape:** reads `tests/fixtures/canary_variants.json`, runs each variant through `auto_classify()`, compares actual result vs. expected (label, confidence, reportability) — exact match or exit-1 (line 159–165).
- **Runtime:** <5s pure Python, no I/O (line 8 docstring).

**Independence question (key for RSI):** Does canary re-derive from the SAME source/lineage as the rules it checks?

- **ANSWER: PARTIAL** — The canary reads the live `auto_classify()` code (which reads thresholds from `pipeline_config.py`, gene panels from `config/gene_panels.json`, variant registry from `config/variant_registry.json`). So yes, it consumes the same lineage.
- **But the FIXTURE PINNING PROBLEM exists:** If an agent edits `generate_review_packets.py::auto_classify()` AND edits `tests/fixtures/canary_variants.json` in the same commit, the canary can pass a wrong change (the fixture and code drift together). **This is a KNOWN gotcha in CLAUDE.md line 85–86:** _"Regression fixtures need assay-specific spec, not fixed variant count — … defer fixture pinning until drain settles to avoid double-pinning + multi-agent collision risk."_ So the canary is green-and-wrong vulnerable if both the code and fixture mutate together.

**Other gates (the differential landscape):**
- **`scripts/precommit-qa-gate.sh`** (mentioned in CYCLE.md line 70 & CLAUDE.md) — wraps canary_gate.py, runs before commit. Exit-2 blocks commit on classification regression.
- **`scripts/verify_genotypes.py`** (CLAUDE.md line 13, line 130) — validates genotype dicts after adding rsIDs. Blocks on strand/coordinate hallucinations.
- **`scripts/variant_hygiene_gate.py`** (20 lines; in canary results lines 268–271) — checks variant data completeness.
- **`scripts/clinical_attestation_gate.py`** (9 KB) — evidence-class admission gate; runs post-classification.
- **Canary windows / canary_results** — The knowledge.duckdb tables (schema shows `canary_windows` & `canary_results` tables with 0 rows currently). These are historical tracking, not active. The ACTIVE canary is the Python test.
- **No differential count-delta gate observed** — only variant-level checks; no "catch if variant count shifts" sentinel.

**VERDICT:** canary_gate.py IS the accept-gate. It is deterministic but has the fixture-pinning vulnerability for simultaneous code+fixture edits. No separate "differential count-delta" gate found.

### 4. Ledger: data/knowledge/knowledge.duckdb Tables & Columns

**Path:** `/Users/alien/Projects/genomics/data/knowledge/knowledge.duckdb`

**Confirmed tables & their tracking columns:**

| Table | Row Count | Key columns | What it tracks |
|-------|-----------|-------------|-----------------|
| `claim_verdicts` | 952 | `verdict_id, claim_id, support_state, review_status, model_version, prompt_template_hash, canary_window_id, evidence_event_id, verdict_projection_hash, evidence_projection_hash, claim_binding_hash` | Claim support state & model version @ derivation time. `canary_window_id` links to a canary window (if result came from a model run). `verdict_projection_hash` + `evidence_projection_hash` are the semantic hashes for detecting drift. |
| `rederivation_triggers` | 2515 | `trigger_id, claim_id, kind, detected_at, evidence_json, batch_window, enqueued_at` | Triggers for re-running claim verification (source deleted, evidence drift). `kind` is the trigger type (EVIDENCE_CHANGED, SOURCE_DELETED, etc.). |
| `canary_windows` | 0 | `window_id, model_version, prompt_template_hash, started_at, baseline_window_id` | Historical canary run metadata (model version, prompt used, start time). Currently unused (0 rows). |
| `canary_results` | 0 | `result_id, window_id, prompt_id, parsed_support_state, raw_text, run_at` | Canary result details. Currently unused. |
| `source_observations` | 1994 | `observation_id, source_id, source_release_id, status, source_content_hash, fetched_at, fetched_via, evidence_depth, valid_from, asserted_at, canonical_source_id` | Physical observations of external sources (PubMed, ClinVar, gnomAD, PharmGKB). `source_content_hash` is the evidence projection. `evidence_depth` tracks how deep the evidence goes. |
| `evidence_bindings` | 1510 | `binding_id, verdict_id, observation_id, valid_from, asserted_at` | Links verdicts to the source observations that support them. Bi-directional graph. |
| `trigger_drain_events` | 2515 | `drain_event_id, trigger_id, claim_id, drained_at, outcome, produced_verdict_id, cost_usd` | Execution record for each trigger (when drained, outcome success/fail, cost). One-to-one with `rederivation_triggers`. |
| `verdict_supersedings` | 787 | `event_id, prior_verdict_id, new_verdict_id, superseded_at, reason` | Tracks verdict replacements (when a new verdict made the prior one obsolete). `reason` documents why. |
| `verdict_binding_mismatch` | 294 | `claim_id, stored_binding, live_binding, detected_at` | Anomaly detector rows — when DB binding doesn't match live recomputation. |
| `cycle_defects` | 0 | `cycle_defect_id, claim_id_a, claim_id_b, detected_at, drain_id, resolved_at, resolution_note` | Cycle detection ledger (two claims depending on each other). Currently unused. |

**Calibration signal:** YES, present.
- **`claim_verdicts.verdict_projection_hash`** — computed by `knowledge/projection.py::compute_verdict_projection_hash()`. Compares live projection vs. stored projection to detect semantic drift.
- **`verdict_binding_mismatch`** — 294 rows show cases where DB binding diverged from live recomputation (anomaly signal).
- **`trigger_drain_events.outcome`** — execution result (success/fail).
- **`canary_window_id`** — historical link to canary runs (unused; the Python test is the live canary).

**VERDICT:** Ledger is PRESENT and tracks claim verdict drift, source observation freshness, binding mismatches, and execution outcomes. Calibration signal exists but is **reactive** (detects drift) not **proactive** (proposes improvements).

### 5. Bus: Queues, Decision Staging, Flag Files

**Search for:**
- `queue/`, `decisions-pending/`, `.flag`, `improvement-queue.md`, event-driven staging areas

**Found:**
- **`decisions/`** (path: `/Users/alien/Projects/genomics/decisions/`) — **What it is:** Decision log, NOT a queue. Each file is a YAML-frontmatter markdown record (`YYYY-MM-DD-slug.md`). Examples: `decisions/2026-05-18-sbayesrc-defer-fanout-stacking-probe.md`, `decisions/2026-06-13-completion-authority-owncode-validity-kernel.md`. These are **operator-written** decisions, not auto-generated improvement proposals.
  - **Verbatim from CLAUDE.md lines 247–248:** "Concept-level pivots get one file per decision (`YYYY-MM-DD-slug.md`, template in `decisions/.template.md`, YAML frontmatter required). Write when: path-dependent pipeline choices, dropping analyses after validation fails, adopting tools that changed belief, curation-strategy shifts."
  - **VERDICT:** Decision **log**, not improvement queue. No auto-proposal mechanism.

- **`docs/ops/plans/`** (path: `/Users/alien/Projects/genomics/docs/ops/plans/`) — **What it is:** Indexed operational plans. Template in `docs/ops/plans/index.md` (CYCLE.md line 32: "generated source of truth is `docs/ops/plans/index.md`; do not hand-maintain counts here"). Plans are operator-written, indexed, never auto-generated.
  - **No improvement-log.md in genomics** — improvement-log is ONLY in agent-infra (source: agent-infra/improvement-log.md). Genomics findings feed into agent-infra's ledger (e.g., MAINTAIN.md line 27: "improvement-log [2026-04-12 genomics 95834a52]").

- **No `queue/`, `decisions-pending/`, or flag files found** — the pipeline uses `_STATUS.json` for attempt state (per CLAUDE.md line 29), not decision queues.

**VERDICT:** No improvement bus/queue in genomics. Agent-infra's improvement-log.md is the canonical ledger; genomics feeds findings into it. Bus exists only in agent-infra.

### 6. Verifier Regime: Canary + Other Deterministic Gates

**Determinism check:**

| Gate | Deterministic? | Scheduling | Failure mode |
|------|---|---|---|
| `canary_gate.py` (70 sentinels) | YES — pure Python, no model calls, re-runs identically | Pre-commit hook (blocks commit on exit-2) | Fixture-pinning vulnerability (code + fixture mutate together) |
| `verify_genotypes.py` | YES — strand/coordinate checks | Pre-commit hook (explicit `just verify-genotypes`) | Coordinate hallucination in config (handled by CLAUDE.md §13) |
| `precommit-qa-gate.sh` | YES — chains deterministic tests | Pre-commit hook | Orchestrated (wraps canary) |
| Direction E quorum (executor.py) | PARTIAL — Deterministic dispatch, but calls Direction D quorum (LLM-based) | Manual trigger via `MutationGateway.write_verdict()` (called by drain dispatcher) | Model version drift (prompt_template_hash tracks this); verifier-conditioned (DECISION TREE in executor.py, not free-form reasoning) |

**Integration:**
- **Deterministic gates (canary, hygiene, genotype)** run on every commit (pre-commit hooks).
- **Direction E claim verification** runs on data drift (triggered by `rederivation_triggers`; manually invoked by drain dispatcher, not auto-scheduled).
- **No launchd/cron loop observed** — all scheduling is manual or hook-driven.

**Mixed regime:** Deterministic frontend (code-change detection), LLM-driven backend (claim verification).

**VERDICT:** Verifier regime is **clean** (deterministic + decision-tree-based quorum, not free-form LLM judging). Scheduling is hook-driven (pre-commit) + manual (via MutationGateway). No auto-loop.

---

## 3-LINE SUMMARY: What a Genomics LOOP.md Would Need

1. **Phase 2 (current):** Genomics is a knowledge witness + data-driven verification pipeline. No standalone loop contract needed; genomics is improved BY agent-infra's `/improve` conductor (MAINTAIN.md, improvement-log.md). The canary gate is an accept-boundary; rederivation triggers are a data-freshness detector, not an improvement proposer. **Contract: a typed `KNOWLEDGE_CYCLE.md`** documenting the trigger→executor→verdict→cascade lifecycle (lives in `knowledge/` subsystem docs, not a top-level loop).

2. **Phase 3 (future, ~3–6 months):** IF the project pivots to autonomous classification improvement (e.g., "auto-propose new canary variants when classification performance drifts"), THEN migrate to a standalone `LOOP.md` contract with a Dreamer operator (proposes new thresholds/rules), a verifier (runs canary + cross-validation), and a MutationGateway-backed accept gate. This requires: (a) measuring classification accuracy on a holdout set (currently all 70 canaries are manually curated); (b) building an auto-proposer for threshold/rule changes (currently human-driven); (c) defining a feedback loop (accuracy → trigger proposal → gate decision). **Decision point: 2026-09-01** (when gnomAD v5 + AlphaMissense updates land per CYCLE.md line 551).

3. **DEPLOY PHASE:** Phase 2 is standalone-deferred (MAINTAIN.md as conductor-relay, no autonomous loop). Phase 3 decision at strategc review (depends on Phase 1–2 maturity + whether autonomous improvement ROI justifies the architecture). Genomics LOOP.md contract goes live only if Phase 3 is approved; until then, `/improve maintain` governs both agent-infra + genomics as a single external conductor.

---

## KEY EVIDENCE CITATIONS

| What | Where | Quote |
|------|-------|-------|
| Knowledge ledger tracking | data/knowledge/knowledge.duckdb | `claim_verdicts` (952 rows), `rederivation_triggers` (2515), `source_observations` (1994), `verdict_binding_mismatch` (294 anomaly rows) |
| Canary as accept-gate | scripts/canary_gate.py:105–176 | "Run all canary variants and return exit code... label_ok = result.label == expected_label... if failures: print(f'\nFAILURES...'); return 1" |
| No autonomous loop driver | CYCLE.md:1–595 + MAINTAIN.md:1–64 | CYCLE.md tracks operator-gated checkpoints (Tier 1 BIO, Tier 0.5 probe); MAINTAIN.md feeds findings into agent-infra, no reverse conductor. |
| Direction E is reactive, not proactive | knowledge/executor.py:1–60 | "Called by the drain dispatcher when the Resolver returns `needs_trigger` / `source_deleted` / `drift_detected`. The Executor... Returns... but NEVER writes." |
| MutationGateway is the only writer | knowledge/mutation_gateway.py:1–40 | "`MutationGateway` is the only module permitted to INSERT into the knowledge tables... The gateway acquires `data/knowledge/writer.lock` on `__enter__`... all DB writers land atomically (or all roll back)." |
| Conductor is in agent-infra | agent-infra/improvement-log.md:1–40 | "Findings from session analysis. Each tracks: observed → proposed → implemented → measured... improvement-log is ONLY in agent-infra... Genomics feeds findings into it." |
| Fixture-pinning vulnerability | CLAUDE.md:56–58 | "`defer fixture pinning until drain settles — pinning `expected.json` against pre-drain bytecode while the drain rewrites the same stages 30 min later = born-stale fixture + multi-agent collision risk.`" |
| No discovery/proposal mechanism | knowledge/ subsystem (cascade, executor, projection) | All modules are READ-ONLY except MutationGateway (write-only, single-threaded). Zero proposer code. |

