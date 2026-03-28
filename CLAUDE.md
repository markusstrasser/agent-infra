# Meta — Agent Infrastructure

## Purpose
This repo plans and tracks improvements to agent infrastructure across projects (intel, selve, genomics, skills, research-mcp). It's the "thinking about thinking" repo.

## Quick Start

```bash
just --list                              # all recipes, grouped
just preflight                           # fast prereq check (<10s)
just smoke                               # minimal functional test (<1m)
just health                              # full validation suite (<5m)
uv run python3 scripts/doctor.py         # cross-project health check
uv run python3 scripts/dashboard.py      # agent ops dashboard
uv run python3 scripts/runlog.py recent  # recent runs across vendors
uv run python3 scripts/sessions.py search <query>  # FTS5 session search
```

## Key Files

**Core (root):**
- `GOALS.md` — what the system optimizes for (human-owned)
- `justfile` — task runner (grouped). Root workspace justfile at `~/Projects/justfile` for cross-project dispatch
- `maintenance-checklist.md` — pending improvements, monitoring list, sweep schedule
- `improvement-log.md` — structured findings from session analysis (session-analyst appends here)
- `agent-failure-modes.md` — documented failure modes from real sessions
- `AGENTS.md`, `GEMINI.md` — symlinks to CLAUDE.md (multi-editor compatibility)

**MCP Server:**
- `meta_mcp.py` — meta-knowledge MCP server (section-based search over all .md files)

**Scripts** (61 Python files — see `.claude/rules/codebase-map.md` for full inventory with dependency arrows):
- *Orchestration & Ops:* orchestrator, doctor, propose-work, runlog, code-review-scout/schedule, vendor-versions, best-sync, autoresearch
- *Self-Improvement Loop:* session-shape (zero-cost pre-filter), fix-verify (closed-loop validation), sessions (FTS5 search/dispatch)
- *Epistemic Measurement:* supervision-kpi, calibration-canary, pushback-index, safe-lite-eval, epistemic-lint, trace-faithfulness, tool-trajectory, session-features, compaction-canary
- *Hook Telemetry:* hook-outcome-correlator, hook-roi

**Agents** (`.claude/agents/`):
- `session-analyst.md` — persistent (memory: project). Behavioral anti-pattern detection, `--corrections` mode
- `researcher.md` — persistent (memory: user). Deep research with source tracking across sessions

**Reference:**
- `schemas/calibration_canaries.json` — canary definitions with ground truth
- `runlog.md` — runlog architecture, import/query usage, named queries
- `cockpit.md` — human-agent interface: status line, notifications, receipts, dashboard
- `human-instructions.md` — operator decision guide
- `search-retrieval-architecture.md` — CAG vs embedding retrieval, routing framework
- `.claude/overviews/` — auto-generated source + tooling overviews (Gemini via repomix)

## Research Index

~99 research memos in `research/`. Full index with topics and "consult before" triggers: `.claude/rules/research-index.md` (auto-loaded).

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
- Interactive sessions with `/loop` for recurring work
- Subagent delegation for fan-out (>10 discrete operations)
- Orchestrator for unattended scheduled tasks only (session-retro, morning-brief)

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

## Execution Model

**`/loop` + interactive sessions is primary.** The human runs Claude Code directly, uses `/loop` for recurring tasks (steward, research cycles, maintenance), and steers in real-time. Subagents handle fan-out within sessions.

## Orchestrator (`scripts/orchestrator.py`) — Background Only

Queue-backed task runner for unattended scheduled work. Not the primary execution model.

```bash
orchestrator.py status                               # show queue
orchestrator.py submit <pipeline> [--project P]      # submit pipeline
orchestrator.py tick                                  # run one pending task
orchestrator.py log --today [--last N]               # event log
orchestrator.py pipelines                            # cost/status rollup
```

**Used for:** session-retro, morning-brief, runlog-import, and other pipelines that run unattended. Pipelines defined in `pipelines/*.json`.

**Key constraints:** `DAILY_COST_CAP = $25`, `fcntl.flock` prevents concurrent runs, `anyio.fail_after(600s)` stall detection, cross-project steps require approval.

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
- **codex-cli re-enabled** — ~37K token overhead from 9 MCP servers (no disable flag). Viable for substantial tasks (audits, reviews). ChatGPT auth: only `gpt-5.4` and `gpt-5.3-codex` work; `o3`/`gpt-4.1` rejected. Don't use for trivial queries.
- **Exit 6 = billing exhausted** (permanent). Exit 3 = rate limit (transient). Don't retry exit 6.
- **Gemini 503/rate-limit = session-level fallback.** After first 503 from Gemini, switch to GPT or Flash for remaining calls in the session. Don't retry the same Gemini model — 4 confirmed incidents of 4-6 wasted retries before fallback.
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
- **Four hook types:** `command` (bash), `prompt` (Haiku LLM call ~$0.001), `agent` (multi-turn subagent), `http` (POST). Use deterministic command hooks for concrete invariants; use prompt hooks for semantic judgment calls (unsourced claims, unverified completion).
- Fail open unless blocking is clearly worth it. All prompt hooks wrapped with 3-10s timeout.
- `trap 'exit 0' ERR` swallows `exit 2` from Python — disable trap before critical Python calls.
- Stop hooks must check `stop_hook_active` to prevent infinite loops.
- **Deployed prompt hooks:** Agent dispatch turn-budget validation (PreToolUse), Stop verification of claimed work (Stop), unsourced claim detection (PostToolUse Write|Edit).
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
