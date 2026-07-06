# Steward Proposal Triage — Early Half (2026-06-15 → 2026-06-24)

Scope: 37 proposal files in `~/.claude/steward-proposals/` with filename prefix
2026-06-15..2026-06-24 inclusive, plus `TRIAGE-2026-06-16.md`. Read-only grading;
no files committed, edited, or moved. The final ADOPT/REJECT taste call stays with the parent.

Method: each proposal read in full; checked against `implemented/`, `git log --grep` +
`git log -- <path>` in the target repo, and `vetoed-decisions.md`. Every ALREADY-DONE cites a
live file/commit read (not a grep hit).

## Counts

| Verdict | N |
|---|---|
| ALREADY-DONE | 15 |
| STALE | 3 |
| MERGE-WITH | 1 |
| IMPLEMENT-NOW | 6 |
| RECOMMEND-APPROVE | 7 |
| REJECT | 5 |
| **Total** | **37** |

`TRIAGE-2026-06-16.md` (15 items) is already dispositioned; 6 of its "shipped" items now sit
in `implemented/`. Only `2026-06-15-llm-hooks-dead-metered-api` overlapped this active scope
(re-graded below, still pending).

---

## ALREADY-DONE (15) — free closes, cite the commit

| Proposal | Evidence |
|---|---|
| 2026-06-16-anim-workbench-grinder-orchestration-tooling | Headline anim-local items live: `scripts/merge-grinder.ts` + `src/workbench/localize.ts`. Residual cross-project items #4/#7 unbuilt — see "unbundled" note below. |
| 2026-06-16-session-id-private-stamp | `skills/hooks/prepare-commit-msg-session-id.sh:15-23` prefers race-immune `$CLAUDE_SESSION_ID`; commit skills@fea144a. |
| 2026-06-17-agent-tooling-friction-b38baad8 | `--axes standard` preset in `critique/scripts/model-review.py:562-564`; codebase-map git read wrapped try/except in `refresh_codebase_map_on_commit.py:37-41`; commit-mine foot-gun moot (script gone). |
| 2026-06-17-eval-run-packager | `evals/extraction_bakeoff/eval_run_packager.py`; commit evals@e218860 (later rebased onto `evalcore.run_manifest` aa25023). |
| 2026-06-19-peer-aware-uncommitted-attribution | Cluster canonical. Both halves live: skills@4abc666 (`peer-session-count.sh` + peer-aware message branch) + skills@d1907d3 (suppress unattributable nag under peers). |
| 2026-06-19-stop-hook-caseA-and-shared-checkout-ceiling | Content-hash Case-A guard, skills@ce59d36, live `stop-uncommitted-warn.sh:150-187`. Deeper worktree-by-default root operator-gated by design. |
| 2026-06-20-clean-room-finalize-only | phenome@db5718a3 `--finalize-only` on `kg_clean_room_build.py` (~5s revalidate vs ~12min). |
| 2026-06-20-qc-mirror-freshness-gate | genomics ef96fca0d + c7e584888 (gate attestation on mirror currency). |
| 2026-06-20-stop-hook-writer-provenance-attribution | `scripts/common/automation_ledger.py` + `stop-uncommitted-warn.sh:231` + `test_stop_hook_automation_attribution.py`. |
| 2026-06-20-volume-readfile-not-mirror-listdir | genomics 310da524a + 77fb68ffc (ledger reads off un-throttled GetFile); manifest validation in `operator_views.py:283`. |
| 2026-06-21-worktree-hygiene-surfacing | agent-infra b7314f2 + 6c48e3b; file carries DISPOSITION 2026-06-21 (global hook correctly declined for local pulse home). |
| 2026-06-22-audit-head-recheck-dedup | agent-infra df7a369 — `head_recheck()` in `audit_findings_consolidation.py` + test. |
| 2026-06-22-reachability-into-remediation | genomics ea4a61b5 — `just owncode-classify <sample> --diffs`. |
| 2026-06-23-reference-data-integrity-gate | Core slice shipped: no-swallow lint `lint_refdata_staging.py` (037ba35f3) + fail-loud extraction (f2c6badab). Residual volume pre-dispatch gate optional, genomics winding down. |
| 2026-06-20-handoff-consolidation | hutter@5a1f914 (checkpoint.md → bounded live state, 3770→47 lines). |

## STALE (3) — premise no longer holds

| Proposal | Evidence |
|---|---|
| 2026-06-20-claim-context-ref-corpus-grounding | claimcore KG retired: phenome@a9138382 moved `src/phenome/claims/` → `attic/claims-kg/`; content-addressing already borrowed into live path (d702a9b3, 1fa98315). Target `claimcore/identity.py:119` gone. |
| 2026-06-20-clinical-assertion-evidence-gate | Central gate not just unbuilt but explicitly rejected — genomics@be5d4759b chose adapter-level `evidence_class` minting over a central gate. Overcall class handled (OVR-1..6 ecd498f18, caps 36b62ca84/b68e8a389). |
| 2026-06-24-adaptive-ledger-parallelism | List-burst rate-limit removed at source (list-free summary pulls off un-throttled GetFile): genomics@64cdea166 + 278da786a + 06a6c8e80. Eliminating the burst supersedes throttling it. |

## MERGE-WITH (1)

| Proposal | Merge target |
|---|---|
| 2026-06-19-stop-hook-peer-attribution-guard | → 2026-06-19-peer-aware-uncommitted-attribution (same fix, same commit skills@4abc666; own header self-attests IMPLEMENTED). Both ALREADY-DONE. |

## IMPLEMENT-NOW (6) — single-repo, reversible, cheap, no human gate

