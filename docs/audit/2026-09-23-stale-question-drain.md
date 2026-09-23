# Stale-question drain — 2026-09-23

_One revalidation scout per stale item (backend: cursor; `just questions-drain --dispatch`). Scouts recommend; disposition is orchestrator/operator work — see plan 17d2a35c-middle-manager-harvests._

## Steward proposal — Stop hook should not re-surface already-surfaced unattributable files
- ref: `/Users/alien/.claude/steward-proposals/2026-06-17-stop-hook-suppress-resurfaced-unattributable.md` · created 2026-06-17 (98d)
- scout: ok=True wall=81s tok(in/out/reason)=26553/1931/0

VERDICT: MOOT  
EVIDENCE: `b1dfae3` adds `_fresh_unattributable` and `~/.claude/stop-unattrib-seen-*` dedup (`skills/hooks/stop-uncommitted-warn.sh:384–419`, `419` uses `unattributable_fresh` only). `test_stop_uncommitted_quiet.py:87–88` pins second Stop silence for session-deduped advisories. Later `d1907d3` / `7936a23` cut noise further (peer checkout suppress + count-only, no path re-list).  
RECOMMENDED: resolve-moot — the repeat-surface papercut is implemented; proposal’s `/tmp` marker and named-path delta differ but the behavior goal is met.

## Steward proposal — live peer-session WORK visibility (not just existence)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-18-live-peer-work-visibility.md` · created 2026-06-18 (97d)
- scout: ok=True wall=96s tok(in/out/reason)=32498/2939/0

VERDICT: MOOT  
EVIDENCE: skills `1d52f5d` (2026-07-06) added `hooks/peer-work-visibility.py` + wired `sessionstart-peer-session-warn.sh:69-73` (uncommitted paths + Session-ID–filtered recent commits; git-only, no agentlogs).  
EVIDENCE: `docs/audit/2026-07-06-shared-hooks-batch.md` row #5 marks `live-peer-work-visibility` SHIPPED with operator “ship all 8” approval.  
EVIDENCE: No commits to `peer-work-visibility.py` after ship; proposal’s per-peer agentlogs join was explicitly not built (see `peer-work-visibility.py:8-11`).  
RECOMMENDED: resolve-moot — core SessionStart “what’s being touched” visibility shipped; steward file is stale pending closeout only.

## Peer-aware uncommitted-file attribution
- ref: `/Users/alien/.claude/steward-proposals/2026-06-19-peer-aware-uncommitted-attribution.md` · created 2026-06-19 (96d)
- scout: ok=True wall=83s tok(in/out/reason)=22908/1140/0

VERDICT: MOOT
EVIDENCE: skills@4abc666 + d1907d3 — `stop-uncommitted-warn.sh` sources `peer-session-count.sh` via `_peer_count()` (407:417) and skips unattributable nag when peers≥1 (447:461); worktree-only peer model and “most likely YOURS” commit nudge are gone.
RECOMMENDED: resolve-moot — shipped in `~/Projects/skills/hooks/`; proposal frontmatter already records implementation.

## Steward proposal — Stop auto-commit Case-A mis-attribution + the shared-checkout ceiling
- ref: `/Users/alien/.claude/steward-proposals/2026-06-19-stop-hook-caseA-and-shared-checkout-ceiling.md` · created 2026-06-19 (96d)
- scout: ok=True wall=96s tok(in/out/reason)=31308/3187/0

Reading the steward proposal and checking the current implementation state.
VERDICT: SUPERSEDED  
EVIDENCE: skills@ce59d36 + `hooks/posttool-session-touched-log.sh:37-48` (SHA sidecar) and `hooks/stop-uncommitted-warn.sh:176-213` (defer when current bytes ≠ owner hash) close Case-A without the proposed `epoch`/ `last_commit_ts` design. `decisions/2026-06-16-shared-checkout-isolation-by-default.md` Revisions (2026-06-16 later): harden-shared + stood-down isolation Phase 4; `scripts/claude-launch.sh` remains opt-in/unadopted.  
RECOMMENDED: resolve-superseded — hook mis-attribution guard is live under a superseding mechanism; the worktree ceiling was explicitly operator-gated and contemporaneously reframed in the ADR, not an open steward build.

## Steward proposal — Stop-hook peer-attribution guard (suppress "it's yours" when peers share the checkout)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-19-stop-hook-peer-attribution-guard.md` · created 2026-06-19 (96d)
- scout: ok=True wall=86s tok(in/out/reason)=24241/1692/0

VERDICT: MOOT
EVIDENCE: skills@4abc666 added `hooks/peer-session-count.sh` + `_peer_count()` in `hooks/stop-uncommitted-warn.sh:407-417`; skills@d1907d3 gates unattributable surfacing on `_peer_count(cwd) < 1` (`:447-461`). Runtime text no longer emits “most likely YOURS” (only comments at `:142`, `:288`; skills@7936a23 attribution floor).
RECOMMENDED: resolve-moot — the proposed guard shipped 2026-06-19 and the proposal file already self-attests IMPLEMENTED; no open ask remains.

## GPU-class drift — derive heavy/GPU gating from `@app.function(gpu=)`, not `ResourceClass`
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-gpu-class-drift-lint.md` · created 2026-06-20 (95d)
- scout: ok=True wall=328s tok(in/out/reason)=48593/7596/0

VERDICT: SUPERSEDED  
EVIDENCE: `genome_stage_definitions.py:934-941` — planning GPU class comes from launch `profile.gpu`, not legacy `STAGES.resources`; `3951` binds `esm_lfb` to `4c-32768m-gpu-L4-14400s-r1-nomaxc`.  
EVIDENCE: `f02ddc48d` — `pipeline_stages.py:3709-3712` treats kernel `resource_class_label=="gpu"` as heavy even when `STAGES[esm_lfb].resources` stays default CPU; alphamissense/gpn_msa/dl_merge are `nogpu` profiles (`3511`,`3880`,`4099`) with no `gpu=` in their scripts.  
RECOMMENDED: resolve-superseded — the June‑20 five‑way mismatch is reconciled or kernel‑guarded; the proposed STAGES↔script lint was never added but the failure mode moved to kernel transport profiles + `is_heavy_stage` canonical read.

## researcher Stop-gate for the *pathological-empty* case only
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-researcher-pathological-empty-stop-gate.md` · created 2026-06-21 (94d)
- scout: ok=True wall=93s tok(in/out/reason)=25847/3081/0

Reading the proposal and checking the current implementation against git history since 2026-06-21.
VERDICT: STILL-VALID
EVIDENCE: `skills` `da792bc` added shadow-only logging; `skills/hooks/subagent-source-check-stop.sh:12-15` still calls shadow and never blocks on pathological-empty. `skills/hooks/subagent-empty-research-shadow.py:122` always `return 0`; no later commits promote to block (only `8ff5b7d` stderr fix).
RECOMMENDED: keep — the proposed Stop block is unshipped; shadow dataset exists but human promotion/noop decision from the proposal’s test plan is still outstanding.

## Steward proposal — warn on `rg -r` typo'd-as-recursive
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-rg-replace-flag-guard.md` · created 2026-06-21 (94d)
- scout: ok=True wall=151s tok(in/out/reason)=42202/4403/0

VERDICT: STILL-VALID
EVIDENCE: `~/.claude/settings.json:91-98` — Bash still goes only through `pretool-bash-dispatch.py`; `skills/hooks/pretool-bash-dispatch.py:57-99` lists 28 gates with no `rg`/`-r` typo guard (no `pretool-rg*` in `skills/hooks/`).
EVIDENCE: `docs/audit/2026-07-06-steward-triage-early.md:92` deferred for single-session recurrence only — not built; no `skills` hooks commit since 2026-06-21 mentions ripgrep/replace-flag.
RECOMMENDED: keep — glued `-r*` still invokes `--replace` and corrupts output with no warn-only guard or toolbelt line added.

## Watch — global auto-back-stamp misfire monitor (measure-while-deployed)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-22-backstamp-misfire-watch.md` · created 2026-06-22 (93d)
- scout: ok=True wall=95s tok(in/out/reason)=24273/2624/0

VERDICT: STILL-VALID
EVIDENCE: `~/.claude/settings.json:279` still wires global `posttool-decision-backstamp.sh`; `skills/hooks/posttool-decision-backstamp.sh:41-53` still prose-matches flip headers (only post-6/22 changes: b75461e/1b34ee9 session-tracker claims).
EVIDENCE: `substrate/docs/decisions/0022-…:5` declares **Supersedes (for phenome)** only, but `0011-vertical-substrate-claim-production-boundary.md:126` carries a full “NOT a current direction” auto-stamp — concrete misfire the watch was meant to catch.
RECOMMENDED: keep — residual false-positive risk is live and the watch’s own “any wrong stamp → narrow trigger” branch was never applied.

## Lens/generator banks: track APPLICATION, not growth
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-lens-bank-application-tracking.md` · created 2026-06-24 (91d)
- scout: ok=True wall=73s tok(in/out/reason)=29914/2218/0

VERDICT: STILL-VALID
EVIDENCE: `build_lifetime_evidence_warehouse.py:554-558` — `lifetime_generators` DDL still has only registry fields, no `times_applied`/`last_fired`/lifecycle columns.
EVIDENCE: `immigration-lifetime-fiscal-generators.md:18` (124 `rg` headings vs 122 DB) still documents MD↔DB drift and MD-only `G-LIF-Q06`/`G-LIF-S15`; Q06/S15 absent from `research/.mining/`.
EVIDENCE: `9ddf700` — post-proposal cluster V added eight lenses in MD/JSON with no application-stamping path in `infra/immigration-fiscal/build/`.
RECOMMENDED: keep — accretion and drift persist; none of the three fixes (generated MD, apply counters, prune-before-add) are implemented.

## red-team a CONSEQUENTIAL foreclosure BEFORE it drives action (global epistemic discipline)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-redteam-before-foreclosure.md` · created 2026-06-24 (91d)
- scout: ok=True wall=112s tok(in/out/reason)=36673/3875/0

Reading the proposal and checking the codebase for changes since 2026-06-24.


VERDICT: STILL-VALID
EVIDENCE: `~/.claude/CLAUDE.md:46-55` — `<epistemic_discipline>` still has principal/proxy and “matches locate” only; no mandatory cross-model refutation before consequential pivot/abandon/foreclosure.
EVIDENCE: `skills/hooks/posttool-foreclosure-grounding.sh:37-40` (wired in `~/.claude/settings.json:275`) — advisory PostToolUse nudge on finality writes to decision surfaces; optional `/critique`, not the proposed pre-decision refutation dispatch rule (`743888f`, 2026-06-19).
EVIDENCE: Post-2026-06-24 `~/.claude` history (e.g. `81d0470`, `ff78289`) compresses global rules without adding foreclosure red-team; `agent-failure-modes.md:734-744` FM31 still treats confident foreclosure as a probe tell, not global enforcement.
RECOMMENDED: keep — partial hook + plan `/critique` gates do not implement the steward ask for a global, refutation-first consequential-foreclosure discipline.

## auto-checkpoint [wip]-churn on shared main + worktree-isolation silent no-op
- ref: `/Users/alien/.claude/steward-proposals/2026-06-25-wip-churn-worktree-noop.md` · created 2026-06-25 (90d)
- scout: ok=True wall=207s tok(in/out/reason)=53582/4278/0

Reading the proposal and checking the repo state since 2026-06-25.


VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/stop-uncommitted-warn.sh:502-510` still runs ungated `git commit --only` with `[wip] Auto-checkpoint…` on the current branch (Options A/B never shipped; only mitigations like `c13fb48`, `8c1e331`, `.claude/no-auto-checkpoint`).
EVIDENCE: No post-2026-06-25 hook verifies `isolation: worktree` (`pretool-subagent-gate.sh` still only advises); `bad2559`/`bin lane` is an alternate isolation path, not a fix for silent Agent worktree no-op.
RECOMMENDED: keep — main-history `[wip]` reset tax remains on default repos; worktree no-op was never root-caused or fail-loud guarded.

## Donor-export GCS auth — kill the recurring stale-token failure class
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-donor-export-auth.md` · created 2026-06-27 (88d)
- scout: ok=True wall=139s tok(in/out/reason)=32162/2320/0

VERDICT: STILL-VALID
EVIDENCE: `genomics/scripts/modal_donor_export.py:386-398` still uses `Credentials(token=GCS_ACCESS_TOKEN)` from `gcs-push-token` (non-refreshable ~1h OAuth).
EVIDENCE: `genomics/justfile:2536-2543` `donor-export-gcs` / `donor-export-gcs-lab` call `_modal-run` only — no secret refresh; `docs/ops/donor-delivery.md:82-84` still points at this steward proposal as pending.
RECOMMENDED: keep — the stale-token/toil failure class was not replaced by a refresh wrapper or Modal↔GCP WIF since 2026-06-27 (reconfirmed vs 2026-09-02 drain scout).**Revalidation (88d):** Donor-export GCS auth proposal is **still valid**.

GCS push still depends on a short-lived `gcs-push-token` OAuth secret; `just donor-export-gcs*` does not refresh it before Modal runs, and WIF was not added. The runbook still lists the steward fix as pending.

**Recommendation:** Keep the open question — implement the proposed `just` wrapper (refresh secret → run) or WIF when you want to close the class of stale-token failures.

## Steward proposal — standing bio-verify gate for the per-sample HPO rail
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-form-hpo-verify-gate.md` · created 2026-06-27 (88d)
- scout: ok=True wall=204s tok(in/out/reason)=44662/4199/0

Reading the proposal and checking the repo state since 2026-06-27.


VERDICT: STILL-VALID
EVIDENCE: `justfile:1088-1089` adds `hpo-profile-check` (in `validate-data` via `justfile:1283`), but `form_to_hpo.py:373` runs `validate_local_hpo_profiles` only — not `verify_curated_hpo` (`:310-330`, still unused outside tests/docs). `ea08d32d7` fail-closed kernel HPO identity binding does not ontology-check ids; `docs/ops/sample-onboarding-runbook.md` has no curate/`verify-hpo` step.
RECOMMENDED: keep — standing ontology bio-verify (`verify_curated_hpo`) and onboarding docs were never wired despite the identity-check recipe.**Revalidation (88-day steward item):** Still valid.

Genomics already has `just hpo-profile-check` (wired into `validate-data` since `9fe862e4f`) and kernel fail-closed HPO identity binding (`ea08d32d7`). What’s missing vs the 2026-06-27 proposal: **`verify_curated_hpo` is never called** from the recipe/CLI (only schema/identity via `validate_local_hpo_profiles`), **no onboarding runbook step** for curating `hpo-<sample>.json` then verifying, and **no ontology/id drift gate** on exomiser/lirical preflight.

**If you want to close it:** wire `verify_curated_hpo` into `hpo-profile-check` (or alias `verify-hpo`), add the runbook line, optionally call verify at phenotype-driven preflight — then mark the steward proposal resolved. I can implement in Agent mode if you want.

## Steward proposal (#g) — session-end auto-checkpoint + reset --hard wipes peer-owned uncommitted work on a shared checkout
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-shared-checkout-reset-wipes-peer-work.md` · created 2026-06-27 (88d)
- scout: ok=True wall=223s tok(in/out/reason)=65826/5015/0

Reading the steward proposal and checking the repo state since 2026-06-27.
VERDICT: STILL-VALID  
EVIDENCE: `~/.claude/hooks/session-phases/01-session-id.sh:6` still writes one repo-local `current-session-id` per SessionStart (peer overwrite unchanged). `skills/hooks/pretool-destructive-git-ref.sh:23-42` only stash-snapshots/advises on Bash `reset --hard`; no peer-ownership gate and no hook for harness session-end reset (`docs/audit/2026-07-06-shared-hooks-batch.md:37-38`). `ce59d36`/`c13fb48`/`7936a23` hardened `stop-uncommitted-warn.sh` attribution; `pretool-worktree-staleness-guard.py` blocks stale dispatches but does not verify `isolation:"worktree"` actually created a linked worktree.  
RECOMMENDED: keep — partial checkpoint hardening does not close the proposed fail-closed reset guard or dispatch worktree verification.

## mechanical transport pre-flight in evalcore.run
- ref: `/Users/alien/.claude/steward-proposals/2026-06-29-evalcore-transport-preflight.md` · created 2026-06-29 (86d)
- scout: ok=True wall=109s tok(in/out/reason)=26934/2925/0

VERDICT: STILL-VALID
EVIDENCE: `evals/evalcore/run.py:218-273` — `run_eval` loads cases then enters the full candidate×case loop with no per-candidate/judge transport ping or abort. `substrate` `1d4cc7b` / `272ebaf` (2026-06-14/18) add `CandidateError` + `errored` trials and `[BROKEN ARM]` summary only after each item fails, not the proposed pre-batch `SystemExit`.
RECOMMENDED: keep — partial broken-arm mitigation exists but the proposal’s early-abort pre-flight in `evalcore.run` was never implemented and void-batch waste remains if transport dies before authors raise `CandidateError`.

## progress-based stage hang-watchdog (genomics) — 2026-07-03
- ref: `/Users/alien/.claude/steward-proposals/2026-07-03-stage-hang-watchdog.md` · created 2026-07-03 (82d)
- scout: ok=True wall=213s tok(in/out/reason)=53419/3612/0

Reading the proposal and checking the targeted repos for changes since 2026-07-03.
VERDICT: STILL-VALID  
EVIDENCE: `71fb2883d` removed `scripts/orchestrator/hang_watchdog.py` and `tests/test_hang_watchdog.py`; no `hang_watchdog` under `scripts/` today. `scripts/detect_stuck_stages.py:32` is read-only and flags suspects by `started_at` wall age (`190-191`), not frozen `last_progress_json` / `elapsed_s`. M83 in `docs/ops/2026-06-28-end-to-end-dag-failure-pattern-catalog.md:8113-8118` records hang-watch deleted with no current drive caller; `watch_active_apps.py` only auto-stops crash loops.  
RECOMMENDED: keep — interim progress watchdog was landed then removed, and nothing progress-based now kills live-but-stalled Modal attempts.

## Goal conditions: terminal states as checkable predicates
- ref: `/Users/alien/.claude/steward-proposals/2026-07-07-goal-terminal-predicates.md` · created 2026-07-07 (78d)
- scout: ok=True wall=176s tok(in/out/reason)=36039/4734/0

Reading the proposal and checking the codebase for changes since 2026-07-07.


VERDICT: STILL-VALID
EVIDENCE: No `DONE-WHEN` authoring anywhere under `~/Projects/skills` or `~/Projects/agent-infra` (repo grep is only unrelated prose); proposal’s checkable disjunctive terminals were never added.
EVIDENCE: `skills/hooks/stop-goal-wrapup.py:43-71` still uses optional `.claude/goal-deliverable` shell progress only; `:90` still tells the agent to touch `.claude/goal-done` — no multi-criterion predicate grading.
EVIDENCE: `f1ee2b6` (since 2026-07-07) added `.claude/goal-quiet` at `:218-255`, addressing armed event-wait (b), not disjunctive terminal predicates (a).
RECOMMENDED: keep — wakeup ambiguity is hook-fixed, but explicit `DONE-WHEN` terminal predicates remain unimplemented.

## Steward proposal — make the guard layer an executable corpus, not a set of independent regexes
- ref: `/Users/alien/.claude/steward-proposals/2026-07-09-executable-hook-corpus.md` · created 2026-07-09 (76d)
- scout: ok=True wall=148s tok(in/out/reason)=44664/4451/0

VERDICT: STILL-VALID
EVIDENCE: No `skills/hooks/corpus/commands.jsonl` and no `just hook-corpus`; `agent-infra/scripts/hooks_smoke.py:9-18` only pipes one benign payload per hook (syntax/dead-hook), not canonical allow/block commands through the composed stack.
EVIDENCE: `skills/hooks/test_bash_dispatch.py:993-1003` encodes one cross-guard case via `pretool-bash-dispatch.py`; `genomics/.claude/settings.json:97-102` still chains project hooks (e.g. streaming-cli + orchestrator-stop) outside that dispatcher corpus.
EVIDENCE: Instance patches only — `skills/hooks/pretool-timeout-modal-guard.sh:56-62` (9ebd20c, 0845852); `genomics` c7a14850b scoped restart matching; `pretool-orchestrator-restart-guard.sh` is gone (only `pretool-orchestrator-stop-guard.sh` remains).
RECOMMENDED: keep — ad-hoc per-guard pytest and dispatcher parity tests do not replace a skill-seeded JSONL corpus over the full installed PreToolUse set.

## Contested-file stop-hook: cache adjudications by content hash
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-contested-file-adjudication-cache.md` · created 2026-07-10 (75d)
- scout: ok=True wall=86s tok(in/out/reason)=32554/2685/0

Reading the proposal and checking the current implementation.


VERDICT: SUPERSEDED
EVIDENCE: `b1dfae3` (2026-09-18) added `_fresh` + `contested_fresh` in `~/Projects/skills/hooks/stop-uncommitted-warn.sh:343-371` — session path ledger `~/.claude/stop-contested-seen-<sid>.txt`, not sha256(worktree diff).
EVIDENCE: Same commit comment cites the measured repeat-noise case (six contested files on eleven consecutive Stops); no content-hash adjudication cache in the hook (grep/read of current file).
RECOMMENDED: resolve-superseded — per-session once-per-path contested throttling addresses the 7× identical advisory waste; the proposed diff-hash re-flag on change was not implemented.

## Port arc-agi's frontier-sensor pattern to an eval-methodology sensor in evals/
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-eval-frontier-sensor.md` · created 2026-07-10 (75d)
- scout: ok=True wall=102s tok(in/out/reason)=28707/2612/0

VERDICT: STILL-VALID
EVIDENCE: No `scripts/eval_frontier_sensor.py`, `research/frontier_inbox.md`, or `eval-sensor-on` in evals (`justfile:7-8` only `new-eval`; repo grep miss on those names). `research/2026-09-05-newest-evals-two-months.md:139` marks flip-gold automated harvest **DEFERRED**; `9ab700c` still added SWE Pro flips by editing `scripts/eval/build_flipped_truth_cases.py` CASES dict.
RECOMMENDED: keep — the July-10 miss was handled manually (e.g. `7997eae`, `1dc301f`) but unattended lab-eval + dated-authority sensing was never built.

## Proposal: block `git commit --amend` in shared checkouts (peer sessions detected)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-no-amend-shared-checkout.md` · created 2026-07-10 (75d)
- scout: ok=True wall=59s tok(in/out/reason)=28159/1565/0

