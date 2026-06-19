---
title: RSI comparative report — hutter, anim, intel, research
date: 2026-06-18
sources: [hutter, anim-workbench, intel, intel-harness, research git logs + LOOP docs]
---

# RSI comparative report — hutter, anim-workbench, intel, research

Research session 2026-06-18. Compares recursive self-improvement loops across four systems:
how they work, verifier regimes, what improved Jun 11–18, whether a shared `loop-core`
package exists, and cross-repo generator collection.

---

## Executive summary

| | **hutter** | **anim-workbench** | **intel** | **intel-harness** |
|---|-----------|-------------------|-----------|-------------------|
| **Regime** | Clean verifier | Partial verifier | Partial + principal | Offline surrogate |
| **Status** | Live autonomous search | Gates + critics; inner paused | Daily scoreboard + hooks | Paired ablation; spend STOPPED |
| **Inner loop** | GPT-5.5 NEVER-STOP | Composer checklist (paused) | `/propose-rule` + operator | Sealed replay dispatch |
| **Outer loop** | Dreamer + mechanical tick | Opus/GPT/Gemini hourly | `daily_update.sh` + weekly scoreboard | `walk_forward_runner` |
| **Ledger** | SQLite + views | JSONL (103 rows) | paper_book + predictions + hook telemetry | results/v1/ + paper_book resolutions |
| **Judge** | `eval.py` bit-exact | ~150 `verify:*` gates | Market resolve + hooks + harness (paired only) | Paired deltas + instrument battery |
| **Last week** | Historian, bus fix, fx3 | Adversarial gates, EoC oracles | Constitution v2.1, eval preflight | Powered cell UNDERPOWERED (N=43) |

**research repo** (separate): immigration-fiscal **thesis generators** — agent-mined JSON → DuckDB
`lifetime_generators` (104 rows). **Not wired** to intel-harness or rule-evolver.

**Verdict across repos:**

- **hutter** = only **live autonomous search** loop (clean verifier).
- **anim** = best **anti-Goodhart gate stack**; inner evolver cold.
- **intel** = mature **partial-verifier RSI** at daily resolve + hook-telemetry layer; rule
  evolution documented; harness authority **not earned** (bent ruler, surrogate LOCKED).
- **No shared `loop-core` package** — `skills/outer-loop/route.py` (~170 LOC) tested, zero callers.

---

## 1. How the hutter loop works

### Architecture (two roles)

```
OUTER (Dreamer) — Opus 4.8, persistent session + mechanical actor
  ├── Reads: ledger.db, queue/, proposals-pending/
  ├── Writes: queue/, decisions-pending/, fleet dispatch
  └── Subagents: heretic (hourly), historian (2h), /research fleets

INNER (Grinder) — GPT-5.5 codex high, NEVER-STOP on x86 VM
  ├── Reads: queue/ (re-read EVERY iteration)
  ├── Writes: ledger rows, STALL/QUEUE_LOW flags
  └── Judge: eval.py ONLY (bit-exact gate, no LLM judge)
```

### Inner loop contract (`LOOP.md`)

```
PROPOSE → BUILD → GATE(enwik4) → PROBE(enwik45) → PROMOTE(enwik5) → RATCHET → LEDGER → CONFIRM(x86)
```

- **Gate** (~100s): bit-exact only; never a size decision on enwik4
- **Probe** (~5m): direction signal; never ratchets; ~28% probe-win → ACCEPT survival
- **Ratchet**: enwik5 on M3; enwik6/8 x86-only
- **Compress-first**: skip decompress on reject path (~2× faster feedback)
- **Crossover**: multi-parent recombination from `v_clade_yield` fertile-non-best parents
- **Parking lot**: `revisit:scale` tags for ideas that fail on small slices

### Outer loop mechanics

| Component | Cadence | Tokens |
|-----------|---------|--------|
| `dreamer_tick.sh` (launchd) | 20 min | $0 |
| Dreamer model tick | 30 min (2h during long e8) | Opus |
| Heretic subagent | 1h + wake-gate | Opus |
| Historian (`historian-loop.sh`) | 2h | codex xhigh read-only |
| `loop_health.py` | 20 min | $0 |

**Mechanical actor** (`dreamer_tick.sh`): mirror ledger, reap idle boxes, harvest markers,
heretic pre-filter, write `.claude/dreamer-tick.status`. Fixes "model forgot plumbing."

