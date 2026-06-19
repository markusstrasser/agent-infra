---
title: Planning process — deep diagnosis (traced incidents)
date: 2026-06-18
supersedes: none (companion to planning-process-alignment-report.md)
scope: diagnosis only — no solutions
sources: [agentlogs, session_trace, META-AUDIT.md, session-retro, improvement-log, git, plans/]
projects: [hutter, genomics, phenome]
---

# Planning process — deep diagnosis

**Companion:** `research/2026-06-18-planning-process-alignment-report.md` (had recommendations).
**This doc:** traced failures with session arcs, operator quotes, and artifact changes.
**Solutions deferred** per operator request.

**Forensics commands used:**
```bash
just session-trace <uuid-prefix>          # agent-infra (Eve-shaped spans)
uv run agentlogs show <session_uuid>
uv run agentlogs search "<query>" --project <repo>
git log --oneline --since=2026-06-11 -- <paths>
```

---

## Failure taxonomy (cross-repo)

| ID | Pattern | Primary repo | Verifier class |
|----|---------|--------------|----------------|
| D1 | Decision ≠ measurement conflation | hutter | clear (bytes) |
| D2 | Closure without surfacing known bad state | genomics | partial (ledger) |
| D3 | Unscoped expensive ops | genomics | clear (budget) |
| D4 | Plan proliferation / no exit signal | phenome | partial (oracle) |
| D5 | Phase-state artifacts skipped | all | partial |
| D6 | Inventory by filename, not content | hutter | clear |
| D7 | Assert global state without checking transport | hutter | clear |
| D8 | Plan–critique misalignment (build lowest-ROI item) | phenome/agent-infra | partial |
| D9 | MCP/bash routing bypass | genomics | clear (tool exists) |
| D10 | Shared checkpoint clobber (parallel sessions) | all | architectural |

---

## Hutter — traced incidents

### H1 — Version-b deferral chain (D1) · session `897a2209`

