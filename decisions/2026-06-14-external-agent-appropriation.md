---
id: 2026-06-14-external-agent-appropriation
concept: complement-not-rebuild
repo: agent-infra
decision_date: 2026-06-14
recorded_date: 2026-06-14
provenance: contemporaneous
status: accepted
initial_leaning: appropriate the top opencode/hermes patterns (subagent-permission hook + curator) as the high-value path
relations:
  - type: depends_on
    target: 2026-06-12-vendor-binary-skill-archaeology
---

# 2026-06-14: What to appropriate from opencode / hermes / refactor-mcp

## Context
Studied three external agents (opencode = SST TS coding agent; hermes-agent =
NousResearch self-improving Python CLI; refactor-mcp = C# Roslyn refactor server),
cloned to `~/Projects/best/`, to decide what agent-infra (which runs *on* Claude
Code) should appropriate. Six candidates emerged. The operator then directed:
**check historical session evidence + run verifiable probes before deciding.**
That dig flipped the priority order — the durable lesson below.

## The real axis (Phase-0 reframe)
The first framing — "which external patterns to appropriate" — was wrong. The
historical check revealed the actual axis: **for a system running ON Claude Code,
marginal improvement comes from instrumenting our OWN telemetry (audit → enforce
ignored rules) far more than from porting external agents' architecture.** The
external scan was worth doing — it *confirmed* the frame (partition-don't-compete)
and surfaced one governance reframe — but it yielded almost nothing buildable:
every strong opencode/hermes idea either (a) duplicates a CC primitive, (b) hits a
CC hook ceiling, or (c) is an insight, not a build. The buildable wins all came
from our own git-friction audit + output-size probe.

## Assumptions surfaced (and what happened to them)
1. "Appropriating from opencode/hermes is the high-value path." → **FALSIFIED.** Mostly skips.
2. "Build something from each candidate." → **REJECTED** (filter-by-maintenance; recurrence bar).
3. "exa-cap needs registry-level truncation we can't do on CC." → **FALSIFIED** — PreToolUse
   `updatedInput` mutates tool input (`best/claude-code-docs/docs/hooks.md:925`, `changelog.md:1450`).

## Decision (per candidate)

| Candidate | Verdict | Evidence |
|---|---|---|
| opencode subagent permission-derivation (child⊆parent) | **SKIP** | 2084 Agent dispatches ~89% read/analysis; git-friction audit shows pain is peer-session cross-sweep + `--no-verify`, not subagent over-reach; worktree-default + zero-output gate already cover code-touch. No incident history → Pre-Build #1 → don't build. |
| opencode truncation+spill (universal) | **SKIP as-ported** | CC ceiling: PostToolUse can only *add* context, not shrink an emitted result. |
| → narrow variant: **PreToolUse exa `textMaxCharacters` cap** | **BUILD** | Probe: exa_advanced = 8.5M tok of >50KB results across 122 calls; `research-tool-gotchas` rule ("cap on broad sweeps") ignored 122×. Instruction→architecture (Principle 1). Buildable via `updatedInput`. (Param corrected — see Revisions.) |
| hermes gated curator | **RECORD, don't build** | Pattern redundant (gov.py / reclaim-rotate / drift-sentinel already do report-only + archive + dry-run). Value = the veto-reframe below. |
| hermes negative-capture blocklist | **SKIP** | Non-problem: 3 agent-infra memory files have negative phrasing, mostly legit. |
| refactor-mcp | **SKIP** | C#-only (fleet is Python/TS) + maintainer's BUG-REPORT.md: 78 bugs / 8 data-loss in core ops; 2 confirmed unfixed in HEAD. |
| System Context Registry / PTC sandbox | **NOTE** | Design lenses; CC-ceiling-limited (can't inject mid-conversation system msgs). |

## The governance reframe (hermes capture/curate split)
hermes splits self-improvement into greedy **capture** (`background_review.py`) and
conservative **curate** (`agent/curator.py`: provenance-scoped to agent-authored,
archive-never-delete `curator.py:362`, dry-run report `:322-340`, inactivity-triggered).
**Our autobrowse/auto-graduation veto was scoped to the greedy capture-half** ("most
sessions should mint a skill," `background_review.py:46` + no-consumer-check `curator.py:370`
— a direct regression against `consumption-over-autonomy`, correctly vetoed). The **gated
curate-half is constitution-compatible** (it IS the dry-run+human-approve pattern we already
run). This NARROWS the veto's scope; it does NOT reopen it (no build — the pattern is already
covered by gov.py et al.). **Resurrection trigger:** a demonstrated need for semantic
consolidation of an append-only *knowledge* store (research memos / MEMORY) that gov.py +
memory_harvest don't cover.

## Counterevidence sought
For the #1 SKIP: searched the 2084-dispatch population + 21d of git ops for the incident class
opencode's permission-narrowing prevents (subagents committing/over-reaching). Found the opposite —
the documented git incidents (git-friction audit, 14 sessions) are a *different* class (peer main
sessions sharing `.git/index`). Absence of the target incident is the evidence. For the exa-cap
BUILD: verified the mechanism exists (`updatedInput`) rather than assuming portability.

## Disagree-self-check (the one mind-change)
- prior: BUILD #1 (subagent permission hook) — ranked highest pre-probe.
- new evidence: subagent mix 89% read-only; git-friction audit locates the real pain elsewhere;
  no incident history for subagent over-reach.
- flip threshold: Pre-Build #1 ("no incident → hypothetical → don't build"). **CLEARED.**
- action: **FLIP build→skip.** Driven by absent incident class, not by operator conviction
  (operator said "check history," not "skip #1" — the data drove it).

## Build spec (the one deliverable — first task on handoff)
PreToolUse hook matching `mcp__exa__web_search_advanced_exa`: if `textMaxCharacters` is unset
(→ uncapped full-text extraction = the 8.5M-tok source) OR > CAP, set it to CAP via
`hookSpecificOutput.updatedInput` + `permissionDecision:"allow"`. Optionally also clamp
`numResults` (default 10) and, per Exa's own best-practice, nudge toward `enableHighlights` +
`highlightsMaxCharacters` (≈10× fewer tokens than full text). NOTE: `contextMaxCharacters` (my
original spec) is the WRONG knob — it's "not included by default," so capping it is a no-op; the
real lever is `textMaxCharacters`. Open HOW: CAP value (OSS `exa-mcp-server` uses 2000; Exa quick-ref
≈500, tutorial ≈5000). Scope: exa is cross-project → **shared infra → human-gated** before global
deploy; pilot agent-infra-local first.

## Prior art (Pre-Build #1 — operator-directed check, do NOT reinvent)
- **Native lever already on our tool** (verified from the live tool schema): `textMaxCharacters`,
  `highlightsMaxCharacters`, `numResults`. The OSS `exa-mcp-server` (~/Projects/best) hard-defaults
  `DEFAULT_MAX_CHARACTERS: 2000` (`src/tools/config.ts:10`) — our hosted `web_search_advanced_exa`
  does not, which is the entire gap. So the "build" is really "inject the default the OSS server
  already ships."
- **Exa coding-agent guide** (exa.ai/docs/reference/search-api-guide-for-coding-agents): prefer
  `highlights` over `text` for agents (~10× token reduction); cap full text with `maxCharacters`.
- **Productized OSS for the GENERAL problem** (Read 15M + browser 6.7M, not just exa):
  `github.com/mksglu/context-mode` (sandboxes tool output, claims 98% reduction, SQLite+FTS5+BM25 —
  opencode's truncate+spill, shipped) and `mcp-plus.github.io` (MCP+: `expected_info` arg pre-filters
  before output hits context). Both are MCP-layer/sandbox tools → **dependency-eval against the
  CC-on-top ceiling before adopting** (can they wrap our MCP servers without owning the runtime?).
  `openai/codex#6426` tracks the same line-vs-token truncation problem. Don't build a general
  truncation engine without evaluating context-mode first.

## Revisit if
- A subagent-over-reach incident actually occurs (reopens #1).
- The exa-cap produces false-positive truncation harm (agent needed the dropped chars).
- A knowledge-store consolidation need materializes (reopens the curate-half).

## Supersedes
Refines (narrows) the autobrowse auto-graduation veto — see `.claude/rules/vetoed-decisions.md`
and `decisions/2026-05-28-autobrowse-graduation-not-built.md`. Does not overturn it.

## Revisions
**2026-06-14 — operator-directed prior-art check corrected the build spec.** (1) The exa lever
is `textMaxCharacters` (uncapped when unset), NOT `contextMaxCharacters` (which is "not included
by default" — capping it is a no-op). Caught by reading the live tool schema (probe-the-write).
(2) Added Prior-art section: the native cap exists, the OSS `exa-mcp-server` already defaults it to
2000, and `context-mode`/MCP+ productize the general truncate-spill problem — so the exa fix is
cheaper than a custom engine, and the general case must dependency-eval context-mode before any
build. Verdicts unchanged; only the exa build spec sharpened.

**2026-06-14 — exa-cap pilot BUILT + context-mode dependency-eval done.**
- Built `scripts/pretool_exa_cap.py` + wired in `.claude/settings.json` (agent-infra-local pilot,
  Claude-only). Verified on 5 cases. `EXA_TEXT_MAX_CHARS` env-tunable (default 12000). Commit landed.
- **context-mode (mksglu/context-mode) → SKIP adoption** (cloned to best/, evaluated). It DOES work
  on CC — it integrates via hooks (75 PreToolUse / 40 PostToolUse across 8 platforms + openclaw
  plugin) and dodges the PostToolUse-can't-shrink ceiling exactly like our exa-cap (PreToolUse
  routing-block, not PostToolUse). So the ceiling is NOT a blocker for the hook-routing approach —
  useful confirmation. But adoption is wrong for us: (a) massive overlap/conflict with our existing
  stack (it ships its own SQLite session store + SessionStart/Stop/PreCompact hooks that would fight
  agentlogs.db + our hooks); (b) sandbox model changes the workflow (Bash subprocesses don't persist
  to host; route execution through `ctx_execute`); (c) ELv2 license (source-available, not OSI);
  (d) credibility red flags (18 fabricated `href="#"` enterprise-adoption logos; inflated stats;
  single maintainer). **Pattern-extract verdict:** the PreToolUse-routing mechanism is already
  validated + adopted (exa-cap); `src/truncate.ts` + FTS5-spill is the reference IF the long-tail
  (Read 15M / browser 6.7M) ever justifies a general truncator. Don't build that now; don't adopt
  context-mode.
