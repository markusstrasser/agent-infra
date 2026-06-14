---
title: Supervision Audit — Git/Commit/Hook Friction (2026-06-14)
date: 2026-06-14
tags: [supervision, git, hooks, audit, friction]
status: active
---

# Supervision Audit: Git/Commit/Hook Friction

**Window:** 2026-06-01 to 2026-06-14 (14 days). Projects: agent-infra, genomics, intel, hutter, phenome.
**Data sources:** agentlogs.db (tool_calls/sessions), ~/.claude/hook-triggers.jsonl, ~/.claude/commit-check-log.jsonl, session transcripts under ~/.claude/projects/-Users-alien-Projects-*.

---

## Part 1: Git/Commit/Hook Friction Classes

### GF-1: Peer-session cross-sweep (staging race + index lock)

**Frequency:** Confirmed in 8+ distinct sessions across genomics (03e81578, 1c094e24, b38baad8, 7ffc759b, 13edba68), phenome (adfa97e4, 136236fa), agent-infra (ec38e627, 45c85753). Transcript grep: `cross_sweep` hits in 10+ sessions, `index_lock` in 6+ sessions, `commit_retry` in all of the above.

Raw counts (agentlogs, 21d): git reset 103 calls / 53 sessions; git stash 138 / 56 sessions. Many of these are direct remediation for staging contamination.

**Mechanism:** Multiple Claude processes share a `.git/index`. When peer session A stages files and Opus (session B) runs `git commit`, the committed set sweeps A's staged files. The HEAD ref-lock race (`cannot lock ref 'HEAD'`) then forces a retry on the new HEAD. The `pretool-multiagent-commit-guard.sh` (38 blocks in 8 days) catches bare `git commit` when ≥2 claude procs are live — but does not prevent the index contamination that causes the race.

**Transcript evidence:**

- `03e81578` (genomics): "Concurrent-commit race: the other agent landed `6e9bccc67` mid-commit, so my ref-update lost (RC=128). Hooks all passed — only the HEAD lock raced." Then: "My changes landed — but swept into a sibling agent's commit." 4 distinct retry loops in one session.
- `1c094e24` (genomics, 9×-compact session): "a peer session committed (`4daa3dc96`) while my hooks were running... my `git commit` hit `cannot lock ref 'HEAD'`" — followed by index reset, re-stage, retry. Also: "The shared `.git/index` is polluted: a peer session's 22 SBayesRC files are staged as `A` in the index I share with them."
- `b38baad8` (genomics): "Index-lock contention — the peer grabbed `.git/index.lock` to commit their (large) staged set." Retry, no human fix needed but ~3 turns burned.

**ROUTINE vs FEISTY split:**
- ROUTINE (automatable): ~80% of instances. The pattern is: detect peer-staged files, unstage them, re-add own files, retry. Deterministic — own file list is known from the task's staging manifest.
- FEISTY (needs reasoning): ~20%. When the peer's commit swept the agent's own files in (cross-sweep, files already committed by peer), the agent must verify the commit contents, decide whether to amend or move on, and reconcile. Session `03e81578` had one of these: "code is correct and complete; only the commit provenance is wrong."

**Human intervention:** Rare (1 confirmed case in `1c094e24` where human had to disable the GOALS.md hook). The agent self-recovered in 3–6 turns per incident.

**Cost per incident:** 3–8 tool calls of churn. At 8 confirmed multi-session incidents, ~24–64 turns of recoverable mechanical waste.

**Verdict: synchronous context-shield commit subagent.** A thin commit subagent that: (a) snapshots own staged file list before hooks run, (b) detects index contamination post-hook, (c) resets foreign files and retries in one call. Eliminates the retry loop without human attention. NOT an auto-fix hook — the hook-level guard already exists (multiagent-commit-guard); the failure is upstream of the hook, in the staging layer.

---

### GF-2: Pre-commit hook BLOCKS — legitimate guards firing on valid work

