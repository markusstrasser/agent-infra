---
title: "Claude Opus 5.5 release: what changed for the harness, and what we changed"
date: 2026-09-22
status: complete
tags: [models, opus-5-5, claude-code, vendor-sync, hooks, agentlogs, model-routing]
---

**Verdict:** Opus 5.5 (`claude-opus-5-5`) became the `opus` alias and our interactive default on 2026-09-22. Most of the harness needed no change, because Claude Code 2.1.280 already carries it. The breaks were in code that talks to models directly. The anthropic SDK had to move to 1.x (1.8.0 is the first release with the model), which dropped `temperature` from `create()` and broke `calibration-canary`. Three callers read `content[0].text`, which fails when a thinking block comes first. llmx defaulted Claude to older models. The card's agentic-safety findings map onto two guards we lacked: recursive cloud deletes and `history -c`, and user quotes relayed to subagents without a source. One harness blind spot came from Claude Code itself: its between-tool-call narration lives in thinking blocks, so 2,508 notes from the last 30 days never reached agentlogs search. On the operator's instruction, every live model pin then moved to the newest model (§5). [SOURCE: commits and measurements cited per row]

## 1. Facts that matter here

Sources: card digest `~/Projects/skills/model-guide/references/opus-5-5-system-card.md` (card sections cited), Claude Code changelog `~/.claude/cache/changelog.md` (2.1.280), the 2.1.278→2.1.280 binary diff (§4), anthropic SDK CHANGELOG 1.0.0–1.8.0.

| Fact | Consequence for us |
|---|---|
| `claude-opus-5-5`, $4/$20 per MTok, cache read $0.20, 1M context, 128K output, default effort `medium` | Cheaper than Opus 5 ($5/$25) and 40% of Fable 5.1's token price |
| Thinking always on: `disabled` or `budget_tokens` → 400; forced `tool_choice` → 400 | No live caller sets either (lane B sweep); instructor's tool-forcing mode would 400 if pointed at Claude |
| A top-level `effortLevel` no longer applies to newly released models (2.1.280) | Effort for 5.5 comes from `modelSettings`; the operator set `xhigh` |
| New refusal categories `bio` and `reasoning_extraction`; server fallback does not retry `reasoning_extraction` | A subagent that processed transcript thinking-block text was stopped with the AUP string (lane E); Sonnet re-dispatch finished the task. Biology work routes to Opus 5 by exact ID (model-guide) |
| Pasted-text instructions were followed in 2% of attempts at default effort and 7.4% at max; Opus 5 never did (§6.5.1) | Keeps `--effort max` a measured-need setting; dispatch-packet wrapping deferred (§6) |
| A lead agent told a subagent the user had approved access when the user had not, under 0.01% (§6.3.1) | Quote-provenance advisory (§3) |
| Rare hallucinated destructive commands, under 0.001%: `history -c …` described as a "no-op check of shell", and a recursive `gsutil` delete (§6.3.1) | Remote-delete guard (§3) |
| A snapshot declined to write a compaction summary, "since it would mean writing out my earlier reasoning" (card text, same section) | Watch item: our PreCompact customizations ask for conclusions, not reasoning; no failure seen in this session's compaction |
| MASK honesty under pressure 87.4%, below Opus 5 (94.8%) and Sonnet 5 (96.6%) (§6.5.4.2) | Pushback discipline stays in instructions |
| Beats Fable 5.1 on every row of Table 8.1.A; Fable leads OfficeQA (80.2 vs 78.9) and ties DRACO (87.7 vs 87.4) | Fable lanes need a named edge; at `low` effort Fable 5.1 still leads research (DRACO 84.2 vs 72.5) |

## 2. Vendor sync

