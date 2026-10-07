# Stale-question drain — 2026-09-02

_One revalidation scout per stale item (backend: codex; `just questions-drain --dispatch`). Scouts recommend; disposition is orchestrator/operator work — see plan 17d2a35c-middle-manager-harvests._

## Prefer **wire (A)** or **relabel/kill (B)** for the legacy screen?
- ref: `/Users/alien/Projects/agent-infra/decisions-pending/2026-07-15-genomics-export-ship-path.md` · created 2026-07-15 (49d)
- scout: ok=True wall=84s tok(in/out/reason)=260636/1576/558

VERDICT: MOOT
EVIDENCE: b765a9894 relabeled `donor-shipping-readiness` as diagnostic-only and made `donor-export-authority` the shipping path.
EVIDENCE: genomics/CLAUDE.md:254 and scripts/donor_shipping_readiness.py:412 confirm B remains current.
RECOMMENDED: resolve-moot — relabel/kill (B) is implemented.

## LLM hooks on the metered API are silently dead — repoint to $0 subscription
- ref: `/Users/alien/.claude/steward-proposals/2026-06-15-llm-hooks-dead-metered-api.md` · created 2026-06-15 (79d)
- scout: ok=True wall=81s tok(in/out/reason)=226732/1598/580

VERDICT: MOOT
EVIDENCE: 56c24f7 repointed the named hook to subscription-first transport.
EVIDENCE: hooks/posttool-reception-payload-llm.sh:96-135 strips the API key, runs `claude -p`, and emits `[DEGRADED]` if both transports fail.
RECOMMENDED: resolve-moot — the proposed transport swap and fail-loud behavior shipped.

## Steward proposal — grinder-orchestration tooling + a cross-project worktree infra fix
- ref: `/Users/alien/.claude/steward-proposals/2026-06-16-anim-workbench-grinder-orchestration-tooling.md` · created 2026-06-16 (78d)
- scout: ok=True wall=118s tok(in/out/reason)=511645/3502/1644

VERDICT: MOOT
EVIDENCE: 9e0bc35 implemented `scripts/merge-grinder.ts`; 21563e5 implemented `src/workbench/localize.ts:296`.
EVIDENCE: 648de68 implemented the glob dispatcher at `scripts/verify-scene.ts:18`; 1fa61e9 later added the worktree-isolated grind loop.
RECOMMENDED: resolve-moot — the concrete workflow and product gaps were implemented and remain present.

## session-private Session-ID commit stamping
- ref: `/Users/alien/.claude/steward-proposals/2026-06-16-session-id-private-stamp.md` · created 2026-06-16 (78d)
- scout: ok=True wall=114s tok(in/out/reason)=482059/2672/1002

VERDICT: MOOT
EVIDENCE: `skills/hooks/prepare-commit-msg-session-id.sh:15-33` prefers process-private `CLAUDE_SESSION_ID`/`CODEX_THREAD_ID`, using shared files only as fallback.
`f7e7a96` added Codex support and regression tests proving the private ID beats a peer-overwritten shared file.
`agent-infra/.git/hooks/prepare-commit-msg` currently symlinks to that implementation.
RECOMMENDED: resolve-moot — the proposed race-safe stamping is implemented and active.

## Steward proposal — agent self-tooling friction (session b38baad8, 2026-06-17)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-17-agent-tooling-friction-b38baad8.md` · created 2026-06-17 (77d)
- scout: ok=True wall=167s tok(in/out/reason)=704161/4360/967

VERDICT: MOOT
EVIDENCE: dc4434f; `skills/critique/scripts/model-review.py:1447-1465` expands preset aliases, including mixed forms.
EVIDENCE: bf6731f54; `genomics/justfile:174-177` adds read-only `commit-mine-check`.
EVIDENCE: 6f4d02a; `agent-infra/scripts/refresh_codebase_map_on_commit.py:36-42` catches failed staged reads and emits one-line diagnostics.
RECOMMENDED: resolve-moot — all three proposed fixes are implemented.

## eval_run_packager — reproducible eval-run wrapper
- ref: `/Users/alien/.claude/steward-proposals/2026-06-17-eval-run-packager.md` · created 2026-06-17 (77d)
- scout: ok=True wall=65s tok(in/out/reason)=161180/849/349

VERDICT: MOOT
EVIDENCE: e218860 implemented the proposed wrapper; aa25023 generalized it into `evalcore.run_manifest`.
EVIDENCE: evalcore/run_manifest.py:180-288 records hashes/provenance/scorer/trials and fail-closes on non-production inputs and single-trial superiority.
RECOMMENDED: resolve-moot — the requested capability exists and remains wired through the genomics-specific wrapper.

## substrate capability map — eradicate the substrate blind spot
- ref: `/Users/alien/.claude/steward-proposals/2026-06-17-substrate-capability-map.md` · created 2026-06-17 (77d)
- scout: ok=True wall=131s tok(in/out/reason)=365646/1871/664

VERDICT: MOOT
EVIDENCE: f61c9b6 removed claimcore after its kill-switch found no capability edge; c5f7b4a parked substrate.
EVIDENCE: substrate/README.md:3-6 says it is dormant, has no product consumers, and live behavior was rehomed.
EVIDENCE: config/codebase-map-repos.json:2-31 no longer maps the deleted phenome repository.
RECOMMENDED: resolve-moot — the consumer and capability surface that created the blind spot no longer exist.

## Steward proposal — kill the qualifier-drop class structurally (compute-don't-copy + lint)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-19-compute-dont-copy-admission.md` · created 2026-06-19 (75d)
- scout: ok=True wall=138s tok(in/out/reason)=309581/1545/423

VERDICT: SUPERSEDED
EVIDENCE: be5d4759b / decisions/2026-07-01-finding-layer-overcall-evidence-class.md:61-88 explicitly rejects a central confidence ceiling and selects adapter-time classification; scripts/finding_policy.py:62-78 remains intentionally generic.
RECOMMENDED: resolve-superseded — the accepted architecture replaced compute-don’t-copy with producer-boundary evidence-class minting.

## Steward proposal — Measurement fan-out discipline (generate/measure split + no-nohup + ephemeral recordings + disk-precheck)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-19-measurement-fanout-discipline.md` · created 2026-06-19 (75d)
- scout: ok=True wall=194s tok(in/out/reason)=703850/3268/1200

VERDICT: SUPERSEDED
EVIDENCE: b59dc68 + skills/hooks/pretool-bash-background-ampersand.py:7-15 replace the blanket nohup ban with tracked-job/watcher guards.
EVIDENCE: arc-agi/.claude/rules/teammate-dispatch-protocol.md:84-86 explicitly standardizes nohup with logs/status files.
EVIDENCE: e7848339 + arc-agi/.claude/rules/storage-layout.md:9-22 retain traces durably but compress 283 GiB to ~10 GiB.
RECOMMENDED: resolve-superseded — newer job-liveness guards and compressed durable trace storage replace the proposed bundle.

## Proposal: make claimcore identity CONTENT-ADDRESSED (absorb genomics' SourcePaperBundle)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-claim-context-ref-corpus-grounding.md` · created 2026-06-20 (74d)
- scout: ok=True wall=137s tok(in/out/reason)=401761/2214/829

VERDICT: SUPERSEDED
EVIDENCE: 2103a03 and 81ed80d implemented content-addressed `artifact_id`, retired path-keyed `document_id`, and made `context_ref` a locator.
EVIDENCE: f61c9b6 then removed claimcore entirely after its kill-switch found no capability edge; `substrate/pyproject.toml:4-14` confirms the retired stack.
RECOMMENDED: resolve-superseded — the proposed fix shipped, then its entire target architecture was retired.

## Steward proposal — `kg_clean_room_build`: separate ingest from gate/finalize
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-clean-room-finalize-only.md` · created 2026-06-20 (74d)
- scout: ok=True wall=126s tok(in/out/reason)=290220/1366/459

VERDICT: MOOT
EVIDENCE: db5718a3 implemented `finalize_release()` and `--finalize-only` in `scripts/tools/kg_clean_room_build.py`.
EVIDENCE: 70b9efaf later deleted that script with the retired KG subsystem; the target no longer exists.
RECOMMENDED: resolve-moot — implemented before the subsystem itself was retired.

## Fix the overcall class with ONE shared clinical-assertion evidence gate — not 6 per-stage patches
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-clinical-assertion-evidence-gate.md` · created 2026-06-20 (74d)
- scout: ok=True wall=160s tok(in/out/reason)=780536/3285/1129

VERDICT: SUPERSEDED
EVIDENCE: 345f16873 centralized clinical admission in `scripts/finding_policy.py:54-133`; `scripts/generate_clinician_summary.py:96-128` now default-denies unadmitted assertions.
EVIDENCE: 6ad7fd26c demoted AnnotSV vendor classifications to candidate-only (`scripts/annotsv_scope.py:14-27`).
RECOMMENDED: resolve-superseded — typed assertion admission plus sink enforcement replaced the proposed API.

## Steward proposal — deletion-guard should verify attribution, not assert "peer"
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-deletion-guard-attribution-verify-first.md` · created 2026-06-20 (74d)
- scout: ok=True wall=97s tok(in/out/reason)=224965/1239/401

VERDICT: MOOT
EVIDENCE: d5b13f7 implemented Option A; hooks/stop-mass-deletion-guard.py:58-63 now says “ORIGIN UNKNOWN” and requires attribution checks.
EVIDENCE: ~/.claude/settings.json:374-384 shows the revised guard remains globally wired.
RECOMMENDED: resolve-moot — the proposed wording fix is live.

## GPU-class drift — derive heavy/GPU gating from `@app.function(gpu=)`, not `ResourceClass`
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-gpu-class-drift-lint.md` · created 2026-06-20 (74d)
- scout: ok=True wall=106s tok(in/out/reason)=374570/2357/1070

VERDICT: STILL-VALID
EVIDENCE: scripts/modal_esm_lfb.py:572-579 still declares an L4 GPU, while scripts/pipeline_stages.py:4802-4820 leaves `esm_lfb` at default CPU with no duration estimate.
EVIDENCE: 271cffc63 centralized heavy gating, but scripts/pipeline_stages.py:3620-3635 still trusts `ResourceClass.GPU`; justfile:276-290 has no GPU-class drift lint.
RECOMMENDED: keep — four original mismatches were reconciled or migrated, but `esm_lfb` remains silently misclassified and the drift class is unenforced.

## Steward proposal — hutter handoff consolidation (one canonical bounded live-handoff)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-handoff-consolidation.md` · created 2026-06-20 (74d)
- scout: ok=True wall=88s tok(in/out/reason)=150996/1012/394

VERDICT: MOOT
EVIDENCE: hutter commit 5a1f914 replaced the 3,723-line checkpoint with bounded live state; `.claude/checkpoint.md:1-6` remains canonical and git-backed.
EVIDENCE: `DREAMER-BOOT.md:7-10,22-23` directs boots to that single live-state file; `.claude/legal-stall-ack:1-2` is suppression metadata only.
RECOMMENDED: resolve-moot — the proposed consolidation is implemented and remains current.

## eval loops must ratchet on HELD-OUT, never in-sample (proxy-as-truth → overfitting)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-holdout-not-insample-eval-metric.md` · created 2026-06-20 (74d)
- scout: ok=True wall=118s tok(in/out/reason)=537380/2078/653

VERDICT: MOOT
EVIDENCE: 7d9fcff9 added the held-out-only ratchet, explicit in-sample split, and per-game-fit flag.
EVIDENCE: e9f2e123 wired the unseen 262-game corpus; `agent/holdout_eval.py:68-108,700-728` makes held-out TIER-H1 the headline.
EVIDENCE: `GOAL.md:19-26,153-164` now forbids in-sample gate-passes and requires LOFO held-out evaluation.
RECOMMENDED: resolve-moot — the proposed guard is implemented and subsequently hardened.

