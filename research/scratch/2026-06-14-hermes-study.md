# Hermes-Agent Study — What agent-infra Can Appropriate

**Date:** 2026-06-14. Target: `/Users/alien/Projects/best/hermes-agent` (NousResearch self-improving CLI agent, Python, MIT). Read-only study.

Standing constraint enforced throughout: AUTOMATED skill-graduation (auto-distill session trace → SKILL.md) is **VETOED** in agent-infra (`decisions/2026-05-28-autobrowse-graduation-not-built.md`; failure modes = no consumer, low-quality distillation). Hermes's skill-creation judged against that veto, not adopted blindly.

Scale note: 1.1M LOC Python. Files are huge (run_agent.py 241KB, cli.py 638KB, hermes_state.py 205KB). I read the load-bearing mechanism files, not the whole repo. Ignored all star/popularity claims per instructions.

---

## Architecture map

**Agent loop** — `agent/conversation_loop.py` (249KB) + `run_agent.py` (`AIAgent` class). Single long-running `AIAgent` that owns provider/model/credentials/system-prompt cache. The loop is a standard tool-calling turn loop with compression (`agent/context_compressor.py` 116KB), turn finalizer, retry state. Multi-provider adapters (`anthropic_adapter.py`, `codex_responses_adapter.py`, `gemini_native_adapter.py`, bedrock, azure) — model-agnostic by design.

**Persistent memory/state** — `hermes_state.py` (205KB) is the state store; `agent/memory_manager.py` (36KB) + `agent/memory_provider.py` manage MEMORY.md / USER.md on disk plus optional external providers (Honcho dialectic user-modeling, mem0, supermemory). Memory writes carry provenance metadata (`build_memory_write_metadata` in background_review.py:300 — write_origin, execution_context, session_id, platform).

**Sandboxed code execution via Unix-socket RPC** — `tools/code_execution_tool.py` (the "PTC" = Programmatic Tool Calling). See candidate #1.

**Sub-agent spawning** — `tools/delegate_tool.py` (`delegate_task`). Spawns child `AIAgent` instances, fresh context, restricted toolset, own task_id/terminal. Parallel via `ThreadPoolExecutor`. `MAX_DEPTH = 1` (flat: parent→child, no recursion by default — `delegate_task` is in `DELEGATE_BLOCKED_TOOLS` for children, delegate_tool.py:46). Parent blocks until children finish; only the summary returns to parent context.

**Multi-platform gateway** — `gateway/run.py` (16.5KB lines!) — one process serving Telegram/Discord/Slack/WhatsApp/Signal/Matrix/email. Per-platform adapters under `gateway/platforms/`. Cross-platform conversation continuity. Not relevant to agent-infra (single-user Claude Code on a laptop; no chat-platform surface).

**Cron/routines** — `cron/scheduler.py` (95KB), `cron/jobs.py` (46KB), `cron/blueprint_catalog.py`, `cron/suggestions.py`. See candidate #4. The `hermes-already-has-routines.md` file is a marketing comparison vs Claude Code Routines — NOT an implementation doc, but it points at the real mechanisms: `--script` injection, `--skills` chaining, `--deliver`, the `[SILENT]` no-op pattern.