| Proposal | What to build | Evidence it's unbuilt |
|---|---|---|
| 2026-06-24-verified-failloud-ingest-tool | Promote scratch `prod_ingest.py`/`ingest_loop.sh` → tested fail-loud `corpus-mine fetch\|extract\|drain` CLI (claim_events delta + non-zero exit). | substrate/corpus-extract; no corpus-mine CLI (grep hits are outbox.py/pdf_mineru.py). Recurred 2+ sessions (6h silent OOM then fetch-hang). |
| 2026-06-20-gpu-class-drift-lint | Advisory drift-lint: GPU class from `@app.function(gpu=)` vs `ResourceClass`. | genomics; no gpu-drift check in `validate_orchestrator.py`. Silent-proxy, 5 stages mis-classed, $1-13/run. |
| 2026-06-24-lens-bank-application-tracking | Generated-MD view of the lens DB (serves "track generator, derive output"). | immigration-research; kills 9-day MD↔DB drift phantom (Q06/S15 "reconciliation pending since 2026-06-15"). NOT the decay/bayesian vetoes. |
| 2026-06-21-pytest-collection-error-gate | `--collect-only` gate (~6s) as `just validate` leaf / pre-commit. | genomics; no gate present. No FP class (collection errors always real). |
| 2026-06-21-phenome-pytest-timeout | Add `pytest-timeout` + `timeout=300`/`timeout_method="thread"`. | phenome/pyproject.toml lacks it. |
| 2026-06-17-substrate-capability-map | `just substrate-map` recipe (grep CREATE TABLE across editable path-deps). | No recipe/generator (grep empty). Do the recipe stopgap before the deeper codebase-map generator change. |

## RECOMMEND-APPROVE (7) — genuine human gate (shared hooks / 3+ projects / irreversible)

| Proposal | Rec |
|---|---|
| 2026-06-15-llm-hooks-dead-metered-api | Repoint `posttool-reception-payload-llm.sh:38,97` + `source-check-haiku.py:34,47` off metered `api.anthropic.com` to the $0 subscription path (as `stop-smart-judge.sh:166` does). Shared hooks, still failing silent. |
| 2026-06-24-attestation-output-content-binding | Bind plausibility verdict to `output_content_hash`, demote own_code staleness to advisory. Touches genomics certification gate (cardinal failure surface) — needs focused session + replay harness. |
| 2026-06-19-compute-dont-copy-admission | Add confidence_ceiling to `finding_policy.py` + adapter-qualifier lint. Architectural clinical-grading change; gated per proposal's own guardrails (defer until syn2sr/canary). |
| 2026-06-21-researcher-pathological-empty-stop-gate | Add substantive-stub-after-N-calls logic to `subagent-source-check-stop.sh`. Global hook; approve conditional on 0-FP transcript validation (self-flagged "do not ship blind"). |
| 2026-06-17-stop-hook-suppress-resurfaced-unattributable | Add per-session already-surfaced marker + delta-only logic to `stop-uncommitted-warn.sh`. Shared hook; chronic 5×/session re-surface. |
| 2026-06-18-live-peer-work-visibility | Enrich `sessionstart-peer-session-warn.sh` with per-peer edited paths / recent commits / active topic. Shared SessionStart hook. |
| 2026-06-20-deletion-guard-attribution-verify-first | Reword `stop-mass-deletion-guard.py:58` to lead with "origin UNKNOWN — verify before attributing to a peer" (Option A, cheap/reversible). Same unverified-attribution class 4abc666 fixed elsewhere; distinct hook. |

## REJECT (5) — fails governance bar (recur 2+ sessions / not covered / checkable-or-architectural)

| Proposal | Why rejected |
|---|---|
| 2026-06-19-measurement-fanout-discipline | Lead item (block `nohup` in tool-call Bash) contradicts newer global `wakeup-cadence.md` sanctioning `nohup+disown` for harness-reaped jobs; other items arc-agi-scoped / covered by >10GB disk-preflight. |
| 2026-06-20-holdout-not-insample-eval-metric | Already covered by global CLAUDE.md epistemic_discipline #8 — which names the same arc-agi 2026-06-20 session verbatim. |
| 2026-06-21-rg-replace-flag-guard | Single-session recurrence (018ee7c8, 3× within it) — below the 2-session bar. Revisit on 2nd-session recurrence. |
| 2026-06-22-backstamp-misfire-watch | By design "a monitor, no code change now." Nothing to build; passive `/improve maintain` glance, 30d window → 2026-07-22. |
| 2026-06-24-redteam-before-foreclosure | Recurred 3-4× in ONE session (hutter), not 2+ sessions; substantially covered by wakeup-cadence heretic front + `/critique` gate + proxy-as-truth #8. |

---

## Notes for the parent

- **Cluster (peer-attribution / shared-checkout, 5 files):** canonical = `2026-06-19-peer-aware-uncommitted-attribution` (done, skills@4abc666). `stop-hook-peer-attribution-guard` merges into it; `caseA-and-shared-checkout-ceiling` (done, distinct content-hash guard) and `stop-hook-writer-provenance` (done, automation ledger) share only the operator-gated worktree-by-default ceiling; `deletion-guard-attribution-verify-first` targets a *different* hook and stays open (RECOMMEND-APPROVE).
- **Unbundled ask:** `anim-workbench-grinder` is graded ALREADY-DONE on its headline items, but its cross-project residuals #4 (CLAUDE.md content-hash dedup) and #7 (dispatch-routing nudge hook) are unbuilt — if you want them tracked, each is its own RECOMMEND-APPROVE, not covered by the close.
- **No vetoed-decisions matches** across all 37. `lens-bank-application-tracking` is explicitly *not* the decay-salience / bayesian-surprise veto (usage counter ≠ decay engine).