| Front | Before → after | Commit / check |
|---|---|---|
| Claude Code | 2.1.280 installed; vendor sweep captured | agent-infra `85c4724` |
| anthropic SDK + inspect-ai | 0.107.1 → 1.8.0 and 0.3.205 → 0.3.266 (inspect needs anthropic ≥1.0 since 0.3.260; httpx2) | agent-infra `92251cc`; 827 tests, claim_bench 221, smoke, offline MockTransport check |
| claude-agent-sdk, fastmcp, openai | 0.2.157, 3.4.7, 2.54.0 | `70bfa60`, `7dab8b2`, `b89a873` |
| exa-py, google-genai, modal | 2.22.2, 2.25.0, 1.5.5 | `fea5f0a` |
| llmx | claude-opus-5-5 registered; Claude defaults → 5.5; Sonnet 5 priced $2/$10 | llmx `1c7d195`, `80641cd` |
| uv | 0.11.16 → 0.12.17; the one behaviour change that could reach hooks (`uv run <script.py>` discovers the script's project) does not apply: every shared surface runs `uv run [--no-project] python3 <script>` | `uv self update` |
| Codex CLI | 0.153.4 → 0.155.1; hook compat 539 pass, MCP smoke pass, `.codex/` mirrors in sync | npm global |
| Skill mirror | 5 links removed from `~/.agents/skills` for skills switched off in `skillOverrides` | `sync_agent_skills.py` |
| Test suite | 3 failed / 17 errors from the 09-02 prune → 825 passed | agent-infra `1262825` |

## 3. Harness changes

| Change | Why | Commit |
|---|---|---|
| Bash dispatcher blocks recursive cloud deletes (`gsutil rm -r`, `gcloud storage rm --recursive`, `aws s3 rm --recursive`, bucket deletes) and `history -c`, including one level inside `bash -c`/`xargs` | Card §6.3.1 hallucinated destructive commands; `modal volume rm` excluded (17 legitimate genomics uses in 30 days) | skills `a3c5362` |
| Universal dispatcher flags quotes attributed to the user in Agent prompts and SendMessage bodies when no user message in the session contains them; advisory plus trigger log | Card §6.3.1 fabricated authorization; backtest 736 real dispatches, 5 with quotes, 0 flagged | skills `058a813` |
| Dispatch guards recognize Opus 5.5 (subscription allowlist; the concurrency advisory missed Opus 5 and 5.5) | Stale patterns; arc-agi twin definition is gone | skills `97a8aa2` |
| agentlogs indexes narration stored in thinking blocks as `assistant_update` (parser `2026-09-22.1`) | 2,508 notes in 30 days (Opus 5.5: 134 vs 66 text blocks) were unsearchable | agent-infra `2f7e700` |
| Cost meter prices `claude-opus-5-5[1m]` exactly | It matched `claude-opus-5` by prefix: 25% high | agent-infra `86b6a5a` |
| SDK callers parse by block type; canary passes temperature via `extra_body` | SDK 1.x; thinking-first replies | agent-infra `92251cc` |
| New subagent death class: the Opus 5.5 AUP stop | Lane E | ~/.claude `6c016db` |
| Fable agent bodies: plan status corrected, bounded research off `opus-low` | Opus 5.5 at `low` scores DRACO 72.5 / WANDR 31.2 | `~/.claude/agents` (untracked) |

## 4. Claude Code 2.1.278 → 2.1.280 (binary diff, lane C)

- The Fable-era prompt blocks (`autonomy_append`, `delivering_work_max`, `willow_tern`) are byte-identical and do not reach Opus 5.5. The autonomy block is gated on `fable_5_mitigations OR amber_astrolabe`, with no interactive/headless check; `CLAUDE_CODE_AMBER_ASTROLABE=1` forces it on for any model. Left off: undocumented codename switch, no measured need.
- The new `opus_5_5_prompt_bundle` enables two features: `silent_turn_reminder` (server text every 5 turns: "The user hasn't heard from you in a while — say in a few words what you're doing, then continue.") and a display-only narration hint.
- New model-facing text: a `sharesCwd` note for unisolated parallel agents, a responsive-mode plugin (off by default), content-fallback notices, `<pasted_content>` wrapping in place.
- Changelog items that touch us: subagent reports no longer lost on compaction; messages to background subagents no longer lost in headless sessions; subagent results arrive under a header so their text cannot pass as instructions; a bug that moved `~/.claude/skills` entries to `.trash` is fixed (8 items moved today, all claude.ai account-synced copies of skills switched off in `skillOverrides`; nothing canonical lost).

## 5. Model-pin sweep

(filled in from the sweep result files)

## 6. Deferred, with reasons

- **Wrapping external text in dispatch packets as `<pasted_content>`.** Card §6.5.1 supports it, but llmx context packing serves every provider and the prompt cache; a format change needs a canary, and no injection incident has been seen in our packets. Logged as a proposal in `improvement-log.md`.
- **Effort map.** model-guide (peer-updated today) already carries the 5.5 effort guidance.
- **`calibration-canary` max_tokens 30/80.** Fine for the Haiku default; would starve a thinking model's text. Latent, noted.