## QC must not attest a stale mirror — gate "mirror == volume" as a checked precondition
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-qc-mirror-freshness-gate.md` · created 2026-06-20 (74d)
- scout: ok=True wall=80s tok(in/out/reason)=233694/1407/511

VERDICT: SUPERSEDED
EVIDENCE: c7e584888 and ef96fca0d implemented resilient sync and the mirror-currency gate on 2026-06-21.
EVIDENCE: 35a27b5cd and 14e072b86 later replaced ambient-mirror QC with exact principal receipt packets.
EVIDENCE: genomics/scripts/mirror_currency.py:75 and attestation_packet.py:434 enforce certified equality, exact receipt bytes, and fail-closed packet construction.
RECOMMENDED: resolve-superseded — the original gap is closed by a stronger receipt-bound design.

## Steward proposal — Stop-hook attribution by writer-provenance (consolidates 5 peer proposals + closes the automation gap)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-stop-hook-writer-provenance-attribution.md` · created 2026-06-20 (74d)
- scout: ok=True wall=85s tok(in/out/reason)=225561/1567/299

VERDICT: MOOT
EVIDENCE: skills@f5bf0ad; hooks/stop-uncommitted-warn.sh:260 reads the automation ledger and excludes its paths from session attribution.
EVIDENCE: agent-infra@ae529d5; scripts/common/automation_ledger.py:29 and scripts/fm.py:51 implement writer registration; the live ledger exists.
RECOMMENDED: resolve-moot — the proposed provenance mechanism is fully implemented.

## Orchestrator run-state reads → volume `read_file(current.json)`, never mirror-listdir
- ref: `/Users/alien/.claude/steward-proposals/2026-06-20-volume-readfile-not-mirror-listdir.md` · created 2026-06-20 (74d)
- scout: ok=True wall=118s tok(in/out/reason)=332006/1757/768

VERDICT: SUPERSEDED
EVIDENCE: 603d1f3ac deleted the ledger volume crawl and made PG realization-index discovery mandatory for Modal.
EVIDENCE: genomics/scripts/orchestrator/operator_views.py:2030-2046 confirms production discovery uses `pg_realization_index`, with no volume `listdir`.
RECOMMENDED: resolve-superseded — the newer PG-index architecture eliminates the targeted crawl entirely.

## make the phenome test suite always-terminating
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-phenome-pytest-timeout.md` · created 2026-06-21 (73d)
- scout: ok=True wall=99s tok(in/out/reason)=252117/1509/443

VERDICT: MOOT
EVIDENCE: `/Users/alien/Projects/phenome` is absent today; genomics commit `01b9438ea` explicitly retired cross-repo bridges because “repo is gone.”
EVIDENCE: `genomics/.claude/rules/code-pitfalls.md:74` records the 2026-07-18 Phenome consumer-path retirement.
RECOMMENDED: resolve-moot — the targeted repository and test suite no longer exist

## gate on pytest collection errors
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-pytest-collection-error-gate.md` · created 2026-06-21 (73d)
- scout: ok=True wall=103s tok(in/out/reason)=213872/918/217

VERDICT: MOOT
EVIDENCE: f2ef0ef01 implemented the proposal on 2026-07-06.
EVIDENCE: genomics/justfile:1230 wires `pytest-collect-gate` into `validate-code`; lines 1280-1287 run collection and block on errors.
EVIDENCE: genomics/tests/test_validate_code_report_all.py:12 verifies the gate remains included.
RECOMMENDED: resolve-moot — the requested gate is implemented and still wired.

## researcher Stop-gate for the *pathological-empty* case only
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-researcher-pathological-empty-stop-gate.md` · created 2026-06-21 (73d)
- scout: ok=True wall=101s tok(in/out/reason)=231203/1514/591

VERDICT: STILL-VALID
EVIDENCE: `da792bc` implemented only a shadow detector; `hooks/subagent-source-check-stop.sh:12-15` explicitly never blocks.
`hooks/subagent-empty-research-shadow.py:106-122` logs would-fire cases only; the live log contains 5 pathological-empty firings across 2 sessions.
RECOMMENDED: keep — the failure still occurs and the proposed Stop gate has not been promoted.

## Steward proposal — warn on `rg -r` typo'd-as-recursive
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-rg-replace-flag-guard.md` · created 2026-06-21 (73d)
- scout: ok=True wall=88s tok(in/out/reason)=224701/1870/694

VERDICT: STILL-VALID
EVIDENCE: ~/.claude/settings.json:84-92 routes Bash checks solely through the shared dispatcher.
EVIDENCE: skills/hooks/pretool-bash-dispatch.py:57-99 enumerates its gates; no `rg -r` guard exists (03baad9).
EVIDENCE: Current probe: dispatcher gave no warning; `printf 'xneedle\n' | rg -rn needle` produced `xn`.
RECOMMENDED: keep — the typo remains silently destructive and unguarded.

## Surface stranded worktree-agent branches — currency-check before work rots
- ref: `/Users/alien/.claude/steward-proposals/2026-06-21-worktree-hygiene-surfacing.md` · created 2026-06-21 (73d)
- scout: ok=True wall=77s tok(in/out/reason)=188117/1088/439

VERDICT: MOOT
EVIDENCE: b7314f2 implemented age and `git cherry` duplicate detection in `scripts/worktree_gc.py:505`.
6c48e3b wired proactive `--check` surfacing into `scripts/pulse_tick.py:62`; current LAND/INSPECT/REAP output remains at `scripts/worktree_gc.py:746`.
RECOMMENDED: resolve-moot — the proposed currency check and proactive surfacing are implemented and still active.

## audit consolidation must re-check findings vs HEAD + dedup
- ref: `/Users/alien/.claude/steward-proposals/2026-06-22-audit-head-recheck-dedup.md` · created 2026-06-22 (72d)
- scout: ok=True wall=90s tok(in/out/reason)=327855/1702/636

VERDICT: SUPERSEDED
EVIDENCE: df7a369 implemented deterministic HEAD re-check; 2150d18 later retired `audit_findings_consolidation.py` and its tests with the file-bus pipeline.
EVIDENCE: scripts/debug_until_dry.py:70 and :354 retain claim-hash dedup; :312 and :550 independently re-check current code through the active verifier lane.
RECOMMENDED: resolve-superseded — the criticized consolidator no longer exists and its live replacement covers dedup plus current-tree adjudication.

## Watch — global auto-back-stamp misfire monitor (measure-while-deployed)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-22-backstamp-misfire-watch.md` · created 2026-06-22 (72d)
- scout: ok=True wall=115s tok(in/out/reason)=317013/1885/707

VERDICT: STILL-VALID
EVIDENCE: skills/hooks/posttool-decision-backstamp.sh:41-53 still accepts loose prose headers; :72 marks the entire target “NOT a current direction.”
EVIDENCE: substrate/docs/decisions/0022-phenome-is-a-data-dir-mechanism-re-homes-by-telos.md:5 supersedes ADR 0011 only “for phenome,” but 0011:126 was globally auto-stamped.
RECOMMENDED: keep — a concrete false-positive confirms the trigger still needs narrowing.

## surface the own_code reachability triage IN sample_remediation
- ref: `/Users/alien/.claude/steward-proposals/2026-06-22-reachability-into-remediation.md` · created 2026-06-22 (72d)
- scout: ok=True wall=107s tok(in/out/reason)=359579/1535/368

VERDICT: SUPERSEDED
EVIDENCE: ea4a61b57 originally implemented the advisory and recipe.
EVIDENCE: 97d5822d1 deleted `scripts/owncode_cosmetic_classify.py`; 809f50ccc removed `own_code_coverage`.
EVIDENCE: `scripts/orchestrator/sample_remediation.py:559` now permits reruns only from exact `RECOMPUTE_REQUIRED` decisions.
RECOMMENDED: resolve-superseded — exact semantic currency authority replaced reachability triage.

## Pre-dispatch reference-data integrity gate (genomics)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-23-reference-data-integrity-gate.md` · created 2026-06-23 (71d)
- scout: ok=True wall=174s tok(in/out/reason)=1144707/3507/1146

VERDICT: SUPERSEDED
EVIDENCE: 037ba35f3/d69e68951/f2c6badab implemented the no-swallow/curl/extraction lint; `justfile:1011,1230` gates it in `validate-code`.
EVIDENCE: 63d0538df and 938ad5733 replaced ambient refs with exact external-input binding and immutable sealing.
EVIDENCE: `kernel_exact_target.py:645-695` refuses dispatch when binding fails; `kernel_input_binding.py:791-820` verifies source integrity.
RECOMMENDED: resolve-superseded — the kernel’s exact-input gate now covers the proposal’s pre-dispatch integrity requirement.

## adaptive concurrency for the full-DAG ledger crawl
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-adaptive-ledger-parallelism.md` · created 2026-06-24 (70d)
- scout: ok=True wall=81s tok(in/out/reason)=203951/1302/536

VERDICT: SUPERSEDED
EVIDENCE: 603d1f3ac deleted the full-DAG volume-listdir crawl and made PostgreSQL realization-index discovery mandatory.
EVIDENCE: scripts/orchestrator/operator_views.py:1980-1985 shows concurrency now overlaps VolumeGetFile reads, not the deleted crawl.
EVIDENCE: scripts/orchestrator/operator_views.py:2030-2046 confirms Modal discovery uses the PG index with no VolumeListFiles crawl.
RECOMMENDED: resolve-superseded — the rate-limited operation adaptive concurrency targeted no longer exists.

## Decouple attestation plausibility from code-closure freshness (output-content binding)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-attestation-output-content-binding.md` · created 2026-06-24 (70d)
- scout: ok=True wall=93s tok(in/out/reason)=238309/1890/897

VERDICT: MOOT
EVIDENCE: d8fe4a9da introduced content-addressed packet binding; f6943532a completed the migration. `scripts/attest_sample.py:80` now compares packet hashes only, explicitly excluding code freshness; `tests/test_attest_verdict_status.py:46` locks that separation.
RECOMMENDED: resolve-moot — the proposed decoupling is implemented and regression-tested

## Lens/generator banks: track APPLICATION, not growth
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-lens-bank-application-tracking.md` · created 2026-06-24 (70d)
- scout: ok=True wall=131s tok(in/out/reason)=288758/1789/606

VERDICT: STILL-VALID
EVIDENCE: `build_lifetime_evidence_warehouse.py:320-353,492-497` still creates `lifetime_generators` without application/lifecycle fields.
EVIDENCE: `immigration-lifetime-fiscal-generators.md:6` still reports 124 MD headings vs 122 DB rows; `9ddf700` added eight more lenses without tracking.
RECOMMENDED: keep — both application tracking and generated-view reconciliation remain unimplemented.

## red-team a CONSEQUENTIAL foreclosure BEFORE it drives action (global epistemic discipline)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-redteam-before-foreclosure.md` · created 2026-06-24 (70d)
- scout: ok=True wall=77s tok(in/out/reason)=190307/1511/619

VERDICT: STILL-VALID
EVIDENCE: ~/.claude/CLAUDE.md:80 requires generic review only for consequential plans; it does not require a refutation-oriented red-team before foreclosure.
EVIDENCE: ~/.claude/rules/plan-review-gate.md:19-25 excludes pure research and many single-repo decisions; post-2026-06-24 history contains no foreclosure-specific rule.
RECOMMENDED: keep — the concrete consequential-foreclosure safeguard remains uncovered.

## Steward proposal — promote the mining-ingest to a tested, fail-loud repo tool
- ref: `/Users/alien/.claude/steward-proposals/2026-06-24-verified-failloud-ingest-tool.md` · created 2026-06-24 (70d)
- scout: ok=True wall=114s tok(in/out/reason)=411327/1940/472

VERDICT: SUPERSEDED
EVIDENCE: 6c83492 implemented the tested, chunked, `claim_events`-verified ingest CLI and retired scratch scripts.
EVIDENCE: f61c9b6 deleted `corpus-extract`; substrate/CLAUDE.md:20-27 records the claim-KG kill-switch and retirement.
RECOMMENDED: resolve-superseded — the requested tool landed, then its entire capability stack was deliberately retired.