**Frequency:** Confirmed in 10+ distinct sessions. From hook-telemetry (8-day window): `multiagent-commit` 38/38 blocks; `git-add-all-guard` 9/9 blocks; `append-only-guard` 6/6 blocks; `research-gate` 17/17 blocks. Broader pre-commit chains (genomics `lint_registry`, `precommit-qa-gate`, `lint_silent_fallbacks`, `codebase-map stale`) blocked in sessions 1c094e24, 03e81578, b38baad8.

**Transcript evidence:**

- `1c094e24` (genomics): "P6 commit blocked by `lint_registry` — Registry drift detected. The P6 files shouldn't touch a registry, so this is likely pre-existing drift." Then: "the slash commit is blocked by a different gate (`precommit-qa-gate`: codebase-map stale) — and crucially, the 4 migration agents are actively editing ~22 scripts, so codebase-map will keep going stale until they all finish." Then: "Commit blocked by `lint_silent_fallbacks`." Three distinct hooks blocking in the same session.
- `1c094e24`: "The hook blocked it — GOALS.md is human-owned and refuses all agent edits, even with your say-so." — Human had to intervene to disable the hook.
- `53a9f3e3` (agent-infra): "The hook just false-positive-blocked my own git commit — my commit message contains the literal text `uvx python3`, and the hook matched it inside the string." Needed 2 tool-call retry; then: "Now retry the `~/.claude` settings commit that the buggy hook blocked earlier."
- `b38baad8` (genomics): "That commit was blocked by the pre-commit QA gate — but the 16 failures are all `FileNotFoundError` on `.scratch_*.py` files I never touched. The peer deleted their scratch scripts mid-test-run."

