# Steward-Proposal Triage — Late Half (2026-06-25 .. 2026-07-06)

Read-only grading pass. 32 proposals in scope (a) + 2 decision briefs (b). Implementation
status verified via `git cat-file`/`log`, file/recipe existence, and vetoed-decisions grep
(no veto matches for this cohort). Final taste call stays with the parent.

Counts: ALREADY-DONE 11 · MERGE-WITH 6 · IMPLEMENT-NOW 8 · RECOMMEND-APPROVE 6 · STALE 1 · REJECT 0.

---

## Decision brief 1 — Native-First commit-trailer enforcement (`decisions-pending/2026-06-24`)

- **Proposed:** extend the shared `commit-check-parse.py` with one advisory block — when a new `.py`
  is staged and no `Native-First:` trailer is present, *suggest* one (never blocks), parallel to the
  existing `Evidence:` suggestion (lines 160-163).
- **Live options:** (i) ship the advisory now; (ii) do nothing (stay instruction-only); (iii) later
  promote to a `warnings`-level nudge if the advisory proves ineffective (pre-registered rollback).
- **Evidence:** gov-report 2026-06-24 — 150/191 new scripts in 90d carry no trailer (`native-patterns`
  FAIL, margin 0.215; `P1-rule-hook-balance` contradiction). Grader `native_first.py` reads a rolling
  90d window → forward-fixable, not dead debt.
- **Doc recommends:** ship advisory-only, measure via the grader, promote only if the missing-trailer
  fraction doesn't fall in 30d.