## generalize own-code attribution into the completion-authority kernel
- ref: `/Users/alien/.claude/steward-proposals/2026-06-25-owncode-attribution-to-completion-kernel.md` · created 2026-06-25 (69d)
- scout: ok=True wall=177s tok(in/out/reason)=764136/2996/767

VERDICT: SUPERSEDED
EVIDENCE: 809f50ccc deleted hash freshness, `own_code_drift`, and the proposed `staleness_ledger.py`/`owncode_cosmetic_classify.py` authority.
EVIDENCE: scripts/orchestrator/sample_remediation.py:190-196 now makes exact-pair `StageCurrencyDecision` authoritative and explicitly excludes own-code classification.
EVIDENCE: tests/test_rerun_authority_legacy_deletion.py:16-31,92-105 enforces deletion of every competing own-code/staleness authority.
RECOMMENDED: resolve-superseded — the exact-pair semantic-currency cutover replaced the proposed attribution generalization.

## auto-checkpoint [wip]-churn on shared main + worktree-isolation silent no-op
- ref: `/Users/alien/.claude/steward-proposals/2026-06-25-wip-churn-worktree-noop.md` · created 2026-06-25 (69d)
- scout: ok=True wall=100s tok(in/out/reason)=394467/2028/770

VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/stop-uncommitted-warn.sh:405-470` still creates ungated `[wip]` commits directly on the current branch.
EVIDENCE: `c13fb48` and `8c1e331` prevent peer-index sweeps and defer active subagent files, but do not remove main-history churn.
RECOMMENDED: keep — the worktree failure is superseded, but the core auto-checkpoint behavior remains.

## Steward proposal — `sample-remediation` payload-blind verdict misleads (phantom-cascade trap)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-26-sample-remediation-payload-blind-phantom.md` · created 2026-06-26 (68d)
- scout: ok=True wall=113s tok(in/out/reason)=320270/1658/637

VERDICT: SUPERSEDED
EVIDENCE: c6f37718c migrated remediation to canonical stage-currency authority; scripts/orchestrator/sample_remediation.py:171-184 allows rerun only for explicit `RECOMPUTE_REQUIRED`.
EVIDENCE: 17f1d2e0d added typed authority/legal-next output; sample_remediation.py:291-316 routes uncertifiable payloads to audit and refuses completion claims.
EVIDENCE: ac9cdeaf5 retired `--mirror-root`/ambient mirror reads; control-plane evidence is now authoritative.
RECOMMENDED: resolve-superseded — later authority and control-plane refactors eliminate payload absence as rerun authority.

## Steward proposal — suspect-empty detector: make silent extraction failures visible
- ref: `/Users/alien/.claude/steward-proposals/2026-06-26-suspect-empty-extraction-detector.md` · created 2026-06-26 (68d)
- scout: ok=True wall=111s tok(in/out/reason)=351180/1863/696

VERDICT: MOOT
EVIDENCE: bea7af8 + 2958530 implemented detection and bounded healing; f61c9b6 later deleted `packages/corpus-extract` because it had zero live consumers and no capability edge.
EVIDENCE: substrate/pyproject.toml:4-8 and docs/CANONICAL.md:23-28 confirm the claim-KG/extraction stack remains retired.
RECOMMENDED: resolve-moot — the detector’s entire target pipeline no longer exists.

## Steward proposal — value-kind ingest gate (REFRAMED: the mechanism exists; root cause was a kind-resolution bug)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-26-value-kind-ingest-gate.md` · created 2026-06-26 (68d)
- scout: ok=True wall=147s tok(in/out/reason)=325430/2208/974

VERDICT: SUPERSEDED
EVIDENCE: 2c60db6 implemented the reviewed, narrower gate via `SCAFFOLD_PREFIXES` + `classify_scaffold`, explicitly rejecting broad kind demotion.
f61c9b6 then deleted `claimcore` and `corpus-extract`; `substrate/docs/CANONICAL.md:23` records the entire claim-KG stack as retired.
RECOMMENDED: resolve-superseded — the safe mechanism landed, then its target architecture was removed

## Steward proposal — deterministic `ADMISSION_OVERCALL` flag (enforce the orthogonal-modality rule the classifier already violates)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-admission-overcall-flag.md` · created 2026-06-27 (67d)
- scout: ok=True wall=171s tok(in/out/reason)=479245/2523/1292

VERDICT: MOOT
EVIDENCE: 1f33e5217 implemented the exact proposal in `scripts/variant_review_rules.py:559` and wired the flag into packets at `scripts/generate_review_packets.py:3419`.
EVIDENCE: `tests/test_admission_overcall.py:29` preserves the PGK1 V81F canary; 36b62ca84 also caps single-family P/LP labels directly.
RECOMMENDED: resolve-moot — the deterministic flag shipped and remains wired, with stronger classifier-level prevention too.

## Steward proposal — `commit-mine` silently drops `git rm` deletions on retry
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-commit-mine-drops-git-rm-deletions.md` · created 2026-06-27 (67d)
- scout: ok=True wall=343s tok(in/out/reason)=482037/2294/634

VERDICT: MOOT
EVIDENCE: 1d00ad670 (2026-07-06) implemented `git rm`/`git mv` tracking; `.claude/settings.json:227-233` wires the hook.
EVIDENCE: `scripts/session_commit.sh:205-240,270-275` handles deleted paths and unstages only the invocation’s explicit pathspec; `tests/test_track_git_removals.py:61-124` covers retry and peer isolation.
RECOMMENDED: resolve-moot — the proposed fix is implemented and tested.

## Donor-export GCS auth — kill the recurring stale-token failure class
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-donor-export-auth.md` · created 2026-06-27 (67d)
- scout: ok=True wall=151s tok(in/out/reason)=283144/1479/561

VERDICT: STILL-VALID
EVIDENCE: genomics/scripts/modal_donor_export.py:390-398 and :911-918 still build GCS clients from non-refreshable `Credentials(token=GCS_ACCESS_TOKEN)`.
EVIDENCE: genomics/justfile:2758-2767 exposes both GCS export recipes but neither refreshes `gcs-push-token`; commits 1a6ac071f/a29027728 retained this auth path.
RECOMMENDED: keep — the active GCS sinks still retain the stale-token failure class.

## Steward proposal — standing bio-verify gate for the per-sample HPO rail
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-form-hpo-verify-gate.md` · created 2026-06-27 (67d)
- scout: ok=True wall=175s tok(in/out/reason)=381804/2450/1043

VERDICT: STILL-VALID
EVIDENCE: 9fe862e4f added `just hpo-profile-check`, but `scripts/form_to_hpo.py:364-384` calls only identity/schema validation; ontology/name verification at lines 310-330 remains uncalled.
EVIDENCE: `docs/ops/sample-onboarding-runbook.md:49-115` still omits HPO curation and verification.
RECOMMENDED: keep — the standing gate still does not catch unknown IDs or name drift.

## Steward proposal (#g) — session-end auto-checkpoint + reset --hard wipes peer-owned uncommitted work on a shared checkout
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-shared-checkout-reset-wipes-peer-work.md` · created 2026-06-27 (67d)
- scout: ok=True wall=157s tok(in/out/reason)=353482/2854/1221

VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/stop-uncommitted-warn.sh:62-65,132-156` now excludes peer-owned/contested files from auto-checkpoints.
`skills/hooks/pretool-destructive-git-ref.sh:19-40` only snapshots and warns; it neither checks peer ownership nor blocks `reset --hard`.
Genomics reflog still records `reset: moving to HEAD` on 2026-08-21 and auto-checkpoints through 2026-08-30.
RECOMMENDED: keep — the checkpoint attribution is hardened, but the requested fail-closed reset guard remains unimplemented.

## Steward proposal — stage liveness via the EXISTING worker_state Dict
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-stage-liveness-worker-state.md` · created 2026-06-27 (67d)
- scout: ok=True wall=97s tok(in/out/reason)=346054/2026/649

VERDICT: SUPERSEDED
EVIDENCE: `3fe91f25c` shipped `just stage-progress`; `scripts/ops/worker_state.py:24-122` now reads `worker_state` with heartbeat ages.
EVIDENCE: `cb4e29551` added the long-stage progress ratchet; `1cc7bbf19` added automatic progress-stall detection.
EVIDENCE: `48bb1a402` retired the proposed `modal-triage` MCP path in favor of fresh subprocess tools.
RECOMMENDED: resolve-superseded — the reader, lint, and automated stall watchdog now exist on the replacement control plane.

## stop-gate should detect + report an UNSTARTED goal, not just "condition unmet"
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-unstarted-goal-detection.md` · created 2026-06-27 (67d)
- scout: ok=True wall=103s tok(in/out/reason)=263012/1327/480

VERDICT: MOOT
EVIDENCE: 3a2fd5b implemented the proposed one-time `GOAL UNSTARTED` warning for zero progress.
EVIDENCE: skills/hooks/stop-goal-wrapup.py:277 and test_goal_night_controller.py:146 implement/test it; ~/.claude/settings.json:403 deploys the hook globally.
RECOMMENDED: resolve-moot — the exact proposal shipped and remains active.

## Steward proposal — `just watch-drain <sample>`: volume-free PG-frontier monitor (eradicate the iatrogenic crawl)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-27-watch-drain-volume-free-monitor.md` · created 2026-06-27 (67d)
- scout: ok=True wall=68s tok(in/out/reason)=164146/1042/355

VERDICT: MOOT
EVIDENCE: 8fa83b09b implemented `scripts/watch_drain.py` and `just watch-drain` as the PG monitor.
EVIDENCE: `genomics/justfile:2454-2460` and `CLAUDE.md:58` make it the default active-drive check without `VolumeListFiles`.
RECOMMENDED: resolve-moot — the proposed tool and routing safeguards are implemented.

## Steward proposal — PreToolUse guard: full-DAG volume crawl while sample has live Modal apps (F16)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-28-f16-midwrite-volume-crawl-guard.md` · created 2026-06-28 (66d)
- scout: ok=True wall=101s tok(in/out/reason)=290317/1850/432

VERDICT: MOOT
EVIDENCE: ceafeb7 implemented the F16 guard; c8e8e48bc wired it into genomics PreToolUse.
EVIDENCE: skills/hooks/pretool_f16_midwrite_crawl_guard.py:42 detects broad crawls and :116-150 blocks when canonical stage writers are live.
EVIDENCE: 095b899 narrowed it after genomics 603d1f3ac replaced remediation’s crawl with the PG index.
RECOMMENDED: resolve-moot — the proposed guard is implemented, active, tested, and subsequently calibrated.

## Steward proposal — de-identification pre-commit gate (fail-closed, name-scoped)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-29-deid-precommit-hook.md` · created 2026-06-29 (65d)
- scout: ok=True wall=77s tok(in/out/reason)=148785/1297/590

VERDICT: MOOT
EVIDENCE: 4f37338 implemented `skills/hooks/pre-commit-deid-guard.sh`; current lines 51-76 scan staged scoped files and block identifier hits.
EVIDENCE: 95d10d7 added `substrate/.deid-guard.env`; its live pre-commit symlink still targets the dispatcher, which invokes the guard at `pre-commit-guards.sh:40-46`.
RECOMMENDED: resolve-moot — the proposed name-scoped commit gate is implemented and wired.

## mechanical transport pre-flight in evalcore.run
- ref: `/Users/alien/.claude/steward-proposals/2026-06-29-evalcore-transport-preflight.md` · created 2026-06-29 (65d)
- scout: ok=True wall=104s tok(in/out/reason)=282678/2084/701

VERDICT: STILL-VALID
EVIDENCE: 4ab4bde moved evalcore authority to `evals/evalcore`; `evals/evalcore/run.py:223-261` still detects transport errors only inside the full candidate×case loop and never preflights or aborts a dead arm.
RECOMMENDED: keep — the mis-scoring guard exists, but the proposed fail-fast transport preflight does not.

