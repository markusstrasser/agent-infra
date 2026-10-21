claude-opus-5-5

**Verdict:** Twelve findings. The two largest: (1) bare `python3` in hook commands has resolved to Apple's Python 3.9.6 since about 2026-10-14, so five hook modules crash on import. That silently disables the live-batch edit guard, the source-check validator, the backtick-commit guard and the background-commit guard: 3,112 crash events in 23 of 32 operator sessions, still happening today. (2) UserPromptSubmit advisories fire on task notifications and peer relays. 62% of PRIOR-CONTEXT injections and 72% of DISK LOW injections answer harness frames rather than the operator, about 110K tokens of injected context in 7 days. A third finding breaks the instrument itself: about 47% of operator prompts (queued mid-turn) are invisible to the shared operator-text predicate and are stored as `role=system` in agentlogs. Analysis only. No hooks, rules or settings were edited and nothing was committed.

## Scope and denominators

- Sessions: Claude `sessions.session_role='operator'` with `end_ts >= 2026-10-14`, excluding this session. 32 sessions; scanned 352,935 lines, parsed 352,935, 0 missing files. This includes the four named sessions: genomics 1cce6699 (92,796 lines, 43 compactions) and 4cc7a0b4 (99,406 lines, 62 compactions), immigration-research 74db9a8f (9,499 lines, 3 compactions) and pitchtest db491c87 (31,648 lines, 19 compactions).
- Codex: 40 operator sessions. Only the hook-shim log was mined (`~/.codex/log/hook_shim_invocations.jsonl`, 247,866 rows since 10-14), not the Codex transcripts turn by turn.
- Method: deterministic stream miners over raw JSONL (scripts in the scratchpad: `hookmine.py`, `retry.py`, `advisory.py`, `pc.py`, `ctx.py`, `ctxq.py`). Every quoted turn was read in context. The skill's Gemini classify pass and the fast_extract precision pass were not run, because every finding here is backed by counts plus raw turns. No signals were staged and nothing was promoted; promotion is the parent's call.
- Mined: 7,874 hook events (4,193 additional_context, 3,299 non-blocking errors, 64 blocking, 252 system messages, 66 Stop summaries), 413 tool denials and 1,027 operator texts (540 typed plus 487 queued; see F3).
- Skipped as parent-owned: SubagentStop epistemic-gate visibility, the pretool-terse-bash cat nag, worktree-cd-guard (`cd $S`, plus the 60 literal-worktree-path cd blocks, the largest denial class at 110), PreToolUse:Agent subagent-gate advisories (SUBAGENT FILE EDIT, WRITE-FIRST, WAIT DISCIPLINE and others, 226 fires, 139KB), and the vendor changelog.

## Findings

### F1. Hook interpreter drift: `python3` means 3.9.6, and four guards are silently dead (NOVEL)

- **Evidence:** 3,112 `hook_non_blocking_error` events with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`, in 23 of 32 sessions, from 2026-10-13T15:31Z to 2026-10-21T07:45Z:

  | Hook | Errors |
  |---|---|
  | pretool-live-batch-edit-guard.py on Edit | 1,653 |
  | pretool-live-batch-edit-guard.py on Write | 971 |
  | postwrite-source-check.sh → source-check-validator.py | 484 |

  First seen in 4cc7a0b4 and 74db9a8f (immigration-research 74db9a8f's first Write error is shown in its own transcript). `/opt/homebrew/bin/python3` no longer exists (only `python3.14`, relinked 2026-10-13 23:49 JST), so `/usr/bin/python3` (3.9.6) serves every settings entry that says `python3 <hook>`. Running every module under `skills/hooks/` with 3.9 shows five crash at import: the two above, plus `pretool_bash_backtick_guard.py`, `pretool_no_background_commit.py` and `posttool_research_reformat.py`. The last three are loaded inside `pretool-bash-dispatch.py`, which catches the exception and fails open.
- **Positive control:** the payload `git commit -m "fix \`foo\` thing"` is BLOCKED by `pretool-bash-dispatch.py` under python3.14. Under `/usr/bin/python3` it passes with only a COMMIT CHECK advisory.
- **Why the regression check missed it:** `just hooks-smoke` reports pass=166 because it runs under `uv run --no-project`, which puts `.venv/bin/python3` (3.13) first on PATH. A minimal hook PATH gives `/usr/bin/python3` 3.9.6.
- **Recurrence:** every Edit/Write and every Bash call in every session for 8 days.
- **Fix (hook/infra, not prose):** pin the interpreter in settings. Use an absolute `/opt/homebrew/bin/python3.14`, or `uv run --no-project`, or a `#!` plus executable bit. Add `from __future__ import annotations` as belt and braces. Make hooks-smoke run each configured command under a hook-equivalent PATH, and fail it on any `Traceback` in stderr even when rc is non-blocking. Add a doctor check that `command -v python3` in hook env is ≥3.10.

