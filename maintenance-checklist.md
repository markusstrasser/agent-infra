# Agent Infrastructure Maintenance Checklist

## Dated Checkpoints

- [ ] **2026-04-07 Decision journal 30-day check:**
  - Decision records exist for genuinely path-dependent choices (>2 ADRs)
  - >85% commit body compliance on research/decisions files (check hook telemetry)
  - ~~Cross-referencing from research memos~~ (removed 2026-03-21 — write-only role accepted)
- [ ] **2026-04-04 Evidence systems 2-week check:**
  - Stale injection → action rate: >50% of sessions where stale objects surfaced
  - `query_stale` MCP calls > 0 per week
  - Zero PRS-pattern data regressions from documented retractions
  - `substrate_guard.py` catches synthetic regression fixture

## When a New Model Ships (Claude, GPT, Gemini)

### 1. Update Model Guide
- [ ] Pull release notes / system card / technical report
- [ ] Fetch and read the actual paper (don't summarize from training data)
- [ ] Update `~/.claude/skills/model-guide/SKILL.md` with new model capabilities, pricing, known issues
- [ ] Update `memory/MEMORY.md` frontier model section if it changes our routing decisions
- [ ] Search for independent evals (not just provider self-assessments)

### 2. Update Claude Code Docs (Claude releases only)
- [ ] Check Claude Code changelog: `claude --version`, release notes
- [ ] Claude Code source is not public — read the docs instead
- [ ] Check for new hook types, skill features, MCP changes, settings options, **plugin capabilities**
- [ ] Update `~/.claude/skills/` with any new capabilities
- [ ] Update project `.claude/rules/` if new features change best practices
- [ ] Check if CLAUDE.md spec changed (new fields, frontmatter, etc.)
- [ ] Re-evaluate plugins if: rules support added, non-namespaced skills added, or collaboration starts

### 3. Cross-Agent Parity
Each project should have:
```
CLAUDE.md          ← canonical agent instructions
AGENTS.md -> CLAUDE.md   ← symlink for OpenAI Codex CLI
GEMINI.md -> CLAUDE.md   ← symlink for Google Gemini CLI
```

**Agent-specific config files:**
| Agent | Config | Instructions | Settings | Skills/Rules |
|-------|--------|-------------|----------|-------------|
| Claude Code | `.claude/` | `CLAUDE.md` | `.claude/settings.json` | `.claude/skills/`, `.claude/rules/` |
| Codex CLI | — | `AGENTS.md` | — | — |
| Gemini CLI | — | `GEMINI.md` | — | — |

The other two read the same instructions via symlink. They don't have hooks, skills, or rules — that's OK. The shared content (hard constraints, DuckDB, data, principles) works universally.

**Parity gaps (known):**
- Codex/Gemini have no equivalent of hooks (PreToolUse, Stop, PreCompact)
- Codex/Gemini have no equivalent of path-scoped rules
- Codex/Gemini have no equivalent of skills/slash commands
- MCP server config is Claude-specific (`.mcp.json`)
- These are real capability gaps, not just config differences

### 4. Research Sweep (Weekly)
- [ ] Search arxiv for last 7 days: "LLM agents", "coding agents", "tool use", "agentic AI"
- [ ] Search for Anthropic employee blog posts / personal setups
- [ ] Search for new papers on: agent evaluation, prompt engineering, CLAUDE.md patterns
- [ ] Check Trail of Bits, Simon Willison, Hamel Husain for agent security/best practices posts
- [ ] Check Kapoor/Narayanan (normaltech.ai) for reliability research updates
- [ ] Save interesting papers to corpus: `mcp__research__save_paper`
- [ ] Fetch + read key papers: `mcp__research__fetch_paper` + `read_paper`
- [ ] Export to selve: `mcp__research__export_for_selve` → `./selve update`
- [ ] Update `frontier-agentic-models.md` with significant findings
- [ ] **Use Exa for recency searches, not S2** (S2 has no date filtering)

### 4a. Papers Pending Save
- [ ] arXiv:2602.16943 — Mind the GAP. Not in S2 index yet — retry later.
- [ ] arXiv:2506.04018 — AgentMisalignment. Capability-misalignment scaling.
- [ ] arXiv:2601.20103 — TRACE. Reward hacking detection. 37% undetectable.
- [ ] arXiv:2509.25370 — AgentDebug. Targeted correction +24% vs blind retry.

### 4b. Monitor: RLM "Learned Context Folding" (arXiv:2512.24601)
Prime Intellect's Recursive Language Models treat long prompts as external environment — LLM uses Python REPL to inspect/transform input, recursively calls sub-LLMs. **Never summarizes.** Frames compaction as information-lossy and delegation-to-code as superior.

Why this matters: If delegation consistently beats compaction, our compaction contract may be suboptimal. We already use subagents for delegation — RLM formalizes this pattern.

Watch for:
- [ ] Independent replication (currently single lab, preprint only)
- [ ] Latency measurements in production settings (recursive sub-calls add latency)
- [ ] Comparison with compaction on tasks matching our workflows (entity refresh, research synthesis)
- [ ] Whether Claude Code or similar tools adopt this pattern

**Don't change anything yet.** Wait for independent replication. But if 2+ labs confirm delegation > compaction, revisit our compaction contract.

### 5. Skills Propagation
When updating a skill in `~/.claude/skills/` (user-level):
- [ ] Check if any project has a project-level override in `.claude/skills/`
- [ ] If so, decide: update the project version or delete it to inherit user-level
- [ ] Currently overridden in intel: `researcher`, `deep-research` (redirected), `competing-hypotheses`, `multi-model-review`, `thesis-check`, `new-dataset`, `commands`
- [x] Intel `researcher` is a symlink to shared skill — updates propagate automatically
- [x] `entity-management` flipped to `user-invocable: true` (2026-02-27)
- [x] `model-review` skill exists at shared level (cross-model adversarial review via llmx)

### 6. Global CLAUDE.md (`~/.claude/CLAUDE.md`)
Created 2026-02-27. Loaded in every project session. Contains universal rules that don't belong in any single project:
- No `Co-Authored-By: Claude` in git commits
- AI-generated text (pasted or from llmx) treated as unverified — 4-step check, reference `model-guide`
- Branch-work-merge workflow pattern
- Proactive `/model-review` offering for non-trivial work

When updating: keep it under ~30 lines. It competes with project CLAUDE.md for context.

### 7. Snippet Retirement (2026-02-27)
User snippets analyzed against skills/hooks/rules. Six snippets retired:
- 6-phase research protocol → `/researcher` (strict superset)
- Research tool instructions (`;tre`/`;t`) → researcher Phase 2
- "Use gemini/gpt to review" → `/model-review`
- "Pasted AI text, be critical" → global CLAUDE.md
- "Git commit semantic, no claude" → global CLAUDE.md
- Exa API docs block → researcher now encodes the philosophy

Remaining as manual snippets (human steering, can't automate):
- Post-session retro ("gotchas to eradicate") — manual invocation = snippet is superior
- "Check ~/Projects/meta" — human judgment call
- "Generate ideas to improve" — direction-setting
- Parallel refactor agents — per-situation decision
- "Sanity check controversial takes" — steering

## Project Setup for New Repos
```bash
# Create agent instruction symlinks
ln -sf CLAUDE.md AGENTS.md
ln -sf CLAUDE.md GEMINI.md

# Add to .gitignore
echo ".claude/" >> .gitignore

# Initialize Claude Code
mkdir -p .claude/rules .claude/skills
```

## Session Analysis (Recurring)
- [ ] Run `/session-analyst intel 5` — analyze last 5 intel sessions for behavioral anti-patterns
- [ ] Run `/session-analyst selve 5` — analyze last 5 selve sessions
- [ ] Review `improvement-log.md` for actionable findings
- [ ] Implement proposed fixes (hooks > rules > instructions)
- [ ] Measure: did the fix reduce the failure rate in subsequent sessions?

**Frequency:** After major work sessions, or weekly during active development.
**Tool:** `~/Projects/skills/session-analyst/` — preprocesses transcripts via `extract_transcript.py`, dispatches to Gemini for analysis.
**Transcripts:** `~/.claude/projects/-Users-alien-Projects-{project}/` (native Claude Code storage, ~151 sessions across projects)

## Shared Hooks (`~/Projects/skills/hooks/`)
Reusable hook scripts symlinked into projects. All fail open (broken hook ≠ blocked work).

| Hook | Type | What it does |
|------|------|-------------|
| `postwrite-source-check.sh` | PostToolUse | Blocks writes to research paths without source tags (exit 2) |
| `stop-research-gate.sh` | Stop | Reminds about primary sources + disconfirmation before stopping |
| `pretool-data-guard.sh` | PreToolUse | Generalized data file protection (configurable paths) |
| `pretool-bash-loop-guard.sh` | PreToolUse | Blocks multiline for/while/if that causes zsh parse errors |
| `posttool-bash-failure-loop.sh` | PostToolUse | Detects 5+ consecutive Bash failures, warns agent to stop retrying |
| `pretool-commit-check.sh` | PreToolUse:Bash | Checks git commit messages: [prefix], no Co-Authored-By, governance trailers |
| `pretool-search-burst.sh` | PreToolUse | Warns at 4, blocks at 8 consecutive searches |

**Deployed to:** intel (postwrite-source-check.sh, posttool-bash-failure-loop.sh), global (commit-check, search-burst, bash-loop-guard)
**Selve:** has its own prompt-type Stop hook for research quality (more sophisticated than shell version)

## Shared Agents (`~/.claude/agents/`)
User-level subagents with persistent memory. Created 2026-03-01.

| Agent | Memory | Model | What it does |
|-------|--------|-------|-------------|
| `researcher.md` | user | inherit | Cross-session research with source memory + Stop prompt hook for citation checking |
| `session-analyst.md` | user | sonnet | Transcript analysis with recurrence tracking + Stop agent hook for output quality |

## Intel Agents (`intel/.claude/agents/`)
Project-level subagents. Upgraded 2026-03-01 with frontmatter (memory, model, tools).

| Agent | Memory | Model | What it does |
|-------|--------|-------|-------------|
| `entity-refresher.md` | project | sonnet | Refreshes entity files, remembers stale data sources |
| `dataset-discoverer.md` | project | sonnet | Finds and assesses public datasets, remembers rejections |
| `investment-reviewer.md` | project | sonnet | Adversarial thesis review with DuckDB access |
| `sql-reviewer.md` | — | haiku | DuckDB SQL and Python review |

## PostToolUse Output Rewrite Hooks (`updatedMCPToolOutput`)
- [x] PostToolUse `updatedMCPToolOutput` for research MCP `read_paper` — restructure raw PDF text to sections
- [x] PostToolUse `updatedMCPToolOutput` for Exa `web_search` — trim verbose metadata, keep title+URL+snippet
- [x] PostToolUse `updatedMCPToolOutput` for paper-search — normalize cross-source output format
- [x] Audit: raw output retention + hash logging for rewrite hooks now active in global settings (`~/.claude/tool-output-archive/`)

## Evidence System Health (added 2026-03-21)

Consumption-based metrics, not write volume. Check bi-weekly.

| Metric | What it measures | How | Target |
|--------|-----------------|-----|--------|
| Stale resolution (cohort) | Of objects stale at T0, fraction resolved by T+14 | changelog timestamps | >50% |
| Stale injection → action | Do surfaced stale objects get addressed? | session-end substrate diff | >50% sessions |
| Retraction completeness | Is data-first rule followed? | `substrate_guard.py` — 0 bypasses | 0 regressions |
| `query_stale` MCP calls | Read path has a pulse | runlogs.db tool_calls | >0/week |

**Retired:** substrate assertion count (vanity), MCP read:write ratio (invisible to runlogs with direct SQLite).

## Key Architecture Docs
- `search-retrieval-architecture.md` — CAG vs embedding retrieval decision framework, Groq/Gemini/Kimi assessment (2026-02-28)
- `research/claude-code-native-vs-meta-infra.md` — What Claude Code native features can/cannot replace (2026-03-01)
- `research/native-leverage-plan.md` — 5-phase plan for leveraging native features (2026-03-01)

## Ideas / Future Work

### Cross-Project Shared Library (`~/Projects/lib/`)
Deduplicate ~680 LOC across intel, meta, genomics, research-mcp. Six modules: io, files, db, http, telemetry, env. Full plan: `research/cross-project-infra-factoring.md`. Implementation plan: `.claude/plans/65730c3c-infra-and-cleanup.md`.

### IB API Integration (Future Phase)
Interactive Brokers API for agent-managed trading. $10K sandbox account. Outbox pattern: agent proposes → queue → execute. Pending paper trading validation proving consistent edge.

### Fraud/Corruption Separation (Decide Later)
Currently in intel as analysis/fraud/, analysis/sf/. May become separate repo if compute burden grows. Entity graph is shared regardless. Not urgent — the join is the moat.

## Key URLs to Monitor
- Claude Code releases: `anthropic.com/claude-code` (no public changelog URL — check `claude --version`)
- Codex CLI: `github.com/openai/codex` (or wherever they publish)
- Gemini CLI: `github.com/google/gemini-cli` (or wherever they publish)
- Agent benchmarks: SWE-bench, BFCL, Terminal-Bench
- Security: Trail of Bits blog, OWASP LLM Top 10