**batch_runner.py** (57KB) + **mini_swe_runner.py** (28KB) — research/training infra: batch trajectory generation across tasks, and a minimal SWE-bench-style runner. For producing tool-calling training data + `trajectory_compressor.py` (69KB) compresses trajectories for training the next model. This is RL/datagen infra for training models — NOT relevant to agent-infra (we consume frontier models, don't train them).

**Skills system** — `tools/skills_hub.py` (148KB), `tools/skills_tool.py` (60KB), `tools/skill_manager_tool.py` (43KB), `tools/skills_guard.py` (44KB), `tools/skill_usage.py` (33KB), `agent/curator.py` (78KB), `agent/background_review.py`. agentskills.io-compatible. See candidates #2 + #3 (and the veto analysis).

---

## THE VETO ANALYSIS (most important section)

Hermes has TWO distinct autonomous-skill mechanisms. They must be judged separately.

### Mechanism A — `background_review.py`: post-turn skill MINTING (the part that mostly CONFLICTS with our veto)

`agent/background_review.py:573` `spawn_background_review_thread` — after a turn, `AIAgent.run_conversation` may fire a **daemon thread** that forks a fresh `AIAgent` (inherits parent runtime + cached system prompt for prefix-cache reuse, background_review.py:402-442), replays the conversation snapshot, and runs `_SKILL_REVIEW_PROMPT` with a tool whitelist of `{memory, skills}` only (background_review.py:470-483).

The prompt (background_review.py:45-148) is the smoking gun for our veto:
> "Be ACTIVE — most sessions produce at least one skill update, even if small. A pass that does nothing is a missed learning opportunity, **not a neutral outcome**." (lines 46-49)

**This is precisely the failure mode we vetoed.** A standing bias toward minting/patching on every session is exactly what produces low-signal sediment. There is **no consumer check** anywhere — the decision to mint is purely the review-agent's judgment of "did a non-trivial technique emerge."

BUT — and this is the part worth stealing — the prompt is unusually well-engineered against the *symptoms*:
1. **Strict prefer-patch-over-create hierarchy** (lines 70-105): (1) update a currently-loaded skill → (2) update existing umbrella → (3) add a `references/`/`templates/`/`scripts/` support file → (4) only then create a new class-level skill. Creating is the LAST resort.
2. **Explicit anti-narrow-naming rule** (lines 100-105): name MUST be class-level; MUST NOT be a PR number, error string, feature codename, library-alone name, or "fix-X/debug-Y/audit-Z-today" artifact. "If the proposed name only makes sense for today's task, it's wrong — fall back."
3. **A "Do NOT capture" blocklist** (lines 124-143) that is *genuinely good* and agent-infra lacks an explicit version of: never capture (a) environment-dependent failures (missing binaries, "command not found", unconfigured creds), (b) **negative claims about tools** ("X tool is broken", "cannot use Y") — "these harden into refusals the agent cites against itself for months after the actual problem was fixed", (c) transient errors that resolved, (d) one-off task narratives. Capture the FIX, never "this tool doesn't work."

**Verdict vs veto:** the MINTING TRIGGER (mint-by-default, no consumer) is a downgrade — do NOT adopt. The MINTING PROMPT'S NEGATIVE CONSTRAINTS (#2 + #3 above) are independently valuable and transferable to *any* knowledge-write path (our `/observe`→improvement-log, MEMORY.md appends). The "don't capture negative tool claims — they harden into self-cited refusals" rule is a real insight we don't encode.

### Mechanism B — `agent/curator.py`: background CONSOLIDATION (the part that is GOOD and largely SOLVES the sprawl the veto feared)

This is separate from minting. The curator is **inactivity-triggered** (no cron; runs after N idle hours, `should_run_now` curator.py:198), and its entire job is to *fight* skill sprawl:

- `CURATOR_REVIEW_PROMPT` (curator.py:344): "A collection of hundreds of narrow skills where each one captures one session's specific bug is a **FAILURE of the library — not a feature**." Target = CLASS-LEVEL umbrella skills with `references/`/`templates/`/`scripts/` subfiles. It clusters by prefix, merges siblings into umbrellas, demotes narrow content to support files, archives (never deletes — "Archives are recoverable; deletion is not", line 362).
- **Provenance-scoped (the key safety property):** the curator ONLY touches skills the agent autonomously created. `tools/skill_provenance.py` is a ContextVar (`BACKGROUND_REVIEW`) set during the review fork; `skill_usage.is_curation_eligible`/`_is_curator_managed_record` (skill_usage.py:431,449) gate on `created_by == "agent"`. **User-authored skills are never auto-curated.** This is the exact guard our autoDream veto wanted (autoDream was vetoed because native memory pruning DELETES user files — see `autodream-disabled-append-only-conflict.md`). Hermes shows the clean version: provenance-scope + archive-not-delete.
- **DRY-RUN + human approval gate:** `CURATOR_PREVIEW_PROMPT` (curator.py:~318) — a preview pass produces "the actions you WOULD take" as a deliverable; "A downstream reviewer will read the report and decide whether to approve a live run with `hermes curator run` (no flag)." So consolidation defaults to propose-and-wait. (Lines 322-340.)
- Per-run reports to `~/.hermes/logs/curator/{ts}/run.json + REPORT.md` (curator.py:490). Structured YAML output distinguishing `consolidations:` (with `into:`) from `prunings:` (curator.py:465-483) so downstream tooling can migrate skill references.

**Verdict vs veto:** the curator is NOT covered by our auto-graduation veto — that veto is about MINTING from a trace, not maintaining a library. The curator is the missing other half: it assumes sprawl will happen and continuously re-shapes it into class-level umbrellas, archive-not-delete, provenance-scoped, dry-run-gated. agent-infra HAS an `/improve maintain` loop but does NOT have a dedicated skills-consolidation pass that fights micro-skill sprawl with these guards. This is the single most appropriable idea.

**The deep lesson (worth stealing as a principle):** Hermes splits "capture" from "curate." Capture is greedy/biased-active (and that half we reject). Curate is conservative, provenance-scoped, archive-only, human-gated, and runs on a different cadence. Our veto effectively rejected the *whole pipeline* because we only looked at the greedy-capture end. The curator end is the safe pattern — and it generalizes beyond skills to ANY append-only knowledge store (our research memos, improvement-log, MEMORY.md) where we already mark-stale-don't-delete: a periodic provenance-scoped, dry-run consolidator is constitution-compatible.

---

## Top appropriation candidates (detail)

### Candidate #1 — Programmatic Tool Calling (PTC): LLM-writes-a-script, tools-via-RPC, results never enter context

**What it is.** `tools/code_execution_tool.py`. The model writes a Python script; the script calls Hermes tools (`web_search`, `read_file`, `write_file`, `search_files`, `patch`, `terminal`, `web_extract` — `SANDBOX_ALLOWED_TOOLS`, line 57) as ordinary Python functions. Those calls travel over a **Unix domain socket** back to the parent, which dispatches them through the normal tool handler. **Only the script's stdout returns to the model; intermediate tool results never enter the context window** (module docstring lines 1-30).

**How it works (file:line):**
- Parent auto-generates a `hermes_tools.py` stub module — one Python function per allowed tool, each body is `return _call(name, args)` (`generate_hermes_tools_module` line 259; stub templates line 213; `_call` does newline-framed JSON over the socket, line 373).
- Parent opens an `AF_UNIX` stream socket, `chmod 0600`, starts `_rpc_server_loop` in a thread (line 468). Child process runs `script.py` with `HERMES_RPC_SOCKET` env pointing at it (line 1233).
- Server loop enforces an **allow-list** (`if tool_name not in allowed_tools`, line 525) AND a **tool-call cap** (`DEFAULT_MAX_TOOL_CALLS = 50`, enforced line 537), strips forbidden `terminal` params (line 548), dispatches via `handle_function_call` (line 561), logs each call's duration for observability (line 576).
- **Env scrubbing** before spawning child (`_scrub_child_env` line 136): secret-substring block (`KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH|DSN|WEBHOOK`, line 132) then a safe-prefix allowlist; only `HERMES_HOME/PROFILE/CONFIG/ENV` pass by exact name (line 105). Issue #27303 in comments: they tightened this after a broad `HERMES_` prefix leaked non-secret config.
- Cross-platform: Windows falls back to loopback TCP (`tcp://127.0.0.1:port`) since AF_UNIX is flaky there (line 1156); remote backends (Docker/SSH/Modal/Daytona) use file-based RPC instead (line 877, `_execute_remote`).
- Bundled convenience helpers injected into every stub module: `json_parse` (strict=False), `shell_quote`, `retry` with backoff (line 296).
- Guarded: the whole script passes `check_execute_code_guard` before spawning (line 1112).

**Why it'd help agent-infra.** This is a context-compression lever orthogonal to model choice — the same idea as Anthropic's "code execution with MCP" but self-hosted. For multi-step deterministic pipelines (e.g. "for each of 40 SKUs, probe + check tier + record"), agent-infra currently either fans out subagents or runs sequential tool calls that each round-trip through context. PTC collapses an N-tool-call pipeline into ONE turn at zero intermediate context cost. agent-infra's `state-externalization-lens` memo (externalize recoverable bookkeeping; policy keeps only semantic decisions) is *exactly* this principle — PTC is a concrete mechanism for it. Note: Claude Code already exposes Bash; the novel part here is the **typed tool-RPC stubs + call-cap + allow-list + env-scrub** so the script can call *governed MCP-style tools* (not just shell) without their outputs polluting context. This is the appropriable design.

**Caveat / where it's only partial:** the "sandbox" is isolation-lite — a child process with scrubbed env + socket-permission gating, NOT seccomp/namespaces/rlimits. On the local backend the script can still `os.system` anything the user can (that's why `check_execute_code_guard` runs first). For agent-infra's single-trust-domain laptop use this is acceptable; don't oversell it as a security sandbox.