**Single-writer:** one Dreamer session; subagents for bounded parallel work.

### Parallelization

- **Search parallelizes** across Hetzner boxes (beam ≤4, `night-cell.sh`, `box_wave_runner.py`)
- **Ratchet serializes** — one committer merges winner
- Bottleneck = cmix wall-clock, not LLM propose time
- Linear lever = boxes (one ChatGPT sub quota)

### Verification & ledger

- **Fitness:** compressed bytes S (lower = better), hard gates (bit-exact, RAM, time budget)
- **Verdict ladder:** GATE_PASS → PROBE_* → ACCEPT / REJECT / ACCEPT_HELD
- **`heretic_audit.py`:** stateless anti-self-dealing at accept (reject rate, tautology, oracle ratio)
- **Ledger:** SQLite with views (`v_leaderboard`, `v_clade_yield`, `v_calibration_by_tag`, `v_revisit`)
- **Git bus:** ledger via `ledger-dump.sql`; queue/decisions are **gitignored** → rsync to boxes

### Codex coverage (agentlogs)

- CLI (`codex_exec`, `codex-tui`) + Desktop (`Codex Desktop`) both index from `~/.codex/sessions/`
- anim-workbench: 23 codex sessions indexed (15 Desktop, 7 exec, 1 tui)

---

## 2. How the anim-workbench loop works

### Architecture (two roles)

```
OUTER — digest (GPT minimal) → RSI Opus max + Arch GPT medium + Heretic Gemini (parallel)
  ├── launchd hourly (skips unchanged tree → $0 idle)
  ├── Outputs: .model-review/outer-loop-{rsi,arch,heretic}-<ts>.md
  └── dreamer:tick (ported from hutter) → evolver/dreamer-tick.status

INNER — Composer via Cursor agent -p (PAUSED: evolver/GRIND_PAUSE)
  ├── Checklists: grind/grow/shrink (all 0 open)
  ├── keep-going prompt on stop hooks
  └── Judge: ~150 verify:* gates + try:corpus (never LLM-judged)
```

### Inner loop contract (`evolver/LOOP.md`)

```
0. CHECKLIST → 1. PROPOSE → 2. BUILD → 3. VERIFY → 4. RATCHET → 5. LEDGER → goto 1
```

- **Primary mode:** GROW (wild Manim capability)
- **Shrink:** ON HOLD until gates bind harder
- **Scopes:** A (core IR, auto), B (wave corpus, tier ladder), C (human greenlight)
- **Tier ladder:** typecheck → try:scene → try:corpus → measure:v2-scrub

### Outer loop mechanics

| Lane | Model | File |
|------|-------|------|
| Digest | gpt-5.5 minimal | (feeds arch) |
| RSI | claude-opus-4-8 max | `.model-review/outer-loop-rsi-*.md` |
| Architecture | gpt-5.5 medium | `.model-review/outer-loop-arch-*.md` |
| Heretic | gemini-3.5-flash medium | `.model-review/outer-loop-heretic-*.md` |

Config: `evolver/outer-loop-models.json`

### Parallelization

| Layer | Pattern |
|-------|---------|
| Outer reviews | RSI + arch + heretic concurrent |
| Gates | `runGatesPool()` up to 8-wide; `try:corpus --parallel` |
| Inner grind | Sequential; `grow:agent-loop` exits after 1 prompt |
| Worktree grind | `grind:worktree-loop` exists but paused |

**Orchestration pattern:** Opus critic + Composer executor (correct split); in-place grind
collides with interactive sessions.

### Verification & ledger

- **~150 gates** including adversarial stack (Jun 17 wave):
  - `verify:invariants` (~4800 checks)
  - `verify:wrong-edit-caught`
  - `verify:engine-diff-fuzz`
  - `verify:oracle-backed`, `verify:negative-control`
  - `verify:grow-predictions`
- **`verify:quick`:** ~5–8s pre-push (typecheck + 40 gates + parallel corpus)
- **Ledger:** `evolver/ledger.jsonl` — 103 rows; accept-rate last 20 = **100%**
- **`loop-health`:** 0 open checklist items; 37 proposals-pending; 5 dirty files (Jun 18)

### Generative objective (designed, not live)

- `evolver:search-wave` + `verify:generative-objective` proof slice exists
- Golden-gated search found nothing new; generative move-space not yet the live loop
- Formal problems in `formal-problems/` (04-generative-objective-nonemptiness.md)