## Steward proposal — harden qc_fanout against the two failure modes seen on syn3sr (2026-06-29)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-29-qc-fanout-hardening.md` · created 2026-06-29 (65d)
- scout: ok=True wall=91s tok(in/out/reason)=267869/1445/552

VERDICT: MOOT
EVIDENCE: 6eb49392e implemented both fixes; `scripts/qc_fanout.py:251-262` retains tissue/modality lookup and the primary-source bio-claim guard.
EVIDENCE: `scripts/qc_fanout.py:703-709,583-588` retains staggered Cursor launches and fails campaigns lacking successful terminal receipts.
RECOMMENDED: resolve-moot — the named failure modes are already hardened.

## Steward proposal — Edge-infra needs the tooled-agent kill-switch eval BEFORE building, not after
- ref: `/Users/alien/.claude/steward-proposals/2026-06-30-edge-infra-killswitch-pre-build-gate.md` · created 2026-06-30 (64d)
- scout: ok=True wall=68s tok(in/out/reason)=141624/792/327

VERDICT: MOOT
EVIDENCE: a153565 implemented the proposal directly in global `~/.claude/CLAUDE.md`.
EVIDENCE: `~/.claude/CLAUDE.md:23` still requires a pre-build tooled-agent kill-switch eval for edge/moat infra.
RECOMMENDED: resolve-moot — the proposed gate is already live.

## eradicate the stale-mock test class (genomics)
- ref: `/Users/alien/.claude/steward-proposals/2026-06-30-stale-mock-test-class.md` · created 2026-06-30 (64d)
- scout: ok=True wall=124s tok(in/out/reason)=602344/2817/836

VERDICT: MOOT
EVIDENCE: ceb9938f6 updated the named audit/base-image stale mocks to current contracts.
EVIDENCE: 7521ca5dd closed the broader stale-test program; docs/ops/2026-08-18-stale-test-remediation-handoff.md:121 records all remaining reds as deferred or intentional.
RECOMMENDED: resolve-moot — the proposed remediation was implemented and closed.

## Steward proposal (CORRECTED 2026-07-01): closure-drive auto-reconcile — core ALREADY SOLVED
- ref: `/Users/alien/.claude/steward-proposals/2026-07-01-closure-drive-auto-reconcile.md` · created 2026-07-01 (63d)
- scout: ok=True wall=118s tok(in/out/reason)=403735/2277/590

VERDICT: SUPERSEDED
EVIDENCE: 2f1544975 implemented the wave-parallel auto-reconciling driver; 568090ab3 fixed host-side reload warning spam.
5ff6f4289 then deleted that driver, and dca21c7bd replaced it with exact-target execution.
Current sole launch surface is `just drive <sample> <target>` (`genomics/justfile:2094-2101`); retired-driver absence is enforced at `scripts/lint_architecture.py:162-172`.
RECOMMENDED: resolve-superseded — the proposed closure driver was implemented, then intentionally replaced by the exact-target kernel authority.

## Steward proposal — make sample "done" a machine state (kills the overclaim class + enables autonomy)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-01-machine-state-done-autonomy.md` · created 2026-07-01 (63d)
- scout: ok=True wall=119s tok(in/out/reason)=449804/2233/653

VERDICT: SUPERSEDED
EVIDENCE: bd509b3aa implemented the full remediation-action driver; dca21c7bd later deleted that legacy driver during the exact-kernel cutover.
EVIDENCE: genomics/justfile:2094-2101 now exposes only exact-target `drive`; broad remediation is no longer the executor.
EVIDENCE: genomics/.claude/rules/code-pitfalls.md:39-40 and scripts/sample_trust_tier.py:71-90 machine-enforce full-DAG, certifiable, tier-2 completion.
RECOMMENDED: resolve-superseded — the overclaim class is now guarded by the replacement authority architecture.

## Steward proposal — batch-divergence-refresh orchestrator
- ref: `/Users/alien/.claude/steward-proposals/2026-07-02-batch-divergence-refresh.md` · created 2026-07-02 (62d)
- scout: ok=True wall=91s tok(in/out/reason)=241185/1724/769

VERDICT: SUPERSEDED
EVIDENCE: 7521bdaf implements `tools/gen_divup_brief.py`, machine-feeding per-name refresh briefs into generic Codex lanes.
EVIDENCE: `docs/workflows/divergence_refresh.md:24-45` records six concurrent lanes without rate limits and identifies parent cosign/landing—not dispatch—as today’s bottleneck.
RECOMMENDED: resolve-superseded — the proposed ≤4-worker bespoke orchestrator reflects an obsolete bottleneck and concurrency limit.

## unblock phantom-free many-stage rerun (genomics) — 2 verified deep fixes
- ref: `/Users/alien/.claude/steward-proposals/2026-07-02-ledger-closure-depth-and-cca-executor.md` · created 2026-07-02 (62d)
- scout: ok=True wall=101s tok(in/out/reason)=300470/1460/359

VERDICT: SUPERSEDED
EVIDENCE: 97d5822d1 deleted `staleness_ledger.py` and `code_change_attest.py`; dca21c7bd later removed `drive_sample.py`/`complete_sample.py`.
EVIDENCE: 072eb361c made the exact ledger sole authority; `scripts/stage_currency.py:2154` requires a resolved exact delta and semantic judgment for recompute.
EVIDENCE: `scripts/stage_currency.py:2591` maps exact judgments to RECOMPUTE or REUSE, replacing closure-depth/COSMETIC heuristics.
RECOMMENDED: resolve-superseded — the proposed legacy rerun stack no longer exists and exact-pair currency now governs reruns.

## `load_json_or_default` must fail loud on a PRESENT-but-corrupt file
- ref: `/Users/alien/.claude/steward-proposals/2026-07-02-load-json-fail-loud-on-corrupt.md` · created 2026-07-02 (62d)
- scout: ok=True wall=77s tok(in/out/reason)=158859/751/201

VERDICT: MOOT
EVIDENCE: 6bfd2f98c implemented the root fix and removed redundant guards.
EVIDENCE: genomics/scripts/json_io.py:100-116 now raises on present-but-corrupt JSON unless explicitly opted out.
EVIDENCE: genomics/tests/test_harness_contracts.py:284-309 covers corruption, absence, valid empty JSON, and opt-in tolerance.
RECOMMENDED: resolve-moot — the proposed fail-loud behavior and regression tests are already shipped.

## warn on AskUserQuestion during an autonomous/loop run
- ref: `/Users/alien/.claude/steward-proposals/2026-07-03-askuserquestion-autonomous-warn.md` · created 2026-07-03 (61d)
- scout: ok=True wall=86s tok(in/out/reason)=211262/1059/282

VERDICT: MOOT
EVIDENCE: 4ad1cc7 implemented the warning hook; `hooks/pretool-askuserquestion-autonomous-warn.py:40-67` detects autonomous markers and emits a non-blocking warning.
EVIDENCE: 9166800 registered it globally; `~/.claude/settings.json:198-203` wires the hook to `AskUserQuestion`.
RECOMMENDED: resolve-moot — the proposed change is implemented and active.

## progress-based stage hang-watchdog (genomics) — 2026-07-03
- ref: `/Users/alien/.claude/steward-proposals/2026-07-03-stage-hang-watchdog.md` · created 2026-07-03 (61d)
- scout: ok=True wall=125s tok(in/out/reason)=627298/2091/399

VERDICT: STILL-VALID
EVIDENCE: scripts/watch_active_apps.py:236-250 auto-stops only classified crash loops, never progress-stalled live apps.
EVIDENCE: scripts/orchestrator/controller_reconcile.py:1896-1902 repairs stale attempts only when Modal liveness is DEAD; a live, heartbeating-but-frozen stage is skipped.
EVIDENCE: dbb811997 added observer-progress stall diagnostics, but scripts/attempt_observer_status.py:47-56 only reports “stalled” and has no kill/failure actuator.
RECOMMENDED: keep — the original live-without-progress hang remains unhandled.

## prose-vs-structured-field contradiction lint (genomics catalogs)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-04-prose-structured-field-drift-lint.md` · created 2026-07-04 (60d)
- scout: ok=True wall=90s tok(in/out/reason)=216095/1110/278

VERDICT: MOOT
EVIDENCE: 907e03383 implemented the advisory lint, tests, and Just recipe on 2026-07-04.
EVIDENCE: scripts/lint_prose_structured_drift.py:231-275 scans catalogs, classifies contradictions, and exits advisory-zero.
EVIDENCE: justfile:1536-1537 exposes `prose-structured-drift-audit`; tests/test_lint_prose_structured_drift.py:84-121 covers classification and exit behavior.
RECOMMENDED: resolve-moot — the proposed lint is implemented and remains wired today

## Ungoverned science lives in catalog free-text prose (the root of "200 unchecked")
- ref: `/Users/alien/.claude/steward-proposals/2026-07-04-ungoverned-science-in-catalog-prose.md` · created 2026-07-04 (60d)
- scout: ok=True wall=103s tok(in/out/reason)=259313/1497/553

VERDICT: MOOT
EVIDENCE: 8ee8224ab implemented the advisory lint, tests, and `just ungoverned-science-audit`.
EVIDENCE: `scripts/lint_ungoverned_catalog_science.py:91` still detects the backlog; `justfile:1526` exposes it.
RECOMMENDED: resolve-moot — the proposed governance surface is implemented and maintained.

## Advisory guard: run_in_background Bash + relative script path
- ref: `/Users/alien/.claude/steward-proposals/2026-07-05-background-bash-relative-path-guard.md` · created 2026-07-05 (59d)
- scout: ok=True wall=90s tok(in/out/reason)=277412/1234/286

VERDICT: MOOT
EVIDENCE: bc6f557 implemented the exact advisory in `skills/hooks/pretool-bg-dispatch-footgun.py:51`; 03baad9 wired it through `pretool-bash-dispatch.py:2191`, globally registered at `~/.claude/settings.json:83`.
RECOMMENDED: resolve-moot — the proposed guard has been implemented and remains active.

## Guard: background `codex exec` without `< /dev/null` hangs forever
- ref: `/Users/alien/.claude/steward-proposals/2026-07-05-codex-exec-stdin-guard.md` · created 2026-07-05 (59d)
- scout: ok=True wall=100s tok(in/out/reason)=212638/1133/318

VERDICT: MOOT
EVIDENCE: bc6f557 (2026-07-06) implemented the advisory guard in hooks/pretool-bg-dispatch-footgun.py:34-47.
EVIDENCE: hooks/pretool-bash-dispatch.py:2191-2195 wires it into the active dispatcher; ~/.claude/settings.json:89 registers that dispatcher.
RECOMMENDED: resolve-moot — the proposed guard is implemented and active.

## Steward proposal — Single-source the payload-validity verdict; kill the misleading "payload-blind" count
- ref: `/Users/alien/.claude/steward-proposals/2026-07-06-single-source-payload-verdict.md` · created 2026-07-06 (58d)
- scout: ok=True wall=179s tok(in/out/reason)=433141/2380/854

VERDICT: SUPERSEDED
EVIDENCE: ac9cdeaf5 retired ambient-mirror reads from readiness; Modal receipt evidence is now authoritative.
EVIDENCE: 307d8ecd0; scripts/orchestrator/sample_readiness.py:1144 reads payload denominators directly from the ledger-selected SUCCESS receipt.
RECOMMENDED: resolve-superseded — receipt-bound payload evidence replaced the proposed mirror-audit authority.

## Proposal: UserPromptSubmit hook injects current local time
- ref: `/Users/alien/.claude/steward-proposals/2026-07-06-userprompt-clock.md` · created 2026-07-06 (58d)
- scout: ok=True wall=62s tok(in/out/reason)=160083/870/347

VERDICT: MOOT
EVIDENCE: 57d72e2 implemented `skills/hooks/userprompt-clock.sh`; lines 14–15 emit the requested local-time context. c3cfa1a registered it globally at `~/.claude/settings.json:485`.
RECOMMENDED: resolve-moot — the proposal was implemented exactly.