VERDICT: STILL-VALID  
EVIDENCE: `~/Projects/skills/hooks/pretool-multiagent-commit-guard.sh:139-176` allow-lists `--amend` and `exit 0` before the peer block; no `skills` commit since 2026-07-10 adds amend blocking (`-S'--amend'` → only `e160cf7`, pathspec safety). `sessionstart-peer-session-warn.sh:62-65` still has no “never `--amend`” line; `pretool-destructive-git-ref.sh` does not cover amend or `rebase -i`.  
RECOMMENDED: keep — the incident class (history rewrite racing peer staging) is still unguarded at the pretool decision point the proposal names.

## Stop-hook peer detection: false "no peer shares this checkout" under live peers
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-stop-hook-peer-liveness.md` · created 2026-07-10 (75d)
- scout: ok=True wall=87s tok(in/out/reason)=18953/3332/0

VERDICT: SUPERSEDED
EVIDENCE: skills 7936a23 removed “most likely YOURS”/path naming for unattributable files (count-only at stop-uncommitted-warn.sh:447–461); ec7a807’s codex-liveness wording was dropped in that same change. `peer-session-count.sh` is still pgrep/lsof-only — no git Session-ID OR-in — but the hook no longer emits “No peer claude shares this checkout…”.
RECOMMENDED: resolve-superseded — the mis-attribution risk was closed by the 2026-09-22 attribution floor, not by the proposed git-evidence peer check.

## Schedule intel's executive tick — supersede the 2026-03-07 "manual tool only" decision
- ref: `/Users/alien/.claude/steward-proposals/2026-07-11-intel-executive-tick.md` · created 2026-07-11 (74d)
- scout: ok=True wall=98s tok(in/out/reason)=41323/2633/0

VERDICT: STILL-VALID
EVIDENCE: `intel/tools/orchestrator.py:9-12` still `MANUAL TOOL ONLY` / unwired; `intel/tools/CLAUDE.md:48` still DORMANT (no launchd/just/Makefile). `~/Library/LaunchAgents/com.intel.*` has 8 jobs (daily/weekly/scoreboard data only) — no executive-tick plist; `weekly_update.sh` runs `weekly_scoreboard.py` but no `claude -p` dispatch.
RECOMMENDED: keep — weekly verdict/healthcheck surfaces exist; the proposed Sun autonomous executive session was never scheduled.

## Triage-verdict → same-turn dispatch reflex (converts rsi-hindsight queue row)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-11-triage-dispatch-reflex.md` · created 2026-07-11 (74d)
- scout: ok=True wall=97s tok(in/out/reason)=26951/2847/0

Reading the proposal and checking the codebase state since 2026-07-11.


VERDICT: STILL-VALID
EVIDENCE: skills@8b53735 added TRIAGE-DISPATCH in `hooks/userprompt-prior-context.py:873-876` (same-turn obligation for in-queue/chartered items).
EVIDENCE: `hooks/posttool-background-portfolio.sh:21-22` still exits unless Bash `run_in_background=true`; no PostToolUse:Agent branch since 2026-07-11.
EVIDENCE: `~/.claude/settings.json:297-323` wires portfolio hook under `matcher: Bash` only; `358-363` Agent hooks are `posttool-subagent-output-check.sh` alone.
RECOMMENDED: keep — proposal delta 1 is shipped; delta 2 (portfolio nudge on Agent dispatches) is still the open gap.

## reflect_capture: exclude headless-dispatch prompts from operator attribution
- ref: `/Users/alien/.claude/steward-proposals/2026-07-12-reflect-capture-headless-dispatch-exclusion.md` · created 2026-07-12 (73d)
- scout: ok=True wall=81s tok(in/out/reason)=28622/2459/0

Reading the proposal and checking the codebase and git history since 2026-07-12.


VERDICT: STILL-VALID  
EVIDENCE: `scripts/reflect_capture.py:153-168` still classifies any non-notification `role=user` text as operator input (no headless/`claude -p` or driver-tick filter). `scripts/common/transcript_text.py:21-28` only drops `isCompactSummary`/`isMeta`, not dispatch prompts. Since 2026-07-12, targeted git history on those paths is test-only (`1262825`), not this fix.  
RECOMMENDED: keep — headless-dispatch prompts can still false-trigger `operator_dx` / `operator_added_value` on SessionEnd close.

## reflect_session_close.py — two defects found during 2026-07-15 arc-agi close
- ref: `/Users/alien/.claude/steward-proposals/2026-07-15-reflect-close-prefix-and-teammate-fp.md` · created 2026-07-15 (70d)
- scout: ok=True wall=71s tok(in/out/reason)=28946/2025/0

VERDICT: STILL-VALID
EVIDENCE: 601a967 added prefix match only in `latest_digest()` (`reflect_session_close.py:299-301`); `ack_digest()` still logs `session_id` verbatim (`:358-362`) so `_closed_sessions()` exact-set won’t clear nudges for 8-char `--ack`. `extract_operator_dx_interventions()` (`reflect_capture.py:166-167`) still skips only task-notification/system-reminder, not `<teammate-message` / `<local-command-` (pattern exists in `supervision_session.py:411-414`, not wired here).
RECOMMENDED: keep — half of defect #1 shipped; prefix `--ack` + operator_dx teammate/local-command FPs are still open in agent-infra.

## Subagent sessions auto-commit UNGRADED work — protocol inversion
- ref: `/Users/alien/.claude/steward-proposals/2026-07-15-subagent-autocommit-leak.md` · created 2026-07-15 (70d)
- scout: ok=True wall=132s tok(in/out/reason)=38034/3401/0

Reading the proposal and checking the codebase since 2026-07-15.


VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/stop-uncommitted-warn.sh` never reads `agent_id`/subagent identity (contrast `lib_hook_identity.sh:4-7`); `:466-512` still runs `git commit --only` for ledger-owned files on Stop.
EVIDENCE: Since 2026-07-15, `c13fb48`/`b05a67b`/`7936a23` tighten peer/in-flight attribution and surfacing only — no warn-only path for Task/subagent sessions (proposal’s core fix).
RECOMMENDED: keep — shared-checkout subagents can still idle into ungraded `[wip]` checkpoints; worktree policy doesn’t replace this hook guard.

## Guard: block history mutation when HEAD isn't yours (shared checkouts)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-16-shared-checkout-history-mutation-guard.md` · created 2026-07-16 (69d)
- scout: ok=True wall=117s tok(in/out/reason)=30655/2349/0

VERDICT: STILL-VALID
EVIDENCE: `~/Projects/skills/hooks/pretool-multiagent-commit-guard.sh:139-176` still treats `--amend` as safe with peers and never reads HEAD’s `Session-ID:` trailer. `pretool-destructive-git-ref.sh:32-43` only advisory-warns on `reset --hard|--mixed` (always exit 0); `git reset --soft` is out of scope. Post-2026-07-16 work (e.g. `f10ce69`, `e160cf7`) tightened pathspec/partial-staging commits only — no HEAD-ownership block for reset/amend/rebase.
RECOMMENDED: keep — the 2026-07-16 cross-session history-mutation race (soft reset vs peer commit) is still unguarded; Session-ID infrastructure exists (`prepare-commit-msg-session-id.sh`) but isn’t used for this check.

## llmx per-model concurrency semaphore (opt-in) — structural fix for subscription-lane contention kills
- ref: `/Users/alien/.claude/steward-proposals/2026-07-19-llmx-per-model-concurrency-semaphore.md` · created 2026-07-19 (66d)
- scout: ok=True wall=90s tok(in/out/reason)=33916/2622/0

Reading the proposal and checking the codebase for current llmx concurrency handling.


