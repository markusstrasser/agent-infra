# Intel Self-Improvement Loop Map (2026-06-13)

## CENTRAL QUESTION VERDICT

**Intel is a CONDUCTOR-COUPLED data/analysis system improved by agent-infra's /improve maintain conductor, NOT a standalone RSI loop.**

### Evidence:

1. **No self-contained Dreamer/Cycle/LOOP conductor:** Intel has NO:
   - OUTER-LOOP.md or LOOP.md driver
   - /dream or /cycle skill spawned by intel
   - launchd job for a self-contained improvement loop
   - Standalone agent that proposes and gates its own changes

2. **Intel proposes → human gates:**
   - Rule proposals flow through `/propose-rule` skill (autonomous candidate generation) → operator review (Step 2) → backtest eval in intel-harness (Step 3) → **operator approval only** (Step 4, constitutional gate)
   - Improvement-log improvements are operator-issued or routed to human approval (MAINTAIN.md: 5/10 steward-proposals require shared-infra/cross-repo operator sign-off)
   - Candidates bubble up via `/fleet_review.py` decay surface → operator runs retirement (Step 5)
   - Constitution Law 6: "Agent may change freely... Rules of adjudication: market outcomes adjudicate; monthly scoreboard review; revert methodology changes showing no improvement. Auto-commit: low (refresh) → medium → high (trade-relevant) all require evidence trails, never autonomous assertions"