### Agentlogs (anim-workbench, project_slug)

- 106 sessions (52 Claude, 23 Codex, 31 Cursor), May 31 – Jun 17
- 957 user_message events; 395 operator / 562 subagent dispatch
- Exports written: `/tmp/anim-workbench-human-prompts.md` (349 human-like operator msgs)

---

## 3. Is there a shared loop-core?

**No.**

| Candidate | Status |
|-----------|--------|
| `~/Projects/substrate/packages/loop-core` | Does not exist |
| `ledger-core` | Does not exist (corpus-core, evalcore, claimcore only) |
| `skills/outer-loop/route.py` | Exists (~170 LOC); **zero external callers**; not a loaded skill |
| Cross-repo ports | anim `dreamer-tick.ts`, `heretic-gate.ts` ← hutter scripts (copy, not import) |

**Recommendation:** no shared runtime package until ≥3 live loops share a ledger contract
and deletion probe shows mechanics > trivial wrapper. Steal patterns; copy ports.

---

## 4. What improved last week (Jun 11–18)

### hutter

**Apparatus / meta-loop (biggest theme)**

- **Historian loop shipped** (`0e0d7d7`): codex xhigh read-only mines ledger/history every 2h →
  `analysis/DREAMER-INBOX.md`; Dreamer triages (route 2, prune false positives Jun 17–18)
- **Bus doc corrected** (`d6d0350`): queue/decisions are gitignored; only ledger rides git;
  rsync+verify required after queue writes (META-AUDIT row 2026-06-17)
- **Generative backlog collapsed** into canonical `IDEAS.md` (no shadow duplicate)
- **`dreamer_tick.sh` surfaces idle generative targets** when ACTIONABLE empty
- **loop_health** advisories vs failures split; capacity = high-value util not box count

**Search / compression**

- **Capacity frontier wave** concluded (`a297d1b`): overnight cap cells; row 156–159 ACCEPT
  (B27-CELLS320-MQ-E7 legal capacity gain)
- **fx3 probe line** (`a8d13b9`–`85eac9b`): reproduce winning cmix variant; phase-2 spec;
  RAM/disk-mmap root-cause; probe-3 GREEN
- **QUEUE_015** redirect grinder off tapped capacity to preprocessing
- **Critique refutes quantization pivot** → redirect to fx-transforms
- **Harvest fix** (`7bd18d6`): compress-only bit_exact=PENDING parse failure
- **heretic_audit** wired in eval.py (ACCEPT_HELD on self-dealing)

**Live state (Jun 18):** WAIT_OK — 3/25 boxes busy, ledger row 14m ago, grinder UP.

### anim-workbench

**Verifier moat (biggest theme)**

- **Adversarial testing wave** (`27dd378`–`e441e90`):
  - `verify:invariants` (property-based, 5 invariants trippable)
  - `verify:engine-diff-fuzz` (reference vs VM)
  - `verify:wrong-edit-caught` (Surface 4 — moat catches lies)
- **Geometry unification primitive #1** (`b23a4c7`): `geometry.containsPoint` + consumers
- **In-IR convergence checks** for leibniz + ch8
- **Shrink axis safely exhausted** (`1af46c7`, `25329a2`): dead exports removed under gates
- **`capability:status`** (`cc2f613`): gate-grounded truth index (scene → gates)

**Outer loop hardening**

- **Hourly launchd cadence** (`e5cf5c2`, running-notes Jun 16): skips unchanged tree
- **Heretic lane C** added: Gemini adversarial (3-lab outer loop)
- **`dreamer:tick`** ported from hutter (session-injected, not launchd yet)
- **`dreamer:promote`** classifies proposals (most Scope-C = human-gated, not stuck fuel)

**EoC fidelity wave (product)**

- ch2, ch3, ch5, ch7, ch8, ch9 scenes + geometry-binding oracles
- Heretic F1–F4 closed (cube derivative bound to DRAWN geometry, ch8 FTC mechanism)
- ch6, ch10, ch4 remain (running-notes next session)

**Inner loop status**

- All checklists complete (grind/grow/shrink open = 0)
- `GRIND_PAUSE` held (worktree isolation needed)
- `loop-health`: 100% accept-rate → inner loop is checklist executor, not search
- Latest Opus RSI verdict (Jun 17): "PIVOT — ~100%-accept checklist executor, not search"