### Candidate #2 — Provenance-scoped, dry-run, archive-only background CURATOR (the safe half of self-improvement)

See "Mechanism B" above. **What to appropriate:** the *pattern*, not the code — a periodic consolidation pass over an append-only knowledge store that (a) only touches agent-authored entries (provenance ContextVar → `created_by: agent`, skill_provenance.py + skill_usage.py:449), (b) archives never deletes (curator.py:362), (c) defaults to a DRY-RUN that emits "what I WOULD do" for human approval (curator.py:322-340), (d) emits structured `consolidations/prunings` YAML so reference-migration is mechanical (curator.py:465). agent-infra equivalent: a `/improve consolidate` mode (or launchd job mirroring the existing report-only `gov.py`/`drift-sentinel.sh` pattern) that clusters `research/` memos or skills, proposes umbrella merges, and writes a report-only digest surfaced at SessionStart — exactly like the existing `drift-digest.md`/`blindspot-digest.md` surfacing. Fully constitution-compatible (append-only, provenance-scoped, dry-run = propose-and-wait).

### Candidate #3 — The "Do NOT capture" negative-constraint blocklist for knowledge writes

`background_review.py:124-143` and curator anti-patterns. The transferable rule set, independent of any minting trigger:
- Never capture environment-dependent failures (missing binary, "command not found", unconfigured creds) as durable rules — "the user can fix these."
- **Never capture negative tool claims** ("X is broken", "can't use Y") — "these harden into refusals the agent cites against itself for months after the actual problem was fixed." (Strong, specific, and we have no explicit guard for it.)
- Never capture transient errors that resolved (the lesson is the retry pattern, not the failure).
- Never capture one-off task narratives.
- Class-level-name discipline: reject names containing PR numbers, error strings, codenames, dates, "fix-X/debug-Y/audit-today" (background_review.py:100-105).

