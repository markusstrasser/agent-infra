# Latency Audit — Agent/Process Drag Across Repos (2026-07-13)

Status: complete. Read-only, timing-only. No commits made, no repo state mutated.

## Prior art (checked before re-measuring)

- `research/2026-06-14-leverage-hunt-rsi-system.md` WIN 3 already flagged "6 independent
  SessionStart surface hooks — a digest-fragmentation smell" and explicitly deferred:
  "gate on whether the fragmentation actually costs (measure SessionStart latency + digest
  read-rate first). Flagged, NOT recommended without that measurement." **This audit supplies
  that measurement**: agent-infra's SessionStart (`control-plane-surface.sh`, 53ms) and
  genomics' 4 SessionStart hooks (18/86/12/58ms ≈ 174ms total) are both cheap — SessionStart
  is NOT where the cost lives in either repo. The digest-fragmentation consolidation proposal
  is still architecturally reasonable but is not a latency win per this data; don't cite
  latency as the justification if it's picked back up.
- `research/2026-06-11-intel-hook-retirement-audit.md` already coverage-audited a proposed
  RETIRE-21 against intel's hook set and independently arrived at the same total this audit
  found (**"the other ~48"** hooks, matching my count of 48 PreToolUse Write|Edit gates
  exactly) — confirming 6 CONFIRMED-RETIRE + 4 RETIRE-UNVERIFIED (redundant with shared
  global hooks) out of that set. That audit was scoped to **correctness/redundancy**
  (duplicate local-vs-shared coverage), not to the **per-call latency cost of running 48
  serial processes** — a different axis this audit adds. Actioning that audit's 6
  confirmed-retire would save ~6 × 147ms ≈ 900ms per Write/Edit; the bulk of the ~7.1s tax
  is architectural (one process per gate) and survives even a full retirement pass — the
  consolidation fix below (#4) is still needed on top of, not instead of, that audit's cuts.
- `research/2026-06-14-supervision-audit-git-friction.md` covers git/commit/hook **friction**
  (false-positive BLOCKS, bypass patterns, warning fatigue) in depth but does not measure
  wall-clock latency of the pre-commit chain itself — no overlap with this audit's genomics
  findings; complementary, not redundant.
- No existing memo measures genomics' `staged_ownership_guard.py` cost or the `uv run pyright`
  step, and none profiles the ancestor-PID walk — that finding (and its root cause) is new.

## Repos scanned
All 10 exist: agent-infra, genomics, intel, phenome, arc-agi, hutter, skills, substrate, evo, anim-workbench.

## uv run python3 -c "pass" cold-start cost per repo (ms)

| repo | cold | warm |
|---|---|---|
| agent-infra | 244 | 85 |
| genomics | 88 | 92 |
| intel | 240 | 176 |
| phenome | 187 | 146 |
| arc-agi | 248 | 143 |
| hutter | 108 | 70 |
| skills | 78 | 82 |
| substrate | 130 | 105 |
| evo | 58 | 58 |
| anim-workbench | 127 | 75 |

Every `uv run python3 <script>` invocation in a hook chain pays ~70-250ms of interpreter/resolver
startup BEFORE the script's own logic runs. A hook chain with N sequential `uv run` calls pays
N × this cost just in startup, serialized.

## Git hooks inventory (non-.sample, per repo)

- **agent-infra**: pre-commit → `skills/hooks/pre-commit-guards.sh` (5 sub-steps) + `scripts/pre-commit-architecture-render.sh`
- **genomics**: pre-commit → `.claude/hooks/run-git-pre-commit.sh` — LARGE chain, ~20+ conditional `uv run python3` invocations gated on staged-path patterns; several UNCONDITIONAL ones (staged_ownership_guard.py, lint_architecture.py, lint_no_direct_corpus_writes.py, generated_index_transaction.py ×2) plus `qa-checks.sh` which runs `uv run pyright --project scripts/pyrightconfig.json` (whole Zone-0 project check, UNCONDITIONAL whenever any .py is staged) + `uv run python3 scripts/run_index_tests.py tests/test_repo_contracts.py tests/test_report_contracts.py` (materializes index tree, full pytest run) + several more uv-run lints, ALL SERIALIZED.
- **intel**: pre-commit → symlink to `skills/hooks/pre-commit-guards.sh` (shared dispatcher, same 5 steps as agent-infra)
- **phenome**: pre-commit → `scripts/hooks/pre-commit-chain.sh`, 9 sequential sub-hooks (no-large-binaries, protected-paths, ruff, content-floor, citation-audit, claim-provenance, claim-invariants, migration-record, todos, tracked-gitignored)
- **arc-agi**: NO git hooks installed (core.hooksPath empty, no .git/hooks/* beyond samples)
- **hutter**: only prepare-commit-msg (session-id stamp) — no pre-commit chain
- **skills**: pre-commit → `skills/hooks/validate-changed-hooks.sh` (syntax-check staged hook files only — narrow, fast)
- **substrate**: pre-commit → `skills/hooks/pre-commit-guards.sh` (shared dispatcher)
- **evo**: pre-commit is a REPO-OWN 134-line script (bb lint, biome/npx, E2E grep, namespace checks) — potential `npx biome` cold-start cost; NOT yet timed
- **anim-workbench**: no git hooks installed

genomics is the standout suspect for the reported "20s+ commits."

## genomics pre-commit chain — measured components (read-only timing, git-hook script itself NOT executed to avoid side effects on a live multi-agent repo — see note below)

- `uv run python3 scripts/staged_ownership_guard.py` (UNCONDITIONAL, first step): **~4.8-5.3s wall** (0.75s user / 2.1s system — I/O-bound, not CPU). Ran twice, consistent. NOTE: genomics currently has 7 files staged by a DIFFERENT live Claude session (session=019f5a29) — did not touch/unstage them (another agent's in-flight work, per governance). This script's job is exactly to detect that, and it does, but at ~5s cost EVERY commit even when nothing is contested.
- `uv run pyright --project scripts/pyrightconfig.json` (UNCONDITIONAL whenever any .py staged, inside `qa-checks.sh`): **~4.9s wall** (6.69s user / 0.50s sys, 147% cpu — parallelized but still ~5s wall).
- Chain also unconditionally runs (not individually timed — same `uv run python3 <script>` tax applies, ~85-250ms cold-start EACH before the script's own logic): `lint_architecture.py`, `lint_no_direct_corpus_writes.py` (staged .py only), `generated_index_transaction.py begin` + `capture`, plus `pre-commit-protected-paths.sh` and `pii-guard.sh` (bash, cheap).
- `qa-checks.sh` ALSO unconditionally runs (whenever staged_py non-empty): ruff check (fast), merge-marker grep (fast), sample-ID awk (fast), silent-fallback lint (uv run), modal-first-paths lint (uv run), type_coverage.py ratchet (uv run), AND `run_index_tests.py tests/test_repo_contracts.py tests/test_report_contracts.py` — this MATERIALIZES the git index into a temp tree and runs a full pytest module against it. Not timed (declined to execute — materializing a tree in a repo with 7 files currently staged by another live session carries real collision risk even though the mechanism itself is designed to be safe; flagged as unsafe-to-time in this audit, not confirmed non-mutating enough to run mid-collision).

**Genomics commit-time floor, conservatively, from just the two UNCONDITIONAL heavy steps alone: ~10s** (ownership guard ~5s + pyright ~5s), before any of the ~15 conditional path-triggered gates (canary_gate, snapshot-freshness pytest suite, mount-coverage lint, container-syntax lint, control-plane validate, PRS allowlist checks, etc.) or the contract-test pytest run add anything. A commit that touches `scripts/*.py` AND any of the conditional trigger patterns easily crosses 20-30s. This is architecturally consistent with the reported "20s+ commits" — genomics' pre-commit hook is a full CI suite run synchronously on every commit, not a fast pre-commit gate.

## Claude Code PreToolUse hook tax — intel is the standout (per-tool-call, not just per-commit)

intel's `.claude/settings.json` registers **48 separate PreToolUse Write|Edit|MultiEdit gate scripts** (`pretool-*-gate.py`), each a distinct process spawn, run SERIALLY on every single Write/Edit/MultiEdit tool call (not just commits). Measured 6 representative gates with a synthetic Write envelope (`CLAUDE_PROJECT_DIR` + JSON on stdin, matches the real hook input contract):

| script | measured |
|---|---|
| pretool-adversarial-review-gate.py | 183ms |
| pretool-bare-duckdb-connect.py | 113ms |
| pretool-hardcoded-path-gate.py | 114ms |
| pretool-document-delete-gate.py | 55ms |
| pretool-instrument-selection-gate.py | 112ms |
| pretool-cohort-stamp-deferral-gate.py | 304ms |

Mean ≈ 147ms/script. Bare `python3 -c "pass"` in the same shell = **23ms** — so each gate pays ~120ms of overhead beyond raw interpreter startup (module resolution: `sys.path.insert` + importing the shared `hook_runtime` lib + per-script stdlib imports like `re`/`pathlib`/`datetime`). All scanned scripts import only stdlib + the local `hook_runtime`/`tools.lib` modules — no heavy deps (no pandas/numpy), so this is pure process-spawn + import-resolution tax, not algorithmic cost.

**Extrapolated: 48 scripts × ~147ms ≈ 7.1 seconds of SERIAL hook latency on every single Write/Edit/MultiEdit tool call in intel.** Over a session with ~200 tool calls (per the task's own estimate), if even half are Write/Edit, that's ~100 × 7.1s ≈ **~700s (11.8 minutes) of pure hook overhead across a session** — separate from and additive to genomics' per-commit tax. intel also has 8 PreToolUse `Bash` gates, 2 `Read` gates, 3 `Agent` gates, 2 `UserPromptSubmit`, 6 `SessionStart`, 4 `Stop` — all separate process spawns on their respective events.

genomics' `.claude/hooks/` PreToolUse set is similarly large (23 Bash/Write gates counted in the settings dump) but wasn't individually timed here (context budget); same architecture (many single-purpose `.py` gates, no `uv run` on the Bash/Write PreToolUse path — direct python3 shebang like intel) — worth the same treatment in a follow-up pass.

## Root cause found: `staged_ownership_guard.py`'s ~5s is an O(depth) subprocess-spawn loop, not I/O

Read `/Users/alien/Projects/genomics/scripts/staged_ownership_guard.py` in full. `_process_ancestor_pids()` (line 123) walks the parent-process chain by spawning a SEPARATE `ps -o ppid= -p <pid>` subprocess **once per ancestor level**, serially, until PID 1:

```python
while cur and cur != 1 and cur not in seen:
    seen.append(cur)
    result = subprocess.run(["ps", "-o", "ppid=", "-p", str(cur)], ...)  # one fork+exec PER level
    cur = int(result.stdout.strip())
```

This function is called from BOTH `_own_tracker_files()` and (transitively) the cross-session check — so it can run the whole ancestor walk twice per invocation. On a Claude Code Bash subprocess, the process tree to PID 1 (shell → node harness → … → launchd) is deep enough that this loop plausibly accounts for the measured 2.1s of *system* time (many serial fork+exec syscalls) inside the 4.8-5.3s wall time. This is the mechanical explanation for genomics' single most expensive UNCONDITIONAL pre-commit step.

**Fix:** one `ps -axo pid,ppid` (or `ps -eo pid,ppid` on macOS) call up front, parsed into a `dict[pid,ppid]` in Python, then walk the chain in-memory. Same semantics, O(1) subprocess spawns instead of O(depth) — should cut this step from ~5s to well under 100ms.

## Team-lead field data + two more confirmed root causes in the same script

Team-lead independently timed a live genomics commit at **10.8s wall (0.84s user / 3.28s system)**, attributing it to the same `staged_ownership_guard.py` and flagging two additional mechanisms. Both confirmed by re-reading the script (already fully read earlier in this audit) plus live evidence:

**Root cause 3 — O(all trackers ever written) glob+read, unscoped, unbounded.** `tracker_paths()`, `_find_foreign_owners()`, and `find_cross_session_foreign()` each independently `glob.glob()` **every** `/tmp/claude-write-intent-*-*.txt` and `/tmp/claude-session-touched-*-*.txt` file on the host — not scoped to this repo, this session, or any age bound — then `open()`+`read()`+parse each match. `_find_foreign_owners()` in particular reads every match's full content with no staleness pre-filter (unlike `find_cross_session_foreign()`, which at least filters by mtime before reading — an inconsistency between the two functions). Confirmed live: `posttool-bash-credit.sh` (PostToolUse, matcher=Bash — read in full, non-mutating to repo state, only touches `/tmp`) fires on **every single Bash call in genomics** and rewrites `/tmp/claude-write-intent-{session_id}-{ppid}.txt` + a parallel `/tmp/claude-bash-snapshot-{session_id}-{ppid}.txt` baseline file — one PPID per session **and per subagent** (subagent fan-out multiplies tracker count), with no reap-on-write. On this machine right now: 20 `claude-session-touched-*.txt` files sit in `/tmp` (0 write-intent files currently, but team-lead observed "hundreds" during heavier concurrent/subagent activity — consistent with the no-reap design, since nothing deletes a tracker after its session ends).

**Fix:** self-clean at write time, not read time. `posttool-bash-credit.sh` and the Edit/Write touch-log hook (`posttool-session-touch-log.sh`) already run on every tool call anyway — add one `os.path.getmtime` sweep there that unlinks any `claude-write-intent-*`/`claude-session-touched-*` file older than `RECENT_PPID_GRACE_SECONDS` (30 min, the same constant the guard already uses to define "recent") before writing its own. This bounds the corpus the guard ever has to scan to "sessions active in the last 30 minutes," regardless of how many days/sessions have accumulated trackers, with zero new standing infrastructure (native-patterns: guardrail fires on invocation, not a daemon). Additionally, make `_find_foreign_owners()` skip stale files before reading (matching the staleness check `find_cross_session_foreign()` already does) — currently the two functions are inconsistent on this.

**Root cause 4 — 30-minute mtime grace window trusts a DEAD session's claim, not a LIVE one.** `find_cross_session_foreign()` trusts any tracker with `mtime >= now - 1800s` as belonging to a still-active peer session, with no check that the owning process is actually alive. A session that crashed, was force-killed, or exited cleanly 2 minutes ago still has its file claims honored for up to ~28 more minutes — exactly the false-positive team-lead hit twice ("false-foreigned my legitimate cross-repo file relocation"). The same mtime-window design also cuts the other way: a genuinely long-running, quiet session (>30 min since its last tracker write) silently LOSES trust of its own prior claims, which is a second bug from the same root cause.

**Fix:** replace the mtime-window heuristic with an actual liveness probe. The tracker filename already encodes the owning PPID (`_tracker_ppid_suffix()` is already implemented and used elsewhere in the same file). Liveness of a specific PID is one `os.kill(pid, 0)` call — a pure syscall, no subprocess spawn, effectively free (microseconds) and strictly cheaper than both the current mtime heuristic's stat() calls AND the ancestor-walk `ps` loop from root cause 1-2. Decision rule: `os.kill(ppid, 0)` succeeds (or raises `PermissionError`, meaning it exists but isn't ours) → trust regardless of mtime age; raises `ProcessLookupError` → the tracker is dead, discard regardless of how fresh its mtime is. This one change fixes both directions of the bug (false-trust of dead sessions AND false-distrust of quiet-but-alive ones). Keep mtime only as a secondary sanity bound (e.g. reject anything >24h old even if the PID number happens to be alive-but-reused by an unrelated process) — cheap insurance against PID-reuse edge cases, not the primary trust signal.

## Global Claude Code hooks — matcher=`*` tax on EVERY tool call, every repo

Three global hooks fire on literally every tool invocation regardless of project (`~/.claude/settings.json`, matcher=`*`). Measured with a synthetic Bash envelope:

| hook | event | measured |
|---|---|---|
| `~/.claude/hooks/tool-tracker.sh` | PreToolUse | 124ms |
| `~/Projects/skills/hooks/pretool-companion-remind.sh` | PreToolUse | 126ms |
| `~/Projects/skills/hooks/posttool-governance-state.py` | PostToolUse | 210ms |

**~460ms of baseline tax per tool call, before any per-repo hook runs**, additive across the whole fleet (every repo pays this on top of its own hooks). Both read/write small `/tmp` state files (tab-title tracking, companion-skill reminder dedup, dup-read detection) and a `~/.claude/governance-state.jsonl` log — legitimate small logging jobs, but each is a full process spawn + several `jq`/`python3` sub-invocations per call (tool-tracker.sh alone shells out to `jq` up to 4 times). None of the three were read as fully mutating repo state — confirmed /tmp-scoped and append-only log writes, safe to execute for timing.

`agent-infra`'s SessionStart (`control-plane-surface.sh`, 53ms) and `just --list` (25ms) are cheap — NOT offenders.
genomics' 4 SessionStart hooks are cheap individually (18/86/12/58ms ≈ 174ms total) — NOT the genomics bottleneck; the pre-commit chain is.

## Skipped as unsafe-to-time (per task's own read-first / non-mutating constraint)

- genomics `run_index_tests.py` (materializes a temp git-index tree + full pytest run) — declined given genomics currently has 7 files staged by a live peer session (session=019f5a29); did not want to risk any interaction with that in-flight state, even though the mechanism is designed to be side-effect-free.
- genomics `generated_index_transaction.py begin`/`capture` — manipulates the git index directly by design; not run standalone outside an actual commit.
- The remaining 42 of intel's 48 PreToolUse gates, and genomics' ~23 Bash/Write PreToolUse gates — not individually read+timed (context/time budget); the 6-script intel sample and cross-checked import-weight scan (all stdlib + local `hook_runtime`, no heavy deps) is treated as representative, but a full per-script pass would sharpen the total.
- evo's pre-commit (`bb lint`, `npx biome check`) — not timed; `npx` cold-start is a plausible added cost given Node tooling's own startup tax, flagged for follow-up.
- Did not attempt to actually simulate a genomics `git commit` (would require staging real files in a repo another session is actively using) — all genomics pre-commit numbers are component-level, not an end-to-end commit measurement.

## Ranked offender table

| repo | surface | script/hook | measured | est. per-commit/session cost | root cause | suggested fix |
|---|---|---|---|---|---|---|
| genomics | git pre-commit | `staged_ownership_guard.py` | ~5.0s wall (2.1s sys) | every commit, unconditional | O(depth) serial `ps` subprocess spawns walking ancestor chain | one `ps -eo pid,ppid` snapshot + in-memory walk |
| genomics | git pre-commit | `uv run pyright --project scripts/pyrightconfig.json` (in `qa-checks.sh`) | ~4.9s wall | every commit touching any `.py` | whole Zone-0 project type-check runs synchronously, unconditional | scope to staged files only, or move to a pre-push/CI gate instead of every commit |
| intel | CC PreToolUse (Write/Edit/MultiEdit) | 48 `pretool-*-gate.py` scripts | ~147ms mean/script | ~7.1s PER Write/Edit tool call (not just commit) | one process spawn + module-import per gate, all serial | merge into one dispatcher process that imports all gate modules once and runs their checks in-proc (48 spawns → 1) |
| genomics | git pre-commit | `run_index_tests.py` (contract pytest) + ~15 conditional path-triggered lints/tests | not timed (materializes tree; declined given live peer session) | plausibly several more seconds when triggers fire | full CI suite embedded in commit path | move contract tests + conditional heavy gates to pre-push or a background/async check, keep pre-commit to fast syntax/lint only |
| all repos | CC hooks (global) | `tool-tracker.sh` + `pretool-companion-remind.sh` + `posttool-governance-state.py` (matcher=`*`) | ~460ms combined | every single tool call, every repo | 3 separate process spawns + multiple `jq` shell-outs per call for what is fundamentally state logging | consolidate the 3 into 1 script (or 1 Python process) that does tab-title + dup-read + companion-remind + governance-log in one pass |
| genomics | git object store | `.git` = 1.9GB, largest of the 10 repos | n/a | marginal (git status/log still <200ms) | pack accumulation over time | not urgent — `git gc` is cheap insurance but git status/log are NOT slow, so this is not currently a latency driver |
| hutter | git object store | 0 packs, 5950 loose objects | n/a | marginal | never gc'd | `git gc` — low priority, same reasoning as above |

## Top 5 offenders — concrete fixes

1. **genomics `staged_ownership_guard.py` — four compounding root causes, all in one script (~5-10s+/commit, field-measured 10.8s wall / 3.28s sys end-to-end).** (a) serial `ps` subprocess-per-ancestor-level → single `ps -eo pid,ppid` + in-memory dict walk. (b) `glob.glob()` over EVERY tracker file ever written to `/tmp`, unscoped by repo/session/age, in three separate functions → reap trackers older than the 30-min grace window at WRITE time (in `posttool-bash-credit.sh` / `posttool-session-touch-log.sh`, which already fire every tool call) instead of scanning the unbounded backlog at READ time; also make `_find_foreign_owners()` skip stale files before reading, matching `find_cross_session_foreign()`'s existing (but inconsistently-applied) staleness filter. (c) 30-minute mtime-window "liveness" heuristic trusts dead sessions' claims for up to 28 minutes past their actual death, causing team-lead-observed false-foreign blocks on legitimate work → replace with a real liveness probe: `os.kill(ppid, 0)` (one syscall, no subprocess, cheaper than the mtime stat() calls it replaces) against the PPID already encoded in the tracker filename; dead PID discards the claim regardless of mtime freshness, live PID trusts it regardless of mtime staleness (fixes the symmetric bug where a quiet-but-alive session past 30 min loses its own claims). Highest-confidence, lowest-risk fixes in this whole audit — all four are pure internal refactors with identical intended semantics, no behavior change for the correctness the guard exists to provide, only for its cost and its false-positive rate.
2. **genomics `uv run pyright` on every commit (~5s/commit).** Currently unconditional whole-project Zone-0 check inside `qa-checks.sh`. Fix: scope pyright to the staged files' containing modules (pyright supports file-list invocation), or relegate the full project check to `just validate-code` / pre-push / CI, keeping commit-time to an incremental check.
3. **genomics pre-commit chain overall is a full CI suite, not a commit gate.** Between the two unconditional heavy steps above (~10s), plus 15+ conditional path-triggered gates (canary_gate, snapshot-freshness pytest, mount-coverage lint, container-syntax lint, control-plane validate, PRS allowlist resolution, event-sourced registry replay, research-trace WAL probe, verification-debt ledger) each paying its own `uv run python3` startup, a commit touching several trigger patterns easily reaches 20-30s+. This directly explains the reported symptom. Fix: split into a FAST commit-time tier (syntax, merge-markers, protected-paths, ruff — all sub-second) and a SLOW tier (pyright, contract tests, ownership cross-check, conditional lints) that runs on `pre-push` or as a background `just` check, not synchronously in `git commit`.
4. **intel's 48-gate PreToolUse Write/Edit stack (~7.1s per file edit).** This is a per-tool-call tax, not per-commit — it fires on every Write/Edit/MultiEdit across a whole session, which compounds far more than genomics' per-commit cost given typical edit frequency. Fix: consolidate the 48 single-purpose gate scripts into one dispatcher process (they already share the `hook_runtime` lib) that imports each gate's check function once and iterates in-process — same checks, 1 process spawn instead of 48.
5. **Global matcher=`*` hook stack (~460ms × every tool call, every repo).** Small individually, largest in aggregate across the fleet (any session with hundreds of tool calls pays this hundreds of times). Fix: same consolidation pattern as #4 — one small Python/shell dispatcher for tab-title tracking + dup-read detection + companion-skill reminders + governance-state logging, replacing 3 separate process spawns (and tool-tracker.sh's internal 4× `jq` shell-outs) with 1.

## Bottom line

The reported "20s+ commits" symptom is real and explained: genomics' git pre-commit hook runs a synchronous full CI suite (ownership cross-check + whole-project pyright + contract pytest + up to 15 conditional lints) on every commit, not a fast local gate. The two unconditional heavy steps alone (~10s) already exceed most teams' entire CI budget for a pre-commit hook. Separately and additively, intel's 48-script PreToolUse gate stack imposes a ~7s tax on every single file edit (not just commits) — likely the dominant per-session drag for anyone actively editing in intel. Neither issue is git/repo-bloat related (all `git status`/`git log` calls measured under 300ms everywhere); both are hook-architecture issues: too many serial process spawns doing work that could be one process.