### F2. UserPromptSubmit advisories fire on harness frames (HAD-PARTS: the predicate exists in `agentlogs.authorship`, but the hooks don't load it)

The trigger prompt was taken from the preceding `queued_command` or user line:

| Advisory | Fires | On task-notification or peer frames | Bytes (frames / total) |
|---|---|---|---|
| PRIOR-CONTEXT | 178 | 111 (62%) | 243KB / 367KB |
| DISK LOW (additionalContext) | 209 | 150 (72%) | 232KB / 329KB |
| POINTER-DISPOSITION | 20 | 7 | 14KB / 22KB |
| CONTINUATION DIRECTIVE | 19 | 9 | 4KB / 10KB |
| [clock] | 2,935 | 1,902 | cheap (29B) |

- The CONTINUATION DIRECTIVE tells the model that "this prompt is a request to RESUME the prior task". On a task notification that statement is false.
- **Example:** genomics 1cce6699 L9725 is a `<task-notification>` for an agent output file. The PRIOR-CONTEXT fire at L9727 then lists the topics `[cce6699-dd28-…, users-alien-projects-genomics]`.
- **Fix (narrow):** one shared guard at the top of each UserPromptSubmit hook that exits 0 when the prompt is a harness frame (`origin.kind != human`, or a `<task-notification>` or peer-relay prefix). Load `src/agentlogs/authorship.py` by path, the same way `transcript_text.is_operator_authored` does. One definition, no new copy.

### F3. Queued operator prompts are invisible to operator-text instruments (NOVEL)

- **Evidence:** 494 `queued_command` attachments carry typed operator prompts (for example 4cc7a0b4 L95666, 1cce6699 L9182 and L8243). 487 of them never appear as `type=user` lines. `transcript_text.user_texts()` returns 540 operator texts across the 32 sessions, so it misses about 47% of the operator's input. That share is concentrated in long multi-agent sessions: 4cc7a0b4 has 132 queued human prompts against 111 typed ones.
- agentlogs ingests the `queue-operation` record as `role=system`, `vendor_kind=queue-operation` (`src/agentlogs/adapters/claude*.py` L118, `_parse_status_record`). 4cc7a0b4 has 1,895 such rows, and the operator question "are you rerunning a lot of syn5 and syn7?" sits among them.
- **Effect:** `/observe --corrections`, supervision-audit, blindspot and prior-context mining undercount corrections exactly where supervision is heaviest.
- **Fix (code):** extend `user_texts` and `claude_line_author` to read `attachment.type=='queued_command'` (with `origin.kind`), and make the adapter emit those rows as `role=user` with the authorship label. Add a drift test on a fixture line, then reindex.

### F4. DISK LOW repeats the same genomics worktree list into every prompt of every project (NOVEL)

