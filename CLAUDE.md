# Meta — Agent Infrastructure

## Purpose
This repo plans and tracks improvements to agent infrastructure across projects (intel, selve, genomics, skills, research-mcp). It's the "thinking about thinking" repo.

## Key Files

**Core:**
- `GOALS.md` — what the system optimizes for (human-owned)
- `justfile` — task runner (grouped): `just --list` shows groups. Root workspace justfile at `~/Projects/justfile` for cross-project dispatch (`all-health`, `push-all`, `todos`)
- `maintenance-checklist.md` — pending improvements, monitoring list, sweep schedule
- `improvement-log.md` — structured findings from session analysis (session-analyst appends here)
- `agent-failure-modes.md` — documented failure modes from real sessions
- `AGENTS.md`, `GEMINI.md` — symlinks to CLAUDE.md (multi-editor compatibility)

**MCP Servers:**
- `meta_mcp.py` — meta-knowledge MCP server (section-based search over all .md files)
- `scripts/repo_tools_mcp.py` — repo navigation tools (RETIRED from MCP, 2026-03-20). Zero usage across 4,287 runs. Scripts remain as CLI tools via Bash: `repo-outline.py` (outline, callgraph, xrefs, symbol), `repo-summary.py` (file map with `--compact`).

**Orchestration & Ops:**
- `scripts/orchestrator.py` — cron-driven task runner (dual-engine: `claude -p` + scripts). See Orchestrator section below.
- `scripts/doctor.py` — cross-project health checker (hooks, settings, skills, MCP, git state)
- `scripts/propose-work.py` — daily morning brief: ranked work proposals from cross-project signals
- `scripts/runlog.py` — cross-vendor run importer/query CLI for Claude, Codex, Gemini, and Kimi local logs
- `scripts/code-review-scout.py` — continuous code review via Gemini/Codex CLI (free tier)
- `scripts/code-review-schedule.py` — daily rotation: 5 projects × 5 focuses, 25-day cycle
- `scripts/vendor-versions.py` — parallel version checker for AI vendor tools/SDKs
- `scripts/best-sync.py` — daily git fetch for priority OSS repos in `~/Projects/best/`
- `scripts/autoresearch.py` — evolutionary code search: LLM-as-mutator, deterministic eval, git reset on regression
- `pipelines/` — JSON pipeline templates (recurring workflows)
- `experiments/` — autoresearch experiment configs

**Self-Improvement Loop** (the core feedback cycle):
- `scripts/session-shape.py` — zero-LLM-cost structural anomaly detector. Pre-filter: flags sessions with unusual tool patterns for deep analysis
- `scripts/finding-triage.py` — RETIRED. Inline improvement-log approach (2+ recurrence noted in text) replaced the separate DB. Script kept as archive.
- `scripts/fix-verify.py` — closed-loop fix validation. Runs detection queries against recent sessions to verify fixes are holding. Commands: `run`, `tag`, `report`

**Epistemic Measurement** (run via `uv run python3 scripts/<name>.py --days N`):
- `scripts/supervision-kpi.py` — SLI (supervision load), AIR (alert intervention rate), AGR (autonomy gain trend). Constitutional north-star metric.
- `scripts/thesis-challenge.py` — measures agent pushback on investment theses in intel sessions
- `scripts/session-features.py` — extracts 11 behavioral features per session for trajectory calibration
- `scripts/calibration-canary.py` — 35 canaries across 6 categories (incl. prediction_market, constitutional), weekly runs
- `scripts/compaction-canary.py` — post-compaction invariant loss detection (baseline + analyze modes)
- `scripts/tool-trajectory.py` — ATP-derived tool-opportunity utilization model, normalized by task type
- `scripts/pushback-index.py` — sycophancy word detection + fold rate
- `scripts/safe-lite-eval.py` — factual precision via Exa verification
- `scripts/epistemic-lint.py` — unsourced claim detection with severity weighting
- `scripts/trace-faithfulness.py` — matches agent claims to actual tool_use entries
- `scripts/fail_open.py` — `@fail_open` decorator for measurement functions (timeout + graceful degradation)
- `schemas/calibration_canaries.json` — canary definitions with ground truth

**Hook Telemetry:**
- `scripts/hook-outcome-correlator.py` — joins hook triggers with session receipts
- `scripts/hook-roi.py` — hook trigger pattern analysis (fires, blocks, false positive candidates)

