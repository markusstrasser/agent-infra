---
id: 2026-09-22-model-pins-track-newest
concept: model-routing
repo: agent-infra
decision_date: 2026-09-22
recorded_date: 2026-09-22
provenance: contemporaneous
status: accepted
initial_leaning: repoint stale pins one at a time as they surfaced (lane's claude-opus-4-8 → claude-opus-5-5)
relations: []
---

# 2026-09-22: Live model pins track the newest models, through aliases where a tool accepts them

## Context
Opus 5.5 shipped on 2026-09-22 and became the `opus` alias and the plan default. An inventory of dated model ids found 1,222 files across 16 repos, 261 of them outside record trees. Some live pins pointed at `gpt-5.5`, which llmx now refuses with exit 2, so those tools were broken. While `lane`'s Claude worker was being moved off `claude-opus-4-8` (pinned since 2026-08-27), the operator said: "remove all these old settings or none at all ... maybe it's cruft ... we should use the newest models etc", then "go".

## Alternatives considered
1. **Piecemeal:** fix pins as they surface. The tail of stale pins stays; every release repeats the audit.
2. **Newest exact ids everywhere:** one sweep, then the drift restarts with the next release.
3. **Aliases where the tool accepts them (`claude --model opus`), newest exact ids elsewhere; registries and records untouched.** Chosen.
4. **Remove pins and inherit tool defaults:** loses role differences that are real (cheap bulk lane vs flagship, the biology lane).

## Counterevidence sought
Pins that exist for a technical reason rather than as leftovers. Found and kept, each labelled in the sweep result files: (A) registries — pricing tables, allowlists and retired-id lists must keep old ids to price history and refuse retired models; (B) records; (C) docs about a specific model; (D) name-matching regexes; (E) fixture ids and retired-id refusal tests; (F) biology and cyber lanes — Opus 5.5 declines dual-use biology, so model-guide routes that work to Opus 5 by exact id, the newest model that does it; (G) arms of completed experiments, where the model is the measured variable. One real cost: bake-off-chosen cheap extraction models (intel's gpt-5.3 Instant) move to current cheap tiers without re-running the bake-off. The operator's call is "use the newest"; the move is recorded so a measured regression can re-pin that one role.

## Decision
Every live model pin moves to the newest model in its role, using the mapping in the sweep rules (Opus → `claude-opus-5-5` or `opus`; Fable → `claude-fable-5-1`; Sonnet → `claude-sonnet-5`; GPT flagship roles → `gpt-6-astra`; metered cheap roles → `gpt-5.6-luna`; Gemini flash → `gemini-3.8-flash`, pro → `gemini-3.1-pro-preview`). Where a tool accepts an alias, the pin becomes the alias so the next release needs no sweep. Categories A–G stay.

## Evidence
- Inventory and per-repo results: `research/2026-09-22-claude-opus-5-5-release.md` §5.
- `lane` alias: skills `6d8d2f0`. llmx defaults: llmx `80641cd`.
- Retired ids: llmx refuses `gpt-5.5` with exit 2 (`~/.claude/rules/llmx-routing.md`).

## Revisit if
- A newest-model move regresses a measured metric (an extraction bake-off, an eval score, a cost ceiling): re-pin that single role and put the measurement in the commit.
- An alias starts resolving to a model a lane cannot use (for example a biology lane hitting the `bio` classifier).

## Supersedes
None.

## Revisions
- 2026-09-22: the Decision mapping omits two rows the sweep applied: Gemini flash-lite → `gemini-3.5-flash-lite`, and Haiku 4.5 stays. Where a flat mapping would put both tiers of a deliberate pair on one id, the pair was split instead (research-mcp `cag.py`) or the dead tier removed (intel `--deep`); see the memo's §5.
