claude-opus-5-5

**Verdict:** Two live defects and one constitution gap. `posttool-bash-poll.sh` points the model at the removed TaskOutput tool (CC 2.1.277). `~/.codex/config.toml:4` sets a dead `personality` key. The three protected-data PreToolUse guards fail OPEN through `trap 'exit 0' ERR`, and CC 2.1.295 `onFailure:"block"` now fixes that natively. Biggest shrink candidates: `attribution` setting, Agent `effort` param (3 wrapper agents), `RETRY_WATCHDOG` knobs for unattended lanes, and Codex SessionEnd/PreCompact parity.

[DATA] [INFERENCE] [SOURCE: https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md] [SOURCE: https://github.com/openai/codex/releases] [UNVERIFIED items marked inline]

# Vendor delta: Claude Code + Codex CLI, 2026-09-17 → 2026-10-21

Scope: Claude Code (installed 2.1.306) and codex-cli (installed 0.162.0) changes in window; builds on
`research/trending-scout-2026-09-17.md` and `research/claude-code-native-features-deferred.md` (not repeated).


## Claude Code 2.1.275 → 2.1.306 (32 releases in window)

Source for every CC row: raw CHANGELOG fetched 2026-10-21 (`https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`), cited as `CL:<line>` in that file's numbering. [DATA]
Already adopted in window, not re-reported: Claude Mods (2.1.287; `mods/` in agent-infra@9833280d), `/goal` (ideas.md@7ef35786), `claude agents --json`, `claude plugin eval`, `/code-review` CLAUDE.md findings (ideas.md@c827f7c8).

### Category 2 — breaking changes that hit us (fix first)

| Ver | Change | Our surface | Action |
|---|---|---|---|
| 2.1.277 | "Removed the deprecated TaskOutput tool; Claude reads a background task's output file with Read instead" (CL:2243) | `~/Projects/skills/hooks/posttool-bash-poll.sh:92-109`, wired at `~/.claude/settings.json:322`: its block message tells the model to `ToolSearch(select:TaskOutput,…)` then `TaskOutput block=true` — a tool that no longer exists [DATA] | Rewrite the hint to "arm one `run_in_background` watcher (you are notified on exit) or Read the output file once"; drop the parent/subagent split. Cost: ~10 lines + hook test |
| 2.1.300 | PreToolUse/PermissionRequest `updatedInput` "now validated like Claude's own input: unknown keys are dropped, and input the tool rejects denies the call" (CL:318) | 8 mutators emit `updatedInput`: `pretool-bash-dispatch.py:837,871,2825` (chains mutators), `pretool-uv-python-guard.py:175`, `pretool-git-noext-inject.sh`, `pretool-pyunbuffered-inject.sh`, `pretool-subagent-gate.sh`, `pretool-bare-modal-guard.py`, `pretool-emb-project-guard.py`, `pretool-arc-agi-agent-cwd-guard.py` [DATA] | A malformed rewrite now DENIES the call instead of passing. Add one hooks-smoke case per mutator asserting the emitted object only has keys of the tool's schema (`command`, `timeout`, `description`, `run_in_background`, …). [INFERENCE] none observed broken; not live-probed |
| 2.1.299 | `UserPromptSubmit` hooks now run BEFORE a skill/slash command expands (CL:511); a skill's own front-matter UserPromptSubmit hook first fires on the NEXT prompt (CL:512) | 8 UserPromptSubmit hooks (`userprompt-prior-context.py`, `continuation-directive-guard.py`, `userprompt-session-limit-guard.py`, …) now see `/skill args`, not the expanded body [DATA] | Check `userprompt-prior-context.py` retrieval query: on `/research …` prompts it now embeds the literal command line, which is arguably better. No change unless a hook keyed on expanded skill text. [INFERENCE] |
| 2.1.299 | MCP allow rules exact-server: "`mcp__a` no longer allows a server named `a__b`"; agent `tools:` lists likewise (CL:502-503) | `~/.claude/settings.json` allow rules are all full tool names (`mcp__exa__web_search_exa`, `mcp__fmp__…`) [DATA]; agent `tools:` lists grepped: only `~/Projects/evo/.claude/agents/researcher.md:4`, full names [DATA] | None — verified unaffected |
| 2.1.292 | "`<system-reminder>` tags written in a hook's output are escaped before they reach Claude" (CL:892) | No hook emits the tag; `userprompt-prior-context.py:117,130` only strips it from input [DATA] | None |
| 2.1.280 | Agent-type `PermissionRequest` hooks no longer run (CL:2137) | `settings.json` PermissionRequest has 1 hook, type `command` [DATA] | None |
| 2.1.288 | PreToolUse/PermissionRequest hooks whose matching fails or whose input can't serialize now BLOCK the call (CL:1209) | All 21 PreToolUse hooks | Fail-closed by vendor default on matcher error; matches constitution P10 spirit. Watch `hook-telemetry` for new blocks. [INFERENCE] |
| 2.1.285 → 2.1.288 | Background Bash/PowerShell now stop at their `timeout` (default 30 min, max 2 h) (CL:1529), then narrowed to unattended sessions only (`-p`, SDK, CI, cloud) (CL:1227) | `~/.claude/rules/wakeup-cadence.md:11` "Background jobs get reaped (observed at ~2-4 min and at ~57 min)" — the 30-min default explains part of the `-p` reaping class; the ~57-min and 2-4-min kills are not explained by this [INFERENCE] | Add one line to wakeup-cadence: in `-p`/SDK lanes pass `timeout` up to 7,200,000 ms on `run_in_background`; `bgrun` stays for >2 h. Cost: 1 line |
| 2.1.302 | Fork subagents (`subagent_type: "fork"`) on by default in `claude -p` and SDK (CL:164); a subagent's own Agent calls in `-p` run foreground by default (CL:165) | Headless dispatch (`justfile:892`, `lane run`, llmx claude lane) | Forks inherit the parent's full context — cheap via cache but they bypass `omitClaudeMd`-style trimming. Set `CLAUDE_CODE_FORK_SUBAGENT=0` only if a lane measures token blowup. [INFERENCE] |
| 2.1.284 / .285 / .302 | No configured permission mode → interactive and `-p` start in **auto** mode (CL:1645, 1535); 2.1.302 reverts `-p`/SDK on third-party/telemetry-off to `default` (CL:163) | Headless lanes that pass no `--permission-mode` | Pin `--permission-mode` explicitly in every dispatch recipe; `justfile:892` already passes `--permission-prompts none` but no mode [DATA] |

## Category 1 — Claude Code native features that delete or shrink our surfaces

| Ver | Change (source) | Replaces / shrinks | Action · cost |
|---|---|---|---|
| 2.1.295 | `onFailure: "block"` on command/http hooks: a hook that can't start, times out or exits with an unexpected code blocks the action (CL:620; docs `code.claude.com/docs/en/hooks.md` lines 447, 888-923) | `pretool-data-guard.sh:5-8`, `pretool-append-only-guard.sh:15`, `pretool-archive-guard.sh:12` all `trap 'exit 0' ERR` = **fail OPEN**, while constitution P10 says protected-data writes fail CLOSED [DATA] | Delete the ERR traps, add `"onFailure":"block"` to those 3 entries in `~/.claude/settings.json`. Closes a P10 gap and removes hand-rolled error handling. Codex has no `onFailure` (not in `developers.openai.com/codex/hooks.md`), so the Codex side stays covered only by the commit-time backstop. ~10 lines; hooks-smoke case with the script missing |
| 2.1.292 | Agent tool takes an `effort` parameter (CL:831) | `~/.claude/agents/fable-high.md`, `fable-low.md`, `opus-low.md` exist only to pin model+effort [DATA] | Delete the 3 wrapper agents once a call that passes `model`+`effort` directly is confirmed; update model-guide. [UNVERIFIED] whether the Agent tool's `model` accepts `fable`. ~3 files |
| 2.1.281 | `"attribution": false` hides all commit/PR attribution (CL:1877) | The harness injects a Co-Authored-By reminder every session that contradicts global `<git_rules>` "No co-author trailer"; `skills/hooks/commit-check-parse.py` / `pretool-commit-check.sh` catch it after the fact [DATA] | Set `"attribution": {"commit": "", "pr": ""}` (object form, since older CLIs skip a file holding the boolean, CL:1877). Removes a per-session conflicting instruction; the commit hook stays as backstop. 1 line |
| 2.1.288 / .293 | Path-scoped `.claude/rules` + nested CLAUDE.md now load on Write/Edit (CL:1205) and on Bash single-file `cat/head/tail/sed -n/grep` (CL:799) | Any hook that re-injects rule text on file touch. `rg` hits for `.claude/rules` in `pretool-source-remind.sh`, `posttool-citation-remind.sh`, `pretool-data-guard.sh` … are unclassified [UNVERIFIED] | Audit those hits; drop any reminder that only restates a path-scoped rule. 1 audit pass |
| 2.1.295/.301/.305 | `CLAUDE_CODE_RETRY_WATCHDOG` gains `_MAX_WAIT_MS`, `_MAX_USAGE_LIMIT_WAIT_MS`, `_USAGE_LIMIT_RECHECK_MS` (CL:633, 200, 11); it already fails fast on spend/credit errors (CL:3624) | Death-class retry handling for rate/usage limits in unattended lanes (`~/.claude/references/subagent-death-classes.md`, `wakeup-cadence.md` "Subagent death classes"); `rg RETRY_WATCHDOG` over scripts/justfile/skills/rules = 0 hits [DATA] | Set the watchdog + `_MAX_USAGE_LIMIT_WAIT_MS` in `lane run` / headless env, then shrink the manual rate-limit redispatch guidance. Needs one unattended run to measure |
| 2.1.296 | `autoCompactWindow` in subagent frontmatter / `--agents` (CL:539) | `justfile:833-892` sets `CLAUDE_CODE_AUTO_COMPACT_WINDOW` per launch for resume lanes; subagents had no knob | Put `autoCompactWindow` in `researcher.md`/`session-analyst.md` frontmatter for long research epochs. 2 lines |
| 2.1.296 / .280 | `--debug` logs each command hook's command, outcome and duration (CL:594); OTel `hook_execution_complete` carries output sizes (CL:2056) | Part of what `just hook-telemetry` / `hook-roi` measures by hand | Source hook latency from the native log before extending our timing code. 0 build |
| pre-window (docs only) | `UserPromptExpansion` hook fires when a typed `/command` expands; matches `command_name` (hooks.md:1519-1529) — not in prior sweep's unwired list | Transcript mining of typed `/commands` (memory `skills-subagent-channel-routing`) | One async logging hook gives typed-skill usage directly. ~20 lines |
| 2.1.277 | TaskOutput removed | `posttool-bash-poll.sh` TaskOutput branch (see Category 2) | Shrinks the hook |

Not deletions (decide, don't build): **idle compaction** (2.1.299, CL:346-347): a ≥200K-token session idle ~54 min is compacted before the 1 h cache expires; `"idleCompaction": false` disables. Interplay with `precompact-goal-guard.py` (blocks up to 5×) and `autoCompactWindow: 320000` is [UNVERIFIED]: does idle compaction fire PreCompact, and does a block cancel it? Probe once before relying on it.

## Category 3 — Claude Code, other improvements (one line each)

- `/doctor prompt-audit` (2.1.283, CL:1691): audits CLAUDE.md, skills, agents for older-model prompting; free input to the instruction-mass lever. Cost: one run.
- OTel `cache_creation_5m_tokens` / `_1h_tokens` (2.1.300, CL:255): split cache-write cost for `eval-token-costs.md`. Cost: parse 2 fields.
- Transcripts now record each request's system prompt, tools and params (2.1.300, CL:315): exact request replay for forensics; also transcript growth under `cleanupPeriodDays: 365`. Check agentlogs ingest skips/handles the new record. [UNVERIFIED]
- Subagent results now arrive under a "subagent output" header (2.1.277, CL:2240): native injection fence; nothing to add.
- Read `allow_large` (2.1.296, CL:543) and `CLAUDE_CODE_DISABLE_FILE_MENTIONS` (2.1.299, CL:345): context control at 0 cost.
- `--bare` now connects only CLI-named MCP servers and sends no system reminders (2.1.286, CL:1408): cheaper headless probes. 0 cost.
- `prompt`/`agent` hooks written as instructions no longer allow what they should block (2.1.294, CL:766-767); max 12 concurrent per event (2.1.302, CL:168). Relevant if `SMART_JUDGE_*` uses prompt hooks.
- Mods API drift since our 2.1.289 build: Text `bold` deprecated for `weight` (CL:350), hook `.catch` runs only on throw/timeout (CL:243), `$.env.set` resolves `{}`/`{deny}` (CL:244), `settings.read` gets each layer (CL:105). Run `claude plugin test` on `mods/*`. [UNVERIFIED] which mods use these.
- Models: Opus 5.5 (2.1.280), Sonnet 5.5 (2.1.284), Haiku 5.5 $0.10/$0.50 (2.1.293, CL:771) — confirm model-guide lists Haiku 5.5.
- WebSearch budget refills 100/h (2.1.290, CL:1087); 529 backoff knobs `CLAUDE_CODE_OVERLOADED_RETRY_*` (2.1.292/.296).

## Codex CLI 0.155 → 0.163 (0.150–0.154 covered by trending-scout-2026-09-17 §3)

Source: `gh release view rust-v<N> -R openai/codex` for each tag, fetched 2026-10-21 (PR numbers cited); hooks docs `https://developers.openai.com/codex/hooks.md`. 0.163.0 (2026-10-15) is out; installed 0.162.0. [DATA]

**Category 1 — native features that shrink ours**

| Ver | Change | Our surface | Action |
|---|---|---|---|
| 0.156 / 0.162 | Worktree support on by default (#46839, #45276); managed Git worktree create/list tools (#50148) | `lane run` worktree primitive for Codex lanes | Evaluate native worktrees for Codex lanes before extending `lane`. Eval only |
| docs (version not in 0.155–0.163 notes) | Codex hooks docs list `SessionEnd`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Interrupt` | `~/.codex/hooks.json` wires 7 events (PermissionRequest, PostCompact, PostToolUse, PreToolUse, SessionStart, Stop, UserPromptSubmit) while CC wires SessionEnd×3, PreCompact×3, SubagentStart/Stop [DATA]; `codex_hook_shim.py:51-61` JSON event set lacks SessionEnd/PreCompact | Extend `codex_parity_sync.py` to mirror SessionEnd + PreCompact (+ Subagent*) and add them to the shim's event sets. [UNVERIFIED] whether the omission is deliberate |
| 0.163 | Independent read-only tools run in parallel (#52245) | none | Free on upgrade |

**Category 2 — breaks / deprecations**

| Ver | Change | Our surface | Action |
|---|---|---|---|
| 0.156 | `friendly`/`pragmatic` personality settings no longer select styles (#45809, #44935) | `~/.codex/config.toml:4` `personality = "pragmatic"` = dead key [DATA] | Delete the line |
| 0.163 | Patched zsh backend removed; retired shell flags get a migration notice (#52160, #52213) | `config.toml` has no zsh/shell-backend keys (grep) [DATA] | Upgrade to 0.163 is safe on this axis |
| 0.159 | `tui.prompt_suggestions` setting removed (#48621); bundled `plugin-creator` skill removed (#48604) | not set; not referenced | None |
| 0.155 / 0.158 | Hook commands detached from the controlling terminal (#43876), no hang on blocked stdin (#44288), native POSIX spawn (#47610) | `codex_hook_shim.py:_resolve_agent_tty` walks parent pids for the tab title | Still firing: `~/.codex/log/hook_shim_invocations.jsonl` last entries 2026-10-21T14:38 SessionStart/UserPromptSubmit [DATA]. Re-check after 0.163 upgrade |
| 0.155 | SessionStart hooks distinguish forked sessions (#44349) | Shim passes `source` through to CC-shaped hooks; `sessionstart-compact-resume.sh` matches `compact` | Confirm the fork value doesn't hit a CC hook expecting startup/resume/clear/compact. [UNVERIFIED] |
| 0.162 | Partial-history subagent forks removed (#51329) | none known | None |

**Category 3 — other**
- 0.159 opt-in `instant_interrupt` (#48135): steer mid-response; 0.163 makes follow-up steering default (#51812). Free.
- 0.161 GPT-6.1 Sol default model (#49318): matches llmx routing (gpt-6-sol → 6.1-sol). None.
- 0.162 honors `Retry-After` (#50418, #51440): fewer premature 429 failures in codex-cli lanes. Free on upgrade.
- 0.156 opt-in compaction after final responses (#46541); 0.155 memory v2 with configurable versions (#43797): `features.memories = true` is on; no change.
- 0.163 `/config` search UI (#52990). Cosmetic.

## Search record

Search record: raw CC CHANGELOG (2.1.275–306 filtered by `scripts/filt.py` in session scratchpad); `code.claude.com/docs/en/hooks.md`; `gh release view` codex 0.155–0.163; `developers.openai.com/codex/hooks.md`; local greps over `~/.claude/settings.json`, `~/.claude/agents`, `~/Projects/skills/hooks`, `~/.codex/config.toml`, `~/.codex/hooks.json`, `scripts/codex_hook_shim.py`. Not read: docs/vendor/*.json beyond the latest tag (each holds one release); binary-extracts diffs (daily vendor-sync already commits them); Codex changelog page on developers.openai.com.