**Why it'd help.** agent-infra's `/observe`→improvement-log and MEMORY.md appends have a self-improvement-governance gate (recurs 2+ sessions, checkable predicate OR architectural) but NO explicit list of *anti-patterns that should never be captured as durable rules*. The "negative tool claims harden into self-cited refusals" insight is genuinely missing and maps onto our context-rot concern (a stale wrong one-liner is worse than a long correct one — context-budget-principles.md §8). This is a cheap rules-file addition, not infrastructure.

### Candidate #4 — Cron script-injection + `[SILENT]` no-op pattern + skill-chaining

`cron/jobs.py:523` `create_job(... script=..., skills=..., deliver=..., no_agent=...)`:
- **Script pre-processing** (jobs.py:557-580): a Python/shell script runs BEFORE the agent; its stdout is **injected into the agent's prompt as context** (mechanical work — fetch/diff/compute — done deterministically, agent only reasons over the result). With `no_agent=True` the script IS the job (stdout delivered verbatim, agent skipped entirely).
- **`[SILENT]` pattern** (routines.md:83; jobs.py:581 "Empty stdout = silent (no delivery)"): the prompt instructs the agent to emit `[SILENT]` / empty output when nothing changed, so you're only notified on real events. No-spam scheduled monitoring.
- **Skill-chaining** (`_normalize_skill_list` jobs.py:71, `--skills "arxiv,obsidian"`): load an ordered list of skills before running a scheduled prompt.

