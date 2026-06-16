# Architecture — how the whole setup ties together

**Start here** if you want the shape of the system in one screen. This is the visual
front-door; the prose detail lives in the pointers at the bottom. Revise the diagram
when you observe drift — don't let it rot (regen: edit `architecture.mmd`, then run the `mmdc` command at the bottom).

![Architecture flowchart](architecture.png)

**Mermaid source:** [`architecture.mmd`](architecture.mmd) — the single source the `png` renders from. Edit it, then regen the image (below). The inline duplicate was removed 2026-06-16 (two copies drift; one source is constitution principle 9).

## The two loops (sessions are the only sensor; the harness the only actuator)
Everything the operator does happens **inside a session** — so sessions are the system's one
ground-truth signal, and the **harness is the one thing worth changing**. The system is a
**cascaded control loop** with two timescales (verified against control theory / active inference /
H-JEPA, `research/2026-06-16-predictive-arch-rsi-loops.md`):

- **⚡ SHORT-TERM "reflex" loop** (seconds, *within one session*): SessionStart digests +
  PreToolUse guards + Stop nudges shape the live session; the human corrects in the moment; the
  agent adapts before the turn ends. No durable write needed. (`HARNESS ⇄ S1`.)
- **🔄 LONG-TERM "learning" loop** (days–weeks, *across sessions*): transcripts/commits/verdicts →
  durable stores → launchd miners (the de-facto **middle timescale**) → `/observe`+`/improve` →
  improvement-log → **2+ recurrence gate** → promote to rules/hooks/skills → propagate to the
  harness → shapes future sessions. Objective: declining supervision (`supervision-kpi`/AIR).

They are **coupled**: the long loop's *output is short-loop machinery* — a hook is a reflex the
slow loop installed. Cascade-control law (Skogestad/Shinskey): the inner loop must run ~4–10×
faster than the outer or they fight; ours does (seconds vs days), so the split is sound.

## Proposed edges — verified 2026-06-16, NOT yet built
The literatures say our 2-loop cut is *correct but under-instrumented* — add **named edges, not
new loops** (full decision table + provenance in the research memo). Drawn dashed/purple in the
diagram:

| # | Edge | What it adds | Value | Status |
|---|------|--------------|-------|--------|
| ① | **Anti-windup gate** | long loop stops promoting a rule-class whose reflexes fire-but-don't-fix (AIR not dropping) — the integral-windup analog | HIGH | unblocked by the 2026-06-16 AIR-instrument fix (`supervision-kpi`) |
| ② | **Precision-weighting** | weight each miner by demonstrated precision (1−FP), not all-equal — "which detector to trust" | HIGH | clash-detector's 2-wk window already collects the number |
| ③ | **Problem-hiding guard** | alarm when supervision↓ co-occurs with error-visibility↓ (the dominant iterative-loop collapse mode; already half-stated in the constitution) | HIGH | drift-sentinel can run the joint check |
| ④ | **Anticipatory edge** (cheap only) | long loop predicts next-likely miss-class, pre-installs a reflex — the one genuinely-reactive gap. NOT an EFE planner (intractable) | MED | must pair with ① or predicting-misses-that-never-come IS the windup failure |

**All four are harness-state edges, not rules.** Each externalizes *recoverable bookkeeping* into
the harness (recurrence-per-class, per-detector precision, the joint supervision×visibility trend)
so the policy only *judges* — building any of them as a prompt instruction is the wrong layer
(constitution P1 / `decisions/2026-06-07-state-externalization-lens.md`; control theory gives the
*why*, the lens gives the *where*). Independent corroboration that the middle timescale already
exists: SAMULE micro/meso/macro reflection (EMNLP 2025). MAST (NeurIPS 2025) grounds the verdict —
44% of multi-agent failures are system-design not capability, 23.5% are task-verification (exactly
what edges ① + ③ target); its "reasoning-action mismatch" + "information withholding" categories
are candidate precision-weighted detectors we don't yet have.

DON'T import: the FEP/EFE formalism, JEPA architecture, or a Gödel-machine self-rewrite loop —
our regime is observable **scaffolding-RSI**, the converging non-FOOM kind.

## Legend (one line each → where the detail lives)
| Block | What it is | Deeper doc |
|---|---|---|
| Harness | The layered instruction/skill/hook/MCP surface loaded per session | `CLAUDE.md` §Cross-Project Architecture · `.claude/rules/context-budget-principles.md` |
| Durable stores | git + `agentlogs.db` + corpus — the system's memory | `.claude/rules/session-forensics.md` · `decisions/2026-05-26-cross-attestation-substrate-v2.md` |
| Self-monitoring | zero-API launchd jobs (sense half of RSI) — live set: `launchctl list \| grep com.agent-infra` | `CLAUDE.md` §Active launchd jobs |
| RSI governance | observe → improvement-log → promote to architecture | `CLAUDE.md` <constitution> · `.claude/rules/gov-id.md` |
| Governed projects | intel/phenome/genomics/skills + their stances | `research/cross-project-architecture-overview.md` (prose, 2026-05-11) |
| Codebase | py files by group + import-hubs (count is GENERATED, never hand-kept) | `.claude/rules/codebase-map.md` |

## Derive live state — never trust a hand-kept count

The blocks above show the **shape**; the exhaustive, current inventory is **derived**. A
hand-maintained list drifts the day you add a job (this doc said "13 jobs / 138 files" one
day after it was written). So: **what's POSSIBLE is a map (slow-changing); what's WIRED is
derived (changes hourly) — never hand-document liveness.**

### → Start with `just orient`
`just orient` (`scripts/orient.py`) IS the unifier: the live map — repos, launchd loops,
hook wiring (by event), MCP servers, skills — assembled from ground truth on every run, so
nothing in it can go stale. It correctly shows jobs added minutes ago (it reads `launchctl`,
not prose). `orient = what is it?` · `doctor = healthy?` · `dashboard = what happened?`

Drill deeper into one question:

| Question | Command |
|---|---|
| Doc-vs-reality drift (live jobs vs this doc / CLAUDE.md) | `uv run python3 scripts/orient.py --drift` |
| Dead scripts (generator, no consumer) | `uv run python3 scripts/orphan_check.py` |
| Scaffold lifecycle (rules/hooks, shrink-eligible vs backlog) | `just gov-report` |
| Cross-project health (hooks · MCP · skills · symlinks) | `uv run python3 scripts/doctor.py` |
| Which hooks actually FIRE (not just registered) | `uv run python3 scripts/hooks_smoke.py` |
| Open human-gated decisions (pending · steward · DUE predictions) | `just questions` |

## Regenerate the image
```bash
mmdc -i architecture.mmd -o architecture.png -t dark -b '#0b0f19' --scale 2 \
  -p /tmp/puppeteer-cfg.json   # cfg: {"executablePath":"<system Chrome>","args":["--no-sandbox"]}
```