3. **Agent-infra is the outer-loop orchestrator:**
   - MAINTAIN.md (last tick 2026-04-17) is agent-infra's conductor tick, tracking intel+genomics+other repos as coupled systems
   - .claude/plans/ (intel's planning surface) houses actor plans that agent-infra eventually improves as cross-project maintenance
   - Constitution law enforcement happens via agent-infra hooks (pretool gates, etc.) + scheduled scoreboard reviews

4. **Prediction/calibration surface is domain data-quality gate, not RSI loop:**
   - `tools/prediction_tracker.py` + `intel/indexed/theses.duckdb` track falsifiable predictions
   - Brier score + calibration spine measure but do NOT auto-propose rule changes
   - Outcome data only gates whether a thesis entry is valid (frozen if calibration breaks), never gates whether intel's OWN architecture improves

**Verdict: Phase-3-conductor-coupled. Defer standalone intel LOOP.md contract until Phase 3 (cross-project RSI). Intel's improvements flow through agent-infra MAINTAIN + human gates, not a self-contained loop.**

---

## 6-ITEM LOOP MAP

### 1. Loop Doc / Driver: NONE (conductor-coupled)

**Finding:** No intel-native loop document exists. The equivalent of an OUTER-LOOP.md is handled by:

- **Path:** `/Users/alien/Projects/agent-infra/MAINTAIN.md` (lines 1-58)
  - **What:** Agent-infra's quality-assurance conductor, last tick 2026-04-17
  - **Quote (lines 33-40):**
    ```
    | brainstorm-dedup-precheck | meta skill | review |
    | codex-agents-md-no-verify-mirror | genomics AGENTS.md | human approval (cross-repo) |
    | destructive-git-ref-hook | shared hook (3+ projects) | human approval (shared infra) |
    ```
  - Maps intel improvements as external items in a shared proposal queue

- **Path:** `/Users/alien/Projects/intel/.claude/plans/44a5364f-recursive-self-improvement.md` (lines 1-11, 76-116)
  - **What:** Intel's most recent self-improvement plan, fully executed 2026-05-29
  - **Quote (lines 2-11):**
    ```
    Evidence-grounded structural fixes from the retro session. Every item traces to a
    concrete event. Ranked by leverage (deep × strictly-better × long-term). No
    backward-compat. Iatrogenic risk noted per item. **Status: FULLY EXECUTED
    2026-05-29 (session f38d4d74). Phases 1-3: b8f08445 / 34d74927 / 95e22bc4 /
    ce9578d0. /critique close fixes: 9853c973 / 757f3881 / 2b19fb41. G1 (§9
    calibration stratification): 499aa8da. G2 (gate-fleet prune — line-linter scope
    cut + audit method): 844df711.
    ```
  - Phase 1-3 are BUILD-READY but deferred until "no peer agent is active on this repo" (line 183), showing operator-gated sequencing, not autonomous loop

- **CLAUDE.md section:** Constitution §6 (lines 171-175)
  - **Quote:** "Agent may change freely (cross-checked against the Generative Principle): rules, hooks, tooling, memory, CLAUDE.md operational sections, base rates (evidence ≥10% of prior effective n; log prior→evidence→posterior). Rules of change: observed-session evidence, never speculation; architectural enforcement over advisory text; one-in-one-out."
  - No self-contained loop; changes require "observed-session evidence" + "monthly scoreboard review" (operator).

### 2. Candidates — What Does the Loop Actually Improve/Accept?

**Candidates:** Rules (`.claude/rules/`), hooks (`.claude/hooks/`), memory (base rates), and entities (analysis/entities/*.md).

- **Rule candidates:** `.claude/rules/rule-evolution-pipeline.md` (path `/Users/alien/Projects/intel/.claude/rules/rule-evolution-pipeline.md`, lines 19-26)
  - **Quote (lifecycle states):**
    ```
    | **Candidate** | `docs/rules/_registry/_candidate_<slug>.md` | Has ≥3 cited distinct incidents from session traces | `/propose-rule` skill (autonomous) |
    | **Proposed** | `docs/rules/_registry/_proposed_<slug>.md` | Operator reviewed, draft rule body sound; eval cohort designed | Operator |
    | **Eval-tested** | `docs/rules/_registry/_eval_<slug>.md` | `bin/eval_proposed_rule.py` run on ≥6 names INCLUDING ≥2 control names; reasoning-citation rate ≥75% on triggered cases; false-positive rate on controls ≤30% | Operator after reading eval report |
    | **Active** | `.claude/rules/<slug>.md` (no prefix) | Operator approval — constitutional gate per Constitution Law 6 | Operator |
    ```
  - Candidates are **rules**, not entities or theses. Acceptance is operator-gated + backtest evidence (intel-harness).

- **Entity-file candidates:** None autonomous. Entities are written by the agent but gated by `/disqualify` + `/confirm` workflows (lines 119-120, CLAUDE.md)
  - **Quote:** "Adversarial-first DD ordering: run `/disqualify TICKER` BEFORE any bull thesis on a RESEARCH/WATCHLIST/BUY name (sizing >0). Hook `pretool-disqualification-required-gate.py` enforces."

- **Base-rate updates:** `memory/priors.md` (Constitution Law 6, line 144)
  - **Quote:** "Updating `memory/priors.md`: new data must be >= 10% of prior effective sample size. Log prior -> evidence -> posterior."

- **Thesis/prediction candidates:** None autonomous. Tracked in `analysis/_logs/prediction_events.jsonl` + resolved via `tools/prediction_tracker.py resolve` (daily_routine.md line 169), operator-judged.

### 3. The Accept-Gate(s)

**Multi-layer gates:**

#### Gate 1: Tier-1 Data-Source Health + Pipeline Liveness (Data-Quality Guard, NOT RSI accept-gate)

- **Path:** `/Users/alien/Projects/intel/.claude/hooks/pretool-tier1-pipeline-liveness-gate.py` (lines 1-37)
  - **What:** Blocks Tier-1 cross-domain edge writes when daily pipeline is dead (>35d stale resolve loop) OR data plane is corrupt
  - **Quote (lines 3-18):**
    ```
    This gate CONSUMES those signals at the decision boundary. When an entity /
    research / theme file asserts a Tier-1 cross-domain edge AND the data-production
    control plane is not live, it blocks (hard-dead) or warns (soft-stale) so the
    dead loop blocks downstream Tier-1 use instead of being merely reported.
    
    Signals (reality-anchored — file mtimes + the completion marker, not model
    judgment):
      HARD-DEAD (block in `block` mode):
        - a critical-failure beacon exists (the last daily run aborted on a
          CRITICAL step and hasn't recovered), OR
        - check_pipeline("daily") reports a CRITICAL FAILURE in the last run, OR
        - the resolve-loop heartbeat is >= RESOLVE_LOOP_FAIL_DAYS (35d) stale.
    ```
  - **Verdict:** Data-quality guard ONLY. Does NOT decide whether a rule is good or a thesis is valid. Blocks on pipeline death, not on outcome score.

#### Gate 2: Rule Evaluation Backtest (Evidence-Based Acceptance)

- **Path:** `/Users/alien/Projects/intel-harness/bin/eval_proposed_rule.py` (intel-harness repo, not intel)
  - **What:** Backtest-harness eval that measures whether a proposed rule improves decisions vs baseline
  - **Quote (rule-evolution-pipeline.md lines 78-82):**
    ```
    Builds A (baseline, no proposed rule) vs A+proposed (with) bundles for
    each cohort ticker. Dispatches under opus. Computes:
    - Verdict diff per (ticker, config)
    - Conviction-stamp diff
    - Reasoning-citation rate (does agent cite the new rule by name in
      ≥75% of triggered cases?)
    - False-positive rate on control names
    ```
  - **Columns tracked:** verdict_diff, conviction_stamp_diff, reasoning_citation_rate (≥75% for promotion), false_positive_rate_controls (≤30% for promotion)
  - **Verdict:** This IS the real "is this rule good" verifier. Outcome-based (backtest residual return). Consumed by rule-evolution-pipeline Step 4 (operator).

#### Gate 3: Operator Approval (Constitutional Gate)

- **Path:** Constitution Law 6 (CLAUDE.md lines 171-175) + rule-evolution-pipeline.md lines 93-113
  - **Quote (rule-evolution-pipeline.md lines 93-98):**
    ```
    **Tool:** Operator manually.

    **Behavior:**
    - Reads eval report
    - If promotion-eligible AND operator concurs:
      - `git mv docs/rules/_registry/_proposed_<slug>.md .claude/rules/<slug>.md`
    ```
  - **Verdict:** Constitutional gate (human). Operator reads eval report + decides activation. Intel's self-improvement is NOT autonomous at this stage.

### 4. Ledger: Prediction Tracking & Calibration

**Finding:** Predictions are tracked but NOT used to auto-propose rule changes.

- **Path:** `/Users/alien/Projects/intel/tools/prediction_tracker.py` (lines 1-50)
  - **What:** Scoring rule for investment intelligence; tracks falsifiable predictions
  - **Quote (lines 9-13):**
    ```
    Storage: analysis/_logs/prediction_events.jsonl is the SOLE store (append-only,
             content-addressed). Every command emits/reads events that fold into the
             current_predictions projection (intel/indexed/theses.duckdb) via the
             tools.lib.predictions_read DAL. The predictions.csv + state.duckdb shadow
             stores were retired in the event-sourcing cutover (zesty-napping-frost P4).
    ```
  - **Columns:** thesis_ref, entity_ref, direction (ABOVE/BELOW/OUTPERFORM/UNDERPERFORM), target_value, timeframe_months, date_made, deadline, confidence (p_ours), source, resolution_type (market_return | dual), fundamental_criterion, Brier_score (auto-derived), actual_outcome (manual or price-based)
  - **Data location:** `analysis/_logs/prediction_events.jsonl` (source of truth), projected into `intel/indexed/theses.duckdb` table `current_predictions`

- **Path:** `/Users/alien/Projects/intel/intel/indexed/theses.duckdb` (DuckDB)
  - **What:** Thesis graph index, derived from entity-file frontmatter
  - **Quote (CLAUDE.md lines 102-105):**
    ```
    Query access to the thesis graph (`intel/indexed/theses.duckdb`, gitignored — rebuild `just rebuild-theses`). Built from entity-file frontmatter → assertions (predicates in `tools/theses/predicates.py`, slots in `slot_vocab.py`) → derivable views. Read-only tools: `thesis_query`, `belief_history`, `evidence_for_thesis`, `contradictions`, `stale_theses`, `entry_readiness(file)`, `monitoring_state(file)`, `theses_status`, + others. The Closure FSM (`entry_readiness`/`monitoring_state`) is on-demand only — NOT wired to any hook; the graph is a reference surface + advisory cron worklists, never a verdict gate.
    ```
  - **Calibration:** Brier score tracks prediction accuracy. Per Constitution Law 3 (lines 162-163): "Probabilities are legitimate ONLY while the calibration spine is live; if it breaks, new probability-bearing writes block until fixed."
  - **Verdict:** Predictions are SCORED but NOT auto-feedback into rules. The calibration spine is a DATA SURFACE (locked if broken), not an RSI gate. No autonomous "this prediction outcome tells us to retire a rule" loop.

- **Resolution process:**
  - **Path:** `/Users/alien/Projects/intel/docs/workflows/daily_routine.md` (lines 169-171)
    - **Quote:**
      ```
      uvx --with duckdb python3 tools/prediction_tracker.py resolve
      uvx --with duckdb python3 tools/source_eval.py resolve && uvx --with duckdb python3 tools/source_eval.py calibrate
      ```
    - Manual operator-triggered via cron, not continuous. Resolves price-based predictions; operator judges dual-resolution cases.

### 5. Bus: Queues & Decision Surfaces

**Finding:** Multiple decision queues exist but none are part of a unified RSI loop.

- **Source-Miss Queue:**
  - **Path:** `/Users/alien/Projects/intel/.scratch/source_miss_sweep_<date>.md`
  - **Emitted by:** `tools/source_miss_sweep.py` (daily_routine.md line 326)
  - **What:** Positive/high-conviction source claims where entity file is missing or stale. Admission queue, not action queue.
  - **Quote (daily_routine.md lines 19-20):** "Daily output includes `.scratch/source_miss_sweep_<date>.md`, which ranks positive/high-conviction source claims whose tickers are missing entity files or still have cautious entity stances. Treat it as an admission queue, not a BUY list."

- **Thesis Review Queue:**
  - **Path:** `/Users/alien/Projects/intel/analysis/paper_book/review_queue.jsonl`
  - **Emitted by:** `tools/thesis_review_queue.py` (daily_routine.md line 318, run_soft)
  - **What:** WATCHLIST stamps within 14d + friction-challenge rows. Monitoring surface, not improvement proposal.

- **Insider Cluster Scan:**
  - **Path:** `/Users/alien/Projects/intel/.scratch/insider_clusters_<date>.md`
  - **What:** Tickers with >$100K insider buy clusters lacking entity files. Admission queue.

- **Falsifier-Fired Events:**
  - **Path:** `/Users/alien/Projects/intel/analysis/_logs/monitoring_events.jsonl` (appended by monitoring_evaluator)
  - **Quote (daily_routine.md lines 203-212):**
    ```
    This reads the atomized falsifier_for / kill_condition_for assertions, evaluates the AUTO-class
    (text-parsed absolute close-price) thresholds against split-adjusted prices with
    a freshness gate, and appends tripped events to monitoring_events.jsonl — which
    the Theses Rebuild below projects into the graph so monitoring_state() flips.
    Runs BEFORE the rebuild so trips project same-cycle.
    ```
  - **What:** Falsifier trips; used for thesis closure, NOT rule improvement proposals.

- **No unified improvement-log or decisions-pending queue:**
  - Agent-infra's `/improve maintain` conductor has no coupled intel-specific ledger
  - Intel's improvement proposals are filed as `.claude/plans/` or `.claude/rules/_registry/_candidate_*.md`
  - No queue structure that maps "prediction resolved badly" → "rule proposal"

### 6. Verifier Regime & Scheduling

**Regime: Mixed (outcome-scored + freshness setpoints) + operator-gated scheduling.**

#### Verifier Types:

1. **Outcome-scored (Rules):**
   - **Tool:** `bin/eval_proposed_rule.py` (intel-harness)
   - **Measures:** Brier residual return on cohort tickers (A vs A+proposed rule)
   - **Promotion rule:** reasoning-citation ≥75% + false-positive ≤30%
   - **Schedule:** Operator-initiated per rule proposal (Step 3)
   - **Consumed by:** Operator, Constitution Law 6 approval gate

2. **Outcome-scored (Predictions):**
   - **Tool:** `tools/prediction_tracker.py score` (weekly_routine.md line 169)
   - **Measures:** Brier score per prediction; calibration spine health
   - **Consumed by:** Entity-file prob updates (p_ours recalibration), NOT rule proposals
   - **Schedule:** Weekly manual cron (`tools/prediction_tracker.py resolve` then `calibrate`)

3. **Freshness setpoints (Data quality):**
   - **Tool:** `tools/healthcheck.py` + FRESHNESS_CHECKS (daily_routine.md line 242)
   - **Measures:** Last-run age for prices, insider forms, prediction resolves
   - **Thresholds:** e.g., prices ≤5 days (FAIL); predictions pending ≤90 cases
   - **Consumed by:** Operator alerts + pretool-tier1-pipeline-liveness-gate
   - **Schedule:** Daily cron (run_important), emits to pipeline_failures.log

#### Scheduling:

- **Daily (launchd/cron):** `tools/daily_update.sh` (21 critical + soft steps)
  - Lines 95-348 in daily_update.sh
  - Ticket: daily prices, form4, healthcheck, DuckDB rebuild, signal scanner, coverage-gap scanner, prediction resolve
  - **Emit:** signals_YYYYMMDD.csv, falsifier_status_<date>.md, source_miss_sweep_<date>.md, alerts
  - **No loop closure:** Outputs are human-reviewed; no autonomous next-cycle proposal

- **Weekly (Saturday 10am, launchd/cron):** `tools/weekly_update.sh` (deep update)
  - Deeper data pulls + prediction resolve + calibrate + evaluation refreshes
  - **Emit:** prediction scores, calibration surface updates
  - **No loop closure:** Operator reviews scoreboard (manual monthly per Constitution Law 6)

- **On-demand:** `/propose-rule` skill, `/disqualify`, `/confirm`, rule-evolution pipeline steps
  - No scheduled tick; operator-initiated

#### Verdict:

- **Clean:** No (mixed). Outcome-scored rules exist; prediction scores exist; but no unified "bad outcome → proposal" automation. Constitution Law 6 explicitly deferring to "monthly scoreboard review" (operator).
- **Freshness:** Setpoint-based, operator-gated. Healthcheck FRESHNESS_CHECKS gate individual datasets; pipeline-liveness gate blocks Tier-1 writes if data plane is dead. No autonomous decay or circuit-breaker.
- **Autonomy:** Zero-to-low. `/propose-rule` can generate candidates (≥3 incidents), but all other steps (review, eval, approval, archival) are operator-only. Prediction resolution is manual cron, not autonomous event-driven.

---

## SUMMARY: What a Faithful intel LOOP.md Contract Needs + Phase Placement

**If intel were a standalone RSI loop (hypothetical for Phase-2 migration):**

1. **Loop doc needs:**
   - Tick: daily (`.scratch/prediction_scores.md` + `.scratch/rule_candidates.md` + falsifier trips)
   - Dreamer: `/propose-rule` + `bin/eval_proposed_rule.py` (already exists in distributed form)
   - Verifier: outcome-scored rules (Brier residual) + prediction Brier calibration (already measured, not gated)
   - Acceptor: operator approval only (Constitution Law 6 — cannot be automated)
   - Ledger: `analysis/_logs/prediction_events.jsonl` + `.claude/rules/_registry/_*` lifecycle

2. **Current state:** Intel's loop pieces exist but are not bound into a unified LOOP.md contract:
   - Proposal (Rule-Evolution-Pipeline Steps 1-3): ✓ in place, partially autonomous
   - Acceptance (Step 4): ✗ operator-only, not automatable without Constitution change
   - Feedback (prediction outcome → rule proposal): ✗ missing (predictions are tracked but not routed back)
   - Scheduling: ✓ daily/weekly cron, but no unified loop tick

3. **Phase placement:** **Phase-3-conductor-coupled.** Do NOT migrate intel to standalone LOOP.md in Phase 2. Reasons:
   - Constitutional gate (Law 6) requires operator approval at rule activation; cannot be removed without operator sign-off
   - Prediction→rule feedback loop is not wired; adding it requires design (which prediction outcomes trigger which rule proposals?)
   - Agent-infra MAINTAIN.md already covers intel as a coupled system; repeating a LOOP.md in Phase 2 splits ownership
   - **Phase-3 work:** Implement cross-project RSI (agent-infra MAINTAIN.md becomes central tick; intel, genomics, etc. feed back) + formalize the "bad outcome → rule candidate" automation once Constitution Law 6 amendments are approved

---

## Evidence Sources (Exact Paths)

| # | Category | Path | Lines | Key Quote |
|---|----------|------|-------|-----------|
| 1 | Loop doc | `/Users/alien/Projects/agent-infra/MAINTAIN.md` | 1-58 | "MAINTAIN.md (last tick 2026-04-17) is agent-infra's conductor" |
| 2 | Plan | `/Users/alien/Projects/intel/.claude/plans/44a5364f-recursive-self-improvement.md` | 1-11, 76-116 | "Status: FULLY EXECUTED 2026-05-29" + "Phases 1-3 are BUILD-READY" (line 183) |
| 3 | Constitution | `/Users/alien/Projects/intel/CLAUDE.md` | 146-176 | Law 6: "Agent may change freely... monthly scoreboard review... operator re-read" |
| 4 | Rule pipeline | `/Users/alien/Projects/intel/.claude/rules/rule-evolution-pipeline.md` | 19-26, 93-113 | Lifecycle table + "Operator approval — constitutional gate per Constitution Law 6" |
| 5 | Data gate | `/Users/alien/Projects/intel/.claude/hooks/pretool-tier1-pipeline-liveness-gate.py` | 1-37 | "blocks hard-dead or warns soft-stale" (data quality only) |
| 6 | Prediction ledger | `/Users/alien/Projects/intel/tools/prediction_tracker.py` | 9-13, 51 | "analysis/_logs/prediction_events.jsonl is the SOLE store" |
| 7 | Thesis DB | `/Users/alien/Projects/intel/intel/indexed/theses.duckdb` | (DuckDB) | Projected from entity-file frontmatter; read-only (not a gate) |
| 8 | Daily routine | `/Users/alien/Projects/intel/docs/workflows/daily_routine.md` | 1-188 | 21 steps; no unified loop tick, all human-reviewed |
| 9 | Daily pipeline | `/Users/alien/Projects/intel/tools/daily_update.sh` | 1-349 | Cron-driven pipeline; no autonomous next-cycle proposal |
| 10 | Source queue | `/Users/alien/Projects/intel/.scratch/source_miss_sweep_<date>.md` | (daily) | "Treat it as an admission queue, not a BUY list" |

