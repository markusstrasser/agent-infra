---
title: Planning process alignment — phenome, genomics, hutter
date: 2026-06-18
sources: [agentlogs, git logs, plans/, META-AUDIT.md, improvement-log, GOALS.md, subagent forensics]
projects: [phenome, genomics, hutter]
---

# Planning process alignment report

**Question:** Across phenome, genomics, and hutter conversations — what must change in the
planning process to avoid hiccups and stay aligned? Includes recommendations for human
interview, requirements skill, long-term vision, and user stories.

**Method:** Parallel forensics on three repos (git log, `.claude/plans/`, agentlogs operator
messages, META-AUDIT, improvement-log, GOALS/handoffs). Jun 2026 window weighted.

---

## Executive summary

| Repo | Verifier regime | Main planning failure | Main planning strength |
|------|-----------------|----------------------|------------------------|
| **hutter** | Clean (bytes) | Authority mis-routing + global-state blindness | Pre-registered cells, META-AUDIT, explicit "done" via ledger |
| **genomics** | Partial (pipeline truth) | Scope/closure gaps + plan→execution drift | Root-cause plans, operator preflight, per-class fixes |
| **phenome** | Partial (claim oracle) | Plan proliferation + missing "done" decisions | Strong GOALS.md, foundation-exit pivot, ADR discipline |

**Cross-cutting verdict:** The failures are not "agents can't plan." They are:

1. **Wrong human–agent authority split** (agent freezes or escalates the wrong things)
2. **Missing exit criteria** (substrate work has no natural stop)
3. **Phase-state artifacts skipped** on consequential pivots
4. **Closure without surfacing known bad state** (genomics)
5. **Inventory by filename, not content** (hutter leverage rediscovery)

**Fix shape:** Not more plans — **tighter planning contracts** by verifier regime, plus
**demand more from Markus** only on a fixed small decision set.

---

## 1. Cross-repo failure modes (ranked)

### F1 — Decision ≠ measurement conflation (hutter >> genomics)

**Pattern:** Agent escalates a strategic question to Markus, then **freezes all nearby work**
—including measurements that would inform the decision.

**Evidence:**
- hutter META-AUDIT 2026-06-16: version-b build held **7h16m** while waiting on pivot/continue
- Session retro AP-1: recurrence 3→HIGH
- Markus: "why do I have to make the call?" / "go on" / "should you do more?" (×3 same session)

**Fix:** After escalation, mandatory sentence:
> "Proceeding in parallel: [X]. Holding only: [Y — requires your response]."

Measurement never blocked by strategic wait unless the measurement *uses* the decision's output.

---

### F2 — Closure without surfacing known bad state (genomics)

**Pattern:** Agent closes a plan while withholding ledger/readiness facts the operator would
naturally ask next.

**Evidence:**
- improvement-log 2026-04-11: agent closed DAG convergence plan; user ran status → "100 not run yet?!"
- Information was in agent context; not in closure summary
- Failure mode: `INFORMATION_WITHHINDING`

**Fix:** **Closure packet template** (required on plan close):
- `known_open_state:` (what readiness/ledger still shows)
- `what_user_might_ask_next:` (one line)
- `verifier_ran:` (command + exit code)

---

### F3 — Unscoped expensive operations (genomics)

**Pattern:** Requirements omit explicit scope on irreversible/costly ops.

**Evidence:**
- improvement-log 2026-04-24: unscoped `pipeline-run` → Modal budget emergency, 15 GPU apps
- Fix landed: orchestrator refuses unscoped run

**Fix:** **Scope triple** required before any run costing >$3 or >1h compute:
- `--target` / `--from` / explicit env override name
- Written in plan header, not just chat

---

### F4 — Plan proliferation without exit criteria (phenome)

**Pattern:** `.claude/plans/` grows (phenome: **96**, genomics: **79**) while checkpoint/handoff
docs accumulate overlapping DONE/SUPERSEDED tasks.

