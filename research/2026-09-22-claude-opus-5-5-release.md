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
| Claude Code | 2.1.280 installed; vendor sweep captured | agent-infra `7b608cd` |
| anthropic SDK + inspect-ai | 0.107.1 → 1.8.0 and 0.3.205 → 0.3.266 (inspect needs anthropic ≥1.0 since 0.3.260; httpx2) | agent-infra `5d416c5`; 827 tests, claim_bench 221, smoke, offline MockTransport check |
| claude-agent-sdk, fastmcp, openai | 0.2.157, 3.4.7, 2.54.0 | `f9d64d0`, `f9f1e39`, `13d4e3b` |
| exa-py, google-genai, modal | 2.22.2, 2.25.0, 1.5.5 | `569312d` |
| llmx | claude-opus-5-5 registered; Claude defaults → 5.5; Sonnet 5 priced $2/$10 | llmx `1c7d195`, `80641cd` |
| uv | 0.11.16 → 0.12.17; the one behaviour change that could reach hooks (`uv run <script.py>` discovers the script's project) does not apply: every shared surface runs `uv run [--no-project] python3 <script>` | `uv self update` |
| Codex CLI | 0.153.4 → 0.155.1; hook compat 539 pass, MCP smoke pass, `.codex/` mirrors in sync | npm global |
| Skill mirror | 5 links removed from `~/.agents/skills` for skills switched off in `skillOverrides` | `sync_agent_skills.py` |
| Test suite | 3 failed / 17 errors from the 09-02 prune → 825 passed | agent-infra `18aeaad` |

## 3. Harness changes

| Change | Why | Commit |
|---|---|---|
| Bash dispatcher blocks recursive cloud deletes (`gsutil rm -r`, `gcloud storage rm --recursive`, `aws s3 rm --recursive`, bucket deletes) and `history -c`, including one level inside `bash -c`/`xargs` | Card §6.3.1 hallucinated destructive commands; `modal volume rm` excluded (17 legitimate genomics uses in 30 days) | skills `a3c5362` |
| Universal dispatcher flags quotes attributed to the user in Agent prompts and SendMessage bodies when no user message in the session contains them; advisory plus trigger log | Card §6.3.1 fabricated authorization; backtest 736 real dispatches, 5 with quotes, 0 flagged | skills `058a813` |
| Dispatch guards recognize Opus 5.5 (subscription allowlist; the concurrency advisory missed Opus 5 and 5.5) | Stale patterns; arc-agi twin definition is gone | skills `97a8aa2` |
| agentlogs indexes narration stored in thinking blocks as `assistant_update` (parser `2026-09-22.1`) | 2,508 notes in 30 days (Opus 5.5: 134 vs 66 text blocks) were unsearchable | agent-infra `cf03607` |
| Cost meter prices `claude-opus-5-5[1m]` exactly | It matched `claude-opus-5` by prefix: 25% high | agent-infra `ef8b279` |
| SDK callers parse by block type; canary passes temperature via `extra_body` | SDK 1.x; thinking-first replies | agent-infra `5d416c5`, skills `5194a77` |
| Commit guard blocks `git commit -- <paths>` when a listed path has staged and unstaged changes; a git error (exit 128) no longer counts | A sweep worker committed a peer's WIP twice this way (§5) | skills `f10ce69`, `4b16bb5` |
| Cat guard checks only a `$(cat …)` the shell would execute, via a shared lexer (`live_mask`); one token filter for its three callers | Three false blocks in this session: text in `<<'EOF'` bodies and an escaped `\$(` | skills `a8e2812` |
| New subagent death class: the Opus 5.5 AUP stop | Lane E | ~/.claude `6c016db` |
| Fable agent bodies: plan status corrected, bounded research off `opus-low` | Opus 5.5 at `low` scores DRACO 72.5 / WANDR 31.2 | `~/.claude/agents` (untracked) |

## 4. Claude Code 2.1.278 → 2.1.280 (binary diff, lane C)

- The Fable-era prompt blocks (`autonomy_append`, `delivering_work_max`, `willow_tern`) are byte-identical and do not reach Opus 5.5. The autonomy block is gated on `fable_5_mitigations OR amber_astrolabe`, with no interactive/headless check; `CLAUDE_CODE_AMBER_ASTROLABE=1` forces it on for any model. Left off: undocumented codename switch, no measured need.
- The new `opus_5_5_prompt_bundle` enables two features: `silent_turn_reminder` (server text every 5 turns: "The user hasn't heard from you in a while — say in a few words what you're doing, then continue.") and a display-only narration hint.
- New model-facing text: a `sharesCwd` note for unisolated parallel agents, a responsive-mode plugin (off by default), content-fallback notices, `<pasted_content>` wrapping in place.
- Changelog items that touch us: subagent reports no longer lost on compaction; messages to background subagents no longer lost in headless sessions; subagent results arrive under a header so their text cannot pass as instructions; a bug that moved `~/.claude/skills` entries to `.trash` is fixed (8 items moved today, all claude.ai account-synced copies of skills switched off in `skillOverrides`; nothing canonical lost).

## 5. Model-pin sweep

Operator, 2026-09-22: "remove all these old settings or none at all … we should use the newest models". The policy and its alternatives are in `decisions/2026-09-22-model-pins-track-newest.md`. Four Sonnet 5 workers each took a set of repos and shared one mapping and keep-rules file. Every live pin moved; every record stayed. Result files: `scratchpad/opus55/sweep/W{1..4}-result.md` (session 916e6e99).

Mapping: Opus 4.x/5 → `claude-opus-5-5`, or the `opus` alias where the caller is `claude --model`; Fable 5 → `claude-fable-5-1`; Sonnet 4.x → `claude-sonnet-5`; GPT flagship roles and the retired `gpt-5.5` (llmx exit 2) → `gpt-6-astra`; metered cheap roles → `gpt-5.6-luna`; Gemini flash → `gemini-3.8-flash`, pro → `gemini-3.1-pro-preview`, flash-lite → `gemini-3.5-flash-lite`. Haiku 4.5 stays.

| Repo | Commit | What moved | Checks |
|---|---|---|---|
| skills | `b42a22f`, `6d8d2f0`, `4f2542c` | 24 edits in 9 files: critique preflight probes, the `claude_review` dispatch profile, llmx-guide how-tos, raw-OpenAI guard advice; `lane` Claude workers on `opus`; person-into-scene's Flash localizer line | 165 hook + 86 critique tests |
| llmx | `c8cdad7` | SVG fallback, review_plan, README examples; `_MODEL_UPGRADES["gpt-4o-mini"]` pointed at another retired id (`gpt-5.1-mini`) | 180 pass; the 1 failure is the Grok 4.7 peer's in-flight test |
| substrate | `58645bd` | pdf_llm, figure_extract, resolve_references defaults; evalcore docstrings | 281 + 21 |
| research-mcp | `8aa545c` | extraction, rcs, pdf_llm, the Modal Marker config; cag.py's broad/focused pair split lite/full | 71 |
| emb | `536596d` | contextualize default (was `gemini-2.0-flash`) | 171 |
| imagegen | `92e87f7` | four QC, inspect and label defaults | 54 |
| intel | `ba95eee7`, `d71e988e` | 36 files: `gpt-5.5` → astra (~30), `gpt-5.3-chat-latest` → luna (4, metered bulk role), flash (~40), flash-lite, opus-4-8 → 5-5 (11); pricing rows added beside the old ones; the `--deep` tier dropped once both tiers mapped to one id | 108 targeted pass; the full suite's 22 failures predate the sweep (unmounted external volume, unrelated matcher tests) |
| personal, anim-workbench, evo, observer | `ba390477`, `bf05842`, `5f1322c`, `7745667` | psg critique table and essay-pilot judge; outer-loop `claude --model opus`, heretic lane, pulse review; overview script; style-eval default | syntax, build and JSON checks (no suites) |
| evals | `67a1107` | 28 files: the shared judge block in 9 configs and the template, evalcore examples, eval scripts | evalcore self-tests + 38 pytest |
| genomics | `c8e899e1c` | verifier_policy: Anthropic biology lane → `claude-opus-5` (rule F), Gemini → 3.8-flash; six GPT defaults; cost tables gained rows and kept history | 5,327 pass |
| agent-infra | `4f9521c` | claim_bench judge defaults, behavioral replay, debug_until_dry, repo-summary aliases, clash_detect | 827 + 221 |
| immigration-research | none | ~500 hits, all provenance strings in dated results | — |

Kept, by rule: registries, pricing and capability tables; dated records and memos; model docs, including the vendored claude-api examples and model-guide; pattern matchers; test fixtures; the biology and cyber lanes pinned to exact older IDs; completed experiment arms (evals bake-off candidates, the `frontier_verify_edge` stale-floor arm). One more pin sat outside any repo: `session-phases/03-env-export.sh` had exported `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-4-6` to every shell since before Sonnet 4.6 retired (2026-07-07), pinning subagents of every Bash-launched `claude`. The export is removed (untracked file).

What the sweep found beyond version strings:

- **Two-tier pairs collapse under a flat mapping.** research-mcp `cag.py` would have put both tiers on one id, the bug its 2026-06-01 comment records; broad moved to flash-lite instead. intel's extract_episode tiers collapsed, so the dead `--deep` flag was removed.
- **Metered cost rose.** intel calls GPT through the metered SDK: `gpt-6-astra` is $10/$50 per MTok, about 3.3× `gpt-5.5`, so `unit_shipment`'s budget gate moved from $0.015 to $0.05 per call. Routing those calls through `--subscription` is the operator's call.
- **Deferred:** `gemini_model_name` in the local Marker config (substrate and research-mcp `pdf_marker.py`). A peer's in-flight rewrite changed its tier, so the pick belongs to that rewrite. The Modal Marker app runs the old default until redeployed; the redeploy was not done.
- **Incidents:** a worker's `git commit -- <paths>` pulled a peer's uncommitted work into two commits (reset, then guarded: §3). Editing genomics main in place left `scripts/` dirty through two ~5-minute test runs, and genomics launches refuse a dirty tree, so a peer's batch row died. Repos whose runners gate on a clean tree need edits in a worktree.
- **Loose ends for owners:** llmx `PROVIDER_CONFIGS["anthropic"]["legacy_model"]` is never read. Some prose is now stale: evals `run_case_gpt.py` and `gdpval/config.toml`, and claim_bench's Gemini 2.5 price comment. evals `frontier_incorpus_edge/config.toml` is untracked, and its judges still name `gpt-5.5`, which exits 2. OpenRouter has no Opus 5.5 slug yet for intel's pricing anchors. The genomics touch-log hook did not record a teammate's edits, so its ownership guard attributed the file to another session.

## 6. Deferred, with reasons

- **Wrapping external text in dispatch packets as `<pasted_content>`.** Card §6.5.1 supports it, but llmx context packing serves every provider and the prompt cache; a format change needs a canary, and no injection incident has been seen in our packets. Logged as a proposal in `improvement-log.md`.
- **Effort map.** model-guide (peer-updated today) already carries the 5.5 effort guidance.
- **`calibration-canary` max_tokens 30/80.** Fine for the Haiku default; would starve a thinking model's text. Latent, noted.