- **Evidence:** 252 additionalContext fires in 22 sessions, 411KB (about 103K tokens), averaging 1.6KB each. Each lists genomics worktree reclaim candidates with archive commands. There are only 99 distinct candidate sets in those 252 fires; for example, 4cc7a0b4 had 55 fires with 3 distinct sets. It also fires in unrelated chats: personal 3ccd765c (an Osaka pharmacy question), immigration-research 70c56864 (the fall of Rome), and publishing, arena and arc-agi sessions. Each fire is also mirrored as a 252× `hook_system_message` banner to the operator.
- **Operator signal:** 32a06105 L179: "the agents working inside these repos have to know about their worktrees Not the rest!"
- It does change behavior in genomics, where 350 `worktree_gc` tool calls followed. So narrow it rather than delete it.
- **Fix (narrow):** list candidates only for the cwd's repo. Re-inject only when the candidate set or the free-GB band changes; otherwise send a one-line `DISK LOW: X GB`. Skip harness frames (F2).

### F5. The `$(cat …)` missing-file guard false-positives on its own house wait pattern (HAD-PARTS: improvement-log L4353 fixed the heredoc and escape FP class)

- **Evidence:** 72 blocks in 7 sessions, the second-largest denial class. By shape:

  | Shape | Blocks | Sessions |
  |---|---|---|
  | `until/while [ -f X ]; do sleep; done; echo $(cat X)` | 44 | 6 |
  | `bgrun --wait name; $(cat name.done)` | 11 | 3 |
  | `cd DIR && … $(cat relpath)`, path resolved against the pre-cd cwd (4cc7a0b4 L92380, L98768; 864bba94 L701, L7016) | ~9 | — |
  | `test -f X && $(cat X)` (1cce6699 L28410) | 1 | — |
  | `until [ -s X ]` / `until grep -q` forms | some | — |
  | Nested `$(cat $(git rev-parse …))` parsed as file "rev-parse" (4cc7a0b4 L13540) | 1 | — |

  Examples of the wait-loop shape: 4cc7a0b4 L4414, L6405, L16523. Every observed block reads as a false positive. The `posttool-bgrun-watcher-nudge.sh` advisory and the wakeup-cadence rule prescribe this exact `until [ -f X.done ]…$(cat X.done)` watcher, so one hook teaches what another blocks. 33 of 72 next calls were near-identical rewrites (one wasted round trip each); 6 were blocked again.
- **Fix (narrow):** exempt paths guarded earlier in the same command by `-f`, `-s`, `test -f`, `grep -q` or `bgrun --wait`. Resolve relative paths after a leading `cd X &&`. Treat nested `$(` as opaque.

### F6. Two modal hooks teach opposite lessons about `timeout` (HAD-PARTS: improvement-log L740 and L4112 shipped both; the conflict is unlogged)

- **Evidence:** the "`timeout N` wraps a Modal/volume-crawl" block fired 24 times in 6 sessions (4cc7a0b4 ×12, 1cce6699 ×6, db491c87 ×3, 864bba94, 7efe9f03, cc1925f3). Most targets are read-only, bounded listings piped to `head`:
  - `timeout 60 modal volume ls … | head` (4cc7a0b4 L30017, L88845; 1cce6699 L25453)
  - `modal app list --json` and `container list` (4cc7a0b4 L58890, L61508; 1cce6699 L47163)
  - `modal app stop` (7efe9f03 L2870)

  At least two blocks were on grep pattern text alone (1cce6699 L71562 greps `timeout=`).
- Meanwhile `pretool_streaming_cli_guard.py` warns "Wrap each streaming invocation with: timeout 60" on `modal app logs` (6 fires in 4 sessions). Agents then build `& pid; sleep 20; kill` workarounds (4cc7a0b4 L31127, L61348). 17 of 24 crawl-guard blocks were followed by a near-identical retry. The block taught nothing across 6 sessions.
- **Fix (narrow):** one owner for the modal+timeout policy. Allow `timeout` on `modal volume ls` (one level), `app list`, `container list` and `app stop`. Match only on parsed argv, never on quoted grep patterns.

### F7. PRIOR-CONTEXT's TRIAGE-VERDICT instruction is ignored, and topic extraction matches path junk (HAD-PARTS: `94fb3ed` added the two-keyword floor; improvement-log L98)