**Reference:**
- `substrate/` — shared knowledge substrate. See below and `decisions/2026-03-17-shared-knowledge-substrate.md`.
- `schemas/` — `calibration_canaries.json` (active). `open_questions.md` and `pertinent_negatives.json` are design references only (never instantiated by any project).
- `runlog.md` — runlog architecture, import/query usage, named queries
- `cockpit.md` — human-agent interface: status line, notifications, receipts, dashboard
- `human-instructions.md` — operator decision guide
- `search-retrieval-architecture.md` — CAG vs embedding retrieval, routing framework
- `.claude/overviews/` — auto-generated source + tooling overviews (Gemini via repomix)

## Research Index

72 research memos in `research/`. Full index with topics and "consult before" triggers: `.claude/rules/research-index.md` (auto-loaded).

<constitution>
> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

### Generative Principle

> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. In code, you can always run things — if they don't run successfully, they produce errors, and errors get corrected. With good verification, common sense, and cross-checking, autonomy leads to more than caution does. Grow > de-grow. Build the guardrails because they're cheap, not because they're the goal.

Error correction per session is the secondary constraint: autonomy only increases if errors are actually being caught. If supervision drops but errors go undetected, the system is drifting, not improving.

**The arms race:** The better the agent gets, the faster the human must rethink what they want next. Agent capability outpaces goal-setting. The human iteratively discovers what they want based on what they have — goals emerge from capability, not the other way around. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep. Until then, the agent proposes and the human steers.

### Principles

**1. Architecture over instructions.** Instructions alone = 0% reliable (EoG). If it matters, enforce with hooks/tests/scaffolding. Text is a prototype; architecture is the product. Exception: simple format rules and semantic predicates that can't be expressed as deterministic checks.

**2. Enforce by category.**

| Category | Examples | Enforcement |
|----------|----------|-------------|
| Cascading waste | Spin loops, bash parse errors, search flooding | Hooks (block) |
| Irreversible state | Protected data writes, destructive git ops | Hooks (block) |
| Epistemic discipline | Source tagging, hypothesis generation, pushback | Stop hook (advisory) |
| Style/format | Commit messages, naming | Instructions |

**3. Measure before enforcing.** Log every hook trigger to measure false positives. Without data, you can't promote or demote hooks rationally.

**4. Self-modification by reversibility + blast radius.** "Obvious improvement" is unmeasurable. Use concrete proxies:
- **Autonomous:** affects only meta's files, easily reversible, one clear approach, no other project changes
- **Propose and wait:** touches shared infrastructure, multiple viable approaches, affects other projects, deletes/restructures architecture
- **Always human-approved:** this Constitution section, GOALS.md

**5. Divergence budget by uncertainty × irreversibility.** Not every task needs exploration. Routine implementation, bug fixes, and tasks with one correct answer should converge fast. But when both uncertainty (unclear right approach) AND irreversibility (costly wrong move) are high, extend the divergent phase:
- **low uncertainty, low irreversibility** → converge fast, no exploration needed
- **high uncertainty, low irreversibility** → short divergence (brainstorm 3-5 options, pick one, iterate)
- **low uncertainty, high irreversibility** → cautious validation (verify the obvious answer thoroughly)
- **high uncertainty, high irreversibility** → extended divergence + cross-model review required. Produce explicit phase artifacts: options explored, selection rationale, then implementation.

This replaces taste-based "should I brainstorm?" with a decision rule grounded in stakes.

**6. Phase-state artifacts for design decisions.** When a task involves a genuine design choice (architecture, strategy, shared infrastructure), the exploration and selection must be written down as auditable artifacts — not just happening implicitly in conversation. Convention:
- `divergent-options.md` (or section): 5-10 option families with different mechanisms
- `selection-rationale.md` (or section): why these 1-2 were chosen, what was rejected and why
- Then implementation.
These can be sections in a plan file, a research memo, or standalone. The point: if someone asks "what alternatives did you consider?" the answer is a file, not "I thought about it." Session-analyst checks for existence on design tasks.

**7. Research is first-class.** Divergent (explore) → convergent (build) → eat your own dogfood → analyze → research again when stuck. Not every session. Action produces information. Opportunistic, not calendar-driven.