- **New facts since filing:** it edits a SHARED hook (every repo's commit flow) → invariant #4 requires
  human sign-off even for additive-advisory. Clears the governance bar (recurs, not covered — grep-
  confirmed no native-first check today, checkable predicate). Reversible.
- **Parent call:** approve the advisory extension (low risk, P3-consistent) vs accept instruction-only.
  Recommend approve.

## Decision brief 2 — Metered-spend funnel hard-block (`decisions-pending/2026-06-25`)

- **Proposed:** where a HARD BLOCK on metered llmx spend should live (observability half already shipped:
  `usage-check.py --metered-today` + `doctor.check_metered_spend`).
- **Live options:** A = in-llmx pre-dispatch guard reading `~/.claude/llmx-usage.jsonl` (surface-agnostic;
  recommended); B = launchd periodic alarm (detect-not-prevent); C = extend `pretool-cost-guard.sh`
  (foreground-Bash only — rejected alone; does not cover the bg-worker case that caused the incident).
- **Evidence:** $70 silent-spend (substrate `018ee7c8`, 2026-06-22) — a backgrounded worker's metered
  branch was invisible to the foreground-Bash guard; `llmx-usage.jsonl` is the funnel all spend passes.
- **Doc recommends:** A+B at the $25 cap, with `LLMX_SPEND_OVERRIDE=1` for intended large jobs.
- **Two sub-forks needing the operator's call:** (1) *which cap is real* — $25 (constitution/invariants)
  vs `pretool-cost-guard.sh` $500/$1000 (40× disagreement); the block needs ONE number. (2) *unpriced-model
  undercount* — `gemini-3.5-flash` prices $0 (only `gemini-3-flash` in the table); single-source the
  pricing map (invariant #9) + set unpriced policy (fail-open vs overcount vs refuse).
- **New facts:** A edits llmx (every project's dispatch path) → shared, human-gated. Observability half
  is live, so this is purely about *prevention*.
- **Parent call:** approve A+B@$25+override, or stay observability-only. Resolve the cap-number fork
  either way — it's a latent contradiction independent of the block.

---

## ALREADY-DONE (11)

| Proposal | Evidence |
|---|---|
| 2026-06-26-suspect-empty-extraction-detector | substrate `2958530` (+`bea7af8`) — `corpus_extract/extract.py` + lean prompt + tests; self-report confirmed. Part 3 (qc cold-dir metric) low-pri open. |
| 2026-06-26-value-kind-ingest-gate | substrate `676dc4f` — `ingest.py` kinds local entities from prefix (root fix). Remaining mint-time gate + 116K re-kind apply are explicitly operator-gated. |
| 2026-06-27-watch-drain-volume-free-monitor | genomics `scripts/watch_drain.py` + `just watch-drain` (justfile:1956); volume-free PG poll. |
| 2026-06-29-qc-fanout-hardening | genomics `6eb49392e` — stagger+self-heal + tissue-context guard. own_code STALE_BASIS residual addressed by `2dbeb8dee` (2026-07-06). |
| 2026-06-29-deid-precommit-hook | skills `4f37338` — `pre-commit-deid-guard.sh` present + wired into `pre-commit-guards.sh` chain. **Output-filter half OPEN** but harness/proxy-level, not locatable from the hooks dir → not actionable here. |
| 2026-06-30-edge-infra-killswitch-pre-build-gate | Text is verbatim in global `~/.claude/CLAUDE.md` Pre-Build #1 ("run the kill-switch eval BEFORE building… #g 2026-06-30"). Minor anti-cry-wolf provenance-tag companion is a small residual. |
| 2026-07-03-stage-hang-watchdog | genomics `1cc7bbf19` — `scripts/orchestrator/hang_watchdog.py` + `just hang-watch` (justfile:2691); progress-stall (not wall-time) kill. |
| 2026-07-04-prose-structured-field-drift-lint | genomics `417f231b8` — `lint_prose_structured_drift.py` + `just prose-structured-drift-audit` (justfile:1312). |
| 2026-07-04-ungoverned-science-in-catalog-prose | genomics `lint_ungoverned_catalog_science.py` + `just ungoverned-science-audit` (piece 1). Piece 2 is doc/process, folded in. |
| 2026-07-01-closure-drive-auto-reconcile | CORE superseded — `_reconcile_after_dispatch_wait` (`pipeline_orchestrator.py:2580`, built 2026-06-01); fix = always pass `--wait`. 2 surgical peer-owned gaps (attempt-id namespacing, frozen-Volume reload warning) + wave-parallel `drive_sample.py` remain as residual for a focused session. |
| 2026-07-06-single-source-payload-verdict | genomics landing today — `f4aa8411a` "Wire tier-2 cert axis to the synced mirror with a fail-closed currency gate" (15:59) + `d3fab63fc`/`2dbeb8dee` (epistemic-#9 root-cause, "fix in flight"). Core ask (authority reads the mirror, not a PG-blind count) is implemented. |

## MERGE-WITH (6)

| Proposal | Merge target | Why |
|---|---|---|
| 2026-06-25-owncode-attribution-to-completion-kernel | 2026-07-02-ledger-closure-depth-and-cca-executor | Same cca/own-code cosmetic-classification kernel; core landed genomics `2dbeb8dee` (2026-07-06, "single-source with completion axis, stop phantom stale_basis"). |
| 2026-06-25-wip-churn-worktree-noop | 2026-06-27-shared-checkout-reset-wipes-peer-work | Same root: auto-`[wip]` checkpoint + `reset --hard` + silent worktree no-op on a shared checkout. |
| 2026-06-26-sample-remediation-payload-blind-phantom | 2026-07-06-single-source-payload-verdict | Same class: tools mislead by not reading the synced mirror. The lead-banner presentation guard is the cheap complement to the deeper single-source fix landing today. |
| 2026-06-27-stage-liveness-worker-state | 2026-07-03-stage-hang-watchdog (+ watch-drain) | Liveness-read need is now covered by `hang_watchdog` (reads stage-telemetry) + `watch-drain` (PG frontier). Residual = the advisory `_emit_step`-every-60s lint. |
| 2026-07-01-machine-state-done-autonomy | 2026-07-02-ledger-closure-depth-and-cca-executor | Same "done = machine state; executor must run RERUN+REPIN; finalize self-certifies" family being worked today. |
| 2026-07-05-background-bash-relative-path-guard | 2026-07-05-codex-exec-stdin-guard | Both PreToolUse:Bash advisory guards on `run_in_background` footguns → one bg-dispatch-footgun hook. |

## IMPLEMENT-NOW (8 — single-repo, reversible, no human gate)

| Proposal | Why cheap/clean |
|---|---|
| 2026-06-27-admission-overcall-flag | genomics, additive deterministic flag at the admission gate; zero-iatrogenic (flags, never mutates output); canary specified (PGK1 V81F, finding 403). Not in `finding_policy` source today. Serves GOALS #1. |
| 2026-07-02-load-json-fail-loud-on-corrupt | genomics root fix: make `load_json_or_default` raise on present-but-corrupt; subsumes the 3 whack-a-mole guards already added (`c19f8bd17`). Ship with the blast-radius caller sweep + test. |
| 2026-06-27-commit-mine-drops-git-rm-deletions | genomics: track `git rm`/`git mv` in `session_touched_files.py` (symmetric with Edit/Write) + stop the blanket `git reset` on failure. Silent commit-drop, bit twice one session. |
| 2026-06-27-donor-export-auth | genomics `just donor-export <sample> <mode>` recipe (refresh gcs-push-token → run) — no such recipe today (only the SA name at justfile:2172). Native-first wrapper; kills stale-token toil + token-in-error leak. WIF is a separate config-only deeper option. |
| 2026-06-27-form-hpo-verify-gate | genomics `just verify-hpo <sample>` wrapping existing `verify_curated_hpo`; standing bio-verify gate on the phenotype rail (PII-gitignored, so no CI catches it). |
| 2026-06-28-f16-midwrite-volume-crawl-guard | genomics-local PreToolUse:Bash advisory: warn when a full-DAG volume crawl launches while the sample has live Modal apps (VolumeListFiles-quota freeze). Sibling to `pretool-timeout-modal-guard.sh`. |
| 2026-06-29-evalcore-transport-preflight | substrate `evalcore.run`: cheap 1-ping preflight per candidate/judge; abort-loud on unambiguous transport error (401/403/0-byte) instead of scoring 0. Route the companion "answer-API ≠ agent" lesson to the `/eval` skill anti-patterns (not mechanizable). |
| 2026-06-30-stale-mock-test-class | genomics bounded test-fix pass (trace each stale mock to its refactor commit, update or delete; mark env-dependent tests). No behavior change, independently revertable. |

## RECOMMEND-APPROVE (6 — shared/global/3+ projects → human gate)

| Proposal | One-line rec |
|---|---|
| 2026-06-27-shared-checkout-reset-wipes-peer-work | High-value (silent peer data-loss, reflog-verified). Approve the 3 guards; gate on a no-work-loss resume test (proposal's own condition). Absorbs wip-churn. |
| 2026-07-02-ledger-closure-depth-and-cca-executor | Deep genomics fix that gates dispatch (completion authority). cca cosmetic-escape landed `2dbeb8dee`; Fix 1 (depth-1 ledger closure = stage_hash) + cca-into-`from-drift` + `sample-currency` surface remain. Approve a focused, replay-harness-gated session; peer-owned safety code. |
| 2026-07-03-askuserquestion-autonomous-warn | Global PreToolUse warn hook; cost an 8h overnight window once. Approve — needs a runtime autonomous-run marker; non-blocking. |
| 2026-06-27-unstarted-goal-detection | Global stop-gate: loud "GOAL UNSTARTED: X 0/N" on zero deliverable progress. Approve — narrow checkable predicate; needs goal↔deliverable binding. (Single-session evidence — parent weighs vs the 2+-session bar.) |
| 2026-07-05-codex-exec-stdin-guard | Merged bg-dispatch-footgun hook (with background-bash-relative-path). Approve as one global advisory PreToolUse:Bash hook. (Both single-session evidence — parent weighs vs the 2+-session bar.) |
| 2026-07-06-userprompt-clock | Trivial global UserPromptSubmit hook injecting `[clock: …]`; 4.5h stale-clock incident. Approve — additive, read-only, delete to revert. |

## STALE (1)

| Proposal | Evidence |
|---|---|
| 2026-07-02-batch-divergence-refresh | Pattern shipped as a doc (`intel/docs/workflows/divergence_refresh.md`); the SCRIPT orchestrator is deferred by its OWN trigger ("build only if a 3rd run shows doc-following errors" — unmet). No action until the trigger fires. |