- **Evidence:** 178 fires, 367KB. A reply opened with a triage verdict line in only 6 of 178 (3%). A cited ref (SHA or memo name) was touched in the next 15 tool calls in 67 of 178 (38%, which may be coincidental). 85 of 178 fires matched on session-UUID fragments or path slugs (`users-alien-projects-genomics`, `cce6699-dd28-…`, `private`): 193KB.
- Each fire carries about 850 chars of static TRIAGE-VERDICT and TRIAGE-DISPATCH prose (4cc7a0b4 L1805 shows the full text).
- **Fix (narrow):** strip path, UUID and hex tokens before keyword matching. Drop the static TRIAGE paragraphs; at 3% adoption they cost about 150KB in 7 days with no measurable effect. Keep the memo list. F2's frame guard removes most of the rest.

### F8. Repeated operator corrections on dispatch channel and model (NOVEL: no improvement-log or rule entry)

At least 9 corrections in 5 sessions in 7 days, pointing both ways:

- **Toward cheaper external execution:**
  - 75b08f57 L4942: "you ran a subagent claude opus again … not sol 6.1 … try to be more of an orchestrator"
  - 75b08f57 L28570 and 4cc7a0b4 L82702 (identical text, so a reused steering prompt): "Try to be more of orchestrator, designer… saving tokens"
  - 1cce6699 L40756: "Use gpt 6.1 sol for execution"
- **Toward native subagents:**
  - 1cce6699 L9182: "Why are you doing it like this [`LANE_CLAUDE_MODEL=claude-opus-5-5 … lane run`] instead of native claude code?"
  - 1cce6699 L26251: "Weird that you don't use the internal claude native subagent functions"
  - 4cc7a0b4 L1926: "again you can also run opus 5.5 as subagents … native claude code"
  - 1cce6699 L40758: "your own subagents are fine … might be more token efficient"
- **Channel mix in these sessions:** Agent 461 (335 with no model, which the MODEL-GUARD hook sets to opus; 107 opus; 19 sonnet), `lane run` 282 (171 codex, 25 claude, 86 default), `llmx chat` 204, `codex exec` 67. The wakeup-cadence rule sends agents to `lane run` after background reaps. MODEL-GUARD defaults unpinned Agent calls to opus. Neither states the operator's actual policy: Claude execution goes native, bulk execution goes to Sol via codex/llmx, and the parent keeps judgement.
- **Fix (rule, one line):** state the routing policy in one place (model-guide or `<subagent_usage>`). Give `lane run --worker claude` a reason to exist or drop it from the wakeup-cadence text. Optionally add "Try to be more of orchestrator…" to operator-deck as a known steer.

### F9. The wakeup-cadence rule tells agents to do what the harness blocks (NOVEL)

- **Evidence:** 29 native `Blocked: sleep N followed by …` denials in 10 sessions, for example 4cc7a0b4 ×9 and db491c87 ×4. The shape is `sleep 45; tail -5 …log.tmp` (4cc7a0b4 L38931, L43572). The rule `~/.claude/rules/wakeup-cadence.md:9` says "Job < 270s → synchronous Bash wait", while the Bash tool contract blocks foreground sleep and points to Monitor or an until-loop.
- **Fix (rule edit):** change it to "Job < 270s → one Bash call with `until <done-condition>; do sleep N; done` (never a bare leading sleep)", or point to Monitor. The fix depends on F5, because the guard currently blocks the until-loop's `$(cat X.done)`.

### F10. Relative hook paths fail whenever cwd is not the repo root (NOVEL)