**8. Filter by maintenance, not effort.** Dev creation cost ≈ 0 with agents. The "invisible governor" (effort kills ideas before testing) is gone. Decision tables in research memos use: Value | Maintenance | Prerequisites — not Effort | ROI. Gate on ongoing drag (maintenance burden, complexity budget, supervision cost, integration risk), not creation cost. Jevons Paradox applies: cheaper dev = more gets built, so guard against complexity sprawl, not under-building. See `research/agent-economics-decision-frameworks.md`.

**9. Skills governance.** Meta owns skill quality: authoring, testing, propagation. Skills stay in `~/Projects/skills/` (separate). Meta governs through session-analyst (sees usage across projects) and improvement-log.

**10. Fail open, carve out exceptions.** Hooks fail open by default. Explicit fail-closed list: protected data writes, multiline bash, repeated failure loops (>5). List grows only with measured ROI data.

**11. Recurring patterns become architecture.** If used/encountered 10+ times → hook, skill, or scaffolding. Not a snippet, not a manual habit. (The Raycast heuristic.)

**12. Cross-model review for non-trivial decisions.** Same-model review is a martingale. Cross-model provides real adversarial pressure. Required for multi-project or shared infrastructure changes. **Dispatch on proposals, not open questions** — critique is sharper than brainstorming. When model review disagrees with user's expressed preference, surface the disagreement and let the user decide.

**13. The git log is the learning.** Every correction is a commit. The error-correction ledger is the moat. Commits touching governance files (CLAUDE.md, MEMORY.md, improvement-log, hooks) require evidence trailers.

### Autonomy Boundaries

**Hard limits (never without human):** modify Constitution or GOALS.md; deploy shared hooks/skills affecting 3+ projects; delete architectural components.

**Autonomous:** update meta's CLAUDE.md/MEMORY.md/improvement-log/checklist; add meta-only hooks; run session-analyst; conduct research sweeps; create new skills (propagation = propose).

### Self-Improvement Governance

A finding becomes a rule or fix only if: (1) recurs 2+ sessions, (2) not covered by existing rule, (3) is a checkable predicate OR architectural change. Reject everything else.

Primary feedback: session-analyst comparing actual runs vs optimal baseline. If a change doesn't improve things in 30 days, revert or reclassify as experimental.

### Session Architecture
- Fresh context per orchestrated task (no --resume)
- 15 turns max per orchestrated task
- Subagent delegation for fan-out (>10 discrete operations)

### Known Limitations
- **Sycophancy:** instruction-mitigated only. Session-analyst detects post-hoc.
- **Semantic failures:** unhookable. Cross-model review is the only mitigation.
- **Instructions work >0% for simple predicates.** Don't over-hook.

### Pre-Registered Tests

How to verify this constitution is working (check via session-analyst after 2 weeks):

1. **No build-then-undo on shared infrastructure changes.** The reversibility + blast radius boundary should prevent autonomous changes that get reverted. Test: zero reverts of meta-initiated shared changes in 14 days.
2. **Hooks fire on high-frequency failures.** Deployed hooks (bash-loop-guard, spinning-detector, failure-loop) should reduce repeated tool failures. Test: ≥50% reduction in ≥5-bash-failure-streaks vs pre-deployment baseline.
3. **Research produces architecture, not documents.** Research sessions should result in hooks, skills, or code — not just memos. Test: ≥50% of research findings in improvement-log have "implemented" status within 30 days.
4. **Model review surfaces disagreements.** When cross-model review disagrees with a stated preference, the synthesis explicitly flags it. Test: zero instances of silently overriding user preference in review artifacts.
</constitution>

## Orchestrator (`scripts/orchestrator.py`)

Cron-driven task runner. Dual-engine: `claude -p` for LLM tasks, raw `subprocess` for deterministic scripts. SQLite task queue at `~/.claude/orchestrator.db`.

```bash
orchestrator.py init-db                              # create DB
orchestrator.py submit <pipeline> [--project P] [--vars k=v]  # submit pipeline
orchestrator.py run -p <project> --prompt "..."      # one-off task
orchestrator.py status                               # show queue
orchestrator.py show <id> [--full]                   # full task details + transcript path
orchestrator.py approve <id|pipeline>                # approve paused task
orchestrator.py retry <id>                           # reset failed/blocked task to pending
orchestrator.py tick                                 # run one task (launchd calls this)
orchestrator.py log --today [--pipeline P] [--project P] [--last N]  # event log
orchestrator.py pipelines                            # cost/status rollup by pipeline
orchestrator.py efficiency                           # token efficiency breakdown by pipeline
orchestrator.py summary                              # daily markdown
```