**Why it'd help (partial).** agent-infra already has rich launchd routines (drift-sentinel, vendor-sweep, blindspot-miner) that are *zero-API deterministic halves* surfaced to the interactive loop. The **script-injection-as-context** and **`[SILENT]`-when-nothing-changed** patterns are a cleaner formalization of what agent-infra's `drift-surface.sh`/`blindspot-surface.sh` already do ad-hoc (the digest is only written/surfaced when something needs attention). Mild appropriation value — mostly a vocabulary/pattern confirmation, not new capability. The cron *scheduler* itself is NOT appropriable: agent-infra correctly uses launchd (native, zero-quota) per `schedule-is-cloud-not-local.md` and `native-patterns.md`; hermes's Python scheduler is a thing we deliberately DON'T build.

---

## Where hermes is WORSE than what agent-infra already has

1. **Skill MINTING bias** (background_review.py:46): "most sessions produce at least one skill update; a no-op is a missed opportunity." This is a worse default than agent-infra's governance gate (recurs 2+ sessions + checkable-predicate-or-architectural). Adopting hermes's mint-by-default would be a direct regression and re-trigger exactly the auto-graduation veto. **Do not adopt the trigger.**
2. **No consumer check on skill creation.** The curator explicitly says "use=0 is not evidence a skill is valuable" (curator.py:370) — i.e. it deliberately ignores whether anything consumes the skill. agent-infra's `consumption-over-autonomy` principle ("name the consumer before building a detector") is strictly better and directly contradicts this. Hermes mints first and consolidates later; agent-infra gates on consumer-existence up front.
3. **Cron scheduler in Python** vs launchd. Hermes reinvents scheduling/process-supervision in Python (cron/scheduler.py 95KB); agent-infra's native-first rule (launchd plist, zero-quota, KeepAlive/TimeOut) is the correct call and explicitly vetoes Python cron loops (`native-patterns.md`).
4. **"Sandbox" is isolation-lite, not a real sandbox** (env-scrub + socket perms + a pre-exec guard, no seccomp/namespaces). agent-infra's worktree-isolation for code-writing subagents (hard git isolation, measured +7.8pp) is a different and stronger isolation story for the case it covers.
5. **Multi-platform gateway / Honcho user-modeling / batch trajectory + mini-SWE runners** — all irrelevant downgrades for agent-infra's context: single-user, Claude-Code-hosted, consumes frontier models (doesn't train them), no chat-platform delivery surface. Not worse per se, just out of scope; flagged so they're not mistaken for candidates.

---

## Confirming reads (all claims grounded)

- Cron script-injection CONFIRMED: `cron/jobs.py:557-583` — `script` stdout "injected into the agent's prompt as context" without `no_agent`; `no_agent=True` → "script IS the job, stdout delivered verbatim, Empty stdout = silent (no delivery)". Bonus: `context_from` (jobs.py:564) chains job A's latest output into job B's prompt — native cron-job chaining. `workdir` injects that dir's AGENTS.md/CLAUDE.md/.cursorrules into the system prompt (jobs.py:571).
- Delegate batch CONFIRMED: `tools/delegate_tool.py` — `ThreadPoolExecutor`, configurable `delegation.max_concurrent_children` (line 362, no hard ceiling, warns on token cost) and `delegation.child_timeout_seconds` (line 400, **default None = no timeout**). Children get a focused system prompt and return only a "clear, concise summary" to parent (lines 656-664); intermediate tool calls never hit parent context. Safe default: `subagent_auto_approve=False` → dangerous commands auto-DENIED in child threads (line 73); opt-in YOLO for cron/batch.
- Curator trigger CONFIRMED conservative: `agent/curator.py:198 should_run_now` — gated on enabled + not-paused + `last_run_at` older than `interval_hours` (**7-day default**); **first run is DEFERRED** (seeds state, report-only, "do not auto-mutate the library the very first time"); explicit `hermes curator run --dry-run` bypasses the gate for on-demand preview. This is the opposite of the greedy per-turn minting bias — strong evidence the capture/curate split is deliberate.

## STATUS: COMPLETE. All claims grounded in file:line reads.