VERDICT: STILL-VALID
EVIDENCE: `~/Projects/llmx` has zero `LLMX_MODEL_SEMAPHORE`/`semaphore`/`flock` (repo-wide grep); `llmx/cli_backends.py` still spawns subscription `claude`/`cursor-agent` with no slot acquire (e.g. ~1116–1147). skills `97a8aa2` only widened `opus-concurrency-advisory` to advisory `GateResult(0)` warn (`pretool-bash-dispatch.py:2085–2120) — not the proposed blocking llmx chokepoint.
RECOMMENDED: keep — cross-driver subscription over-subscription still converts to EMPTY/timeout kills; nothing since 2026-07-19 implements the env+flock semaphore or arc-agi driver wiring.

## reflect_session_close --latest-digest fallback is project-unscoped
- ref: `/Users/alien/.claude/steward-proposals/2026-07-21-digest-fallback-project-scope.md` · created 2026-07-21 (64d)
- scout: ok=True wall=90s tok(in/out/reason)=25801/1747/0

VERDICT: STILL-VALID
EVIDENCE: `scripts/reflect_session_close.py:303-304` — `latest_digest()` with no session still picks the latest global un-acked digest (`elif sid not in closed: found = row`), with no `project` filter.
EVIDENCE: `scripts/reflect_session_close.py:537-538` — CLI `--latest-digest ""` still calls that path; `pending_nudge` is cwd-scoped (`:464`) but lookup is not.
EVIDENCE: `601a967` — prefix-match only; commit message still notes empty-arg fallback returned a genomics digest from arc-agi (not project-filtered).
RECOMMENDED: keep — the proposed cwd-scoped fallback (~5 lines) is still unimplemented; only prefix matching was added.

## pretool guard — block pathspec commits naming CONTESTED files
- ref: `/Users/alien/.claude/steward-proposals/2026-07-28-pathspec-contested-file-guard.md` · created 2026-07-28 (57d)
- scout: ok=True wall=134s tok(in/out/reason)=34548/4638/0

Reading the proposal and checking the repo state since 2026-07-28.


VERDICT: SUPERSEDED
EVIDENCE: `~/Projects/skills` f10ce69 (2026-09-22) adds `_pathspec_partial_paths` in `hooks/pretool-multiagent-commit-guard.sh:92-151` — blocks `git commit -- <path>` when that path has staged and unstaged diffs (same arc-agi / sweep failure mode as 2026-07-28). `hooks/test_pretool_multiagent_commit_guard.py:307-318` locks that behavior; Stop-hook ledger `contested` is still not consulted in pretool (lines 140-176 still allow pathspec when index matches WT).
RECOMMENDED: resolve-superseded — the cited hazard is enforced via partial-staging detection, not the proposed ledger-CONTESTED predicate.

## Proposal: per-session checkpoint files (checkpoint.md becomes a 2-line index)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-29-checkpoint-per-session-files.md` · created 2026-07-29 (56d)
- scout: ok=True wall=152s tok(in/out/reason)=31613/3443/0

VERDICT: STILL-VALID
EVIDENCE: `~/Projects/skills/hooks/checkpoint_resume.py:41` — still only `checkpoint.md` + `checkpoint-autogen.md`; no `checkpoint-<sid8>.md` or generated index. `~/Projects/skills/hooks/precompact-extract.py:360-366,507` — live-peer divert reads `checkpoint.md` only, then overwrites the chosen path with no autogen peer check (3+ sessions → last-writer on autogen). `49398da` (2026-09-07) — curated divert beside `checkpoint.md`; does not implement per-session files.
RECOMMENDED: keep — two-slot anti-clobber partially covers the 2026-07-29 two-writer case but not N-peer isolation or the proposal’s index contract.

## PostToolUse advisory: zero-hit grep over a structured store → store-schema nudge
- ref: `/Users/alien/.claude/steward-proposals/2026-07-29-zero-hit-grep-on-store-nudge.md` · created 2026-07-29 (56d)
- scout: ok=True wall=76s tok(in/out/reason)=27777/2609/0

VERDICT: STILL-VALID
EVIDENCE: `~/Projects/skills/hooks/` has no `posttool-grep-zero-on-store.sh`; `git -C ~/Projects/skills log --oneline --since=2026-07-29 -- hooks/` shows many PostToolUse changes, none for zero-hit store greps.
EVIDENCE: `~/.claude/settings.json:297-323` Bash PostToolUse still lists six hooks (`posttool-bash-failure-loop.sh`, `posttool-bash-poll.sh`, etc.) with no zero-hit structured-store matcher.
EVIDENCE: Workspace grep finds no `store-schema` recipe or arc-agi protocol outside `docs/audit/2026-09-02-stale-question-drain.md` — SSOT affordance may be gone, but no advisory hook replaced the proposed reminder layer.
RECOMMENDED: keep — the action-time nudge was never implemented or functionally superseded; update nudge copy if `just store-schema` is no longer a live affordance.

## Proposal: `llmx prices --verify` — live drift check for the hand-maintained price table
- ref: `/Users/alien/.claude/steward-proposals/2026-07-31-llmx-price-verify.md` · created 2026-07-31 (54d)
- scout: ok=True wall=100s tok(in/out/reason)=31368/2559/0

VERDICT: STILL-VALID
EVIDENCE: `llmx/llmx/usage_report.py:23-25` — `PRICING` is still a hand-edited snapshot (“verify before quoting”; no staleness check).
EVIDENCE: `llmx/llmx/cli.py:1102-1109` — subcommands are chat/info/usage/…/probe only; no `prices` or `--verify`.
EVIDENCE: Post-2026-07-31 commits `45575db`, `1c7d195`, `80641cd` still patch `usage_report.py` manually; `spend_guard.py:20-22` only refuses *unpriced* models, not wrong rates.
RECOMMENDED: keep — the drift-detector the proposal describes was never built; wrong-price incidents remain possible on vendor cuts.

## Proposal — block a commit that asserts a path is lost while git still holds it
- ref: `/Users/alien/.claude/steward-proposals/2026-08-12-absence-claim-falsifier-guard.md` · created 2026-08-12 (42d)
- scout: ok=True wall=183s tok(in/out/reason)=49510/4369/0

VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/pre-commit-guards.sh:40-48` — dispatcher still runs only binaries/validate/protected-paths/deid/codebase-map; no loss-assertion step. `skills/hooks/commit-check-parse.py:113-116` — PreToolUse commit path blocks only Co-Authored-By; no `(unrecoverable|…)` + `git log`/`rev-list` check. genomics `3d5ab6a26` — restored `claim_events.ndjson` (incident fix), not a global pre-commit guard.
RECOMMENDED: keep — repo-independent gap remains; only soft discipline in `~/.claude/projects/-Users-alien-Projects-genomics/memory/feedback_absence_claims_need_the_falsifying_command.md`, not the proposed enforcement.

## Digest staleness destroys the verify path — flag it at nudge time
- ref: `/Users/alien/.claude/steward-proposals/2026-08-18-digest-staleness-verify-path.md` · created 2026-08-18 (36d)
- scout: ok=True wall=99s tok(in/out/reason)=26538/2419/0

Reading the proposal and checking the codebase for current behavior.
VERDICT: STILL-VALID
EVIDENCE: `scripts/reflect_session_close.py:537-542` — `--latest-digest` still emits raw JSON with no `transcript_path` existence check or warning. `scripts/reflect_session_close.py:468-471` — `--nudge` still says “verify one claim” with no degraded-path flag. `b8f2622` added `--ack-stale` (bulk `stale-unreviewed` acks); no `[STALE-DIGEST]` anywhere in agent-infra.
RECOMMENDED: keep — transcript loss can still make /rsi Step 2 unverifiable for pending digests; only the backlog screen was addressed, not nudge/close-time visibility.

## Proposal: migrate iq-sex-differences analysis scripts into git (kill the SPOF)
- ref: `/Users/alien/.claude/steward-proposals/2026-08-18-iq-sexdiff-track-analysis-scripts.md` · created 2026-08-18 (36d)
- scout: ok=True wall=68s tok(in/out/reason)=28426/2180/0

Reading the proposal and checking the current state of the targeted paths.


VERDICT: MOOT  
EVIDENCE: `f465a12` (2026-08-19) adds ~119 scripts under tracked `analysis/`; `85007ef`/`b3d62b6` repoint data and delete the repo-root `sources` symlink (path gone today). `CLAUDE.md:100-104` documents resident `analysis/` + `data/`; `analysis/variance_ratio_and_menu_displacement.py:22` uses `parent.parent / "data"`.  
RECOMMENDED: resolve-moot — the SSD SPOF migration and doc/path sweep from the proposal landed the day after it was filed; only the optional `stage0_config.py` `MISSING_CODES` dedup remains open as separate hygiene.

## RSI digests must be acked (or expire) inside the transcript-prune horizon
- ref: `/Users/alien/.claude/steward-proposals/2026-08-18-rsi-digest-prune-horizon.md` · created 2026-08-18 (36d)
- scout: ok=True wall=117s tok(in/out/reason)=34574/3253/0

Reading the proposal and checking the current implementation against git history since 2026-08-18.
VERDICT: STILL-VALID  
EVIDENCE: `b8f2622` added manual `--ack-stale` (`reason=stale-unreviewed`); no `transcript_pruned`, no auto-ack when `transcript_path` is missing (`scripts/reflect_session_close.py:441-471`, `:381-430`). `~/.claude/skills/rsi/SKILL.md:28-31` still passes `current-session-id` to `--latest-digest`, so a prior-session nudge can miss the pending digest despite `latest_digest()` un-acked fallback (`:275-305`).  
RECOMMENDED: keep — prune-horizon coupling and nudge evidence-grade hints from the proposal are still unimplemented; bulk `--ack-stale` only screened the 2026-09-02 queue.

## bgrun watcher pairing nudge
- ref: `/Users/alien/.claude/steward-proposals/2026-08-19-bgrun-watcher-pairing-nudge.md` · created 2026-08-19 (35d)
- scout: ok=True wall=70s tok(in/out/reason)=19636/2007/0

Reading the proposal and checking the repo state since 2026-08-19.


Proposal claims it's implemented; verifying the hook and registration still exist.


VERDICT: MOOT
EVIDENCE: `skills` b59dc68 adds `~/Projects/skills/hooks/posttool-bgrun-watcher-nudge.sh` (PostToolUse advisory when `bgrun` has no `.done` watcher in the same command); `~/.claude/settings.json:380` still registers that hook on `PostToolUse:Bash`; proposal frontmatter `status: implemented` (2026-08-19).
RECOMMENDED: resolve-moot — the proposed nudge is live and tested (`test_hook_identity.py:138-140`); queue item is stale paperwork, not an open gap.

## Expire close digests whose transcript is gone
- ref: `/Users/alien/.claude/steward-proposals/2026-08-20-expire-unverifiable-close-digests.md` · created 2026-08-20 (34d)
- scout: ok=True wall=174s tok(in/out/reason)=30693/3081/0

VERDICT: STILL-VALID  
EVIDENCE: `scripts/reflect_session_close.py:441-472` — `pending_nudge` still nudges on any un-acked `invoke_skill` digest with no `transcript_path`/git check; `_closed_sessions()`/`pending_nudge` use exact `session_id` only (`:260-272`, `:462`), so prefix `--ack` rows still fail to suppress.  
EVIDENCE: No `expired_unverifiable` anywhere; b8f2622 added manual `--ack-stale` with `reason: stale-unreviewed` (`:381-430`), not SessionStart auto-expire on missing transcript.  
EVIDENCE: 601a967 prefix-matched `--latest-digest` only (`:297-301`); `ack_digest` still appends the raw arg (`:358-367`).  
RECOMMENDED: keep — `--ack-stale` was a one-off queue freeze, not the proposed nudge-time `expired_unverifiable` path or ack ID normalization.

## Proposal: Hook verification state — stateless revalidation (architectural)
- ref: `/Users/alien/.claude/steward-proposals/hook-state-stateless-revalidation.md` · created 2026-07-03 (82d)
- scout: ok=True wall=103s tok(in/out/reason)=57217/2589/0

Reading the proposal and checking the codebase for current hook verification state.
VERDICT: STILL-VALID
EVIDENCE: `genomics/.claude/hooks/pretool-orchestrator-stop-guard.sh:47,99-104` still gates orchestrator kills on grep of agent-writable `/tmp/claude-session-verified-$SID.txt`; no inline revalidation.
EVIDENCE: `dca21c7bd` deleted `pretool-orchestrator-restart-guard.sh` → `pretool-orchestrator-stop-guard.sh` (narrower surface); same forgeable-marker trust model, not Option A.
EVIDENCE: `dbb73953a` dropped proof-ladder markers only; `posttool-session-verify-log.sh:51-65` still appends `ORCH_VALIDATE`/`ORCH_HEALTH` to that file.
RECOMMENDED: keep — stateless inline revalidation remains unimplemented; the forgery substrate for guarded orchestrator stops is unchanged since 2026-07-03.

## Resolve prediction: **Usage telemetry — subscription blind spot closed (`llmx@7e2d993`)** — light critique (cursor repo-grounded + gpt-5.5) REPLACED the tiktoken plan: `claude -p --output-format json…
- ref: `predictions.jsonl#impl-4980db9d-aba2767d` · created 2026-07-18 (67d)
- scout: ok=True wall=96s tok(in/out/reason)=36578/2568/0

Locating the prediction entry and tracing what it proposes.


VERDICT: MOOT
EVIDENCE: `llmx@7e2d993` shipped JSON usage logging; `llmx/cli_backends.py:1068-1074` still passes `--output-format json` and `:1417-1437` calls `log_usage(..., transport="claude-cli")`.
EVIDENCE: `llmx/tests/test_usage_accounting.py:101-117` (`TestClaudeCliUsage`) still guards `_parse_claude_json`; post-2026-07-18 `cli_backends.py` commits extend grok/codex usage, not remove this path.
RECOMMENDED: resolve-moot — subscription Claude telemetry blind spot is closed and unchanged; only the due earn-its-keep resolution remains.

## Resolve prediction: **Pulse liveness contracts — scoped, NOT universal (`bf68c3a`)** — both critiques killed the "universal registry": a uniform constancy test alarms-on-green for healthy-constant me…
- ref: `predictions.jsonl#impl-4980db9d-03ab1531` · created 2026-07-18 (67d)
- scout: ok=True wall=69s tok(in/out/reason)=32672/3091/0

Tracing the prediction entry and checking the codebase since 2026-07-18.


VERDICT: MOOT
EVIDENCE: `bf68c3a` (2026-06-16) shipped scoped per-metric contracts; `scripts/pulse.py:111-140` still declares `should-vary`/`floor` on three supervision instruments only (no universal registry).
EVIDENCE: `scripts/pulse_tick.py:124-130` runs `pulse.py canary` on every tick; post-2026-07-18 commits `99a48af`/`2bc0c95` extended attention/observe wiring, did not revert contracts.
RECOMMENDED: resolve-moot — the design gap (scoped vs universal liveness) was implemented pre-check_date; only ledger closure remains, not new work.

## Resolve prediction: **llmx usage surfacing** — DONE (`llmx@62ce643`). Verify-before-build paid off: `usage_log.py` + `scripts/usage_summary.py` already recorded + rolled up usage; it just wasn't reac…
- ref: `predictions.jsonl#impl-275e3582-47014afe` · created 2026-07-18 (67d)
- scout: ok=True wall=69s tok(in/out/reason)=28778/2274/0

Tracing the prediction entry and verifying whether llmx usage surfacing is still an open gap.
VERDICT: MOOT
EVIDENCE: `llmx@62ce643` added `llmx usage` + `llmx/usage_report.py`; `llmx/cli.py:1069-1105` still registers `usage_cmd` → `summarize`.
EVIDENCE: `scripts/usage_summary.py:4-14` is a thin wrapper to the same module; post-2026-07-18 commits (e.g. `c277468`) extend pricing/usage, not remove surfacing.
EVIDENCE: `agent-infra@275e358` marked improvement-log done; original gap was “logged but not reachable,” not missing telemetry.
RECOMMENDED: resolve-moot — usage surfacing shipped and remains the canonical path; only the overdue gov-shrink prediction row needs human resolve.

## Resolve prediction: **PPV/reflect-eval counted STALE firings against the current predicate (windowing bug)** — FIXED: added per-rule `since` (predicate-last-changed date) to `config/reflect-omission-…
- ref: `predictions.jsonl#impl-3894d7b4-cbf2123a` · created 2026-07-18 (67d)
- scout: ok=True wall=48s tok(in/out/reason)=23085/1655/0

Tracing the prediction entry and verifying whether the reflect-eval STALE windowing fix is in place.
VERDICT: MOOT
EVIDENCE: `3894d7b` added per-rule `since`; `scripts/reflect_eval.py:46-81` still windows PPV via `_since_map()` / `_fresh()`.
EVIDENCE: `config/reflect-omission-rules.json:2-48` documents `since` on every rule; `git log --since=2026-07-18` on those paths is empty (no revert/supersession).
RECOMMENDED: resolve-moot — the STALE-firings windowing bug is fixed and unchanged; close the prediction as implemented.

## Resolve prediction: **Closure metric repointed (`supervision-kpi.py`)** — `hooks_shown`/`air` read a `progress/hook_progress/Stop` signal present 7× across all transcripts instead of `attachment/hook…
- ref: `predictions.jsonl#impl-e75d3b7c-5f38d971` · created 2026-07-18 (67d)
- scout: ok=True wall=109s tok(in/out/reason)=30821/3145/0

Investigating the prediction entry and current implementation state.


VERDICT: MOOT
EVIDENCE: 5563996 added `attachment/hook_success` counting; logic lives in `scripts/supervision_session.py:170-176` (93797a1 refactor, unchanged by 21cd73e since 2026-07-18).
EVIDENCE: `improvement-log.md:128` marks fix done; `artifacts/observe/2026-08-11-1258/supervision/supervision-report.json:44-52` shows `hooks_shown: 6`, `hooks_visibility_ok: true`.
RECOMMENDED: resolve-moot — dead `hook_progress`-only metric was fixed before check_date and remains live; only the open `predictions.jsonl` resolution is outstanding.

## Resolve prediction: **`over_caution` graduated shadow→enforce (soft nudge)** — `stop-smart-judge.sh` vector #3 ("ends by asking permission for an obvious, reversible, already-authorized action") had…
- ref: `predictions.jsonl#impl-e75d3b7c-2aec2f7a` · created 2026-07-18 (67d)
- scout: ok=True wall=67s tok(in/out/reason)=26460/2733/0

Tracing the prediction entry and current implementation of `over_caution` / `stop-smart-judge.sh`.
VERDICT: SUPERSEDED
EVIDENCE: `e888a08` + `decisions/2026-07-25-over-caution-ablation-closed.md:26-33` — 14d ablation closed with both bands PASS; enforcement latency bought no timidity reduction, policy is keep `over_caution` out of enforce (shadow scoring only).
EVIDENCE: `~/.claude/settings.json:10-11` — `SMART_JUDGE_ENFORCE_VECTORS` is only `verify_before_claim`; `skills/hooks/stop-smart-judge.sh:45` default matches (vector #3 still classified, not enforced).
EVIDENCE: `predictions.jsonl` line 12 still open; no post-2026-07-25 commit re-adds `over_caution` to enforce (`improvement-log.md` explicitly “do not re-open enforce”).
RECOMMENDED: resolve-superseded — the 2026-07-25 ablation decision reversed the graduated enforce the prediction was meant to validate at check_date.

## Resolve prediction: **Un-archive `/code-review` skill** — moved from `skills/_archive/` to `skills/code-review/`; scout scripts live in `agent-infra/scripts/` (not dead `meta/` paths). Default provid…
- ref: `predictions.jsonl#impl-72c1f394-81814792` · created 2026-07-18 (67d)
- scout: ok=True wall=53s tok(in/out/reason)=7116/1947/0

Tracing the prediction entry and comparing it to the current repo state.


VERDICT: MOOT  
EVIDENCE: `~/Projects/skills/code-review/SKILL.md` (L31–32, L55) — live skill, `agent-infra/scripts/code-review-scout.py` + `--provider cursor`; `skills/_archive/code-review/README.md` — tombstone points to active path; `improvement-log.md:135` — same change marked `[x]` done.  
RECOMMENDED: resolve-moot — un-archive and script-path fix are already in place; only the overdue prediction closeout remains.

## Resolve prediction: **Skills wired to Composer CLI** — `/critique` (composer default on diff-closeout + close axes), `/sweep` (`--composer` Phase 3), `/observe` (Step 2b precision pass), `/verify-bef…
- ref: `predictions.jsonl#impl-72c1f394-8b334daa` · created 2026-07-18 (67d)
- scout: ok=True wall=110s tok(in/out/reason)=36036/4267/0

Locating the prediction entry and checking whether Composer CLI wiring for those skills is still outstanding.
VERDICT: MOOT  
EVIDENCE: `improvement-log.md:136` marks **[x] Skills wired to Composer CLI** (2026-06-14); `skills/shared/llm_dispatch.py:210-257` still defines `composer_review` / `composer_screen` / `premise_scout`. `skills` `4dec39a`/`agent-infra` `2bc0c95` removed `/sweep` and `/improve` — only stale names in the prediction text; closeout Composer lives in `code-review/SKILL.md:19` + `critique/lenses/plan-close-review.md:44`, not a critique `composer` close axis (`critique/scripts/review_gate.py:556`).  
RECOMMENDED: resolve-moot — work shipped and still used; close the prediction with an earn-its-keep yes, noting retired skills and the closeout routing split.

## Resolve prediction: **Critique axis overlap + cost tooling (2026-06-14)** — `standard` axes (`arch`,`gaps`,`correctness`,`contracts`) now all carry full-review mandate (structure+bugs); lenses differ…
- ref: `predictions.jsonl#impl-72c1f394-8ed4792d` · created 2026-07-18 (67d)
- scout: ok=True wall=146s tok(in/out/reason)=45217/6513/0

Locating the prediction entry and tracing what it targets in the codebase.
VERDICT: MOOT
EVIDENCE: `~/Projects/skills/critique/scripts/model-review.py:150-258,602-604` — `standard` still runs four full-review axes; `55a794a` only refactored docs/routing, not that design.
EVIDENCE: `~/Projects/skills/critique/references/dispatch.md:17` — overlap mandate (“lenses differ, territories do not”) is current post–2026-07-18.
EVIDENCE: `agent-infra/justfile:470` + `scripts/critique_cost.py:66-98` — `critique-cost` still rolls up `.model-review/**/*.meta.json`.
RECOMMENDED: resolve-moot — June-14 fix is live and maintained; close the prediction as passed (scaffold stays, nothing left to build).

## Resolve prediction: **Review dispatch consolidation (phase 1)** — closeout partition in `critique/SKILL.md`; `review_targets` in plan-close manifest; skill-usage-watch launchd killed; `critique_effic…
- ref: `predictions.jsonl#impl-72c1f394-8d875561` · created 2026-07-18 (67d)
- scout: ok=True wall=128s tok(in/out/reason)=32724/6122/0

Locating the prediction entry and checking the codebase state since 2026-07-18.


VERDICT: MOOT
EVIDENCE: `improvement-log.md:139` marks phase 1 `[x]` (2026-06-14); `skills/critique/scripts/build_plan_close_context.py:397-409` + `review_gate.py:535-561` still emit/enforce `review_targets` layer split.
EVIDENCE: No `com.agent-infra.skill-usage-watch` LaunchAgent plist; `~/Projects/evals/critique_efficiency/README.md:1-7` tombstoned; zero commits on gate/manifest paths since 2026-07-18 (`55a794a` only refactored `critique/SKILL.md:35` without dropping the contract).
RECOMMENDED: resolve-moot — consolidation shipped and stable; close the prediction as confirmed earns-keep, not an open implementation gap.

## Resolve prediction: **Critique full-update Phase A0** — cross2/cross4/lens2/lens4 presets; AXIS_CELLS; review_gate preset triage; ROUTING_VERDICT scaffold. CLI default stays `standard`. — confirmed o…
- ref: `predictions.jsonl#impl-72c1f394-8709f3f1` · created 2026-07-18 (67d)
- scout: ok=True wall=91s tok(in/out/reason)=30192/3442/0

Locating the prediction entry and tracing what it targets in the codebase.


VERDICT: STILL-VALID
EVIDENCE: `~/Projects/evals/critique_replay/ROUTING_VERDICT.md:3-12` — `status: "pending"`, `default_preset: "standard"`; no commits on that file since `cdcf299` (2026-06-15).
`~/Projects/skills/critique/scripts/model-review.py:503-610` + `review_gate.py:442-469` — AXIS_CELLS, cross2/cross4 presets, triage live; CLI still defaults `standard` (`model-review.py:3578`).
`improvement-log.md:144` — phase 2 (full grid → ROUTING_VERDICT JSON) still `[ ]`; doctor gate `scripts/doctor.py:1144-1145` still treats pending as intentional freeze.
RECOMMENDED: keep — Phase A0 is shipped but the check_date earn-its-keep verdict and cross2 promotion gate remain explicitly unresolved.

## Resolve prediction: **VOI-sequenced review ADR** — `decisions/2026-06-15-voi-sequenced-review.md`; Composer scout before adjudication. — confirmed or refuted?
- ref: `predictions.jsonl#impl-72c1f394-68e4b7c1` · created 2026-07-18 (67d)
- scout: ok=True wall=144s tok(in/out/reason)=42259/5891/0

Tracing the prediction, ADR, and post-2026-07-18 changes in the repo.


VERDICT: STILL-VALID
EVIDENCE: `~/Projects/skills/critique/scripts/model-review.py:616-659,3639-3668` — premise scout + `voi-scout.json` still run before adjudication; `~/Projects/skills/shared/llm_dispatch.py:259-270` binds `premise_scout` to Composer 2.5 (post-2026-07-18 commits only retarget cosigner models, e.g. `1459bdc`).
EVIDENCE: `predictions.jsonl:18` — `impl-72c1f394-68e4b7c1` has no `kind:resolution` row; earn-its-keep/gov-shrink verdict still unset 67d past `check_date`.
RECOMMENDED: keep — implementation is live but the gated prediction (confirm vs refute scaffold retention) still needs explicit `predictions.py resolve`, not inferring from `[x]` in `improvement-log.md:141`.

## Resolve prediction: **Critique P0+P1 hardening** — outcome_link `linked_anchor`/`linked_file` tiers; rank → `escalation-recommendation.json`; cross-talk `cross_talk_degraded`; contradiction meaningfu…
- ref: `predictions.jsonl#impl-72c1f394-70205129` · created 2026-07-18 (67d)
- scout: ok=True wall=121s tok(in/out/reason)=37029/5472/0

Locating the prediction entry and tracing what it proposes versus current code.
VERDICT: MOOT
EVIDENCE: `~/Projects/skills/critique/scripts/outcome_link.py:144-158` — `linked_anchor`/`linked_file` tiers; `review_gate.py:771-775` + `398-427` — `cmd_rank` → `escalation-recommendation.json`; `309-344` — `_meaningful_shared`/`ENTITY_STOPWORDS` contradiction gate; `model-review.py:2207-2211` — `cross_talk_degraded`.
EVIDENCE: `agent-infra/improvement-log.md:142` [x] shipped; since 2026-07-18 only routing/triage tweaks on those paths (`skills@f0ba41a`, `aad7fe8`) — hardening not removed or replaced.
RECOMMENDED: resolve-moot — all four mechanisms are live in `~/Projects/skills/critique/`; the engineering gap is closed and the positive earn-its-place claim is revalidated by current code.

## Resolve prediction: **Global review routing sync** — `~/.claude/CLAUDE.md` partitioned review pointers; `plan-review-gate.md` triage/VOI/closeout partition; `dependency-manifest.json` tombstoned orch…
- ref: `predictions.jsonl#impl-72c1f394-3389a5cc` · created 2026-07-18 (67d)
- scout: ok=True wall=90s tok(in/out/reason)=35822/3583/0

Locating the prediction entry and checking the current state of the proposed changes.


VERDICT: MOOT  
EVIDENCE: `improvement-log.md:143` marks **Global review routing sync** `[x]`; live partition at `~/.claude/CLAUDE.md:43` and `references/epistemic-evidence.md:11` (diff→`/code-review`, plan→`/critique model`/gate, closeout→`/critique close`).  
EVIDENCE: `~/.claude/rules/plan-review-gate.md:10-15` still runs VOI→`review_gate.py triage`→`/critique model`→later `/critique close`; `skills@55a794a` (2026-09-05) kept the same layer split in `critique/SKILL.md:16-35`.  
EVIDENCE: `~/.claude/dependency-manifest.json:2-8` lists `skills/critique/SKILL.md` under `llmx` consumers with no orchestrator entry; no manifest edits since 2026-07-18.  
RECOMMENDED: resolve-moot — the June sync shipped and post-check-date edits preserved aligned routing; only the earn-its-place prediction ledger entry remains open.

## Resolve prediction: **`supervision_taxonomy.py` — single-source correction taxonomy + direction vector.** The objective ("declining supervision") was a weighted SCALAR (`sli`) that summed opposite-si…
- ref: `predictions.jsonl#impl-ee04335f-c4f51912` · created 2026-07-18 (67d)
- scout: ok=True wall=58s tok(in/out/reason)=17240/2528/0

Tracing the prediction item and current implementation state.


VERDICT: MOOT
EVIDENCE: `scripts/supervision_taxonomy.py:2-5,58-74` — Gov-ID `lib:supervision-taxonomy`, `Direction` vector + `DIRECTION_IS_AUTONOMY_GAIN` (scalar `sli` only in historical docstring); `blindspot_miner.py:39`, `supervision-kpi.py:27`, `supervision_session.py:321-354` import taxonomy and emit `vector`/`taxonomy_source`.
EVIDENCE: `scripts/tests/test_supervision_taxonomy.py:95-102` bans re-stated `BLINDSPOT_PATTERNS`/`CORRECTION_PATTERNS` in consumers; `improvement-log.md:153` `[x]` records ship + verifier.
RECOMMENDED: resolve-moot — the sign-error and single-source gap were fixed before the 2026-07-18 check_date; ledger item is an unclosed earn-its-keep prediction, not open build work.

## Resolve prediction: **Claude Code 2.1.1xx native-feature adoption** — closed 2026-06-12 same-day; per-item dispositions: (a) `disallowedTools` REJECTED — analysis skills already use the strictly-stro…
- ref: `predictions.jsonl#impl-22aee86f-c92928d3` · created 2026-07-18 (67d)
- scout: ok=True wall=131s tok(in/out/reason)=41798/5087/0

Locating and reading the prediction item, then checking the codebase state since 2026-07-18.
VERDICT: MOOT
EVIDENCE: improvement-log.md:163 — all 2.1.1xx dispositions marked closed 2026-06-12; commit 22aee86f deleted probe-cr and only added context-budget-principles.md §7 (measure-only).
EVIDENCE: skills@4dec39a + agent-infra@2bc0c95 (2026-09-02) folded sweep/upgrade into /observe — the only deferred fork targets from that closure are gone; ongoing CC natives live in research/claude-code-native-features-deferred.md (improvement-log.md:3862).
RECOMMENDED: resolve-moot — the adoption task finished before check_date; close the prediction with a confirmed earn-its-keep note for §7/skills_budget.py, not new adoption work.

## Resolve prediction: [2026-06-08] rule:checkable-claims-carry-probes — checkable "breaking/blocked" verdicts must carry their probe; downstream re-runs before acting on a skip. blast_radius=local, ver…
- ref: `predictions.jsonl#impl-bbb7525c-0433398c` · created 2026-07-18 (67d)
- scout: ok=True wall=115s tok(in/out/reason)=30641/4374/0

Locating the prediction entry and tracing the checkable-claims-carry-probes rule in the codebase.


VERDICT: STILL-VALID
EVIDENCE: `predictions.jsonl` has no `resolution` for `impl-bbb7525c-0433398c`; `scripts/predictions.py list` still marks it DUE (check_date 2026-07-18). `10e2142` / `decisions/2026-07-25-agent-infra-mcp-zero-consumption.md:76-80` records a post-check_date unprobed “correction” that blocked a correct retirement for six weeks and points at `.claude/rules/checkable-claims-carry-probes.md:15-22` (rule unchanged since `bbb7525c`, `verifier: null`).
RECOMMENDED: keep — the failure mode recurred after the check_date and nothing automated or superseded the rule; close the prediction with a manual earn-its-keep `confirmed`, not retire.

## Resolve prediction: **Gated 5 git-only Bash hooks behind `if: "Bash(git*)"` in `~/.claude/settings.json`** — `git-noext-inject`, `git-add-all-guard`, `no-background-commit`, `multiagent-commit-guard`…
- ref: `predictions.jsonl#impl-71823900-f6ee76b3` · created 2026-07-19 (66d)
- scout: ok=True wall=80s tok(in/out/reason)=31568/2884/0

Tracing the prediction entry and comparing it to the current hook configuration.


VERDICT: SUPERSEDED
EVIDENCE: `~/.claude/settings.json:91-98` — one `pretool-bash-dispatch.py` PreToolUse[Bash] entry; no `if:` fields and none of the five hook scripts listed.
EVIDENCE: skills `03baad9` (2026-07-13) collapsed 28 per-Bash spawns into the dispatcher (~1.2s→0.2s), replacing per-hook `if:` in settings.
EVIDENCE: `~/Projects/skills/hooks/pretool-bash-dispatch.py:2309-2386` — same five guards with in-process `Bash(git*)` predicates; `33afe05` hardened command-position matching.
RECOMMENDED: resolve-superseded — the spawn-cost problem is solved by the dispatcher, so the settings.json `if:` scaffold is obsolete and the open prediction no longer names live architecture.

## Resolve prediction: **Codex 0.141 PostToolUse code-mode gating — VERIFIED, no shim change needed** — 0.141 "blocking PostToolUse hooks now correctly reject code-mode tool calls" is strictly ADDITIVE…
- ref: `predictions.jsonl#impl-3ead94aa-d3387cd8` · created 2026-07-19 (66d)
- scout: ok=True wall=79s tok(in/out/reason)=26749/3456/0

Locating the prediction entry and tracing what it targets in the codebase.


VERDICT: MOOT
EVIDENCE: `scripts/codex_hook_shim.py:43-54,283-288` — PostToolUse in `JSON_STDOUT_EVENTS`, exit-2 reason lifted to stderr; no commits to this file since 2026-07-19.
EVIDENCE: `scripts/codex_parity_sync.py:350-360` — `shim_wrap()` still routes every generated `.codex/hooks.json` command through the shim (64e6c92 only pruned MCP mirrors).
EVIDENCE: `~/.codex/log/hook_shim_invocations.jsonl` — Stop/PostToolUse fires on 2026-09-23 under `codex-cli 0.156.1`; Jun-19 “additive, no shim change” claim still holds.
RECOMMENDED: resolve-moot — 0.141 code-mode PostToolUse gating is native Codex coverage; the shim remains required for Claude→Codex output contract, not for that gap.

## Resolve prediction: **CC 2.1.183 native destructive-git block — no conflict, keep our guards** — native block is PreToolUse-equivalent and auto-mode-only; our `pretool-destructive-git-ref.sh` / `git-…
- ref: `predictions.jsonl#impl-3ead94aa-59767fbc` · created 2026-07-19 (66d)
- scout: ok=True wall=118s tok(in/out/reason)=30762/3995/0

Tracing the prediction entry and checking whether the destructive-git guard issue still applies.
VERDICT: MOOT
EVIDENCE: `improvement-log.md:114` — `[x]` records “no conflict, keep our guards” (2026-06-19); no later reversal in repo history since 2026-07-19.
EVIDENCE: `~/Projects/skills/hooks/pretool-bash-dispatch.py:2312,2384-2386` — `git-add-all-guard` and `destructive-git-ref` still wired; `e3dcc1d` retired other shadows, not these.
EVIDENCE: `pretool-destructive-git-ref.sh:19-30` — stash snapshots + advisory multi-agent warnings; CC 2.1.183 auto-mode block remains a subset (no superseding changelog/commits found).
RECOMMENDED: resolve-moot — conflict check is closed, guards kept and active; only the predictions.jsonl row needs resolving.

## Resolve prediction: [2026-06-25] **The funnel ledger already existed — premise of the BACKSTOP GAP entry was stale.** VOI probe: `~/.claude/llmx-usage.jsonl` is appended by llmx for *every* call rega…
- ref: `predictions.jsonl#impl-27ff16ee-7c02e68c` · created 2026-07-25 (60d)
- scout: ok=True wall=98s tok(in/out/reason)=25411/2754/0

Locating and reading the prediction entry, then checking the codebase state since 2026-07-25.
VERDICT: MOOT
EVIDENCE: 27ff16e shipped `usage-check.py --metered-today` + `doctor.check_metered_spend()` (decisions/2026-06-25-metered-spend-funnel-enforcement.md). Still wired at `scripts/doctor.py:679-718` → `usage-check.py --metered-today`; post-2026-07-25 ea79fa9/f8bdcdc only refactored costing/PRICING sync, not a replacement path.
RECOMMENDED: resolve-moot — observability gap the entry named was implemented at ship; the open BACKSTOP *enforcement* fork is a separate `improvement-log.md:4085` / decisions-pending item, not this prediction.

## Resolve prediction: [2026-06-24] HARNESS-EVAL FLAKY STEP: `system_inventory.py --check` — **fixed 2026-06-28**: `_normalize_volatile_inventory()` strips live launchctl lines from `--render --check` c…
- ref: `predictions.jsonl#impl-93797a17-d4334ee9` · created 2026-07-28 (57d)
- scout: ok=True wall=75s tok(in/out/reason)=30132/2749/0

Locating the prediction entry and checking whether the harness-eval flake fix still applies.


VERDICT: MOOT
EVIDENCE: `improvement-log.md:4081` marks the flake fixed; `scripts/system_inventory.py:452-475` still normalizes launchctl/timestamp volatility for `--render --check`.
EVIDENCE: `justfile:231` + `scripts/tests/test_system_inventory.py:26-29` keep harness-eval on `--render --check` with regression coverage; post-2026-07-28 edits (e.g. `a2f4616`) retired file-bus inventory only, not this path.
RECOMMENDED: resolve-moot — harness-eval instability is fixed and still guarded; only the open `predictions.jsonl#impl-93797a17-d4334ee9` earn-its-keep row needs closing.

## Resolve prediction: **Upgrade `stop-stance-flip-shadow.sh` from lexical markers to a Haiku semantic predicate** — Claude Code supports `type: prompt` hooks (Haiku, ~$0.001) but ONLY on tool events (P…
- ref: `predictions.jsonl#impl-4781bd35-c77f9d2f` · created 2026-08-03 (51d)
- scout: ok=True wall=83s tok(in/out/reason)=20977/2198/0

Tracing the prediction entry and comparing it to the current hook implementation.
VERDICT: MOOT  
EVIDENCE: cc7c3ac added in-hook Haiku `haiku_hit`/`haiku_verdict` beside unchanged lexical predicate (file at that rev: `.claude/hooks/stop-stance-flip-shadow.sh` header L32–41). improvement-log.md:159 marked [x] on 2026-07-04 drain (4781bd35). 5ab18ed (2026-09-02) deleted the hook and dropped it from `.claude/settings.json`; path absent on disk today.  
RECOMMENDED: resolve-moot — the named upgrade shipped before check_date; the instrument was later retired, so no open work remains on this proposal.

## Resolve prediction: **Mine `anthropics/defending-code-reference-harness`** (pushed 2026-06-02): packaged find→grade→judge→novelty→dedup→patch pipeline with executable oracle (ASAN PoC) + fresh-contai…
- ref: `predictions.jsonl#impl-4781bd35-20f1fa80` · created 2026-08-03 (51d)
- scout: ok=True wall=89s tok(in/out/reason)=28827/3492/0

Tracing the prediction entry and checking the repo state since 2026-08-03.


VERDICT: MOOT  
EVIDENCE: `improvement-log.md:164` — `[x]` 2026-07-04 drain into `research/2026-06-12-defending-harness-verifier-patterns.md`; hutter/evals adoption explicitly closed (“no follow-on adoption item”). `4781bd35` — same drain retagged the finding done; no edits to that research memo since 2026-08-03; `predictions.jsonl` has no resolution for `impl-4781bd35-20f1fa80`.  
RECOMMENDED: resolve-moot — the mine task shipped before `check_date`; only the overdue earn-its-keep ledger row remains.

## Resolve prediction: CC 2.1.186 `Agent(type)` permission rules now ENFORCED for named subagent spawns — audit `settings.json` (global + project) for any `Agent(...)` allow/deny rule that now silently…
- ref: `predictions.jsonl#impl-4781bd35-16ace8d4` · created 2026-08-03 (51d)
- scout: ok=True wall=104s tok(in/out/reason)=32667/2926/0

Tracing the prediction entry and checking whether CC 2.1.186 `Agent(type)` enforcement still applies.
VERDICT: MOOT
EVIDENCE: `improvement-log.md:4049` — [x] 2026-07-04 drain: zero `Agent(` typed rules in global + 32 project `settings.json`; nothing to fix. Re-scan 2026-09-23: `rg 'Agent\('` on `~/.claude/settings.json` and all `Projects/*/.claude/settings.json` — no hits (only hook `matcher: "Agent"` at `~/.claude/settings.json:163,358`, not parametric permission rules). `git log --since=2026-08-03` on this topic: no follow-up audit/fix commits (`4781bd35` only registered the drain).
RECOMMENDED: resolve-moot — the requested audit already ran clean and the fleet still has no typed `Agent(...)` permission rules that 2.1.186 enforcement could block.

## Resolve prediction: Codex rust-v0.142.0 subagent terminal-error propagation (#28375) — re-check whether the subagent-zero-output gate (claude-code#47936) needs adjustment now that Codex parents RECEI…
- ref: `predictions.jsonl#impl-4781bd35-893f3f01` · created 2026-08-03 (51d)
- scout: ok=True wall=125s tok(in/out/reason)=59083/4068/0

Tracing the prediction entry and checking the codebase for current state.


VERDICT: MOOT
EVIDENCE: improvement-log.md:4052 — [x] 2026-07-04 drain: no gate adjustment; Codex #28375 error propagation ≠ CC #47936 stub-first durability. skills/hooks/pretool-subagent-gate.sh:9-11 — still cites #47936; no post–Aug-3 removal. skills adb3609 (2026-09-21) — brief-scan tuning on checks 7/10 only, not Codex-related policy change.
RECOMMENDED: resolve-moot — substantive re-check already recorded; nothing since 2026-08-03 reopens the Codex-vs-gate question.

## Resolve prediction: [2026-07-05] **#f/#g extractor silent false-zero + the shared harness-requote class, fixed at all 3 in-scope consumers.** (1) `skills/improve/scripts/extract_user_tags.py` read `m…
- ref: `predictions.jsonl#impl-760089db-43c82362` · created 2026-08-04 (50d)
- scout: ok=True wall=91s tok(in/out/reason)=28442/3708/0

Tracing the prediction entry and checking whether the issue still exists in the codebase.
VERDICT: MOOT
EVIDENCE: improvement-log.md:4096–4097 marks all three consumers fixed ([x], skills@837f4d2, agent-infra@c0c2f22, fd3209a); live code matches — `skills/observe/scripts/extract_user_tags.py:47–79` (`_message_texts` + `isCompactSummary`/`isMeta`), `scripts/reflect_capture.py:96`, `scripts/blindspot_miner.py:55` via `scripts/common/transcript_text.py`. Since 2026-08-04 only `4dec39a` (improve→observe path move) and `1262825` (test repair); no reversion of the buggy `msg.get("content", msg.get("message"))` pattern.
RECOMMENDED: resolve-moot — the silent false-zero / harness-requote defects are already shipped; the open bit is only the overdue gov-shrink prediction on whether pins still earn their keep, not unfixed work.

## Resolve prediction: [2026-07-05] **The class is now a schema property, not a per-miner discipline.** Claude adapter labels `vendor_kind = compact_summary|meta_injected` on user_message events (label-…
- ref: `predictions.jsonl#impl-a6edd79b-035365c9` · created 2026-08-04 (50d)
- scout: ok=True wall=114s tok(in/out/reason)=62047/3775/0

Locating the prediction entry and checking whether the proposed change is still relevant.
VERDICT: MOOT
EVIDENCE: f135857 — `src/agentlogs/adapters/claude.py:405-418` sets `vendor_kind` `compact_summary|meta_injected|user`; `tests/agentlogs/test_claude_harness_labels.py` pins label-never-drop. `scripts/common/transcript_text.py` + `scripts/tests/test_transcript_text_drift.py` single-source raw-JSONL miners; DB consumers filter in `scripts/export_sessions_for_emb.py:50`, `scripts/skill-routing.py:55-56`.
RECOMMENDED: resolve-moot — core migration shipped 2026-07-05; stale item is an overdue earn-its-keep prediction, not an open harness-requote gap (residual `supervision_session.py` raw-JSONL skip is logged deferral, not the proposal).

## Resolve prediction: **test_top_priorities fixtures un-rotted** (`23ae5f9`): hardcoded `last_seen: 2026-07-01` aged past `FAILURE_STALE_DAYS=3` → promote-path test red, suppress-path vacuously green.…
- ref: `predictions.jsonl#impl-8c9f7d99-2d2f8484` · created 2026-08-05 (49d)
- scout: ok=True wall=62s tok(in/out/reason)=25215/2531/0

Tracing the prediction and checking whether the issue still exists.


VERDICT: MOOT
EVIDENCE: `23ae5f9` (2026-07-06) replaced hardcoded `last_seen` with `_recent_ts()` (`now()-1d`) in `agent-infra/scripts/tests/test_top_priorities.py`.
`scripts/tests/test_top_priorities.py:14-17,27,50` still uses `_recent_ts()` only; no hardcoded dates.
`git log --since=2026-08-05 -- scripts/tests/test_top_priorities.py` is empty — no regression or rework since `check_date`.
RECOMMENDED: resolve-moot — fixture rot was fixed and remains stable; only the overdue `predictions.jsonl` earn-its-keep row needs closing, not new work.

## Resolve prediction: **test_agent_maintainability dates from now()** (`7c7c5f7`): `2026-02` commit literals aged out of the `days=120` lookback. Same time-bomb class. — confirmed or refuted?
- ref: `predictions.jsonl#impl-8c9f7d99-59939b1f` · created 2026-08-05 (49d)
- scout: ok=True wall=84s tok(in/out/reason)=20654/2057/0

Investigating the prediction entry and the current `test_agent_maintainability` implementation.


VERDICT: MOOT  
EVIDENCE: `7c7c5f7` switched `tests/test_agent_maintainability.py` to `now()`-relative dates (no `2026-02` literals). `a541e25` deleted `scripts/agent_maintainability.py`; `1262825` removed the test (commit message: script retired). Repo has no `test_agent_maintainability` / `agent_maintainability` paths today.  
RECOMMENDED: resolve-moot — original time-bomb was fixed, then the whole maintainability test surface was retired so the gated earn-its-keep check has no live target.

## Resolve prediction: **test_close_fixes timeout-scaler born-red** (`bfa00b6`): asserted the 1200 cap at 80MB but `120+80*12=1080`; now pins linear region AND cap via sparse-truncated files. — confirme…
- ref: `predictions.jsonl#impl-8c9f7d99-d419352b` · created 2026-08-05 (49d)
- scout: ok=True wall=65s tok(in/out/reason)=24072/2440/0

Tracing the prediction entry and verifying the current implementation.


VERDICT: MOOT  
EVIDENCE: `bfa00b6` (2026-07-06) fixed `tests/agentlogs/test_close_fixes.py` — lines 156–170 use `os.truncate` sparse 80MB/200MB files and assert 1080.0 vs 1200.0 per `src/agentlogs/index.py:70-72` (`120 + size_mb*12`, cap 1200). `improvement-log.md` marks the finding `[x]`; no post–2026-08-05 change to that test (only unrelated `b411d86` on `index.py`).  
RECOMMENDED: resolve-moot — the born-red wrong-1200-at-80MB defect was shipped before `check_date`; only the stale `predictions.jsonl` earn-its-keep row remains.

## Resolve prediction: **approval-tiers manifest coverage** (`9f3ee1b`): `pretool-noext-nongit-guard.sh` + `pretool-timeout-modal-guard.sh` shipped in skills without manifest entries → `test_approval_ti…
- ref: `predictions.jsonl#impl-8c9f7d99-a7d8cac8` · created 2026-08-05 (49d)
- scout: ok=True wall=86s tok(in/out/reason)=24156/2542/0

Tracing the prediction entry and verifying current manifest/guard state.
VERDICT: MOOT
EVIDENCE: `9f3ee1b` added both guards to `config/approval-tiers.json` `invocation_discipline` (lines 67–68); hooks live at `~/Projects/skills/hooks/pretool-noext-nongit-guard.sh` and `pretool-timeout-modal-guard.sh`. `scripts/approval_tiers.py` validate: `ok: true`, `uncovered_global: []` (2026-09-23).
RECOMMENDED: resolve-moot — the manifest-coverage gap was fixed before `check_date`; verifier still passes, so the open item is prediction closeout, not rework.

## Resolve prediction: **reclaim-rotate nightly exit-3** (`94a7a04`): 04:10 cron collided with the 2h indexer single-writer lock; added `--wait-seconds 1800` per `agentlogs prune --help`'s own prescript…
- ref: `predictions.jsonl#impl-8c9f7d99-f9d6067f` · created 2026-08-05 (49d)
- scout: ok=True wall=93s tok(in/out/reason)=31086/3682/0

Locating the prediction entry and checking the current reclaim-rotate/indexer implementation.


VERDICT: SUPERSEDED
EVIDENCE: `~/dotfiles/scripts/reclaim-rotate-cron:27-30` — nightly job no longer runs `agentlogs prune` (worktree_gc + uv cache only). `~/dotfiles/scripts/reclaim:373-376` — `cmd_rotate` retired to weekly `just agentlogs-archive`. `8ea8438` relocated reclaim/cron to dotfiles; `94a7a04`'s `--wait-seconds 1800` targeted the removed nightly rotate path (`justfile:780` keeps 1800 on the weekly archive prune only).
RECOMMENDED: resolve-superseded — the 04:10 indexer-lock exit-3 issue is obsolete because retention left the nightly reclaim-rotate motor.

## Resolve prediction: clash-detection shadow precision — window extension (capture pipeline must produce data first) — confirmed or refuted?
- ref: `predictions.jsonl#2026-08-05-clash-shadow-precision-ext` · created 2026-08-05 (49d)
- scout: ok=True wall=109s tok(in/out/reason)=31144/5508/0

Revalidating the stale prediction: locating the entry and tracing clash-detection shadow precision in the codebase.


VERDICT: STILL-VALID
EVIDENCE: `beecb7c` retired `ops/launchd/com.agent-infra.clash-detect.plist` (2026-07-14) but kept `scripts/clash_detect.py` for a pending `--summary` review (`decisions/2026-07-14-gemini-critique-only-policy.md:50-54`). Today: `~/.claude/clash-capture.jsonl` 119 lines (capture live via `.claude/settings.json:18`) vs `clash-shadow.jsonl` 22 rows / 2 CLASH / 0 `promoted` (shadow mtime frozen 2026-07-14); `just clash-detect --summary` → 2 CLASH (9%). No `predictions.jsonl` resolution for `2026-08-05-clash-shadow-precision-ext`; `scripts/questions_view.py:328-331` clash feeder still dormant.
RECOMMENDED: keep — capture contingency is met but the ≥5-CLASH / human-judged ≥80% promote-or-CUT gate was never decided and auto shadow accumulation stopped before the 2026-08-05 check_date.

## Token cost
- scouts: 76 · out_tok: 249101 · reason_tok: 0 · wall_sum: 8297s

## Dispositions applied 2026-09-23T09:06:16+00:00

- resolved: 11
- deleted: 0
- manual: 30
- kept: 35
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-17-stop-hook-suppress-resurfaced-unattributable.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-18-live-peer-work-visibility.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-19-peer-aware-uncommitted-attribution.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-19-stop-hook-caseA-and-shared-checkout-ceiling.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-19-stop-hook-peer-attribution-guard.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-20-gpu-class-drift-lint.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-10-contested-file-adjudication-cache.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-10-stop-hook-peer-liveness.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-28-pathspec-contested-file-guard.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-08-18-iq-sexdiff-track-analysis-scripts.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-08-19-bgrun-watcher-pairing-nudge.md`
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4980db9d-aba2767d` — Resolve prediction: **Usage telemetry — subscription blind spot closed (`llmx@7e
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4980db9d-03ab1531` — Resolve prediction: **Pulse liveness contracts — scoped, NOT universal (`bf68c3a
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-275e3582-47014afe` — Resolve prediction: **llmx usage surfacing** — DONE (`llmx@62ce643`). Verify-bef
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-3894d7b4-cbf2123a` — Resolve prediction: **PPV/reflect-eval counted STALE firings against the current
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-e75d3b7c-5f38d971` — Resolve prediction: **Closure metric repointed (`supervision-kpi.py`)** — `hooks
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-e75d3b7c-2aec2f7a` — Resolve prediction: **`over_caution` graduated shadow→enforce (soft nudge)** — `
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-81814792` — Resolve prediction: **Un-archive `/code-review` skill** — moved from `skills/_ar
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-8b334daa` — Resolve prediction: **Skills wired to Composer CLI** — `/critique` (composer def
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-8ed4792d` — Resolve prediction: **Critique axis overlap + cost tooling (2026-06-14)** — `sta
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-8d875561` — Resolve prediction: **Review dispatch consolidation (phase 1)** — closeout parti
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-70205129` — Resolve prediction: **Critique P0+P1 hardening** — outcome_link `linked_anchor`/
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-3389a5cc` — Resolve prediction: **Global review routing sync** — `~/.claude/CLAUDE.md` parti
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-ee04335f-c4f51912` — Resolve prediction: **`supervision_taxonomy.py` — single-source correction taxon
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-22aee86f-c92928d3` — Resolve prediction: **Claude Code 2.1.1xx native-feature adoption** — closed 202
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-71823900-f6ee76b3` — Resolve prediction: **Gated 5 git-only Bash hooks behind `if: "Bash(git*)"` in `
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-3ead94aa-d3387cd8` — Resolve prediction: **Codex 0.141 PostToolUse code-mode gating — VERIFIED, no sh
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-3ead94aa-59767fbc` — Resolve prediction: **CC 2.1.183 native destructive-git block — no conflict, kee
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-27ff16ee-7c02e68c` — Resolve prediction: [2026-06-25] **The funnel ledger already existed — premise o
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-93797a17-d4334ee9` — Resolve prediction: [2026-06-24] HARNESS-EVAL FLAKY STEP: `system_inventory.py -
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4781bd35-c77f9d2f` — Resolve prediction: **Upgrade `stop-stance-flip-shadow.sh` from lexical markers 
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4781bd35-20f1fa80` — Resolve prediction: **Mine `anthropics/defending-code-reference-harness`** (push
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4781bd35-16ace8d4` — Resolve prediction: CC 2.1.186 `Agent(type)` permission rules now ENFORCED for n
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4781bd35-893f3f01` — Resolve prediction: Codex rust-v0.142.0 subagent terminal-error propagation (#28
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-760089db-43c82362` — Resolve prediction: [2026-07-05] **#f/#g extractor silent false-zero + the share
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-a6edd79b-035365c9` — Resolve prediction: [2026-07-05] **The class is now a schema property, not a per
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-8c9f7d99-2d2f8484` — Resolve prediction: **test_top_priorities fixtures un-rotted** (`23ae5f9`): hard
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-8c9f7d99-59939b1f` — Resolve prediction: **test_agent_maintainability dates from now()** (`7c7c5f7`):
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-8c9f7d99-d419352b` — Resolve prediction: **test_close_fixes timeout-scaler born-red** (`bfa00b6`): as
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-8c9f7d99-a7d8cac8` — Resolve prediction: **approval-tiers manifest coverage** (`9f3ee1b`): `pretool-n
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-8c9f7d99-f9d6067f` — Resolve prediction: **reclaim-rotate nightly exit-3** (`94a7a04`): 04:10 cron co

## Orchestrator dispositions (2026-09-23)

Operator: "do whatever of these 77 items are still current ... use your taste .. unless you
need me (non software, non CS stuff)". Scout verdicts were inputs, not decisions.

**Predictions (34 rows, `predictions.jsonl`).** All 30 MOOT/SUPERSEDED rows the sweep could
not apply, plus the 4 STILL-VALID ones, were resolved by the orchestrator. Landed-and-live rows
became `partial` because none measured the predicted effect (a false `confirmed` is the worse
error). `over_caution` graduated enforce became `refuted` (reversed 2026-07-25). Clash shadow
precision became `refuted`, which is a CUT under its own pre-registered rule (`0391997`). Due
predictions no longer reach the operator's queue (`b37183e`).

**Steward proposals, beyond the 11 the sweep resolved:**

| Proposal | Disposition | Why |
|---|---|---|
| wip-churn-worktree-noop, shared-checkout-reset-wipes-peer-work, subagent-autocommit-leak | SUPERSEDED | Scouts checked for the proposed designs; later hook changes closed the incidents differently (auto-commit off with subagents or peers, no hook resets, stash guard, race-immune Session-ID) |
| backstamp-misfire-watch | DONE | 4 of 5 stamps misfired on partial supersessions; trigger narrowed (skills `e3b2139`), substrate 0011 corrected (`b2c0df1`) |
| researcher-pathological-empty-stop-gate | REJECTED (noop) | 5 shadow fires in July, 0 since across 24 researcher sessions; shadow kept as tripwire |
| lens-bank, redteam-before-foreclosure, goal-terminal-predicates, executable-hook-corpus, eval-frontier-sensor, triage-dispatch-reflex, llmx-concurrency-semaphore, checkpoint-per-session-files, llmx-price-verify, absence-claim-falsifier-guard, hook-state-stateless-revalidation | REJECTED | Stamped per file in `~/.claude/steward-proposals/resolved/`: covered elsewhere, no named consumer, or no incident to justify the maintenance; each carries a revisit trigger |
| donor-export-auth, form-hpo-verify-gate, stage-hang-watchdog | DEFERRED | genomics is off-limits while production batches run; improvement-log `[ ] GENOMICS-DEFERRED` |
| intel-executive-tick | ESCALATED | Scheduling a weekly autonomous intel session is an autonomy and quota call for the operator |
| history-mutation guard + no-amend | DONE | With a live peer in the checkout, `reset --hard` and every `--amend` block, and non-pathspec reset/rebase block unless this session wrote every dropped commit (skills `0e58336`, `834a60e`, `a0b027f`). The 07-10 amend was of the session's OWN checkpoint, so HEAD ownership cannot excuse an amend. The 07-16 peer was a Codex session, which the peer detector could not see until `8a48ead`. Hook-process commits now stamp their own Session-ID (`0b83fdf`) |
| rg-replace guard | DONE | Advisory on glued `-r<letters>` (skills `648fe4a`); 89 real fires in a 30-day replay |
| zero-hit-grep nudge | REJECTED | PostToolUse never fires for a Bash call that exits non-zero (probe), so the designed trigger is unobservable; the incident's load-bearing fix landed in arc-agi |
| reflect-capture headless exclusion, reflect-close prefix/teammate FP, digest-fallback scope, digest expiry cluster (3) | DONE | One operator-authorship predicate on Claude Code's own `origin`/`entrypoint` stamps (agent-infra `4272831`); prefix ids everywhere (`d322d64`); project-scoped fallback (`d357137`); expiry at the 14-day transcript horizon or on a missing transcript (`644772c`); `/rsi` doc (skills `7d44b37`). 36 new tests, each group failing on its pre-fix commit |
| evalcore-transport-preflight | DONE | `run_eval` pre-flight aborts a dead arm before the sweep (evals `407b49e`, `eaf6e5e`, `b758d93`); verify-edge raised `CandidateError` instead of scoring "ERROR:" replies (`aa4c34b`). The live copy is in evals: substrate's copy had no importers and was deleted (`a3ee573`), and the `/eval` skill pointed at it (skills `73dc7b6`) |

**Scout accuracy.** 3 of 35 STILL-VALID verdicts were wrong in the same way: the scout checked
whether the proposed mechanism existed, not whether the incident could still happen. The scout
prompt now says so (agent-infra `questions_drain.py` step 4).