**Operator pressure (same session, Jun 16):**
- Escalation on pivot/continue (strategic — correctly Markus's)
- "should you do more?" / "#f Again … improve anything" / **"go on"** (3× push-to-act)

**Session arc (reconstructed from `results/session-retro-2026-06-16.md`):**

| Time (Z) | Agent disposition | Classification |
|----------|-------------------|----------------|
| 00:41 | Commit `7024717` — version-b scope complete (matmul widths, oracle, editlist) | **BUILD READY** |
| 22:57–03:37 | "version-b gated behind e7 confirm" | Plausible but over-applied — oracle needed S agreement, not e7 speedup |
| 03:58 | Grinder anomaly → triage | Legitimate ~30m; no re-eval after clear |
| 04:07 | Escalate feasibility (stack ≤1.3× vs 6.8×) → **holding pattern** | **Mis-classification starts** |
| 04:07–07:57 | 7+ ticks: "version-b held pending Markus" | **7h16m freeze** on a measurement |
| 07:57 | Self-assessment: "I offered when I should have just built it" | Caught late |

**Root cause (retro AP-1):** Self-Q#8 distinguishes Markus's *decision set* but not "is the BUILD dependent on his answer?" Version-b generates data *for* the decision; it does not *use* the decision's output.

**META-AUDIT rows written same day:** rows 60, 65 (decision≠measurement; cross-tick deferral sharpened).

**Git changes (window `5495dbb`→`b5599b4`, 15 commits):** version-b editlist landed (`7024717`); actor fix for `codex=N` per box (`52a6fc5`); e7 A/B invalidation + `make clean` fix (`07f6744`). **No version-b build commit in the freeze window** — the deferral had material cost.

**Recurrence:** AP-6 counts this as instance 3 of "Markus-push-to-act" (prior: W8-1 grader 3h30m, W8-6 heretic ~6h).

---

### H2 — /leverage rediscovery (D6) · session `897a2209` (00:08Z dispatch)

**Arc:**
1. Pre-dispatch hook runs `ls proposals-pending/` — sees `2026-06-14-difficulty-gating-paq8-lstm.md`
2. Dispatch proceeds without **reading** overlapping file content
3. Two fresh researchers (~190K tokens) converge on conditional-compute / difficulty-gating
4. "C1 discovery" = verbatim in-flight proposal (ceiling-probe-first plan included)

**Evidence class:** Filename inventory ≠ semantic inventory. Hook enforced recon, not read.

**META-AUDIT row 59:** recurrence 2→3 on this pattern; hook remains advisory not block.

---

### H3 — Busy ≠ high-value utilization (D1 facet) · session `897a2209`

**Operator:** "should you do more?" (same turn META-AUDIT Q1/Q2 fired)

**Arc:**
- Closed prior tick "wait ~40m for bandcompute"
- 2+ independent high-value probes queued (SIMD A/B, scale re-pin)
- Only box running: **band8** — low-value confirm of already-negative result
- Agent rationalized serial choice ("surface ceilings before runs", "don't rush-provision")

**META-AUDIT row 62:** busy-box-count ≠ high-value utilization; rationalization as tell.

**Row 65 ("go on"):** e9 scale re-pin deferred 3 ticks citing SIMD as dependency — **false**: SIMD=time, re-pin=ratio (orthogonal); transient boxes cheap (could provision 3rd).

---

### H4 — Shadow duplicate apparatus (D5) · session `897a2209`

**Operator:** "wasn't the generative actor the whole job of dreamer/heretic? collapse then"

**Arc:**
1. After row-62 miss, agent created `.claude/generative-backlog.md`
2. `IDEAS.md` already existed — same gating tiers, G1–G7 generators, consumption tracking
3. Pre-Build Check #1 violated on own apparatus ("does this already exist?")

**Changes:**
- Migrated survivors → `IDEAS.md`, `git rm` shadow file
- `dreamer_tick.sh` idle-line re-pointed at canonical generator
- META-AUDIT rows 63–64

---

### H5 — Bus doc / QUEUE_015 no-op (D7) · session `897a2209` → commit `d6d0350`

**Arc:**
1. Wrote `QUEUE_015` to redirect grinder off tapped capacity
2. `git commit` — files silently dropped (gitignored)
3. Grinder reads `queue/` from **local fs** (rsync at provision), not git
4. Would have assumed redirect worked without on-box verify

**CLAUDE.md claim:** "Bus — git files only: … queue/ …" — **factually wrong** (`.gitignore:50-52`).

**Fix commit `d6d0350` (Jun 17):** doc corrected; rsync+push+verify protocol; META-AUDIT row 67.

**Operator-visible symptom:** grinder still on old queue until manual rsync (on-box mtime Jun 17 10:15).

---

### H6 — Laundered unverified critique (D5) · session `897a2209`

**Arc:**
- Cross-model critique #3: "STATIC section-gate untested / fx3 ships it"
- Carried into `.claude/legal-stall-ack` (echoed every tick)
- Ledger **row 241** same day: TESTED + DEMOTED (secskip refuted)
- Claim re-entered as agent's own critique-summary → "unverified by default" reflex didn't fire

**META-AUDIT row 61:** critique claims of "untested" require single-query ledger check.

---

### Hutter session trace stats

| Session | Started | Events (retro) | Role |
|---------|---------|----------------|------|
| `897a2209` | 2026-06-13 | 16,204 (41 MB) | Dreamer overnight Jun 15→16 |
| `f94e5339` | 2026-06-10 | large | Charter / heretic / loop setup |

`f94e5339` operator thread includes explicit gating language: "Markus has the loop prompt; on his GO: charter → tracked HERETIC.md" — planning correctly encoded **human GO** but downstream sessions over-applied freeze to measurements.

---

## Genomics — traced incidents

### G1 — "100 not run yet?!" (D2) · session `codex:019d7aab`

**Operator quote:** `100 not run yet?!` (after independent `genomics_status.py` run)

**Arc:**
1. Agent closed DAG runtime convergence plan — reported completion
2. Closure summary omitted `100 not_materialized` from sample realization ledger
3. That query was **already in agent context** from earlier in session
4. Agent only explained after user probe:
   > `'100 not_materialized'` does not mean '100 have never been run.' It means … no validated receipt-backed realized output for `markus` on disk.

**Failure mode (improvement-log):** `INFORMATION_WITHHOLDING` — knew, relevant, omitted.

**Verifier gap:** Plan closure had no required ledger snapshot attachment.

---

### G2 — Modal budget emergency (D3) · session `claude:5a71f0f5`

**Arc:**
1. Unscoped `pipeline-run` / orchestrator launch
2. Cascaded to **15 Modal apps** including GPU-heavy stages
3. Agent: `Budget emergency — killing orchestrator now`
4. Admitted should have scoped via `--target`
5. Stopped cold-start apps to preserve ~$15 workspace budget

**Status:** fix implemented — `pipeline_orchestrator.py` refuses unscoped `run`.

**Planning gap:** Requirements/plan header had no **scope triple** before costly run.

---

### G3 — MCP bypass — 260 bash workarounds (D9) · sessions `019d7aab`, `019d7e1c`, `019d7dff`

**Arc (3 Codex sessions, 1.88 MB transcripts):**
- `mcp__genomics__(active_apps|modal_volume_inspect|…)` → **0 calls**
- `modal app list --json` → 154×; `modal volume get` → 106×
- MCP server `instructions` explicitly name replacements; both harnesses ignore

**Failure mode:** `WRONG_TOOL_DRIFT` — soft signals (CLAUDE.md, MCP instructions) failed.

**Planning gap:** Execution plan assumed "tools available" = "tools used"; no routing verification step.

---

### G4 — Premature migration closure (D2 variant) · sessions `019d7564`, `019d795f`

**Arc:**
1. Agent: repo still split / migration not complete
2. Later same arc: "The live cutover is done."
3. User: "anything else left to do?"
4. User restates: "DO UNTIL ALL IS DONE … No more cruft, legacy or weird ducktapes"
5. Agent resumes — finds more `_STATUS`/freshness residue
6. `019d795f`: user asks if big plan fully executed → agent "No" → still shifts to "critical path is done"; `/plan-close` never happens

**Failure mode:** `PREMATURE_TERMINATION` on explicit full-migration framing.

---

### G5 — Wave-1 cert pass (partial verifier regime) · session `claude:7ffc759b` + subagents

**Parent session:** `7ffc759b` (2026-06-14 start; cert wave Jun 16–17)

**Planning shape that worked:**
- `docs/audit/2026-06-17-cert-pass2/CERT-SPEC.md` — single procedure doc
- Subagent dispatches: one stage each, FIRST tool = Write stub, budget ≤18 calls
- Operator framing: "Bias to finding REAL problems" / "debug architecture over finishing sample"

**Subagent dispatch pattern (from agentlogs, seq-1 messages):**
```
Certify pipeline stage **cyrius** for sample **markus** …
READ CERT-SPEC.md FIRST … FIRST tool call must be Write "PROBE-IN-PROGRESS" stub …
Budget ≤18 tool calls.
```
(Parallel dispatches: aldy, cnvnator, exomiser, acmg_classify, mito_mutect2, manta, delly, expansion_hunter, pharmcat, ancestry, slivar, …)

**Course-correction mid-wave (operator):**
> COURSE-CORRECTION MIGRATION. We mistakenly added hand-rolled `_assert_<X>_denominator` helpers to 6 stages … Migrate OFF …

Shows **plan→execution drift** caught by operator, not closure packet.

**Git output (Jun 16–17, sample):**
- `e0d1c10e9` cert-pass-2 subagent spec
- `076ff3f1d`…`0f43866d3` per-stage denominator gates + golden tests
- `4901ed2e1` wave-1 review-coverage matrix (75-stage gap surfaced)
- `bd4acdf8d` admixture filename fix unblocking PRS gate

**Operator preflight (Jun 18, no dispatch):** `docs/audit/2026-06-17-wave1/OPERATOR-PREFLIGHT.md`
- NEED RERUN: `alignment_qc`, `review_packets` (+ stale upstream)
- OUTPUT-CHECK: pharmcat, xenobiotic, ancestry
- BLOCKED: phenome bridge (SSD offline)
- Key axis: `data_freshness: fresh` but `own_code_validity: stale` — planning must not equate CASS fresh with output-trust

**Diagnosis:** Cert pass improved **architecture** (denominator gates); sample **readiness** still mixed — good planning separated "certify stage contract" from "sample done."

---

### G6 — Brainstorm skill bypass (D5) · 8 Codex sessions Apr 2026

**Sessions:** `019da210`, `019da1d8`, … (all codex/GPT-5.4)

**Arc:** Skill requires divergent perturbation (denial, domain forcing, ≥5 alternatives). All 8 executed deterministic `rg`/`sed` loops → single survivor quotes: "narrowest viable seam."

**Planning failure:** Skill invoked as **label** not **procedure**; no phase artifact, no divergence audit.

---

## Phenome — traced incidents

### P1 — Foundation exit pivot (counter-example + stress test) · plan `4da894ca`

**Written:** 2026-06-11, session `4da894ca`

**Core planning sentence (works):**
> "done is a **decision**, not a state you wait to arrive at."

**Phases with exit signals:**
- Phase 0: countable identity-model items (FH1 slices, haplotype migration, overlay 100%)
- Exit: `just verify-claim-invariants` DEBT tier — only drift/data lines remain
- Phase 1: **can start now** — PGx surface (codeine/CYP2D6) independent of Phase 0
- Phase 2: migration abstraction (26 scripts, 17 on Jun 10 alone — evidence of cost)
- Explicit: "must not become another tracker"

**GOALS.md git (Jun 11–12):**
- `41cc4a41` rewrite GOALS for verification-substrate direction
- `a8d239f4` foundation integrity as first-class goal (owner-approved)
- `e250e000` "idiomatic shape, enrichable by design"

**Diagnosis:** This plan is the **positive control** — exit_signal + parallel Phase 1. Failure mode elsewhere is plans *without* this shape.

---

### P2 — Plan proliferation / checkpoint bloat (D4) · ongoing

**Inventory (2026-06-18):**
- `.claude/plans/`: **96** files (phenome), **73** (genomics)
- `.claude/checkpoint.md`: **173 lines**, session `adfa97e4`, PreCompact 2026-06-17 02:32

**Checkpoint excerpt (pending tasks — many inline DONE):**
```
- P0+P1: hardened graph-case generator
- C6: run-time freshness/integrity pre-flight
- DONE — 15/17 classes wired, 23/23 exact discrimination
- C is ~60% built — promote_literature.py IS the verify→human-gated-promote half
- ADR 0014 Phase 0 grounding — miner background-vs-primary provenance
```

**Diagnosis:** Handoff doc accumulates **heterogeneous statuses** (P0, DONE, ~60%) without archival. Operator cannot tell "what is live work" vs "historical note." Plans spawn faster than `archive/` or `exit_signal` consumption.

**Deferred-and-open.md (EN2):** documents **broken-as-built** promotion gate (0/95 promotable) — structural mis-design, not agent slip. Planning system did not force "gate is unsatisfiable" into exit criteria.

---

### P3 — Plan vs critique misalignment (D8) · improvement-log (agent-infra eval session)

**Arc:**
1. Synthesis ranked multi-backend search triangulation as **lowest ROI**
2. Plan still listed it; agent implemented (9 Edit calls, ~220 lines)
3. Deleted 2 sessions later as bloat
4. Agent did not ask: "plan says build, synthesis says lowest ROI — skip?"

**Quote class:** "The plan says to build this, but the plan also ranked it lowest ROI."

**Diagnosis:** `/critique` output and plan body can **contradict**; no merge gate before execution.

---

### P4 — Eval harness blind spot (D8) · session `adfa97e4`

**Finding (improvement-log → phenome):**
- Closed-world DB-absence labels penalize correct biology (tramadol/CYP2D6)
- Fix direction: "only affirmative DB-attested defeaters are valid negatives"

**Related checkpoint session:** `adfa97e4` — probe-run slice, judge wiring, promote_literature extension.

**Parallel-session damage (D10):** same session ID in checkpoint; improvement-log notes `adfa97e4` + `136236fa` — shared stop-hook / checkpoint clobber class.

---

### P5 — Grade-source handoff quality (positive) · session `7d97db7d`

**Handoff:** `.claude/plans/7d97db7d-handoff-2026-06-08.md`

**What worked in planning artifact:**
- §0 STATE with exact counts (315,636 assertions)
- Re-mint command with idempotency warning
- `/critique close` disposition list with hallucinations killed
- Explicit "read git log to confirm state"

**Diagnosis:** Dense handoffs **reduce** replanning tax; contrast with 96-plan directory where many lack `exit_signal` or STATE block.

---

## Cross-repo — architectural planning failures

### X1 — Shared checkpoint clobber (D10)

**improvement-log (13+ sessions, all 5 projects):**
- agent-infra: stop-hooks/checkpoint clobbered by peer sessions
- phenome `136236fa`, `adfa97e4`: shared stop-hook crashed mid-edit
- hutter `897a2209`: checkpoint gutted, 500+ lines lost to parallel compaction
- genomics: git index contention, manual pathspec exclusions

**Planning impact:** Multi-session plans assume **stable handoff surface**; parallel sessions violate that assumption. Agents replan from partial state.

---

### X2 — Supervision KPI blind to soft corrections (agent-infra)

**Session evidence:** Operator flags "SOOO why didn't you find this bug?" scored `corrections:0` in `supervision-kpi.py` (start-anchored blunt patterns only).

**Planning impact:** RSI loop cannot measure planning misses → no gradient to fix interview/closure templates.

---

## Incident index (quick lookup)

| ID | Repo | Session | Operator trigger | Primary D |
|----|------|---------|------------------|-----------|
| H1 | hutter | `897a2209` | "go on" | D1 |
| H2 | hutter | `897a2209` | (hook-caught) | D6 |
| H5 | hutter | `897a2209` | push-verify instinct | D7 |
| G1 | genomics | `019d7aab` | "100 not run yet?!" | D2 |
| G2 | genomics | `5a71f0f5` | budget emergency | D3 |
| G3 | genomics | `019d7aab+` | (observe) | D9 |
| G5 | genomics | `7ffc759b` | cert wave | (partial success) |
| P1 | phenome | `4da894ca` | (foundation arc) | counter-example |
| P2 | phenome | `adfa97e4` | (checkpoint) | D4 |
| P3 | phenome | (eval plan) | (bloat deleted) | D8 |

---

## What changed (Jun 11–18 window)

### Hutter
| Artifact | Change |
|----------|--------|
| `META-AUDIT.md` | +9 rows Jun 16–17 (D1, D6, D7, busy≠value, collapse generative-backlog) |
| `results/session-retro-2026-06-16.md` | AP-1…AP-6 formal retro |
| `dreamer_tick.sh` | Idle → `IDEAS.md` not shadow backlog |
| `CLAUDE.md` | Bus propagation doc fix (`d6d0350`) |
| `IDEAS.md` | Absorbed generative-backlog survivors |

### Genomics
| Artifact | Change |
|----------|--------|
| `docs/audit/2026-06-17-cert-pass2/` | CERT-SPEC + per-stage cert logs |
| `docs/audit/2026-06-17-wave1/OPERATOR-PREFLIGHT.md` | Readiness without dispatch |
| `scripts/payload_contract.py` | Canonical denominator declarations |
| `pipeline_orchestrator.py` | Unscoped run refused (earlier) |

### Phenome
| Artifact | Change |
|----------|--------|
| `docs/GOALS.md` | Foundation + verification substrate rewrite |
| `.claude/plans/4da894ca-foundation-exit-and-surface-pivot.md` | Exit-signal model |
| `.claude/checkpoint.md` | 173-line mixed-status handoff (`adfa97e4`) |
| `docs/decisions/deferred-and-open.md` | EN2 promotion gate broken-as-built |

---

## Diagnosis summary (no fixes)

1. **Hutter's verifier is clean** — failures are almost entirely **authority routing** and **transport assumptions**, not science errors. The Jun 16 session is a textbook case: correct escalation, incorrect freeze scope, false dependencies, filename inventory, wrong bus doc.

2. **Genomics' verifier is partial** — failures cluster at **plan boundaries**: close, scope, tool routing, migration completeness. Wave-1 cert shows planning **can** work when procedure is externalized (`CERT-SPEC.md`) and dispatches are narrow.

3. **Phenome's verifier is partial + unbounded substrate** — without `exit_signal` plans, agents rationally keep hardening. `4da894ca` is the exception that proves the rule. Checkpoint/plan proliferation is a **symptom** of missing "done" decisions, not bad agents.

4. **Cross-repo:** parallel sessions break handoff assumptions; supervision metrics undercount planning failures; critique and plan can contradict without a merge gate.

**Next step (out of scope here):** solutions live in alignment report §4–7; implement only after operator picks which D-classes to attack first.