**ROUTINE vs FEISTY split:**
- ROUTINE (~60%): False positives from peer-session activity (stale codebase-map, foreign file presence in test runner, commit-message text-match inside quoted strings). Deterministic fix: verify the failure is pre-existing/foreign, skip the check once or fix the artifact. No reasoning required.
- FEISTY (~40%): Genuine hook catch (silent exception blocks, registry drift caused by the agent's own migration). These require understanding what drifted and fixing it before committing. Correct agent behavior — supervision value is real.

**Human intervention:** 1 confirmed case (GOALS.md hook disable). Otherwise agent self-recovered.

**Cost per incident:** 2–5 tool calls. Highest cost is the codebase-map staleness pattern — when 4 peer sessions are editing files simultaneously, codebase-map regenerates to a stale state immediately after each commit, creating a continuous block.

**Verdict: auto-fix hook for the codebase-map staleness case only.** Specific fix: when `precommit-qa-gate` fires with "codebase-map stale" as the reason AND peer sessions are active, auto-regenerate the map and retry once without surfacing to the agent. For all other pre-commit blocks: nothing — they are doing their job. The false-positive text-match issue in `53a9f3e3` was already fixed in the same session (the hook was patched to strip quoted strings).

---

### GF-3: `git commit --no-verify` (hook bypass)

**Frequency:** 29 calls across 14 distinct sessions. GOVERNANCE FINDING — this meets the 2+ session bar at 14×. Cross-repo: agent-infra, genomics, intel, hutter all represented.

**Mechanism:** When pre-commit hooks fire repeatedly (especially the codebase-map staleness loop or peer-session QA failures), the agent routes around the block with `--no-verify`. This silently bypasses ALL pre-commit gates: protected-paths enforcement, large-binary checks, append-only guards.

**Transcript evidence:** No clean transcript snippet isolated (the bypass is in Bash tool calls; session pattern is commit blocked → 1–2 retries → `--no-verify`). The 29-call count and 14-session spread is the evidence.

**ROUTINE vs FEISTY split:**
- ROUTINE bypass (~70%): codebase-map stale, foreign test file failure — situations where the block is genuinely a false positive from peer activity. The agent's judgment is probably correct.
- FEISTY bypass (~30%): Cannot determine from current data whether these were also false positives or legitimate blocks that got routed around.

**Human intervention:** Not detected — that's the problem. The bypass is invisible to the human.

**Cost per incident:** 0 extra tool calls (the bypass "solves" it), but it silently disables the safety layer. The governance cost is unbounded if protected-paths enforcement is bypassed.

**Verdict: auto-fix hook (BLOCK `--no-verify` with a forced log entry).** Add a pretool-commit-no-verify-guard that: (a) blocks `git commit --no-verify` by default, (b) logs the attempt with the pre-commit failure that caused it (from the agent's prior tool output), (c) forces the agent to explicitly name why the bypass is safe. Allow-list: CLAUDE.md `GIT_ALLOW_GUARD_BYPASS=1` env var already exists for legitimate bypass — require the agent to set it explicitly rather than reaching for `--no-verify` silently. This is the highest-ROI finding: 14 sessions, invisible to human, touches protected-paths enforcement.

---

### GF-4: `commit-check` advisory warnings (message format)

**Frequency:** 3202 commits checked (14d), 2792 with warnings (87% warning rate). Top categories: subject >80 chars (1874 occurrences), em-dash missing (718), no body (485), missing scope prefix (191), unknown scope (1302). Cross-repo: every project represented. This hook fires 2248 times in 8 days — the #1 hook by volume.

**Key observation:** These are ALL advisory warnings — the hook does NOT block. There are 0 blocks from `commit-check` in the telemetry. The 87% warning rate means the warnings are consistently ignored.

**ROUTINE vs FEISTY split:** 100% ROUTINE. Subject length, em-dash, scope prefix — all deterministic checks with deterministic fixes.

**Human intervention:** None (advisory-only). But if the warnings are universally ignored, the hook's value as a learning signal is near zero.

**Cost per incident:** Near-zero per commit (hook runs in <100ms, advisory output is discarded). But at 87% warning rate on 3202 commits, the hook is not improving behavior — it's emitting noise.

**Specific sub-issue — unknown scope warnings:** The scope check fires 1302 times in 14d with `[ops]`, `[outer-loop]`, `[observer]`, `[infra]`, `[harness]`, `[research]`, `[decisions]` all flagged as unknown. These are legitimate scopes being used by the agent (especially in hutter, where `[ops]`, `[outer-loop]`, `[levers]` appear 56, 47, 28 times). The `.git-scopes` file in hutter does not include them.

**Verdict: nothing for the warning behavior itself** (it's advisory and non-blocking; the agent correctly ignores format nags when they don't affect correctness). **But: fix the scope registries.** The unknown-scope false-positives are pure noise — add `ops`, `outer-loop`, `observer`, `levers`, `fleet`, `research`, `decisions`, `infra`, `harness` to the hutter and agent-infra `.git-scopes` files. 1302 spurious warnings over 14 days, all from stale scope lists.

---

### GF-5: Evidence: trailer — governance commit overhead

**Frequency:** 18 suggestions in 14d from commit-check (suggestions, not blocks). Confirmed in sessions 1c094e24 (5+ instances), 53a9f3e3 (2 instances). The agent consistently adds the trailer correctly when reminded — not a compliance failure, but a turn cost.

**ROUTINE vs FEISTY split:** 100% ROUTINE. Governance commit → add trailer. No reasoning required.

**Human intervention:** None.

**Cost per incident:** ~1 extra tool call per incident (read the check warning, add the trailer, re-commit). At 18 suggestions = ~18 extra tool calls of trivial work.

**Verdict: auto-fix hook (suggest-and-scaffold, not block).** When a governance commit is detected and `Evidence:` is absent, pre-populate the trailer in the commit message template rather than warning after the fact. The `prepare-commit-msg` hook already auto-appends `Session-ID:` — extend it to scaffold `Evidence: ` on governance file commits. This eliminates the post-commit warning → re-edit loop.

---

### GF-6: Rebase/non-fast-forward / merge conflicts

**Frequency:** rebase 2 calls / 2 sessions, merge 42 / 15 sessions. The rebase count is minimal. Merge calls are mostly `git merge --no-ff` in automation scripts, not conflict resolution.

**Transcript evidence:** Session `1c094e24` mentioned rebase once (in a plan context, not execution). No evidence of actual merge conflict resolution burns in the 14-day window.

**Verdict: nothing.** Below governance bar for rebase (2 sessions, both context mentions). Merge is infrastructure-adjacent, not friction.

---

## Part 2: General Top-5 Wasted-Supervision Items

### WS-1: commit-check warnings universally ignored (87% warning rate)

See GF-4. The signal-to-noise ratio of the commit-check hook is near zero. A hook firing 2248 times in 8 days with 87% warnings and 0 behavior change is consuming compute, not producing learning. The scope-list staleness is the actionable piece (fix `.git-scopes`). The format warnings are a lost cause as advisories — either enforce them or drop them.

**Verdict:** Fix the scope registries immediately (no-brainer). For the format warnings: consider promoting em-dash to a soft block (abort-with-reformat) rather than advisory — or drop the warning entirely since it demonstrably produces no compliance. Measure before deciding.

---

### WS-2: Hook false positives from peer-session artifact contamination

From transcript grep, `hook_false_pos` pattern hits: genomics/1c094e24 (845 text-matches in session!), hutter/f94e5339 (133), phenome/adfa97e4 (261), agent-infra/53a9f3e3 (60). Note: these grep counts include the phrase appearing in any context (including CLAUDE.md instructions text), so absolute counts are inflated. But the signal is consistent: peer-session test failures and stale artifacts trigger legitimate hooks on innocent commits.

The root pattern: hooks that check repo-wide state (codebase-map currency, test suite pass, registry coherence) fail when peer sessions are modifying the repo concurrently. These are not hook bugs — they are genuine state violations. But the agent can't fix them without either blocking peers or bypassing the hook.

**Verdict:** Pre-commit hooks that check repo-wide state (not just staged files) should be conditioned on "no active peer sessions" OR should identify the specific changed file causing the failure and gate only on that. This is architectural, not a quick fix — track as a proposal.

---

### WS-3: `uv run python3` guard firing on inline scripts / bare Bash calls

From hook-telemetry: not shown in the top-25 list but the uv-python-guard blocked this audit itself twice. From session transcripts, it fires when agents try to run quick diagnostic Python without the `uv run` wrapper. The fix (use `uv run python3`) is 3 words, but it interrupts flow and costs a re-issue.

**Verdict:** Nothing new — the guard is correct. The friction is worth the benefit of catching bare-python in project code. The audit's own experience (two blocks) is noise.

---

### WS-4: Bash loop-guard blocking single-line work

From transcripts: `f94e5339` (hutter), `7ffc759b`, `79c6963a`, `d1fd2609` — all have `[HOOK_BLOCK] role=assistant: Hook blocked the multiline loop. Writing it as a script.` This is the pretool-bash-loop-guard pattern: multiline bash → must write to a file first.

**Frequency:** Consistently present across all projects (session grep shows it in every project's recent transcripts). From hook-telemetry: `terse-bash` 227 warns in 8d, though this is a separate but related hook.

**ROUTINE vs FEISTY split:** 100% ROUTINE. The redirect ("write it as a script") is mechanical and the agent handles it correctly every time.

**Cost per incident:** 2 tool calls (blocked attempt → write script file → run script). At ~20+ incidents/14d, ~40 extra tool calls of pure overhead.

**Verdict:** Nothing — the guard is correct (inline multiline bash has caused parse errors and been a shell injection risk). The 2-tool-call overhead is acceptable for the safety benefit. The agent's handling is already optimal (it writes a script, doesn't argue with the hook).

---

### WS-5: Stop hook / plan-completion-guard iatrogenic pressure

From session `1c094e24`: "the 'rinse-and-repeat indefinitely' Stop hook fired every turn and pressured me to spin past genuine human-decision/budget boundaries (iatrogenic — it couldn't tell 'legitimate stopping point' from 'spinning'). " This was flagged as a `/loop` legitimate-boundary failure: the stop hook fires on genuine task completion and forces the agent to justify stopping.

**Frequency:** Not quantified in hook-telemetry (stop hooks log differently). One explicit transcript mention in 1c094e24. But this is the highest-attention-cost item if it's blocking human decision checkpoints.

**ROUTINE vs FEISTY split:** 100% FEISTY — by definition this is the hook that should require reasoning. The issue is the hook firing on genuine stopping points, not the cost of its firing.

**Verdict:** Improve the stop hook's false-positive discrimination — it should not fire when the agent's stop message explicitly lists a human-decision boundary (budget, GOALS.md edit, irreversible action). The current `stop-stance-flip-shadow.sh` upgrade proposal (improvement-log 2026-06-12) to Haiku semantic predicate is the right path. Escalate that from shadow to production.

---

## Summary Table

| Class | Sessions | ROUTINE% | Verdict |
|-------|----------|----------|---------|
| GF-1: Peer cross-sweep + index lock | 8+ | 80% | Synchronous commit subagent |
| GF-2: Pre-commit blocks (legit guards) | 10+ | 60% | Auto-fix codebase-map staleness only |
| GF-3: `--no-verify` bypass (governance) | 14 | 70% | BLOCK: add pretool-commit-no-verify-guard |
| GF-4: commit-check warnings (format) | all repos | 100% | Fix scope registries; format warns = nothing |
| GF-5: Evidence: trailer overhead | 3+ | 100% | Scaffold in prepare-commit-msg |
| GF-6: Rebase/merge conflicts | 2 | n/a | Nothing (below bar) |
| WS-1: commit-check 87% warn rate | all | 100% | Fix scopes; measure em-dash enforcement |
| WS-2: Repo-wide hook FP from peer sessions | 8+ | 100% | Architectural (future proposal) |
| WS-3: uv-python guard | all | 100% | Nothing (guard correct) |
| WS-4: Bash loop-guard overhead | all | 100% | Nothing (guard correct) |
| WS-5: Stop hook iatrogenic | 1+ | 0% | Promote stance-flip to Haiku predicate |

---

## Prioritized Action Items

1. **[HIGH, NOW] Add `pretool-commit-no-verify-guard`** — 14 sessions, invisible bypass of protected-paths. Block `--no-verify`, require explicit `GIT_ALLOW_GUARD_BYPASS=1`. Cite: 29 calls / 14 sessions.

2. **[HIGH, NOW] Fix `.git-scopes` in hutter + agent-infra** — 1302 spurious unknown-scope warnings in 14d. Add: `ops`, `outer-loop`, `observer`, `levers`, `fleet`, `research`, `decisions`, `infra`, `harness`, `wip`, `gov`, `strategy`. Takes 5 minutes.

3. **[MED] Synchronous commit subagent pattern** — 8+ sessions, 3–8 turns per incident of peer-sweep. Design: capture own-file list before hooks, detect contamination post-hook, auto-reset/retry. Propose implementation.

4. **[MED] Scaffold `Evidence:` in prepare-commit-msg** — 100% ROUTINE, 18 incidents. Extend the Session-ID hook to pre-populate `Evidence: ` on governance commits.

5. **[LOW] codebase-map pre-commit gate conditioned on peer-session activity** — Only fire the stale-map check when no peer sessions are active (or scope to staged-file ancestry only). Architectural, not urgent.

6. **[LOW] Promote stop hook to Haiku predicate** — Already proposed (improvement-log 2026-06-12). Escalate from shadow.

---

## Evidence Trail

- Session transcripts: genomics/1c094e24, genomics/03e81578, genomics/b38baad8, genomics/7ffc759b, agent-infra/53a9f3e3, hutter/f94e5339, hutter/897a2209
- Hook telemetry: `~/.claude/hook-triggers.jsonl` (just hook-telemetry report, 9661 triggers / 8 days)
- Commit check log: `~/.claude/commit-check-log.jsonl` (3202 commits / 14 days)
- Raw counts (agentlogs, 21d): git commit 4279/386 sessions; git add 312/109; git reset 103/53; git commit --no-verify 29/14; git stash 138/56