## Steward proposal — container build-canary + crash-loop detector (genomics)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-07-container-build-canary-and-crashloop-detector.md` · created 2026-07-07 (57d)
- scout: ok=True wall=185s tok(in/out/reason)=919075/3516/1075

VERDICT: MOOT
EVIDENCE: 8fa7be5d5 fixed all six PEP 695 hazards and added the blocking container-syntax gate (`scripts/lint_container_syntax_compat.py:1`; `justfile:86`).
EVIDENCE: 5c4c55b15 implemented the proposed crash-loop predicate and shared normalization (`scripts/orchestrator/app_health.py:57`; `scripts/watch_active_apps.py:170`).
EVIDENCE: Both remain wired today: syntax checking in `validate-code` (`justfile:1230`) and crash-loop scans exit 2 (`scripts/watch_active_apps.py:9`).
RECOMMENDED: resolve-moot — the proposal’s prevention and runtime-detection gaps are implemented.

## Goal conditions: terminal states as checkable predicates
- ref: `/Users/alien/.claude/steward-proposals/2026-07-07-goal-terminal-predicates.md` · created 2026-07-07 (57d)
- scout: ok=True wall=129s tok(in/out/reason)=494006/3524/1783

VERDICT: STILL-VALID
EVIDENCE: f1ee2b6 fixed armed-event waiting via `.claude/goal-quiet` (`hooks/stop-goal-wrapup.py:218`).
EVIDENCE: `hooks/stop-goal-wrapup.py:43` checks progress only; completion still requires manually touching `.claude/goal-done` at line 90, with no terminal-predicate evaluation.
RECOMMENDED: keep — the wakeup ambiguity is fixed, but checkable disjunctive terminal conditions remain unimplemented

## Steward proposal — auto-commit stop hook: defer ACTIVE subagent build dirs (dir-level recency)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-08-autocommit-defer-active-subagent-dirs.md` · created 2026-07-08 (56d)
- scout: ok=True wall=86s tok(in/out/reason)=204589/1712/981

VERDICT: SUPERSEDED
EVIDENCE: 8c1e331 widened deferral from 90s to 900s whenever subagent task output is active.
EVIDENCE: b05a67b; hooks/stop-uncommitted-warn.sh:218 and :497 add peer-aware 15-minute deferral and non-blocking commit-failure handling.
RECOMMENDED: resolve-superseded — later activity-aware safeguards address the measured false-positive without directory-level recency.

## Steward proposal — make the guard layer an executable corpus, not a set of independent regexes
- ref: `/Users/alien/.claude/steward-proposals/2026-07-09-executable-hook-corpus.md` · created 2026-07-09 (55d)
- scout: ok=True wall=119s tok(in/out/reason)=509167/3249/1301

VERDICT: STILL-VALID
EVIDENCE: `~/.claude/settings.json:83-90` and `genomics/.claude/settings.json:82-98` still compose separate global/project Bash guards; no corpus tests their combined verdicts.
EVIDENCE: `skills/hooks/test_bash_dispatch.py:1-8` checks dispatcher parity, while `scripts/hooks_smoke.py:9-18` uses one benign input—not canonical allow/block commands. `9ebd20c` fixed only the named Modal deadlock.
RECOMMENDED: keep — the cross-hook executable command corpus remains unimplemented.

## Proposal: Require Answer-Reflex Evidence In External Research Memos
- ref: `/Users/alien/.claude/steward-proposals/2026-07-09-research-answer-reflex-gate.md` · created 2026-07-09 (55d)
- scout: ok=True wall=82s tok(in/out/reason)=214546/984/252

VERDICT: MOOT
EVIDENCE: 17be40a0 implemented the proposal as an advisory PostToolUse/Stop gate.
EVIDENCE: arc-agi/loop/research_reflex_lint.py:18-44 detects external action claims lacking reflex evidence; .claude/settings.json:117 wires it.
RECOMMENDED: resolve-moot — the requested guard is implemented and active.

## RSI/DX Reflex For User-Added Value
- ref: `/Users/alien/.claude/steward-proposals/2026-07-09-rsi-dx-reflex.md` · created 2026-07-09 (55d)
- scout: ok=True wall=83s tok(in/out/reason)=188794/1275/373

VERDICT: MOOT
EVIDENCE: e7385d7 implemented the reflex; `scripts/reflect_capture.py:130-170` detects operator interventions.
EVIDENCE: `scripts/reflect_session_close.py:108-168` emits the structured fields; `skills/rsi/SKILL.md:90-106` requires action or explicit noop. 5de4a52 subsequently hardened false-positive handling.
RECOMMENDED: resolve-moot — the proposed capture, digest, and closeout behavior is live.

## Contested-file stop-hook: cache adjudications by content hash
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-contested-file-adjudication-cache.md` · created 2026-07-10 (54d)
- scout: ok=True wall=86s tok(in/out/reason)=329225/1385/460

VERDICT: STILL-VALID
EVIDENCE: hooks/stop-uncommitted-warn.sh:302-312 rebuilds the contested advisory unconditionally; lines 360-403 emit it on every Stop without content-hash adjudication.
EVIDENCE: Post-2026-07-10 commits 8c1e331, b05a67b, c13fb48, and ec7a807 changed in-flight/commit/peer handling, not contested-warning deduplication.
RECOMMENDED: keep — unchanged contested files can still trigger repeated identical advisories.

## Port arc-agi's frontier-sensor pattern to an eval-methodology sensor in evals/
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-eval-frontier-sensor.md` · created 2026-07-10 (54d)
- scout: ok=True wall=82s tok(in/out/reason)=239484/1290/214

VERDICT: STILL-VALID
EVIDENCE: `evals/docs/post-cutoff-flips/README.md:45-52` still labels the dated-authority feed harvester “not built.”
`evals/justfile:6-8` exposes only the manual `new-eval` scaffold; no frontier-sensor recipe exists.
Commits `813aba1`–`815db25` added manual benchmark ratings through 2026-07-22, but no standing sensor.
RECOMMENDED: keep — the autonomous eval-methodology surveillance and flip-gold harvesting remain absent.

## Proposal: block `git commit --amend` in shared checkouts (peer sessions detected)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-no-amend-shared-checkout.md` · created 2026-07-10 (54d)
- scout: ok=True wall=191s tok(in/out/reason)=279262/2119/820

VERDICT: STILL-VALID
EVIDENCE: `e160cf7`; `hooks/pretool-multiagent-commit-guard.sh:107-136` explicitly allow-lists `--amend` and exits before the peer block. `hooks/sessionstart-peer-session-warn.sh:62-65` still omits the proposed warning.
RECOMMENDED: keep — the live shared-checkout guard still permits the named history-rewrite race.

## Extend peer-session SessionStart hook with a zombie/live discriminator
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-peer-hook-zombie-discriminator.md` · created 2026-07-10 (54d)
- scout: ok=True wall=93s tok(in/out/reason)=271924/1927/890

VERDICT: SUPERSEDED
EVIDENCE: 70171b1 added `hooks/sessionstart-daemon-twin-warn.sh`; lines 44-72 classify daemon twins via job provenance and transcript growth, refined by 57b2bc4.
EVIDENCE: `~/.claude/settings.json:503-507` registers both the peer-session warning and dedicated daemon-twin discriminator at SessionStart.
RECOMMENDED: resolve-superseded — the zombie/live distinction shipped as a dedicated sibling hook.

## Stop-hook peer detection: false "no peer shares this checkout" under live peers
- ref: `/Users/alien/.claude/steward-proposals/2026-07-10-stop-hook-peer-liveness.md` · created 2026-07-10 (54d)
- scout: ok=True wall=88s tok(in/out/reason)=268068/1723/709

VERDICT: STILL-VALID
EVIDENCE: hooks/peer-session-count.sh:28-60 still relies solely on live `claude` processes plus `lsof`; no commits have changed it since 2026-07-10.
EVIDENCE: hooks/stop-uncommitted-warn.sh:341-400 still emits “No peer claude…most likely YOURS”; ec7a807 only added a Codex-recency proxy, not git/Session-ID evidence.
RECOMMENDED: keep — the original Claude-peer false-negative and unsafe ownership assertion remain possible.

## Schedule intel's executive tick — supersede the 2026-03-07 "manual tool only" decision
- ref: `/Users/alien/.claude/steward-proposals/2026-07-11-intel-executive-tick.md` · created 2026-07-11 (53d)
- scout: ok=True wall=75s tok(in/out/reason)=231326/1556/682

VERDICT: STILL-VALID
EVIDENCE: intel/tools/orchestrator.py:9-12 still declares “MANUAL TOOL ONLY” and unwired; intel/tools/CLAUDE.md:48 confirms no launchd/just/Makefile caller.
EVIDENCE: Latest commit touching it is b1ea9335 (2026-04-26); no post-2026-07-11 commit or installed `com.intel.*` LaunchAgent schedules it.
RECOMMENDED: keep — the proposed autonomous executive tick still does not exist.

## Triage-verdict → same-turn dispatch reflex (converts rsi-hindsight queue row)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-11-triage-dispatch-reflex.md` · created 2026-07-11 (53d)
- scout: ok=True wall=111s tok(in/out/reason)=314758/1897/889

VERDICT: STILL-VALID
EVIDENCE: 8b53735 implemented TRIAGE-DISPATCH in hooks/userprompt-prior-context.py:808.
~/.claude/settings.json:285-311 still binds posttool-background-portfolio.sh only to Bash.
~/.claude/settings.json:346-352 shows Agent dispatches receive only posttool-subagent-output-check.sh.
RECOMMENDED: keep — the Agent-dispatch portfolio nudge remains unimplemented

## reflect_capture: exclude headless-dispatch prompts from operator attribution
- ref: `/Users/alien/.claude/steward-proposals/2026-07-12-reflect-capture-headless-dispatch-exclusion.md` · created 2026-07-12 (52d)
- scout: ok=True wall=113s tok(in/out/reason)=372757/2099/670

VERDICT: STILL-VALID
EVIDENCE: `scripts/common/transcript_text.py:21-28` excludes only compact summaries/meta; no headless-session detection.
`scripts/reflect_capture.py:153-168` still treats other `role=user` dispatch prompts as operator text; targeted-path history has no post-2026-07-12 fix.
`arc-agi/loop/rescue_rate.py:38-57` retains separate local noise regexes rather than a shared predicate.
RECOMMENDED: keep — the false-attribution path remains open.

## reflect_session_close.py — two defects found during 2026-07-15 arc-agi close
- ref: `/Users/alien/.claude/steward-proposals/2026-07-15-reflect-close-prefix-and-teammate-fp.md` · created 2026-07-15 (49d)
- scout: ok=True wall=113s tok(in/out/reason)=336831/1743/568

VERDICT: STILL-VALID
EVIDENCE: 091e40a fixed prefix matching only for `--latest-digest`; `scripts/reflect_session_close.py:358-367` still writes the raw prefix while `:454-463` compares acknowledgments to full IDs.
EVIDENCE: `scripts/reflect_capture.py:162-167` still excludes only task/system notifications, not `<teammate-message>` or `<local-command-*>`.
RECOMMENDED: keep — both `--ack` prefix handling and operator-DX false-positive filtering remain defective.

## Subagent sessions auto-commit UNGRADED work — protocol inversion
- ref: `/Users/alien/.claude/steward-proposals/2026-07-15-subagent-autocommit-leak.md` · created 2026-07-15 (49d)
- scout: ok=True wall=92s tok(in/out/reason)=279543/1519/586

VERDICT: STILL-VALID
EVIDENCE: skills/hooks/stop-uncommitted-warn.sh:405-450 still auto-commits session-owned files without detecting subagent context.
EVIDENCE: b05a67b and c13fb48 mitigate in-flight/peer sweeping but do not make subagents warn-only.
RECOMMENDED: keep — the proposed protocol guard remains unimplemented