- **Evidence:** the genomics `bio-constants-gate.sh` produced 166 `No such file or directory` errors in 4 genomics sessions (1cce6699, 4cc7a0b4, 864bba94, cc1925f3; first 10-12, last 10-21). Its command is `bash .claude/hooks/bio-constants-gate.sh` in `genomics/.claude/settings.local.json:66`. The gate is dead whenever the session sits in a worktree or subdirectory. In `personal/.claude/settings.json:58`, the relative `.claude/hooks/knowledge/ruff-format.sh` failed in personal (2 events; it also produced 2 such events on 10-20, not found in that session's listing here). One arc-agi Stop hook points at the missing `~/Projects/arc-agi/loop/research_reflex_lint.py` (a5695a83, 5 events; the arc-agi repo path no longer exists).
- **Fix:** use `"$CLAUDE_PROJECT_DIR"/.claude/hooks/…`. Add a lint in hooks-smoke for relative hook commands in all project settings, including `settings.local.json`.

### F11. Codex runs each Bash safety gate as its own process: about 2.2s of hook time per tool event (HAD-PARTS: the Claude side was consolidated into `pretool-bash-dispatch.py`; memory `codex-cli-project-parity`)

- **Evidence:** since 10-14 the shim log has 183,550 PreToolUse hook runs totalling 29,443s, plus 63,735 PostToolUse runs totalling 6,969s, across 13,650 tool events. That works out to about 2,157 ms of PreToolUse and 511 ms of PostToolUse per event. `~/.codex/hooks.json` has 26 PreToolUse hooks, 13 on the Bash matcher, each wrapped by `codex_hook_shim.py`, at roughly 200 ms each: `pretool-companion-remind`, `bash-loop-guard`, `corpus-remind`, `terse-bash`, `multiagent-commit-guard` and others.
- **Uncertain:** whether Codex runs these in parallel. Wall-clock latency is not measured; CPU-time is.
- Codex also lacks the gates that exist only inside the Claude dispatcher.
- **Fix:** point Codex's Bash matcher at the single `pretool-bash-dispatch.py` through the shim, and retire the separate copies. Measure per-call wall time before and after.

### F12. Over-deferral on technical calls (HAD-LEVER: memory `feedback_question_scope.md`; global `<technical_pushback>` "If the domain is ambiguous, defer")

- **Evidence:** spaced 7c2aa5ef L5695: "why do you need my taste here?" This came after the agent ended a turn with 4 questions and "I won't act on any of them until you answer"; it then conceded that 3 of the 4 were its own call. 7c2aa5ef L28534: "you're more math domain expert than me … Science/domain calls are yours." Both are in one session, and the lever already exists.
- **Fix (rule wording; operator-owned file, so propose only):** the ambiguous-domain default should be "decide technical/verifiable parts, ask only the taste/irreversible residue", not "defer". Under the HAD-LEVER grade this calls for an architecture fix: the `stop-loop-ended-on-question` hook could flag a turn ending in several questions where a technical-call heuristic matches. That is semantic, so it would be advisory only.

## Working as intended (keep)

| Mechanism | Evidence |
|---|---|
| CONTEXT NEAR AUTO-COMPACT Stop block | 62 fires in 16 sessions; 60 followed by a checkpoint write and 11 by a commit within 12 calls |
| Contested-file Stop advisory | 84 fires; 32 commits within 8 calls |
| `git add -A`, bg-ampersand, piped-commit and process-listing blocks | 7, 8, 6 and 3 fires; agents comply after one block (0–1 re-blocks each). The prose duplicates in global CLAUDE.md change nothing measurable, but this run cannot measure the counterfactual, so no delete is proposed |
| MEMORY PRESSURE Agent block | 7 in spaced 7c2aa5ef (6 parallel fires, then 1 identical retry); recurrence of improvement-log L2377, low cost |

## Grades (rg over improvement-log.md and .claude/rules, plus ~/.claude/rules where relevant)

| Grade | Findings |
|---|---|
| NOVEL | F1, F3, F4, F8, F9, F10 |
| HAD-PARTS | F2, F5, F6, F7, F11 |
| HAD-LEVER | F12 |

## Suggested order

1. F1: interpreter pin plus a smoke check under hook PATH.
2. F3: the instrument fix, before the next corrections or supervision run.
3. F2: one guard, which also removes most of F4 and F7.
4. F5 and F6: narrowing.
5. F10: `$CLAUDE_PROJECT_DIR`.
6. F9 and F8: rule wording.
7. F11: Codex dispatcher.