**Pipelines** (`pipelines/*.json`): algorithm-provenance-audit, code-review-sweep, deep-dive, design-review, earnings-refresh, entity-refresh, epistemic-baseline, epistemic-deep, fix-verify-weekly, intel-research, morning-prep, qa-sweep, repo-index-refresh, research-and-implement, research-api-benchmark, research-sweep, researcher-health, runlog-import, safe-lite-weekly, session-retro, skill-health, skills-drift, trigger-monitor, vendor-anthropic, vendor-google, vendor-openai. Templates support `{variable}` substitution and `pause_before` approval gates.

**Key design choices:**
- `--no-session-persistence` and `--worktree` both dropped — they suppress transcripts (breaks session-analyst)
- `--worktree` now loads skills/hooks (fixed in v2.1.76) — `isolation: "worktree"` agents get full skill/hook access
- Cross-project execute steps auto-require approval (constitutional hard limit)
- `done_with_denials` is a distinct terminal status (permission denials are not silent)
- `DAILY_COST_CAP = $25` enforced before each tick
- `fcntl.flock` prevents concurrent runs
- Stall detection: `anyio.fail_after(600s)` kills hung claude tasks
- Per-pipeline concurrency: max 3 running tasks from same pipeline
- `verify: true` on pipeline steps uses Haiku to check **completeness** (were all sub-questions addressed?), NOT **truth** (are claims factually correct?). Orthogonal to AgentDrift-style corruption — verification of factual correctness requires cross-source checks, not step-level completion scoring.

**Scheduling:** Loaded launchd agents in `~/Library/LaunchAgents/`:
- `com.meta.orchestrator.plist` — tick every 15 min (runs queued tasks)
- `com.meta.session-retro-daily.plist` — submits session-retro at 22:00
- `com.meta.hook-roi-daily.plist` — generates hook ROI report at 22:30
- `com.meta.propose-work-daily.plist` — morning brief at 05:00 (not yet loaded)

**Scheduler:** `tick()` auto-submits scheduled pipelines via `scheduled_runs` table (unique constraint prevents duplicates). Pipelines with `"schedule"` in their JSON template are auto-submitted when their cron hour elapses.

**Artifacts:** `artifacts/session-retro/` and `artifacts/hook-roi/` (gitignored). Session-retro outputs drafts here, not directly to improvement-log.

**Design spec:** `research/orchestrator-design.md`.

## Knowledge Substrate (`substrate/`)

Shared provenance and dependency tracking across intel, selve, genomics, and meta. Per-project SQLite DBs at `~/.claude/knowledge/{project}.db`. Shared schema, per-project domain profiles.

**Core:** `schema.sql` (7 tables), `core.py` (KnowledgeDB class), `cli.py`, `mcp_server.py` (10 tools).

```bash
uv run python3 -m substrate --db ~/.claude/knowledge/intel.db stats    # project stats
uv run python3 -m substrate --db ~/.claude/knowledge/intel.db stale    # stale objects
uv run python3 substrate/propagate_cross_project.py                    # cross-project propagation (dormant — 1 ref in 4+ days)
uv run python3 substrate/stress_test.py                                # 27 tests
uv run python3 substrate/ingest_intel.py                               # re-ingest intel entities
uv run python3 substrate/ingest_selve.py                               # re-ingest selve memos
```

**MCP configured in:** intel, selve, genomics (`.mcp.json`). DB also in meta. Advisory hook in global `settings.json` (PostToolUse on Write/Edit).

**ADR:** `decisions/2026-03-17-shared-knowledge-substrate.md`.

## Backlog

See `ideas.md` for backlog items and architectural ideas. Not loaded into context by default.

## Decision Journal (`decisions/`)

Lightweight decision records for concept-level pivots — when an approach is chosen, dropped, or superseded. One file per decision, format: `YYYY-MM-DD-slug.md`. Template in `decisions/.template.md`. Records use YAML frontmatter for machine-readable metadata (concept grouping, typed relations, provenance).

**When to write a decision record:**
- Path-dependent: choosing this forecloses alternatives
- Costly to reconstruct later (the reasoning, not just the outcome)
- Based on evidence that changed belief
- Likely to matter in publication or external explanation
- Do NOT write for: parameter tweaks, routine implementation, local execution details

**Convention for research memos:** When updating a memo with revised understanding, add a dated `## Revisions` entry at the bottom. Only for claim/interpretation/confidence changes — if wording or organization changed without changing the conclusion, don't add a revision entry. The git diff shows what changed; the revision note says *why*.