**Evidence:**
- `phenome/.claude/checkpoint.md`: 60+ pending lines, many marked DONE inline
- Plans spawn faster than archive/consume
- Substrate has no natural "done" — agents keep finding "one more layer"

**Counter-example (what works):**
- `phenome/.claude/plans/4da894ca-foundation-exit-and-surface-pivot.md`:
  > "done is a **decision**, not a state you wait to arrive at"
- Countable Phase 0 exit signal: `just verify-claim-invariants` DEBT tier

**Fix:** Every multi-session plan requires **`exit_signal:`** block (measurable, not vibes).
Archive plan when exit_signal hits OR operator calls pivot (#f).

---

### F5 — Phase-state artifacts skipped (all repos)

**Pattern:** Agent converges on architecture/strategy without `divergent-options` +
`selection-rationale` (Constitution Principle 6).

**Evidence:**
- improvement-log: pipeline validation plan — critique after convergence, not before
- intel constitution changes without phase artifacts
- hutter strategic pivots (quantization→fx-transforms) live in checkpoint prose only

**Fix:** `/decide` scope gate + hook advisory on `.claude/plans/` with `plan_kind: architecture`.

---

### F6 — Assert global state without checking (hutter)

**Pattern:** Agent states "loops are up" / "bus is git-synced" / "result pending" without probe.

**Evidence (META-AUDIT rows):**
- queue/ assumed git-propagated — **gitignored**, grinder never got QUEUE_015
- Two ledger id-spaces → false "historian fabricated row 143"
- "All loops firing" without `loop_health`

**Fix:** **Probe-before-assert** rule in OUTER-LOOP / daily ops: if load-bearing doc mentions
transport/sync/loop health → cite command output from this session.

---

### F7 — Inventory filename ≠ content (hutter, genomics)

**Pattern:** Pre-dispatch `ls proposals-pending/` without **reading** overlapping docs →
190K-token rediscovery.

**Evidence:** META-AUDIT 2026-06-16; improvement-log inventory-before-dispatch cluster

**Fix:** Extend `gather_context.py` / `/decide` Phase 0: **read** top 3 overlapping artifacts,
not just paths.

---

### F8 — Tool routing not in plan (genomics)

**Pattern:** Plan assumes execution path; agent uses bash workarounds instead of purpose-built tools.

**Evidence:**
- improvement-log 2026-04-11: 0 `mcp__genomics__*` calls vs 260 bash Modal invocations
- MCP instructions explicitly name replacements; ignored

**Fix:** Plan section **`execution_surface:`** — which tools/commands are in-bounds; bash
fallback requires logged exception.

---

### F9 — Vision/telos drift across repos (phenome ↔ genomics)

**Pattern:** Cross-repo substrate work proceeds without reconciling GOALS/ADR telos.

**Evidence:**
- `phenome/docs/GOALS.md` vs `genomics/docs/GOALS.md` — substrate unification research
  (2026-06-17) explicitly hunts clashes
- `da8ad7fc`: "flag GOALS/ADR-0002 clashes — owner #f"
- Phenome: verification substrate, not synthesis; genomics: consumer + pipeline

**Fix:** Cross-repo plans require **`telos_check:`** — 3 bullets: what each repo optimizes,
what this work must NOT become.

---

### F10 — Codex brainstorm/plan mode bypass (genomics)

**Pattern:** Codex sessions treat brainstorm as filtering, skip divergent generation.

**Evidence:** improvement-log 2026-04-18: 8/8 codex sessions bypassed brainstorm skill

**Fix:** Regime-specific: codex dispatch for design work → require `/decide` or written
`divergent-options` section before implementation plan.

---

## 2. What works (keep and propagate)

| Pattern | Where | Why it works |
|---------|-------|--------------|
| **Explicit "done is a decision"** | phenome `foundation-exit-and-surface-pivot.md` | Stops infinite substrate hardening |
| **GOALS.md with deferred scope** | phenome `docs/GOALS.md` | Human-owned telos; agents propose, Markus approves |
| **Root-cause → per-class fixes** | genomics `control-plane-truth-zombie` plan | Refuses batch "reconcile all" wrong fixes |
| **Pre-registered experiment cells** | hutter `paired_metabolic_powered_RUNLOG.md` | Demote/pursue before spend |
| **META-AUDIT corrections log** | hutter `META-AUDIT.md` | Planning failures become mechanisms |
| **Mechanical actor ($0)** | hutter `dreamer_tick.sh` | Planning doesn't depend on model remembering plumbing |
| **Handoff directory** | phenome `docs/handoffs/` | Session continuity without plan bloat |
| **`/decide` six-phase arc** | `skills/decide/SKILL.md` | Frame axis before plan; inventory before dispatch |
| **`interview-prompt` for taste** | `skills/interview-prompt/` | High-information questions only; routes to feedback/writing-style |
| **Operator preflight docs** | genomics `OPERATOR-PREFLIGHT.md` | Readiness axis before dispatch |
| **#f owner flags** | phenome commits (`owner #f`) | Explicit human telos calls in git |
| **Deferred plans with done-when** | phenome `05335ab9-deferred-build-infra.md` | Honest backlog, not silent drift |

---

## 3. Planning process changes (by verifier regime)

Constitution already defines three regimes (`decisions/2026-06-07-verifier-conditional-autonomy.md`).
**Planning kit should differ by regime** — one template for all repos causes misfit.

### Clean verifier (hutter)

| Need | Don't need |
|------|------------|
| Pre-registered cells, oracle-gated A/B | User stories |
| Operator decision set (money, prize, heretic charter) | Long vision essays |
| Phase-state for **strategic pivots** only | `/interview-prompt` before pivots |
| Parallel-work enumeration after escalation | Compatibility scaffolding |

**Required plan sections:** `hypothesis`, `predicted_ΔS`, `tier_ladder`, `exit_signal`,
`operator_decision_if_any`

### Partial verifier (genomics, phenome)

| Need | Don't need |
|------|------------|
| Scope triple on expensive ops | Byte-exact style pre-registration |
| Closure packet with `known_open_state` | Auto-ratchet language |
| `execution_surface` (MCP vs bash) | Harness-as-fitness until surrogate matures |
| Exit signal / foundation-exit pattern | Infinite checklist refill |
| Cross-repo `telos_check` when touching 2+ repos | Shared loop-core package |

**Required plan sections:** `scope_in`, `scope_out`, `exit_signal`, `verifier_commands`,
`operator_gates`, `execution_surface`

### Principal / taste (product direction, constitution, sizing)

| Need | Don't need |
|------|------------|
| `/interview-prompt` or `/decide` Phase 0 | Agent auto-activation |
| `divergent-options` + `selection-rationale` | Harness eval for taste |
| User stories / success metrics tied to GOALS | LLM-as-judge for final call |

**Markus decision set (fixed, publish in each repo CLAUDE.md):**

| Markus owns | Agent owns |
|-------------|------------|
| Money/spend above threshold | Technical sequencing |
| Constitution / GOALS edits | Build + measure |
| Rule/hook **activation** (intel Law 6) | Conviction from evidence → act + report |
| Product-tier forks (anim 3D, phenome OSS scope) | Implementation within approved tier |
| Heretic charter content (anti-defanging) | Apparatus improvement |
| Top-level telos pivot (#f) | Cross-model critique dispatch |

---

## 4. Skill and human-process recommendations

### A. Extend `interview-prompt` → **project kickoff mode**

Current skill targets taste/writing (`skills/interview-prompt/SKILL.md`). Add route
`project-kickoff` triggered when:

- New `.claude/plans/*` with `plan_kind: architecture`
- Cross-repo work (phenome + genomics)
- User says "plan X" without scope triple

**Kickoff questions (N=3, high-information only):**

1. **Exit signal:** "What would make you call this done / wrong to continue?"
2. **Scope OUT:** "What must this explicitly NOT become?" (compatibility layer, second system, etc.)
3. **Authority:** "What decisions are yours vs mine on this arc?"

Use `AskUserQuestion` with concrete stances. Route answers to plan header + `feedback` memory.

**Do NOT** use interview for: hutter compression pivots (ledger is the interview), routine
implementation, facts in corpus.

---

### B. New skill: **`requirements-slice`** (or extend `/decide` Phase 0)

Lightweight, not another platform. One screen before build:

```markdown
## Requirements slice
- user_story: (one sentence, who/what/why — skip for pure infra)
- scope_in: ...
- scope_out: ...
- exit_signal: (measurable)
- verifier_commands: (exact `just`/`bun`/`uv` invocations)
- operator_gates: (list Markus approvals needed)
- execution_surface: (tools in-bounds)
- telos_check: (if cross-repo)
```

**Gate:** Plans missing `exit_signal` + `scope_out` get advisory block on Write to
`.claude/plans/` (measure false positives 2 weeks before promote).

---

### C. Long-term vision — where it lives

| Repo | Vision home | Agent rule |
|------|-------------|------------|
| phenome | `docs/GOALS.md` (strong) | Read before substrate plans; flag clashes #f |
| genomics | `docs/GOALS.md` + decisions/ | Pipeline = truth spine; don't expand scope without ADR |
| hutter | `LOOP.md` + prize constraint | Vision = minimize bytes under bit-exact; no product creep |
| anim | `CLAUDE.md` + `evolver/FITNESS.md` | User story = "one clinical question answered" (PGx codeine) |

**Rule:** Vision changes require **#f or explicit GOALS edit** — not drift via checkpoint prose.

---

### D. User stories — when required

**Require** one-liner user story only when:

- Work is **product-facing** (phenome daily briefing, anim EoC scene, genomics clinical report)
- Work touches **principal register** (taste, UX, what Markus sees)

**Skip** for: pipeline remediation, ledger/harness, hook fleet, compression search.

**Template:**
> As Markus, I want [observable outcome] so that [GOALS metric: verification quality / action output / …].

---

### E. Handoff template (replace checkpoint sprawl)

Standardize `docs/handoffs/` + compact checkpoint:

```markdown
# Handoff — <plan_key>
## Remains (ordered)
## Exit signal (from plan)
## Known open state (commands run + output)
## Operator decisions needed
## Parallel work safe without you
## NOT in scope (restate)
```

**Rule:** PreCompact hook writes handoff, not 60-line task laundry.

---

### F. Closure discipline (genomics-critical)

Before any "plan complete" or session close on pipeline/substrate work:

```bash
# example — adapt per repo
just sample-readiness markus --target <stage>   # genomics
just verify-claim-invariants                     # phenome
just loop-health                                 # hutter
```

Surface output in closure packet even if uncomfortable.

---

## 5. Repo-specific notes

### Phenome

**Strengths:** Best GOALS doc in the stack; foundation-exit pivot is the model for "stop
hardening"; ADR + `/decide` culture; grounding eval loops with measurable probes.

**Gaps:**
- 96 plans / checkpoint bloat — consumption < production
- Cross-repo substrate unification needs telos_check every session
- Many parallel ADR tracks (0019, 0023, 0027…) — require **promotion consumer** or archive

**Demand from Markus:**
- **#f calls** on telos (OSS plugin, distributed-instance vision) — already happening; keep
- **Exit calls:** "foundation is done" style decisions when DEBT tier hits target
- **Reject** new ADR tracks without naming what they supersede

### Genomics

**Strengths:** Operator preflight; wave audit discipline; control-plane plan quality (per-class
fixes); scoped-run gate post-incident.

**Gaps:**
- Closure withholding
- MCP routing not in plans
- Handoff proliferation (79 plans)
- Scope creep in commits (wave1 audit documents this)

**Demand from Markus:**
- **Scope triple** before any `pipeline-run` / Modal fan-out (enforce, don't negotiate)
- **"What does readiness show?"** as mandatory close question
- **Compatibility boundary** when asking for refactors — or default breaking per Constitution §14

### Hutter

**Strengths:** META-AUDIT; pre-registration; historian loop; mechanical actor; only live
autonomous search — planning errors don't block inner loop.

**Gaps:** Authority mis-routing; reactive tick-executor; bus/ledger assert without check;
strategic pivot rationale not in phase-state files.

**Demand from Markus:**
- **"Go on" / "do more"** should become rare if parallel-work sentence + IDEAS.md idle burn work
- **Spend STOP** already correct — keep
- **Don't ask** for technical sequencing (version-b builds, SIMD probes) — only money/prize/heretic

---

## 6. Implementation priority

| Priority | Change | Owner | Verifier |
|----------|--------|-------|----------|
| P0 | Publish **operator decision set** in phenome/genomics/hutter CLAUDE.md | agent-infra → each repo | grep in sessions |
| P0 | **Closure packet** template in genomics `docs/handoffs/` | genomics | observe sessions — withholding recurrence |
| P1 | **requirements-slice** sections in plan template + advisory hook | agent-infra | false positive rate 2w |
| P1 | **interview-prompt `project-kickoff` route** | skills | use count on arch plans |
| P1 | **Handoff template** replace checkpoint sprawl | phenome first (worst bloat) | checkpoint line count |
| P2 | **telos_check** on cross-repo plans | phenome+genomics | critique catches |
| P2 | hutter **selection-rationale.md** for strategic pivots | hutter | META-AUDIT row rate |
| P3 | `gather_context` content inventory (not ls) | agent-infra | token rediscovery zero |

---

## 7. What NOT to do

- **Don't** build shared `loop-core` planning platform
- **Don't** require user stories on hutter compression or genomics pipeline fixes
- **Don't** add more plans — **archive** and **exit_signal** existing ones
- **Don't** use `/interview-prompt` for taste on every task — reserve for kickoff + principal register
- **Don't** let agents auto-activate rules/hooks/constitution (intel Law 6 generalizes)

---

## Appendix: evidence paths

### phenome
- `docs/GOALS.md`
- `.claude/plans/4da894ca-foundation-exit-and-surface-pivot.md`
- `.claude/plans/05335ab9-deferred-build-infra.md`
- `.claude/checkpoint.md` (bloat example)
- `docs/handoffs/README.md`
- `.claude/research/2026-06-17-substrate-unification/`

### genomics
- `.claude/plans/2026-06-02-control-plane-truth-zombie-remediation.md`
- `docs/audit/2026-06-17-wave1/OPERATOR-PREFLIGHT.md`
- `docs/audit/2026-06-18-wave1-commit-and-rerun-blocker.md`
- improvement-log: unscoped pipeline, MCP bypass, closure withholding

### hutter
- `META-AUDIT.md`
- `results/session-retro-2026-06-16.md`
- `OUTER-LOOP.md`, `IDEAS.md`
- `docs/decisions/2026-06-16-session-end-self-improvement.md`

### agent-infra
- `skills/decide/SKILL.md`
- `skills/interview-prompt/SKILL.md`
- `skills/outer-loop/scripts/route.py`
- `decisions/2026-06-07-verifier-conditional-autonomy.md`
- `improvement-log.md` (planning-related findings)
- `research/2026-06-18-hutter-anim-rsi-comparative-report.md`

### agentlogs (operator message counts, planning keywords)
- phenome: 62 sessions, 240 planning-related operator msgs
- genomics: 100 sessions, 270 msgs
- hutter: 30 sessions, 47 msgs
