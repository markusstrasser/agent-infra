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
| → narrow variant: **PreToolUse exa `contextMaxCharacters` cap** | **BUILD** | Probe: exa_advanced = 8.5M tok of >50KB results across 122 calls; `research-tool-gotchas` rule ("cap at 3000 on broad sweeps") ignored 122×. Instruction→architecture (Principle 1). Buildable via `updatedInput`. |
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
PreToolUse hook matching `mcp__exa__web_search_advanced_exa` (+ `web_search_exa`): if
`contextMaxCharacters` unset or > CAP, set it to CAP via `hookSpecificOutput.updatedInput` +
`permissionDecision:"allow"`. Open HOW (tune at build): CAP value (probe what agents currently
pass); whether to also gate `crawling_exa`. Scope: exa is used cross-project → **shared infra →
human-gated** before global deploy; pilot agent-infra-local first.

## Revisit if
- A subagent-over-reach incident actually occurs (reopens #1).
- The exa-cap produces false-positive truncation harm (agent needed the dropped chars).
- A knowledge-store consolidation need materializes (reopens the curate-half).

## Supersedes
Refines (narrows) the autobrowse auto-graduation veto — see `.claude/rules/vetoed-decisions.md`
and `decisions/2026-05-28-autobrowse-graduation-not-built.md`. Does not overturn it.