## Self-arm wakeup on session-limit kills — 2nd measured application failure
- ref: `/Users/alien/.claude/steward-proposals/2026-07-16-selfarm-on-session-limit-kill.md` · created 2026-07-16 (48d)
- scout: ok=True wall=99s tok(in/out/reason)=274991/1837/690

VERDICT: MOOT
EVIDENCE: 9740b71 implemented the guard at hooks/userprompt-session-limit-guard.py:31-36; ab0ff16 wired it globally at ~/.claude/settings.json:487-490. Current 2026-09-01 doctor reports it live.
RECOMMENDED: resolve-moot — the proposed session-limit wakeup nudge has been implemented and remains wired.

## Guard: block history mutation when HEAD isn't yours (shared checkouts)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-16-shared-checkout-history-mutation-guard.md` · created 2026-07-16 (48d)
- scout: ok=True wall=241s tok(in/out/reason)=457811/2034/592

VERDICT: STILL-VALID
EVIDENCE: `hooks/pretool-multiagent-commit-guard.sh:105-112` still explicitly allows `--amend` without checking HEAD’s `Session-ID:`.
EVIDENCE: `hooks/pretool-destructive-git-ref.sh:32-43` only advises on some reset forms; it does not block soft reset, amend, or rebase.
EVIDENCE: Post-2026-07-16 commit `e160cf7` changed pathspec handling only; no ownership guard was implemented.
RECOMMENDED: keep — the original cross-session history-mutation race remains unblocked.

## reframe + prioritize the own-code closure fix as CORRECTNESS-critical
- ref: `/Users/alien/.claude/steward-proposals/2026-07-18-owncode-closure-is-correctness-not-efficiency.md` · created 2026-07-18 (46d)
- scout: ok=True wall=92s tok(in/out/reason)=323761/1741/502

VERDICT: SUPERSEDED
EVIDENCE: b4a9fedbe deleted `modal_local_stage_runner.py`; `tests/test_local_runner_deleted.py:15-44` enforces direct science-entry execution with no wrapper.
EVIDENCE: e97959edc and `CLAUDE.md:104-138` demoted own-code/import closure to diagnostic screens; the exact-pair semantic ledger is now the sole readiness/shipping authority.
RECOMMENDED: resolve-superseded — the blind subprocess architecture and own-code authority were replaced by sealed execution identity.

## `scripts/ship_currency.py` + `just ship-currency <sample>`
- ref: `/Users/alien/.claude/steward-proposals/2026-07-18-ship-currency-tool.md` · created 2026-07-18 (46d)
- scout: ok=True wall=115s tok(in/out/reason)=362640/2416/893

VERDICT: SUPERSEDED
EVIDENCE: 255f8c7c2 removed Git/source-epoch publication vetoes; `justfile:1797-1827` now exposes the principal `donor-export-authority` readiness path.
EVIDENCE: `justfile:2094-2101` + 79fa0a219 replaced full-DAG rerun crawling with exact-target, prerequisite-bounded drives.
RECOMMENDED: resolve-superseded — the proposed restamp screen targets retired currency semantics and workflow.

## llmx per-model concurrency semaphore (opt-in) — structural fix for subscription-lane contention kills
- ref: `/Users/alien/.claude/steward-proposals/2026-07-19-llmx-per-model-concurrency-semaphore.md` · created 2026-07-19 (45d)
- scout: ok=True wall=116s tok(in/out/reason)=417843/1948/584

VERDICT: STILL-VALID
EVIDENCE: llmx/llmx/cli_backends.py:1098 launches subscription CLIs directly; no semaphore exists.
EVIDENCE: ec2b2e4e added only a campaign-local contention workaround after another affected run.
EVIDENCE: arc-agi/experiments/composed_official/run_episode.sh:30-34 still dispatches without a shared limit.
RECOMMENDED: keep — cross-driver subscription concurrency remains unenforced.

## Proposal: ambient loop-state statusline (kills the "did you stop on purpose?" question)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-19-loop-state-statusline.md` · created 2026-07-19 (45d)
- scout: ok=True wall=92s tok(in/out/reason)=234107/2067/855

VERDICT: MOOT
EVIDENCE: fcbb6f9 (2026-06-16) already implemented the cockpit statusline before this proposal.
EVIDENCE: ~/.claude/settings.json:355-360 wires ScheduleWakeup to posttool-loop-tracker.sh; scripts/claude-statusline.sh:107-110,176-185 renders loop countdown, crons, subagents, and background tasks.
RECOMMENDED: resolve-moot — the requested ambient loop-state display is already live.

## reflect_session_close --latest-digest fallback is project-unscoped
- ref: `/Users/alien/.claude/steward-proposals/2026-07-21-digest-fallback-project-scope.md` · created 2026-07-21 (43d)
- scout: ok=True wall=88s tok(in/out/reason)=240098/1286/352

VERDICT: STILL-VALID
EVIDENCE: scripts/reflect_session_close.py:275-305 — bare lookup still selects the latest unacked digest across all projects.
EVIDENCE: 091e40a — later fix addressed prefix matching but explicitly recorded the fallback returning a genomics digest from arc-agi.
EVIDENCE: ~/Projects/skills/rsi/SKILL.md:28-37 — current workflow still invokes the empty-argument fallback.
RECOMMENDED: keep — the cross-project fallback remains live and unsafe.

## pretool guard — block pathspec commits naming CONTESTED files
- ref: `/Users/alien/.claude/steward-proposals/2026-07-28-pathspec-contested-file-guard.md` · created 2026-07-28 (36d)
- scout: ok=True wall=74s tok(in/out/reason)=202852/1380/434

VERDICT: STILL-VALID
EVIDENCE: `skills/hooks/pretool-multiagent-commit-guard.sh:105-136` still allows every scoped pathspec commit without checking contested-file ledgers.
`skills/hooks/test_pretool_multiagent_commit_guard.py:164-169,248-253` explicitly expects pathspec forms to pass with peers.
Post-2026-07-28 history only changes Stop-hook Codex detection (`ec7a807`), not this missing pretool check.
RECOMMENDED: keep — the proposed contested-path conjunction remains unenforced

## Proposal: per-session checkpoint files (checkpoint.md becomes a 2-line index)
- ref: `/Users/alien/.claude/steward-proposals/2026-07-29-checkpoint-per-session-files.md` · created 2026-07-29 (35d)
- scout: ok=True wall=116s tok(in/out/reason)=263996/1898/922

VERDICT: STILL-VALID
EVIDENCE: No commits since 2026-07-29 touch the targeted writer/reader paths.
EVIDENCE: `hooks/checkpoint_resume.py:38-46` still defines only two shared slots: `checkpoint.md` and `checkpoint-autogen.md`.
EVIDENCE: `hooks/precompact-extract.py:340-365` diverts every live peer collision to the same autogen file, so a third concurrent session can overwrite another checkpoint.
RECOMMENDED: keep — per-session files are still needed to eliminate multi-session last-writer-wins loss.

## RSI SessionStart nudge misattributes digest session + project
- ref: `/Users/alien/.claude/steward-proposals/2026-07-29-rsi-nudge-session-misattribution.md` · created 2026-07-29 (35d)
- scout: ok=True wall=86s tok(in/out/reason)=297876/1795/770

VERDICT: SUPERSEDED
EVIDENCE: 091e40a fixed the actual failure: `--latest-digest` now resolves the nudge’s 8-character session prefix (`scripts/reflect_session_close.py:297-304`).
EVIDENCE: `pending_nudge` already selects a digest row matching the current project and prints that row’s session ID (`scripts/reflect_session_close.py:456-471`).
RECOMMENDED: resolve-superseded — the apparent misattribution was a short-ID lookup failure, now fixed.

## PostToolUse advisory: zero-hit grep over a structured store → store-schema nudge
- ref: `/Users/alien/.claude/steward-proposals/2026-07-29-zero-hit-grep-on-store-nudge.md` · created 2026-07-29 (35d)
- scout: ok=True wall=106s tok(in/out/reason)=333951/2106/702

VERDICT: STILL-VALID
EVIDENCE: `~/Projects/skills/hooks/posttool-grep-zero-on-store.sh` remains absent; no post-2026-07-29 skills commit implements an equivalent.
EVIDENCE: `~/.claude/settings.json:285-311` registers six PostToolUse Bash hooks, none detecting zero-hit structured-store greps.
EVIDENCE: `arc-agi/.claude/rules/teammate-dispatch-protocol.md:62-67` retains only the scoped textual `store-schema` precondition.
RECOMMENDED: keep — the proposed action-time advisory has not been implemented or functionally superseded.

## Proposal: `llmx prices --verify` — live drift check for the hand-maintained price table
- ref: `/Users/alien/.claude/steward-proposals/2026-07-31-llmx-price-verify.md` · created 2026-07-31 (33d)
- scout: ok=True wall=94s tok(in/out/reason)=199324/1659/562

VERDICT: STILL-VALID
EVIDENCE: `llmx/usage_report.py:23-25` remains a manually edited price table; post-proposal commits `c7c9da9`, `5de111e`, and `fee6e73` still update it manually.
`llmx/cli.py:1096-1110` registers no `prices`/verification command; `skills/trending-scout/SKILL.md:215-234` wires no price-drift check into weekly runs.
RECOMMENDED: keep — the stale-price failure mode still has no live detector.

## Steward proposals triage — 2026-06-16
- ref: `/Users/alien/.claude/steward-proposals/TRIAGE-2026-06-16.md` · created 2026-06-15 (79d)
- scout: ok=True wall=134s tok(in/out/reason)=447002/2637/835

VERDICT: SUPERSEDED
EVIDENCE: 7148799 executed the triage: six proposals resolved and the still-valid hook-state item retained individually (`docs/audit/2026-07-04-stale-question-drain.md:10-29`).
EVIDENCE: 56c24f7 fixed the prioritized reception-hook transport; `skills/hooks/posttool-reception-payload-llm.sh:15-18` confirms subscription-first operation.
EVIDENCE: 38d9fa5 added verdict application to the current per-item drain (`scripts/questions_drain.py:146-184`), superseding this static omnibus queue.
RECOMMENDED: resolve-superseded — current per-proposal records and the drain workflow now own unresolved items.

## Proposal: Hook verification state — stateless revalidation (architectural)
- ref: `/Users/alien/.claude/steward-proposals/hook-state-stateless-revalidation.md` · created 2026-07-03 (61d)
- scout: ok=True wall=115s tok(in/out/reason)=298149/1372/247

VERDICT: STILL-VALID
EVIDENCE: genomics c7a14850b narrowed/renamed the guard to orchestrator stops; dbb73953a removed proof-ladder state but retained token gating.
EVIDENCE: genomics/.claude/hooks/pretool-orchestrator-stop-guard.sh:47,99-104 still trusts agent-writable `/tmp/claude-session-verified-*`.
EVIDENCE: genomics/.claude/hooks/posttool-session-verify-log.sh:51-56 still creates/appends those forgeable markers.
RECOMMENDED: keep — stateless inline revalidation remains unimplemented for guarded stops.

## Resolve prediction: **Usage telemetry — subscription blind spot closed (`llmx@7e2d993`)** — light critique (cursor repo-grounded + gpt-5.5) REPLACED the tiktoken plan: `claude -p --output-format json…
- ref: `predictions.jsonl#impl-4980db9d-aba2767d` · created 2026-07-18 (46d)
- scout: ok=True wall=121s tok(in/out/reason)=349336/1827/675

VERDICT: MOOT
EVIDENCE: `llmx@7e2d993` implemented the change; `llmx/cli_backends.py:954` still requests Claude JSON usage and `:1264` logs real subscription tokens.
EVIDENCE: `tests/test_usage_accounting.py:100` covers current parsing; post-2026-07-18 history contains no telemetry removal or replacement.
RECOMMENDED: resolve-moot — the blind spot remains closed and the implementation still earns its place

## Resolve prediction: **Pulse liveness contracts — scoped, NOT universal (`bf68c3a`)** — both critiques killed the "universal registry": a uniform constancy test alarms-on-green for healthy-constant me…
- ref: `predictions.jsonl#impl-4980db9d-03ab1531` · created 2026-07-18 (46d)
- scout: ok=True wall=119s tok(in/out/reason)=333924/1923/913