---

## 5. Comparative strengths

### Steal from hutter

1. Verifier IS the judge — generation ≠ verification
2. Mechanical actor vs model actor (20 min, $0 plumbing)
3. Tiered truth ladder with noise floors (probe ≠ ratchet)
4. Parking lot + clade-yield crossover
5. Beam-fork on fleet, serial ratchet
6. Heretic clock-driven + ACCEPT_HELD
7. Compress-first / cheap screen before expensive eval

### Steal from anim (for partial-verifier domains)

1. Verifier **stack** not one gate (regression + oracle + adversarial + meta)
2. Tri-lab outer loop (Opus + GPT + Gemini parallel)
3. Files are the prompt (LOOP.md + checklists + brief bus)
4. Shrink HOLD until gates bind
5. `capability:status` truth index
6. Scope-C firewall for high-blast-radius changes

---

## 6. What anim should do (recommendation)

**Primary:** finish EoC fidelity (ch6, ch10, ch4) + registry single-source metafix.

**RSI hygiene (no unpause yet):**

- launchd-harden `dreamer:tick`
- bind `heretic-gate` accept-rate >90% → block mark-done
- `dreamer:promote` triage (don't treat 37 proposals as backlog)

**H2 probe before waking inner loop:**

- 20 trials, worktree-isolated, generative move-space
- Gate: `verify:generative-objective` + scene oracles
- Go/no-go: organic reject rate >10% → unpause `grind:worktree-loop` with N parallel worktrees

**Do not:** build shared `loop-core` package; unpause in-place grind on main; refill checklists
without new move-space.

---

## 8. How the intel loop works

Intel has **no single `LOOP.md`**. RSI is distributed across cron, hooks, skills, and a
sibling harness repo. This is the **partial-verifier + principal-judgment** regime
(`skills/outer-loop/route.py` → `ATTENDED` / `HUMAN_REQUIRED`, not unattended auto-ratchet).

### Architecture (three layers)

```
LAYER 1 — Write-time guardrails (~46 PreToolUse hooks)
  Epistemic, workflow, eval-integrity gates; shadow → warn → block via telemetry

LAYER 2 — Daily outer loop (just daily → tools/daily_update.sh)
  Marks, scoreboard emit, prediction resolve, source_eval, theses rebuild, paper-book sync
  IMPORTANT lane (must not abort) vs SOFT lane (30+ steps, failure-tolerant)

LAYER 3 — Rule evolution (multi-step, operator-gated)
  /propose-rule → cohort design → intel-harness eval → operator activation only
```

### Verifier setup (three regimes)

| Regime | Mechanism | Examples |
|--------|-----------|----------|
| **Clean / mechanical** | DuckDB views, pytest, schema lints, `healthcheck.py` | PIT joins, `[DATA]` claims, paper-book marks |
| **Partial / bounded** | 10-stream sweeps, agent-judged claim resolution, cross-model critique | `/disqualify`, substack claims, DD memos |
| **Principal / taste** | Operator approval (Constitution Law 6) | Rule promotion, sizing, activation |

**Entity / claim verification:**

- `/disqualify` / `/confirm`: 10 parallel researcher subagents → `sweep_orchestrator.py`
  aggregates CLEAN | MIXED | FLAGGED (or CONFIRMS | NEUTRAL | DISCONFIRMS)
- `mcp__research.verify_claim` before entity files
- `tools/source_eval.py` — price-resolvable auto; binary manual
- `tools/resolve_extracted_claims.py` — ±2% → PARTIAL (goal-sense tolerance)
- **Thesis graph MCP: advisory only** — not a verdict gate

**Constitution v2.1 (Jun 11):** Law 3 reframed around **breakeven** + `prob_margin` — Knightian
honesty vs point-EV theater (`tools/lib/trade_vocab.breakeven_p`).

### Rule evolver lifecycle

Documented in `intel/.claude/rules/rule-evolution-pipeline.md`:

```
Candidate → Proposed → Eval-tested → Active → Archived
docs/rules/_registry/_candidate_*   _proposed_*   _eval_*   .claude/rules/
```

| Step | Tool | Gate |
|------|------|------|
| 1 Generate | `/propose-rule` skill | ≥3 distinct incidents |
| 2 Review | Operator | Cohort JSON ≥6 tickers, ≥2 controls |
| 3 Eval-test | `intel-harness/bin/eval_proposed_rule.py` | Citation ≥75%, control FP ≤30% |
| 4 Activate | **Operator only** | `git mv` to `.claude/rules/`; Law 6 |
| 5 Archive | `fleet_review.py` | DARK/DECIDE/DEAD CODE hooks |

**Admission control:** Rule of Three, search-existing-first, one-in-one-out (Law 6),
measure-before-promote for hooks (shadow→warn→block).

**Ledgers (multiple, domain-specific):**

- `analysis/paper_book/decisions.jsonl` — trade decisions (v2 vocab)
- `tools/prediction_tracker.py` — falsifiable predictions + market resolve
- `datasets/sources/claims.csv` — source calibration
- `.claude/hook_telemetry/*.jsonl` — hook fire rates
- `analysis/failure_modes/registry.jsonl` — cross-session failure registry
- Git history + `docs/rules/_registry/_archived/INDEX.md` for rules

### Scoreboard loop (what actually closes)

Unlike harness fitness (aspirational), the **scoreboard is live**:

- `posttool-stamp-to-scoreboard.py` → `tools/scoreboard_emit.py` at **write-time**
  (decoupled from fragile daily pipeline ordering)
- `tools/weekly_scoreboard.py` → `analysis/paper_book/scoreboard/2026-W*.md`
- Market resolve: `prediction_tracker.py resolve`, `source_eval.py resolve`
- `healthcheck.py:check_resolve_loop_liveness` in daily cron

**Diagnosis (harness fitness doc):** optimize **outcome-time** (market resolve), not
write-time hook compliance. Hooks are guardrails, not the fitness target.

### Parallelization

| Parallel | Serial / blocked |
|----------|------------------|
| `/disqualify` 10 streams → 10 subagents | No parallel parquet loads (OOM) |
| DuckDB MCP max 2 parallel queries | `orchestrator.py` sequential only |
| | Cost gate: >$3 API needs operator approval |

**Models (`docs/compute_routing.md`):** Opus 4.8 max for conviction + adversarial sweeps;
GPT-5.5 xhigh cross-family critique; Grok/Gemini Flash for volume verify/extract.

### What works vs aspirational (intel)

**Works:** daily resolve + scoreboard emit; rule-evolution docs + propose-rule; eval
pre-flight gate (Jun 14); Constitution v2.1 breakeven; parallel DD sweeps; paper-book →
harness feed in daily cron; hook telemetry framework.

**Aspirational / blocked:**

- Harness as fitness function — needs surrogate-validity gate (LOCKED, no mature forward data)
- Absolute harness residuals — **bent ruler** (May 31): only **paired deltas** citable
- Hook fleet ablation — 46 gates, harness `hooks_exercised=false`
- Powered rule activation N≥96 — latest run N=43, CI includes 0
- Stranded DD → entity journals (`d2d56d37` plan deferred)
- In-chat conviction flip gate — instruction-only; unevidenced-flip on persisted diffs only

### Last week (intel, Jun 11–18)

- Constitution **Law 3 v2.1** — breakeven + prob_margin on entities
- **Eval pre-flight gate** registered (`7b831f9c`) — trace-audit before eval runs
- Paper-book IBKR duckdb isolation — fixes silent portfolio clobber
- Memory path validator in daily soft lane
- Skill budget trim + restore deliberate-invoke set
- Generator sharpen: `decompose-the-headline-number` (BG2 bull-side mirror)
- Validator `--strict` noise reduction (59→24 expected-dead)

---

## 9. intel-harness — verifier setup & rule-evolver substrate

**Sibling repo:** `~/Projects/intel-harness/` — sealed point-in-time replay of intel's
markdown rule fleet against ~566 Jan–May 2026 entity decisions. **Not live trading.**
**Not hook execution** (unless separate hook-aware mode built).

### How it connects to intel

| Intel | Harness |
|-------|---------|
| `.claude/rules/` | Snapshotted per-case via `src/rule_fleet.py` |
| `intel.duckdb` | `src/duckdb_timewall.py` (date<T injection) |
| git commit as-of-T | `src/resolve_intel_commit.py` → `src/point_in_time.py` |
| `paper_book/decisions.jsonl` | `bin/resolve_paper_book.py` → forward residuals |
| `rule-evolution-pipeline.md` | `bin/eval_proposed_rule.py` (Step 3) |

**Live entry path** (README stale — no `bin/harness`):

```bash
bin/walk_forward_runner.py → bin/aggregate_walk_forward.py
                          → bin/analyze_paired_cell.py   # primary metric
```

### Verifier stack (stacked layers)

```
1. Evidence fetch verifiers (src/verifiers.py)
   Every broker fetch → verifier_kind + verifier_handle proving pre-T
   duckdb_timewall | sec_accession | price_feed_date | wayback_snapshot

2. Verdict schema (src/verdict_schema.py)
   Validates agent verdict.yaml

3. Instrument battery (src/instrument_power.py)
   control() → BIASED / EQUIVALENT / UNDERPOWERED
   power() → planted-alpha detection
   leakage() → sector concentration sentinel
   CLI: bin/instrument_power_check.py

4. Residual oracle (src/factor_residual.py)
   Two-factor shrunk residual vs SPY + sector bench
   Absolute residuals GATED; paired deltas LICENSED (bias cancels)

5. Citability gates
   Rule activation: N≥96, ≥5 clusters, CI excludes 0
   Surrogate validity (src/surrogate_validity.py): LOCKED — no mature forward data

6. Thesis-event verifier (src/thesis_verifier.py)
   Scores reasoning vs return (SKILL/LUCK/UNLUCKY/DESERVED-MISS), not raw P&L

7. Proposed-rule eval (bin/eval_proposed_rule.py)
   ≥6 cohort names, ≥2 controls; citation ≥75%; control FP ≤30%

8. Cost gate (bin/walk_forward_runner.py)
   Requires --max-total-cost-usd (Constitution >$3 gate)
```

### Rule evolver (harness side)

**LOOP doc:** `docs/roadmap_rule_evolution_loop.md` (4 epochs, kill criteria).

**Fleet testing beyond single-rule eval:**

- Ablation configs: `configs/branch_registry.yaml` (MINIMAL_FLEET, FULL_CURRENT, etc.)
- **Mode 1 (PIT):** rules must predate T — **degenerate** for current fleet (~9-day window)
- **Mode 2 (`--rules-from-head`):** today's rules on past T — **negative screen only**
- **Paired ablation:** only clean fleet-alpha test: `bin/analyze_paired_cell.py`

**Latest powered cell (2026-06-10):** metabolic-bottleneck-prior paired ablation

- N=43 pairs, delta −0.31pp, CI includes 0 → **UNDERPOWERED**
- `citable_for_rule_activation: false` (N<96)
- Operator: **harness new spend STOPPED**

**Authority asymmetry:** auto-demote/quarantine maybe someday; **promotion stays
operator-manual forever** (roadmap §3).

### Cohort generators (harness `bin/`)

| Script | Pattern |
|--------|---------|
| `sample_objective_universe.py` | Stratified sample from duckdb (sector×mcap) |
| `partition_cohort.py` | IS/OOS by ticker overlap with rules corpus |
| `build_targeted_cohorts.py` | Theme-listed / BUY-rich names |
| `sample_regime_flip_cohort.py` | 2022 drawdown negative control |
| `count_rule_assay_triggers.py` | Cheap pre-dispatch capacity counters |

Rule **generation** lives in intel (`/propose-rule`); harness only **evaluates**.

### What works vs broken (harness)

**Works (412/413 tests):** sealed Claude dispatch; multi-pass request-then-judge; PIT commit
resolution; factor-residual + clustered bootstrap; paired-cell analyzer; paper-book resolver
in intel daily cron; instrument power framework.

**Broken / blocked:**

- 1 failing test: fleet taxonomy drift (14 hooks in tagging doc missing on disk)
- Surrogate gate LOCKED
- Latest activation cell UNDERPOWERED
- Absolute residuals unlicensed (`absolute_residual_trustworthy=False`)
- Mode 1 eval degenerate for current fleet
- New harness spend STOPPED (operator 2026-06-10)
- gpt-5.5/codex backend: 0/2 BUY agreement vs Opus on consistency cell

---

## 10. research repo — generator collection

**Separate system.** "Generators" here = **reusable divergence prompts** for immigration-fiscal
research (mechanical "what to ask next" with retrodiction + negative-space fields).

**Not wired** to intel's `generator_library.md`, intel-harness, or rule-evolver. Conceptual
sibling to intel's `/extract-generators` flow (same leverage-skill meta-pattern).

### Collection pipeline

```
Acquire PDFs/CSVs (infra/immigration-fiscal/acquire/setup-lifetime.sh)
    ↓
Agent mine clusters → research/.mining/immigration-lifetime-*.json
    ↓ (parallel: mine_restrictionist_full_claims.py for corpus parse)
build_lifetime_evidence_warehouse.py
    ↓
warehouse/immigration_lifetime_evidence.duckdb
    ├── lifetime_generators (104 rows)
    └── parameter_claims (563 claims)
    ↓
Human registry: research/immigration-lifetime-fiscal-generators.md (106 G-LIF-* headings)
```

**Rebuild command:**

```bash
cd ~/Projects/research/infra/immigration-fiscal
bash rebuild_lifetime_warehouse.sh
```

### JSON schema (per cluster, from diverge cookbook §A4)

Targets per cluster: **6–10 claims, 4–5 generators, 3 theories**.

```json
{
  "parameter_claims": [...],
  "generators": [{
    "id": "G-LIF-...",
    "name": "...",
    "prompt": "...",
    "retrodiction": "...",
    "negative_space": "...",
    "topics": [...],
    "source_rel_paths": [...]
  }],
  "theories_tested": [...]
}
```

**19 clusters (A–S):** NPV, labor, local/welfare, composition, housing, high-skill, legal/tax,
refugee, return migration, admin, incidence bridge, OECD/health, annual↔NPV bridge, school
units, welfare/political, restriction admin, stock/flow denominators, full ledger, restrictionist
steelman.

### Quality gates (meta-framework)

From `~/Projects/skills/leverage/references/generators.md`:

1. Cluster miss-patterns (not one generator per paper)
2. Retrodiction ≥2 prior findings
3. Negative-space field required
4. Consumption path (DuckDB test or explicit data gap)
5. Park after two dry applicable cycles; retirement manual

### Sweep protocol (how a round runs)

1. Carry prior thesis + generator menu + DuckDB state
2. **XDISC preflight** (`immigration-thesis-generator-audit-2026-06-16.md`) — force non-fiscal divergence
3. Diverge: URL probe → acquire → parallel mine → `.mining/*.json`
4. Rebuild warehouse → `lifetime_generators`
5. Append new `G-LIF-*` to human MD registry
6. Converge: unified theory, 5-model critique, 3 disconfirmation hunts
7. Review: model-review packets; running-fixes log
8. Yield accounting (manual, not built): which generators fired / adopted / dry

### Last week (research, Jun 11–18)

- `c703f91` (Jun 12): infra wired — `build_lifetime_evidence_warehouse.py` + acquisition
- `f3abecd` (Jun 16): `immigration-thesis-generator-audit-2026-06-16.md` (XDISC packet)
- `52918c1`: routed generator audit through index, cookbook, sweep protocol
- `fd4ff16`: knowledge delta agent loop codified

**Known drift:** MD has 106 headings; DuckDB has 104 rows (G-LIF-Q06, G-LIF-S15 MD-only).
No lifecycle sidecar yet (`status`, `last_fired`, `adopted_outputs`).

### intel generators (different artifact)

Intel has its own generator system:

- `memory/generator_library.md` — SQL/backtestable screens
- `/extract-generators` skill — mines miss-patterns into reusable prompts
- `thinking_prompts.md` — non-SQL meta-moves
- Jun 11: sharpened `decompose-the-headline-number` for BG2 orbital economics theme

Same **meta-pattern** as research (retrodiction, cluster, park) — different domain, no code link.

---

## 11. Four-way comparison

| Dimension | hutter | anim | intel | intel-harness |
|-----------|--------|------|-------|---------------|
| **Verifier regime** | Clean | Partial | Partial + principal | Offline surrogate |
| **Auto-ratchet** | Yes (bytes) | No (100% accept) | No (operator activates rules) | No (operator only) |
| **Inner search** | Live | Paused | `/propose-rule` + hooks | Sealed replay |
| **Outer loop cadence** | 20m actor + 30m Opus | Hourly launchd | Daily cron + weekly scoreboard | On-demand (spend STOPPED) |
| **Parallelism** | Hetzner fleet | Gate pool 8-wide | 10-stream DD subagents | Cohort generators only |
| **Ledger** | SQLite | JSONL | paper_book + predictions + telemetry | results/v1/ + resolutions |
| **Best steal** | Mechanical actor, tier ladder | Verifier moat stack | Scoreboard at write-time, hook telemetry | Paired deltas + instrument battery |
| **Main gap** | Bus rsync manual | Inner loop not search | Harness authority unearned | Surrogate LOCKED, N too small |

**research generators:** thesis-space divergence tooling; not an RSI loop; valuable for
**consumption-path discipline** (generator → DuckDB test → park if dry).

---

## 12. Role pattern (documented, not packaged)

```
Proposer → Runner → Verifier → Auditor → Accept-gate → Ledger
```

| Role | hutter | anim | intel | intel-harness |
|------|--------|------|-------|---------------|
| Proposer | Opus + queue | Opus outer-loop | `/propose-rule` | (intel-side only) |
| Runner | GPT-5.5 on box | Composer (paused) | DD subagents | `walk_forward_runner` |
| Verifier | eval.py | verify:* | hooks + market resolve | instrument battery + paired cell |
| Auditor | heretic_audit | heretic-gate | cross-model critique | thesis_verifier |
| Accept-gate | greedy bytes | conjunctive (soft) | **operator** (Law 6) | N≥96 + CI (blocked) |
| Ledger | SQLite | JSONL | paper_book + telemetry | results/ + resolutions |

Closest shared artifact: `skills/outer-loop/scripts/route.py` — maps clean → UNATTENDED,
partial → ATTENDED, gate-edit → HUMAN_REQUIRED. Tested, **zero external callers**.

---

## Appendix: key paths

### hutter
- `LOOP.md`, `OUTER-LOOP.md`, `HERETIC.md`, `META-AUDIT.md`, `IDEAS.md`
- `scripts/eval.py`, `scripts/heretic_audit.py`, `scripts/dreamer_tick.sh`
- `scripts/historian-loop.sh`, `scripts/loop_health.py`
- `ledger.db` / `ledger-dump.sql`

### anim-workbench
- `evolver/LOOP.md`, `evolver/OUTER-LOOP.md`, `evolver/HERETIC.md`, `evolver/FITNESS.md`
- `scripts/outer-loop-review.sh`, `scripts/dreamer-tick.ts`, `scripts/heretic-gate.ts`
- `scripts/loop-health.ts`, `scripts/dreamer-promote.ts`
- `evolver/ledger.jsonl`, `evolver/outer-loop-models.json`
- `docs/running-notes.md`

### intel
- `.claude/rules/rule-evolution-pipeline.md`
- `.claude/skills/propose-rule/SKILL.md`
- `tools/daily_update.sh`, `tools/scoreboard_emit.py`, `tools/weekly_scoreboard.py`
- `tools/prediction_tracker.py`, `tools/source_eval.py`, `tools/fleet_review.py`
- `analysis/paper_book/decisions.jsonl`
- `docs/compute_routing.md`
- `analysis/eval_harness/HARNESS_README.md` (local MVP ablation)

### intel-harness
- `docs/roadmap_rule_evolution_loop.md` (the LOOP)
- `docs/target_architecture_harness_as_fitness_function.md`
- `docs/findings_2026_05_31_benchmark_bias.md` (bent ruler)
- `bin/walk_forward_runner.py`, `bin/analyze_paired_cell.py`, `bin/eval_proposed_rule.py`
- `bin/resolve_paper_book.py`, `bin/instrument_power_check.py`
- `src/verifiers.py`, `src/instrument_power.py`, `src/surrogate_validity.py`
- `configs/branch_registry.yaml`, `results/v1/paired_metabolic_2026_06_10/`

### research (generators)
- `research/.mining/immigration-lifetime-*.json` (22 cluster artifacts)
- `research/immigration-lifetime-fiscal-generators.md` (G-LIF-* registry)
- `research/immigration-thesis-generator-audit-2026-06-16.md` (XDISC)
- `notes/immigration-lifetime-synthesis-diverge-cookbook.md`
- `infra/immigration-fiscal/build/build_lifetime_evidence_warehouse.py`
- `warehouse/immigration_lifetime_evidence.duckdb`

### agent-infra
- `decisions/2026-06-16-loop-core-rsi-ledger-factoring.md` (proposed; no package built)
- `skills/outer-loop/` (route.py only; not deployed)
- `skills/leverage/references/generators.md` (meta-framework shared by research + intel)
