---
title: Critique / Decide Eval Strategy — What to Measure, What Exists, What's Novel
date: 2026-06-14
tags: [critique, decide, eval, verifier-conditioned, goal-drift, code-review]
status: complete
---

# Critique / Decide Eval Strategy

**Question:** Is the proposed multi-track eval (bugs + premises + design proxies) the right way?
Given subsidized orchestrator tokens, what should `/eval` in `Projects/evals` actually run?

**Bottom line:** **Don't build a new critique eval from scratch.** You already have
`evals/critique_replay/` — a preregistered, gold-backed instrument that matches published
prior art (SWE-PRBench, SWRBench, Martian). Extend it; calibrate against SWE-PRBench; add a
**delayed-outcome** track for design. Split `critique_efficiency/` into bug-routing only or
merge it into `critique_replay` full grid.

---

## What the literature says (2025–2026)

| Source | Claim | Implication for us |
|--------|-------|------------------|
| **SWE-PRBench** (arXiv:2603.26130, Foundry 2026) | 350 real PRs, human review comments as gold; no model >31% detection; **more context → worse** | Run our arms on their harness as calibration; keep packets **small** |
| **SWRBench** | 500 buggy + 500 **clean** PRs | Invention rate requires known-clean packets — `critique_replay` already has 5/12 clean |
| **Martian code-review-benchmark** | Incomplete gold inflates precision | K2 probe **fired** — gold expanded mid-run (see `critique_replay/outputs/probe/PROBE-RESULTS.md`) |
| **Bean et al. 2025** (construct validity) | 48% of benchmarks measure contested constructs | **Don't eval "better design" as one scalar** — decompose into checkable sub-constructs |
| **Feuer et al. 2025** (LLM-as-judge) | Factor collapse r>0.93 across rubric axes | Design "elegance" judges are noise; use **deterministic predicates** + delayed outcomes |
| **Vendrow 2025** (reliability) | >50% failures on saturated benches = label noise | Gold must be platinum (session-verified traps) — `critique_replay` cases.md standard |

Prior art sweep already in `evals/research/2026-06-12-prior-art-three-instruments.md` — verdict:
**BUILD-WITH-CONTROLS-FROM(SWE-PRBench, SWRBench, Martian)** for review replay; your
process-trap taxonomy (phantom plan joins, dead targets) is **genuinely uncovered** — keep building
there, not a parallel instrument.

---

## Three verifier regimes (maps to constitution)

### 1. Clear verifier — RUN THIS

**What:** Bug detection, premise falsification, injected defects.

**Instrument:** `evals/critique_replay/` (N=12, screening) + `evals/cross_lab_review/` (injected Python defects).

**Metrics (already preregistered):**
- Primary: anchor detection rate per stratum
- Co-primary: invention rate on clean packets
- Disqualify: >1 invention/clean packet

**Probe results (2026-06-13):** Cases discriminate. `gpt55-med` ≈ `gpt55-high` on detection;
`flash35` disqualified at probe (2 inventions on K2). **Action:** finish full grid before routing
changes; do not promote `critique_efficiency` arms until this completes.

**Add:** Run `standard` preset (2G+2GPT overlapping) as a **new arm** on same 12 packets — compares
dispatch shape without new gold.

### 2. Partial verifier — DELAYED + STRUCTURAL PROXIES

**What:** "Better design given goals" — elegance, unification, scalability, robustness.

**Do NOT:** Single LLM judge on "design quality 1–10."

**Do:**

| Proxy | Measurement | Lag |
|-------|-------------|-----|
| **Structural checklist** | Dual paths, unnamed compat layers, missing scope block, no consumer named | At review time (grep + rubric) |
| **Supervision replay** | Human correction in agentlogs — did review mention that class? | Weeks (label once) |
| **Outcome** | build-then-undo, revert, re-litigation of same decision | 30 days post-ship |
| **Goal alignment** | Contradicts live `decisions/` entry or GOALS.md axis | At review time |

**Instrument to build:** `evals/critique_outcome_link/` — 15 historical plans with known outcome
(ship+stable vs reverted). Gold = "issue that caused revert" (human-labeled once). Metric: did
any review axis mention it? (Same machinery as critique_replay, different gold source.)

**Goal drift:** Not predicting taste evolution — detecting **wrong objective** (elegance vs RSI).
Proxy: rising contradiction rate between session recommendations and `decisions/` + GOALS.md;
`supervision_taxonomy` over_caution vs autonomy vector. Already in GOALS.md §Goal-Drift Detection.

### 3. Principal — NO LEADERBOARD

Taste, conviction, final architecture pick → human is verifier. Eval measures **option contrast**
(decision density per human turn), not whether the model picked right.

`/decide` eval subset: **premise packets only** (grep-verifiable). Skip design winner-takes-all.

---

## What to do with existing evals repo artifacts

| Path | Status | Action |
|------|--------|--------|
| `critique_replay/` | Probe done, full grid pending | **Primary** — finish full run; add `standard` 4-axis arm |
| `critique_efficiency/` | Draft prereg | **Merge** into critique_replay as dispatch-shape arms OR narrow to bug-only, drop orchestrator token objective |
| `cross_lab_review/` | Composer arm done | Keep for defect-class calibration |
| `pareto_frontier_pilot/` | Design only | **Different question** (iteration × model tier) — not critique routing |
| `divergence_bakeoff/` | NoveltyBench substrate | `/decide` diverge phase only, not critique |
| `evalcore` + `/eval` skill | Ready | Use `assert_blind`, `leakguard`, Wilson CI, McNemar — don't re-derive |

---

## Orchestrator cost is subsidized — reframe eval objective

Drop orchestrator token minimization from `critique_efficiency` primary metric. Optimize:

1. **Verified recall** (detection − invention)
2. **Human supervision avoided** (supervision-replay label)
3. **External cosigner $** only when comparing +composer / +formal arms

---

## Recommended `/eval` agent task list

1. **Finish `critique_replay` full grid** (preregistered, probe passed).
2. **Add arm:** `model-review.py --axes standard` on same 12 packets.
3. **Calibration run:** SWE-PRBench config_A on gpt55-med vs gpt55-high (external anchor).
4. **Scaffold `critique_outcome_link/`** — mine 15 revert-linked plans from git + improvement-log.
5. **Defer** design-elegance judge eval indefinitely (literature says factor collapse).

---

## Cursor skill parity (fixed 2026-06-14)

`~/.cursor/skills/` now symlinks `research`, `eval`, `critique`, `decide`, etc. via
`scripts/cursor-skills-sync.sh` (also in `friend-sync`). Cursor CLI does not read
`~/.claude/skills/` — separate mirror required. `cli-config.json` unchanged; skills are
filesystem-discovered under `~/.cursor/skills/`.

---

## Sources

- `evals/research/2026-06-12-prior-art-three-instruments.md` (internal, Exa sweep)
- `evals/critique_replay/PREREGISTRATION.md` + `outputs/probe/PROBE-RESULTS.md` (internal, measured)
- `agent-infra/research/benchmarking-science-2026.md` (internal)
- `agent-infra/GOALS.md` §Goal-Drift Detection (internal)
- Kumar 2026, SWE-PRBench, arXiv:2603.26130 [A]
- Feuer et al. 2025, arXiv:2509.20293, LLM judge factor collapse [A for judge skepticism]