**Decision records are for human archaeology** — agents should create them for genuinely path-dependent choices but are not expected to consult them before acting. The value is in the written reasoning, not in agent retrieval.

**Cross-repo convention:** Cross-repo decisions live canonically in one repo (usually meta for infrastructure, or the repo where the evidence lives for research). Affected repos get a one-line stub: `See [repo]/decisions/YYYY-MM-DD-slug.md`.

**Commit bodies for concept shifts:** Commits touching `research/` or `decisions/` should have a non-empty body naming the concept affected and what changed directionally. `git log --format='%s%n%b' -- decisions/` should read as a concept evolution timeline.

## llmx Transport Routing

| Model | Transport | Flag needed | Cost |
|-------|-----------|-------------|------|
| Gemini Flash/Lite | CLI (free) | none | $0 |
| Gemini Pro | CLI (free) | none (no `--stream`) | $0 |
| GPT-5.x | API (direct) | none | per-token |

- **Gemini Pro on CLI works** — hang bug fixed in gemini-cli 0.32.1 (current: v0.34.0). No `--stream` needed.
- **`--stream` forces API fallback** — only add if CLI hits rate limits.
- **`--max-tokens` forces API fallback** — CLI caps at 8K, no override. Brainstorm still uses API.
- **codex-cli disabled** — 34K token overhead per call (MCP descriptions), no bare mode. GPT goes direct to API.
- **Exit 6 = billing exhausted** (permanent). Exit 3 = rate limit (transient). Don't retry exit 6.
- **llmx is editable-installed** (`uv tool install --editable`). Source changes in `~/Projects/llmx/` propagate instantly.
- **No `--fallback`** — model should be the model. Diagnose failures, don't mask with model downgrade.

## What This Repo Is NOT
- Not a place to write more rules about rules.
- Not a place to document things that should be implemented. Plan here → implement in target repo in same session.
- Architectural changes > documentation changes.

<reference_data>
## Cross-Project Architecture
| Layer | Location | Syncs how |
|-------|----------|-----------|
| Global CLAUDE.md | `~/.claude/CLAUDE.md` | Loaded in every project (universal rules) |
| Shared skills | `~/Projects/skills/` | Symlinked into each project's `.claude/skills/` |
| Shared hooks | `~/Projects/skills/hooks/` | Referenced by path in each project's `settings.json` |
| Project rules | `.claude/rules/` per project | Diverges intentionally (domain-specific) |
| Project hooks | `.claude/settings.json` per project | Per-project, similar patterns |
| Global hooks | `~/.claude/settings.json` | Loaded in every project |
| Research MCP | `~/Projects/research-mcp/` | Configured in `.mcp.json` per project |
| Genomics pipeline | `~/Projects/genomics/` | Extracted from selve 2026-02-28 |

## Hook Design Principles
- Deterministic > LLM-judged. Guard concrete invariants, not vibes.
- Fail open unless blocking is clearly worth it.
- `trap 'exit 0' ERR` swallows `exit 2` from Python — disable trap before critical Python calls.
- Stop hooks must check `stop_hook_active` to prevent infinite loops.
- Hook inventory and event types documented in MEMORY.md `hooks.md`.
</reference_data>

<cockpit>
## Cockpit (Human-Agent Interface)

Status line, notifications, receipts, and dashboard. Full details in `cockpit.md`.

| Component | Location | What |
|-----------|----------|------|
| Status line | `~/.claude/statusline.sh` | Model, branch, cost, context bar |
| Config | `~/.claude/cockpit.conf` | `notifications=on\|off` |
| Dashboard | `meta/scripts/dashboard.py` | `uv run python3 scripts/dashboard.py [--days N]` |
</cockpit>

<session_forensics>
## Session Forensics
- Chat histories: `~/.claude/projects/-Users-alien-Projects-*/UUID.jsonl`
- Compaction log: `~/.claude/compact-log.jsonl`
- Session receipts: `~/.claude/session-receipts.jsonl`
- Runlog DB: `~/.claude/runlogs.db`
- Runlog docs: `meta/runlog.md`
- Runlog CLI: `uv run python3 scripts/runlog.py stats|import|query|recent`
- Run `just hook-telemetry` for current error sources
- Session search: `uv run python3 scripts/sessions.py search <query>` (FTS5, faster than bash/grep)
</session_forensics>