VERDICT: STILL-VALID
EVIDENCE: scripts/pulse.py:111 declares scoped per-metric contracts; lines 136–140 retain all three should-vary supervision instruments.
EVIDENCE: scripts/pulse_tick.py:124–130 still runs the canary and fails the tick on alarm; post-cutoff commits 99a48af/cac62c3 did not supersede it.
RECOMMENDED: keep — the constant/non-null dead-producer failure remains uniquely covered and actively wired.

## Resolve prediction: **llmx usage surfacing** — DONE (`llmx@62ce643`). Verify-before-build paid off: `usage_log.py` + `scripts/usage_summary.py` already recorded + rolled up usage; it just wasn't reac…
- ref: `predictions.jsonl#impl-275e3582-47014afe` · created 2026-07-18 (46d)
- scout: ok=True wall=115s tok(in/out/reason)=335031/1294/392

VERDICT: MOOT
EVIDENCE: `llmx@62ce643` implemented the command; `llmx/cli.py:1063`–1099 still exposes `llmx usage`.
EVIDENCE: Live `llmx usage --by model --days 7` successfully rolled up 76 calls with tokens, estimated cost, and context headroom.
RECOMMENDED: resolve-moot — the implemented usage surface remains live and functional.

## Resolve prediction: **PPV/reflect-eval counted STALE firings against the current predicate (windowing bug)** — FIXED: added per-rule `since` (predicate-last-changed date) to `config/reflect-omission-…
- ref: `predictions.jsonl#impl-3894d7b4-cbf2123a` · created 2026-07-18 (46d)
- scout: ok=True wall=250s tok(in/out/reason)=146889/1175/561

VERDICT: MOOT
EVIDENCE: 3894d7b implemented per-rule `since`; scripts/reflect_eval.py:46-81 loads it and excludes stale firings.
EVIDENCE: config/reflect-omission-rules.json:2-52 defines `since` for every rule; no targeted-path commits since 2026-07-18.
RECOMMENDED: resolve-moot — the windowing bug remains fixed in current code.

## Resolve prediction: **Closure metric repointed (`supervision-kpi.py`)** — `hooks_shown`/`air` read a `progress/hook_progress/Stop` signal present 7× across all transcripts instead of `attachment/hook…
- ref: `predictions.jsonl#impl-e75d3b7c-5f38d971` · created 2026-07-18 (46d)
- scout: ok=True wall=112s tok(in/out/reason)=387926/2258/902

VERDICT: MOOT
EVIDENCE: 5563996 implemented `attachment/hook_success`; current `scripts/supervision_session.py:165-180` retains and deduplicates it.
EVIDENCE: `artifacts/observe/2026-08-01-0759/supervision/supervision-report.json:44-47` reports 1,274 hooks, confirming the metric remained live after 2026-07-18.
RECOMMENDED: resolve-moot — the dead-metric problem remains fixed and the prediction has passed.

## Resolve prediction: **`over_caution` graduated shadow→enforce (soft nudge)** — `stop-smart-judge.sh` vector #3 ("ends by asking permission for an obvious, reversible, already-authorized action") had…
- ref: `predictions.jsonl#impl-e75d3b7c-2aec2f7a` · created 2026-07-18 (46d)
- scout: ok=True wall=88s tok(in/out/reason)=257937/1828/556

VERDICT: SUPERSEDED
EVIDENCE: 3273bb3 closed the ablation; decisions/2026-07-25-over-caution-ablation-closed.md:26-33 found enforcement bought nothing and retained only shadow scoring.
EVIDENCE: ~/.claude/settings.json:9-10 currently enforces only `verify_before_claim`, excluding `over_caution`.
RECOMMENDED: resolve-superseded — the measured ablation explicitly reversed the predicted graduation.

## Resolve prediction: **Un-archive `/code-review` skill** — moved from `skills/_archive/` to `skills/code-review/`; scout scripts live in `agent-infra/scripts/` (not dead `meta/` paths). Default provid…
- ref: `predictions.jsonl#impl-72c1f394-81814792` · created 2026-07-18 (46d)
- scout: ok=True wall=151s tok(in/out/reason)=531053/2875/1162

VERDICT: MOOT
EVIDENCE: `~/Projects/skills/code-review/SKILL.md:17-23` is live and points to `agent-infra/scripts/`, exactly the proposed un-archived state.
EVIDENCE: Post-cutoff commits `e824c3f`, `347f983`, `82c6be4`, and `f2ae59b` actively hardened the scout and tests.
RECOMMENDED: resolve-moot — the change remains implemented and maintained.

## Resolve prediction: **Skills wired to Composer CLI** — `/critique` (composer default on diff-closeout + close axes), `/sweep` (`--composer` Phase 3), `/observe` (Step 2b precision pass), `/verify-bef…
- ref: `predictions.jsonl#impl-72c1f394-8b334daa` · created 2026-07-18 (46d)
- scout: ok=True wall=103s tok(in/out/reason)=252663/1825/854

VERDICT: SUPERSEDED
EVIDENCE: 4dec39a deleted `/sweep` and `/improve`, folding their jobs into `/observe`.
EVIDENCE: skills/critique/SKILL.md:35,407 routes diffs to `/code-review` with Composer; the Composer critique axis is now opt-in.
EVIDENCE: skills/observe/SKILL.md:246 and verify-before/SKILL.md:117 retain narrower Composer passes.
RECOMMENDED: resolve-superseded — the original multi-skill topology no longer exists.

## Resolve prediction: **Critique axis overlap + cost tooling (2026-06-14)** — `standard` axes (`arch`,`gaps`,`correctness`,`contracts`) now all carry full-review mandate (structure+bugs); lenses differ…
- ref: `predictions.jsonl#impl-72c1f394-8ed4792d` · created 2026-07-18 (46d)
- scout: ok=True wall=137s tok(in/out/reason)=591342/2657/1188

VERDICT: STILL-VALID
EVIDENCE: `skills/critique/scripts/model-review.py:151-258,503-507,604` retains four overlapping full-review axes; post-2026-07-18 commit `f0ba41a` updated routing without superseding them.
EVIDENCE: `agent-infra/scripts/critique_cost.py:51-115` remains wired at `justfile:470`; current 90-day run processed 405 axis dispatches across 90 review packets.
RECOMMENDED: keep — both the differentiated overlap and live cost rollup still earn their place.

## Resolve prediction: **Review dispatch consolidation (phase 1)** — closeout partition in `critique/SKILL.md`; `review_targets` in plan-close manifest; skill-usage-watch launchd killed; `critique_effic…
- ref: `predictions.jsonl#impl-72c1f394-8d875561` · created 2026-07-18 (46d)
- scout: ok=True wall=185s tok(in/out/reason)=1003745/5245/2488

VERDICT: STILL-VALID
EVIDENCE: `skills/critique/SKILL.md:405-425` still partitions diff→code-review and design→critique; `build_plan_close_context.py:397-409` plus `review_gate.py:535-561` still encode and enforce that split.
`evals/critique_efficiency/README.md:1-7` remains tombstoned; no targeted path has post-2026-07-18 commits, and no skill-usage-watch LaunchAgent exists.
RECOMMENDED: keep — the machine-enforced partition still prevents duplicate closeout review.

## Resolve prediction: **Critique full-update Phase A0** — cross2/cross4/lens2/lens4 presets; AXIS_CELLS; review_gate preset triage; ROUTING_VERDICT scaffold. CLI default stays `standard`. — confirmed o…
- ref: `predictions.jsonl#impl-72c1f394-8709f3f1` · created 2026-07-18 (46d)
- scout: ok=True wall=117s tok(in/out/reason)=368618/2230/893

VERDICT: STILL-VALID
EVIDENCE: `skills/critique/scripts/model-review.py:502` retains AXIS_CELLS/presets; `review_gate.py:442` actively triages cross2→cross4.
EVIDENCE: `evals/critique_replay/ROUTING_VERDICT.md:3` remains PENDING; no commits have touched it since `cdcf299`.
RECOMMENDED: keep — the full-grid verdict and resulting default-preset decision remain unresolved.

## Resolve prediction: **VOI-sequenced review ADR** — `decisions/2026-06-15-voi-sequenced-review.md`; Composer scout before adjudication. — confirmed or refuted?
- ref: `predictions.jsonl#impl-72c1f394-68e4b7c1` · created 2026-07-18 (46d)
- scout: ok=True wall=137s tok(in/out/reason)=754514/3263/1053

VERDICT: STILL-VALID
EVIDENCE: `skills/critique/scripts/model-review.py:3637-3668` still runs the repo-grounded premise scout before adjudication; `skills/shared/llm_dispatch.py:272-280` still binds it to Composer 2.5. No post-2026-07-18 commit supersedes this path.
RECOMMENDED: keep — the VOI sequence remains implemented and active.

## Resolve prediction: **Critique P0+P1 hardening** — outcome_link `linked_anchor`/`linked_file` tiers; rank → `escalation-recommendation.json`; cross-talk `cross_talk_degraded`; contradiction meaningfu…
- ref: `predictions.jsonl#impl-72c1f394-70205129` · created 2026-07-18 (46d)
- scout: ok=True wall=105s tok(in/out/reason)=345173/2555/1262

VERDICT: STILL-VALID
EVIDENCE: `skills@b21ca81f` remains current: `outcome_link.py:140-158`, `review_gate.py:398-427`, and `model-review.py:2210-2223` implement all four hardening mechanisms.
EVIDENCE: Since 2026-07-18, only `skills@f0ba41a` touched these paths, changing model routing—not superseding the hardening; `critique/SKILL.md:431-469` still wires it into the workflow.
RECOMMENDED: keep — the mechanisms remain live and unsuperseded, so the earn-its-place prediction still needs resolution.

## Resolve prediction: **Global review routing sync** — `~/.claude/CLAUDE.md` partitioned review pointers; `plan-review-gate.md` triage/VOI/closeout partition; `dependency-manifest.json` tombstoned orch…
- ref: `predictions.jsonl#impl-72c1f394-3389a5cc` · created 2026-07-18 (46d)
- scout: ok=True wall=160s tok(in/out/reason)=713747/4081/2072

VERDICT: MOOT
EVIDENCE: 81d0470 retained the partitioned routing after today’s global-rule slimming (`~/.claude/CLAUDE.md:80`).
EVIDENCE: ac3ecb7 refreshed VOI→triage→adjudication→closeout (`~/.claude/rules/plan-review-gate.md:8`); the manifest still points to `skills/critique/SKILL.md` and omits orchestrator (`~/.claude/dependency-manifest.json:2`).
RECOMMENDED: resolve-moot — the positive prediction is now revalidated by the current implementation.

## Resolve prediction: **`supervision_taxonomy.py` — single-source correction taxonomy + direction vector.** The objective ("declining supervision") was a weighted SCALAR (`sli`) that summed opposite-si…
- ref: `predictions.jsonl#impl-ee04335f-c4f51912` · created 2026-07-18 (46d)
- scout: ok=True wall=91s tok(in/out/reason)=255366/1779/884

VERDICT: MOOT
EVIDENCE: 21cd73e (2026-07-21) refined the taxonomy after the check date and passed 33 tests.
EVIDENCE: scripts/supervision_taxonomy.py:58-74 still defines the direction vector; scripts/supervision_session.py:301-354 emits it in live reports.
EVIDENCE: scripts/tests/test_supervision_taxonomy.py:95-102 enforces all consumers use this single source.
RECOMMENDED: resolve-moot — the implementation demonstrably still earns its place.

## Resolve prediction: **Claude Code 2.1.1xx native-feature adoption** — closed 2026-06-12 same-day; per-item dispositions: (a) `disallowedTools` REJECTED — analysis skills already use the strictly-stro…
- ref: `predictions.jsonl#impl-22aee86f-c92928d3` · created 2026-07-18 (46d)
- scout: ok=True wall=101s tok(in/out/reason)=250616/2236/1023

VERDICT: MOOT
EVIDENCE: improvement-log.md:163 records all native-feature dispositions as closed; no unresolved adoption remains.
EVIDENCE: skills@4dec39a retired the deferred `sweep`/`upgrade` targets; agent-infra@a431d8e now enforces the 8K skills budget via `scripts/skills_budget.py`.
RECOMMENDED: resolve-moot — the work was completed or rejected, and later architecture removed its only deferred targets.

## Resolve prediction: [2026-06-08] rule:checkable-claims-carry-probes — checkable "breaking/blocked" verdicts must carry their probe; downstream re-runs before acting on a skip. blast_radius=local, ver…
- ref: `predictions.jsonl#impl-bbb7525c-0433398c` · created 2026-07-18 (46d)
- scout: ok=True wall=124s tok(in/out/reason)=217913/1469/527

VERDICT: STILL-VALID
EVIDENCE: 0e671af documents a post-2026-07-18 recurrence: an unprobed correction blocked a correct retirement for six weeks (decisions/2026-07-25-agent-infra-mcp-zero-consumption.md:76).
EVIDENCE: The local rule remains current and directly requires inline probes plus downstream re-runs before “skip/blocked” actions (.claude/rules/checkable-claims-carry-probes.md:15).
RECOMMENDED: keep — a recent real incident confirms the rule still prevents consequential false blockers.

## Resolve prediction: **Gated 5 git-only Bash hooks behind `if: "Bash(git*)"` in `~/.claude/settings.json`** — `git-noext-inject`, `git-add-all-guard`, `no-background-commit`, `multiagent-commit-guard`…
- ref: `predictions.jsonl#impl-71823900-f6ee76b3` · created 2026-07-19 (45d)
- scout: ok=True wall=157s tok(in/out/reason)=509734/2806/1198

VERDICT: SUPERSEDED
EVIDENCE: `~/.claude/settings.json:83-91` now spawns one Bash dispatcher; skills commit `03baad9` collapsed 28 hooks into it, eliminating the per-hook spawn cost.
EVIDENCE: `hooks/pretool-bash-dispatch.py:2176-2253` retains the git guards internally; `33afe05` hardened their predicates after finding compound-command bypasses.
RECOMMENDED: resolve-superseded — the original native per-hook gating scaffold was replaced by a consolidated, subsequently hardened dispatcher.

## Resolve prediction: **Codex 0.141 PostToolUse code-mode gating — VERIFIED, no shim change needed** — 0.141 "blocking PostToolUse hooks now correctly reject code-mode tool calls" is strictly ADDITIVE…
- ref: `predictions.jsonl#impl-3ead94aa-d3387cd8` · created 2026-07-19 (45d)
- scout: ok=True wall=151s tok(in/out/reason)=473168/1784/480

VERDICT: MOOT
EVIDENCE: scripts/codex_hook_shim.py:43-54,283-297 still handles PostToolUse and preserves exit-2 blocking.
EVIDENCE: ~/.codex/log/hook_shim_invocations.jsonl records 1,132 recent PostToolUse fires, including 2026-09-02.
EVIDENCE: No shim implementation commits since 2026-07-19; 66922ec retained parity-sync wiring.
RECOMMENDED: resolve-moot — the prediction is confirmed and requires no further change.

## Resolve prediction: **CC 2.1.183 native destructive-git block — no conflict, keep our guards** — native block is PreToolUse-equivalent and auto-mode-only; our `pretool-destructive-git-ref.sh` / `git-…
- ref: `predictions.jsonl#impl-3ead94aa-59767fbc` · created 2026-07-19 (45d)
- scout: ok=True wall=138s tok(in/out/reason)=339487/1595/566

VERDICT: STILL-VALID
EVIDENCE: 33afe05 fixed a real compound-command bypass affecting both guards; they remain wired in `pretool-bash-dispatch.py:2179,2251-2254`.
EVIDENCE: `pretool-destructive-git-ref.sh:19-30` creates recovery snapshots beyond CC’s auto-mode block; live snapshots/warnings fired through 2026-08-27.
RECOMMENDED: keep — current guards provide all-mode enforcement and recovery behavior the native auto-mode block does not.

## Resolve prediction: [2026-06-25] **The funnel ledger already existed — premise of the BACKSTOP GAP entry was stale.** VOI probe: `~/.claude/llmx-usage.jsonl` is appended by llmx for *every* call rega…
- ref: `predictions.jsonl#impl-27ff16ee-7c02e68c` · created 2026-07-25 (39d)
- scout: ok=True wall=133s tok(in/out/reason)=406957/2654/1320

VERDICT: MOOT
EVIDENCE: 27ff16e implemented the missing ledger consumer; scripts/usage-check.py:116-163 and scripts/doctor.py:679-716 remain wired.
EVIDENCE: abf39bd records hard-block resolution; llmx@6a10f68 enforces the $25 cap at dispatch. Post-cutoff f92c7d7 maintained pricing parity.
RECOMMENDED: resolve-moot — both observability and enforcement are implemented.

## Resolve prediction: [2026-06-24] HARNESS-EVAL FLAKY STEP: `system_inventory.py --check` — **fixed 2026-06-28**: `_normalize_volatile_inventory()` strips live launchctl lines from `--render --check` c…
- ref: `predictions.jsonl#impl-93797a17-d4334ee9` · created 2026-07-28 (36d)
- scout: ok=True wall=105s tok(in/out/reason)=216367/1853/606

VERDICT: MOOT
EVIDENCE: 93797a1 implemented the fix; scripts/system_inventory.py:452-475 still normalizes volatile launchctl state.
EVIDENCE: justfile:221-232 invokes `--render --check`; scripts/tests/test_system_inventory.py:26-29 retains regression coverage.
RECOMMENDED: resolve-moot — the flaky check was fixed and the fix remains wired and tested.

## 2026-07-12 21:10 — Standing fable-wave charter proposal (RSI close #2; removes the pulse-loop)
- ref: `/Users/alien/Projects/arc-agi/HUMAN.md:1227` · created 2026-07-12 (52d)
- scout: ok=True wall=95s tok(in/out/reason)=435013/2126/707

VERDICT: SUPERSEDED
EVIDENCE: 2aac4272 / HUMAN.md:33-35 closes the cap remnant: subscription waves uncapped under SATURATION; paid Fable remains per-ask.
91a7a8df / HUMAN.md:1540-1543 grants standing authorization for all Claude-subscription experiment lanes.
e24fd7a4 / .claude/rules/verified-fable-dispatch.md:214-223 makes GPT-5.6 the default and limits Fable to targeted one-offs.
RECOMMENDED: resolve-superseded — broader standing authorization and newer model routing replace the proposed Fable-specific charter.

## Token cost
- scouts: 118 · out_tok: 231367 · reason_tok: 85152 · wall_sum: 13768s

## Dispositions applied 2026-09-02T12:58:42+00:00

- resolved: 63
- deleted: 1
- manual: 15
- kept: 39
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-15-llm-hooks-dead-metered-api.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-16-anim-workbench-grinder-orchestration-tooling.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-16-session-id-private-stamp.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-17-agent-tooling-friction-b38baad8.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-17-eval-run-packager.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-17-substrate-capability-map.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-19-compute-dont-copy-admission.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-19-measurement-fanout-discipline.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-20-claim-context-ref-corpus-grounding.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-20-clean-room-finalize-only.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-20-clinical-assertion-evidence-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-20-deletion-guard-attribution-verify-first.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-20-handoff-consolidation.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-20-holdout-not-insample-eval-metric.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-20-qc-mirror-freshness-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-20-stop-hook-writer-provenance-attribution.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-20-volume-readfile-not-mirror-listdir.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-21-phenome-pytest-timeout.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-21-pytest-collection-error-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-21-worktree-hygiene-surfacing.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-22-audit-head-recheck-dedup.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-22-reachability-into-remediation.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-23-reference-data-integrity-gate.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-24-adaptive-ledger-parallelism.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-24-attestation-output-content-binding.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-24-verified-failloud-ingest-tool.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-25-owncode-attribution-to-completion-kernel.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-26-sample-remediation-payload-blind-phantom.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-26-suspect-empty-extraction-detector.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-26-value-kind-ingest-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-27-admission-overcall-flag.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-27-commit-mine-drops-git-rm-deletions.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-06-27-stage-liveness-worker-state.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-27-unstarted-goal-detection.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-27-watch-drain-volume-free-monitor.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-28-f16-midwrite-volume-crawl-guard.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-29-deid-precommit-hook.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-29-qc-fanout-hardening.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-30-edge-infra-killswitch-pre-build-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-06-30-stale-mock-test-class.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-01-closure-drive-auto-reconcile.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-01-machine-state-done-autonomy.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-02-batch-divergence-refresh.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-02-ledger-closure-depth-and-cca-executor.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-02-load-json-fail-loud-on-corrupt.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-03-askuserquestion-autonomous-warn.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-04-prose-structured-field-drift-lint.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-04-ungoverned-science-in-catalog-prose.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-05-background-bash-relative-path-guard.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-05-codex-exec-stdin-guard.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-06-single-source-payload-verdict.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-06-userprompt-clock.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-07-container-build-canary-and-crashloop-detector.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-08-autocommit-defer-active-subagent-dirs.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-09-research-answer-reflex-gate.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-09-rsi-dx-reflex.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-10-peer-hook-zombie-discriminator.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-16-selfarm-on-session-limit-kill.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-18-owncode-closure-is-correctness-not-efficiency.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-18-ship-currency-tool.md`
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-07-19-loop-state-statusline.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/2026-07-29-rsi-nudge-session-misattribution.md`
  - SUPERSEDED → `/Users/alien/.claude/steward-proposals/TRIAGE-2026-06-16.md`
  - MOOT → `/Users/alien/Projects/agent-infra/decisions-pending/2026-07-15-genomics-export-ship-path.md`
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-4980db9d-aba2767d` — Resolve prediction: **Usage telemetry — subscription blind spot closed (`llmx@7e
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-275e3582-47014afe` — Resolve prediction: **llmx usage surfacing** — DONE (`llmx@62ce643`). Verify-bef
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-3894d7b4-cbf2123a` — Resolve prediction: **PPV/reflect-eval counted STALE firings against the current
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-e75d3b7c-5f38d971` — Resolve prediction: **Closure metric repointed (`supervision-kpi.py`)** — `hooks
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-e75d3b7c-2aec2f7a` — Resolve prediction: **`over_caution` graduated shadow→enforce (soft nudge)** — `
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-81814792` — Resolve prediction: **Un-archive `/code-review` skill** — moved from `skills/_ar
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-8b334daa` — Resolve prediction: **Skills wired to Composer CLI** — `/critique` (composer def
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-72c1f394-3389a5cc` — Resolve prediction: **Global review routing sync** — `~/.claude/CLAUDE.md` parti
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-ee04335f-c4f51912` — Resolve prediction: **`supervision_taxonomy.py` — single-source correction taxon
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-22aee86f-c92928d3` — Resolve prediction: **Claude Code 2.1.1xx native-feature adoption** — closed 202
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-71823900-f6ee76b3` — Resolve prediction: **Gated 5 git-only Bash hooks behind `if: "Bash(git*)"` in `
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-3ead94aa-d3387cd8` — Resolve prediction: **Codex 0.141 PostToolUse code-mode gating — VERIFIED, no sh
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-27ff16ee-7c02e68c` — Resolve prediction: [2026-06-25] **The funnel ledger already existed — premise o
  - MANUAL (ref missing on disk) `predictions.jsonl#impl-93797a17-d4334ee9` — Resolve prediction: [2026-06-24] HARNESS-EVAL FLAKY STEP: `system_inventory.py -
  - MANUAL (ref missing on disk) `/Users/alien/Projects/arc-agi/HUMAN.md:1227` — 2026-07-12 21:10 — Standing fable-wave charter proposal (RSI close #2; removes t
