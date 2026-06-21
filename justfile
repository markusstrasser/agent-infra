# Meta — Agent infrastructure tooling
#
# Usage: just --list

# ── Orientation ────────────────────────────────────────────────────

# Live system map: repos · loops · hooks · MCP · skills · doc freshness
# (--json machine-readable · --drift only the docs-vs-reality check)
[group('orientation')]
orient *args:
    uv run python3 scripts/orient.py {{args}}

# Typed system inventory (@system tags · launchd · orchestrator recipes)
[group('orientation')]
system-inventory *args:
    uv run python3 scripts/system_inventory.py {{args}}

# Regenerate architecture.mmd from architecture.template.mmd + live inventory
[group('orientation')]
render-architecture:
    uv run python3 scripts/system_inventory.py --write

# RSI-lifecycle neighborhood of a node (decision id, research stem, or prediction id):
# traversable lifecycle edges (supersedes/branches_from/depends_on…) PLUS weak
# non-traversable relates_to + provenance, for a node. Agentlogs-native: rebuilds
# the rederivable lifecycle_edges table, then runs the lifecycle_neighbors named
# query. `just graph <id>`. Counts alone: `uv run agentlogs lifecycle-reindex`.
[group('orientation')]
graph id:
    uv run agentlogs lifecycle-reindex >/dev/null && uv run agentlogs query lifecycle_neighbors --param node={{id}}

# ── Dashboard ──────────────────────────────────────────────────────

# Live Claude sessions: state · cost · ctx% · armed /loop · last tool
[group('dashboard')]
fleet:
    bash scripts/fleet.sh

# Session cost/activity dashboard (default: last 7 days)
[group('dashboard')]
dashboard *args:
    uv run python3 scripts/dashboard.py {{args}}

# Code line → session/model that authored it (e.g. just who src/agentlogs/db.py:25-40)
[group('dashboard')]
who file *args:
    uv run agentlogs who {{file}} {{args}}

# Session → the code it produced (e.g. just whence <session_uuid>)
[group('dashboard')]
whence session *args:
    uv run agentlogs whence {{session}} {{args}}

# Dashboard for last N days
[group('dashboard')]
dashboard-days days:
    uv run python3 scripts/dashboard.py --days {{days}}

# Normalize Codex/OpenAI run receipts
[group('dashboard')]
agent-receipts *args:
    uv run python3 scripts/agent_receipts.py {{args}}

# Auto-loaded context token budget (current project or --compare all)
[group('dashboard')]
context-budget *args:
    uv run python3 scripts/context-budget.py {{args}}

# Skills index description budget (Codex ~8k char ceiling; loaded mount sets)
[group('dashboard')]
skills-budget *args:
    uv run python3 scripts/skills_budget.py {{args}}

# Sync ~/.claude/skills → ~/.agents/skills + ~/.codex/skills
[group('health')]
sync-agent-skills *args:
    uv run python3 scripts/sync_agent_skills.py {{args}}

# Four-surface governance dedup before minting rules/skills
[group('health')]
dedup-surfaces *args:
    uv run python3 scripts/dedup_surfaces.py {{args}}

# Stale agent worktrees — git never removes these on merge; claude --worktree leaks ~1G/wt
# audit: `just worktree-gc` · reclaim stale: `just worktree-gc apply --all-projects`
# unmerged trees (ahead>0) are SKIPPED by default; `--include-unmerged` drops dir only, keeps branch
[group('health')]
worktree-gc *args:
    uv run python3 scripts/worktree_gc.py {{args}}

# Validate .model-review/dispatch.json closeout partition
[group('health')]
lint-closeout-dispatch *args:
    uv run python3 scripts/lint_closeout_dispatch.py {{args}}

# Plan-close shadow log report (promotion readiness)
[group('dashboard')]
plan-close-report *args:
    uv run python3 scripts/plan_close_report.py {{args}}

# ── Hetzner fleet (cross-project idle-spend control) ───────────────

# List NON-hutter Hetzner boxes idling on the shared account + est. €
[group('hetzner')]
hetzner-idle:
    bash scripts/hetzner-idle-watch.sh

# Teardown ONE non-hutter box (snapshot-then-delete). DRY-RUN unless BUDGET_APPROVED=1.
[group('hetzner')]
hetzner-reap name *args:
    bash scripts/hetzner-reap.sh {{name}} {{args}}

# ── Health ─────────────────────────────────────────────────────────

# Fast smoke test (<1m) — indexes, frontmatter, views
[group('health')]
smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Index check (informational) ==="
    uv run python3 scripts/generate-indexes.py --check 2>&1 | tail -5 || true
    echo "=== Governance index currency (regen from canonical if stale) ==="
    uv run python3 scripts/build_governance_index.py --check 2>&1 | tail -2 \
      && echo "OK: governance-index current" \
      || echo "STALE: run \`just governance-index\` (a canonical source changed)"
    echo "=== Research index frontmatter ==="
    head -1 .claude/rules/research-index.md | grep -q '^---$' || { echo "FAIL: research-index.md missing YAML frontmatter"; exit 1; }
    echo "OK: frontmatter intact"
    echo "=== Routing-doc reference closure (advisory) ==="
    uv run python3 scripts/skill_reference_validator.py --repo agent-infra 2>&1 | grep -E 'dangling|missing absolute|closure OK' || true
    echo "=== agentlogs DB ==="
    sqlite3 "$HOME/.claude/agentlogs.db" "SELECT COUNT(*) FROM sessions" > /dev/null 2>&1 || { echo "FAIL: agentlogs sessions"; exit 1; }
    echo "OK: agentlogs readable"
    echo "=== Doc-vs-reality drift (advisory: live launchd jobs vs CLAUDE.md) ==="
    uv run python3 scripts/orient.py --drift 2>&1 | tail -2 || true
    echo "=== MCP server contracts (in-process, \$0, no LLM) ==="
    uv run python3 scripts/mcp_contract_smoke.py
    echo "=== Skill routing locked evals ==="
    uv run python3 scripts/skill-routing.py --cases schemas/skill-routing-cases.json
    uv run python3 experiments/skill-routing/eval.py --locked
    echo "=== Codex parity (.codex/ + .agents/skills mirror Claude assets) ==="
    uv run --no-project python3 scripts/codex_parity_sync.py --check 2>&1 | tail -6
    echo "=== Skills vendor sync (~/.agents/skills mirror) ==="
    uv run python3 scripts/sync_agent_skills.py --check 2>&1 | tail -4 || true
    echo "=== Skills index budget (advisory until trim) ==="
    uv run python3 scripts/skills_budget.py 2>&1 | tail -6 || true
    echo "=== Claude hook smoke (silently-dead hook gate) ==="
    uv run --no-project python3 scripts/hooks_smoke.py --timeout 8
    echo "=== Codex hook compatibility ==="
    uv run --no-project python3 scripts/codex_hook_compat.py --timeout 8
    echo "=== Hook input contract (stdin/.tool_input — all surfaces) ==="
    uv run --no-project python3 "$HOME/Projects/skills/hooks/lint_hook_input_contract.py" --surfaces
    echo "=== Codex project MCP startup ==="
    uv run --no-project python3 scripts/codex_mcp_smoke.py

# Mirror per-repo .claude/ assets (MCP, hooks, skills) into Codex's .codex/ layers
[group('health')]
codex-parity *args:
    uv run --no-project python3 scripts/codex_parity_sync.py {{args}}

# Smoke every registered Claude hook (global + per-repo) with canned event JSON —
# catches silently-dead hooks (SyntaxError behind fail-open traps, missing files, bad JSON)
[group('health')]
hooks-smoke *args:
    uv run --no-project python3 scripts/hooks_smoke.py {{args}}

# Smoke generated Codex hook mirrors for JSON stdout and benign-input exit codes
[group('health')]
codex-hook-compat *args:
    uv run --no-project python3 scripts/codex_hook_compat.py {{args}}

# Smoke project-scoped Codex stdio MCP deltas for startup + tools/list
[group('health')]
codex-mcp-smoke *args:
    uv run --no-project python3 scripts/codex_mcp_smoke.py {{args}}

# Check all research MCP servers respond (<10s)
[group('health')]
mcp-health:
    #!/usr/bin/env bash
    set -uo pipefail
    ok=0; fail=0
    check() {
        local name=$1 cmd=$2
        if eval "$cmd" > /dev/null 2>&1; then
            echo "  OK: $name"; ((ok++))
        else
            echo "  FAIL: $name"; ((fail++))
        fi
    }
    echo "=== Research MCP health ==="
    check "Exa (web_search)" "claude mcp call exa web_search_exa '{\"query\":\"test\",\"numResults\":1}' 2>/dev/null"
    check "Semantic Scholar" "curl -sf 'https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1' > /dev/null"
    check "scite" "claude mcp call scite search_literature '{\"term\":\"test\",\"limit\":1}' 2>/dev/null"
    check "Perplexity" "claude mcp call perplexity perplexity_search '{\"query\":\"test\"}' 2>/dev/null"
    check "Brave" "claude mcp call brave-search brave_web_search '{\"query\":\"test\",\"count\":1}' 2>/dev/null"
    echo "---"
    echo "$ok OK, $fail FAIL"
    [[ $fail -eq 0 ]]

# Cross-project health check
[group('health')]
doctor:
    uv run python3 scripts/doctor.py

# Harness eval — Eve `eve eval` analog for hook/skill changes (~43s).
[group('health')]
harness-eval:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== harness-eval (hooks + drift + prior-context + orient contracts) ==="
    uv run --no-project python3 scripts/hooks_smoke.py --timeout 8
    uv run python3 scripts/orient.py --drift
    uv run python3 "$HOME/Projects/skills/hooks/test_userprompt_prior_context.py"
    uv run python3 -m pytest scripts/tests/test_orient.py scripts/tests/test_system_inventory.py -q
    uv run python3 scripts/system_inventory.py --check
    uv run python3 scripts/approval_tiers.py
    echo "OK: harness-eval"

# Eve-shaped session replay from agentlogs (structural forensics).
[group('health')]
session-trace session *args:
    uv run python3 scripts/session_trace.py {{session}} {{args}}

# Watches the regression signal itself — a non-completing suite produces none.
[group('health')]
test-health *args:
    uv run python3 scripts/test_health.py {{args}}

# Orphaned-generator ratchet (report-only): flag scripts/ generators with no
# consumer (wired/imported/referenced/invoked). Standing consumer for the
# generation-without-consumption disease. Re-verify each flag by hand before deleting.
[group('health')]
orphan-check *args:
    uv run python3 scripts/orphan_check.py {{args}}

# Triage post-deploy prior-context blindspot flags (observe A5 prerequisite).
prior-context-triage *args:
    uv run python3 scripts/prior_context_triage.py {{args}}

# Hook fire rate vs triage flags (measure prior-context ROI)
prior-context-stats *args:
    uv run python3 scripts/prior_context_fire_stats.py {{args}}

# Size-safe observe dispatch context (600KB cap); drops codex first, then truncates.
observe-context project='agent-infra' sessions='5' *args:
    uv run python3 scripts/observe_prepare_context.py --project {{project}} --sessions {{sessions}} {{args}}

# Fast capped multi-project drift context (no --full; per-project byte caps).
observe-drift sessions='5' *args:
    uv run python3 scripts/observe_drift_context.py --sessions {{sessions}} {{args}}

# Mechanical observe promotion gates (health · saturation · promote-check · preflight).
observe-gates cmd='preflight' artifact_root='' *args:
    #!/usr/bin/env bash
    set -euo pipefail
    root="${artifact_root:-${OBSERVE_ARTIFACT_ROOT:-$PWD/artifacts/observe}}"
    exec uv run python3 ~/Projects/skills/observe/scripts/observe_gates.py "{{cmd}}" \
        --artifact-root "$root" {{args}}

# Observe RSI bundle — size-safe context + prior-context triage + blindspot refresh.
observe-all project='agent-infra' sessions='5':
    just observe-context {{project}} {{sessions}}
    just prior-context-triage
    just prior-context-stats
    just pulse-tick --phase sense

# Pre-registered prediction ledger: `predictions list` (open/DUE/resolved),
# `predictions resolve <id> <confirmed|refuted|partial> "<note>"`. drift-sentinel
# surfaces DUE-and-unresolved ones daily (the resolver — a write-only log is false
# comfort). predictions.jsonl is the append-only calibration ledger.
[group('health')]
predictions *args:
    uv run python3 scripts/predictions.py {{args}}

# RSI closing-force registration trigger: scan recent improvement-log commits and
# register a +30d earn-its-keep prediction for each newly-implemented [x] finding so
# no scaffold escapes the "does this still need to exist?" verdict (gov telos: shrink
# as IQ rises). Idempotent/append-only; run daily by drift-sentinel. --all to backfill.
[group('health')]
register-impl *args:
    uv run python3 scripts/register_implementations.py {{args}}

# Orphaned-FINDINGS ratchet (report-only): flag trending-scout memos whose
# adopt-grade verdicts never reached improvement-log (the loop's read path).
# Sibling to orphan-check, findings axis. --all for full history; promote live
# ones to [ ] citing the memo. See consumption-over-autonomy.md.
[group('health')]
orphan-findings *args:
    uv run python3 scripts/orphan_findings.py {{args}}

# Cross-project memory generalization scan — clusters siloed feedback/reference
# memories that look factor-out-worthy (modal lessons, tool-fabrication, etc.).
# Deterministic pre-filter; harvest Phase 2g does the semantic dedup + factoring.
[group('health')]
memory-harvest *args:
    uv run python3 scripts/memory_harvest.py {{args}}

# Audit verdicts ↔ corpus-annotation drift (substrate-v1, Phase 4 backstop)
[group('health')]
audit-corpus-sync *args:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${CORPUS_ROOT:?set CORPUS_ROOT explicitly}"
    uv run python3 scripts/audit_corpus_sync.py --corpus-root "$CORPUS_ROOT" {{args}}

# Analyze always-exposed instruction / skill / MCP surface
[group('health')]
context-health *args:
    uv run python3 scripts/agent_surface.py {{args}}

# Maintainability metrics for conservatively agent-attributed commits
[group('health')]
maintainability *args:
    uv run python3 scripts/agent_maintainability.py {{args}}

# Canonical runner for standalone review-tool tests
[group('health')]
review-tool-tests:
    cd ~/Projects/skills && PYTHONPATH=. python3 critique/scripts/test_build_plan_close_context.py
    cd ~/Projects/skills && PYTHONPATH=. python3 critique/scripts/test_model_review.py

# Browse SQLite database in web UI
[group('dashboard')]
datasette *args:
    uvx datasette ~/.claude/agentlogs.db {{args}}

# ── Skills ───────────────────────────────────────────────────────

# Validate all skills (frontmatter, tool refs, hooks, paths)
[group('health')]
skill-health *args:
    uv run python3 scripts/skill-validator.py {{args}}

# Generate/validate cross-project skill manifests
[group('health')]
skill-manifest *args:
    uv run python3 scripts/skill_manifest.py {{args}}

# Collect NEW /execute + /critique invocations into the skill-usage-watch
# state file (deterministic half of the 2h skim). Normally runs via launchd
# com.agent-infra.skill-usage-watch; run manually to refresh `pending` now.
[group('health')]
skill-usage-watch:
    uv run python3 scripts/skill_usage_watch.py

# External API token/cost rollup from .model-review/*.meta.json (llmx dispatches)
[group('health')]
critique-cost *args:
    uv run python3 scripts/critique_cost.py {{args}}

# Evaluate hand-authored skill routing fixtures
[group('health')]
skill-routing-eval *args:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run python3 scripts/skill-routing.py --cases schemas/skill-routing-cases.json {{args}}
    uv run python3 experiments/skill-routing/eval.py --locked

# Probe filesystem/loader assumptions such as exact SKILL.md casing
[group('health')]
skill-loader-probe *args:
    uv run python3 scripts/skill_loader_probe.py {{args}}

# Validate skill references in hooks, rules, prompts, and workflow docs
[group('health')]
skill-reference-closure *args:
    uv run python3 scripts/skill_reference_validator.py --repo skills --repo agent-infra --repo intel --repo genomics --repo phenome --repo publishing {{args}}

# Generate skill docs from templates (--dry-run to check drift)
[group('health')]
skill-gen *args:
    uv run python3 scripts/gen-skill-docs.py {{args}}

# Generate a verification artifact for a claim-heavy research memo
[group('health')]
research-verify memo *args:
    uv run python3 scripts/research_verifier.py {{memo}} {{args}}

# ── Epistemic Metrics ─────────────────────────────────────────────

# Sycophancy metric from session transcripts (word-level)
[group('epistemic')]
pushback *args:
    uv run python3 scripts/pushback-index.py {{args}}

# Behavioral fold detection (agent reverses position without new evidence)
[group('epistemic')]
fold-detect *args:
    uv run python3 scripts/fold-detector.py {{args}}

# Static analysis for unsourced claims
[group('epistemic')]
epistemic-lint *args:
    uv run python3 scripts/epistemic-lint.py {{args}}

# Per-model /critique axis quality from .model-review artifacts (report-only).
# `just critique-health --days 30` for current-config drift; flags noisy axes.
[group('epistemic')]
critique-health *args:
    uv run python3 scripts/critique_health.py {{args}}

# Post-review integration audit — did the diff implement HALLUCINATED findings?
[group('epistemic')]
integration-audit review_dir repo='.':
    uv run python3 {{justfile_directory()}}/../skills/critique/scripts/integration_audit.py \
        --review-dir {{review_dir}} --repo {{repo}}

# Deterministic review gate: triage | rank | inconclusive (no LLM)
[group('epistemic')]
review-gate cmd='triage' *args:
    uv run python3 {{justfile_directory()}}/../skills/critique/scripts/review_gate.py {{cmd}} {{args}}

# ── Dispatch (just-fronted engines: gather → critique → …) ────────
# Brief-schema contract: .claude/rules/dispatch-brief-schema.md

# Deterministic v0 context gather around a plan/ADR/memo (no LLM). Emits brief-schema.
[group('dispatch')]
gather path *args:
    uv run python3 scripts/gather_context.py "{{path}}" --repo "$(pwd)" {{args}}

# One-call cross-model critique of a design doc: gather → triage → model-review.
# Fronts the EXISTING engine; removes the orchestrator's packet-assembly turns.
# triage routes the preset + writes a packet-bound dispatch.json. --mode model means
# dead refs (cross-repo / basename in ADRs) WARN not block, and model-review
# provenance-gates the auto-load so no stale manifest can poison it (skills@2b6da1b).
[group('dispatch')]
critique path *args:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .model-review
    slug="$(basename "{{path}}" | sed 's/\.[^.]*$//')"
    packet=".model-review/${slug}-context.md"
    uv run python3 scripts/gather_context.py "{{path}}" --repo "$(pwd)" --output "$packet"
    uv run python3 {{justfile_directory()}}/../skills/critique/scripts/review_gate.py triage \
        --repo "$(pwd)" --packet "$packet" --mode model
    uv run python3 {{justfile_directory()}}/../skills/critique/scripts/model-review.py \
        --dispatch-manifest .model-review/dispatch.json \
        --context "$packet" --project "$(pwd)" \
        --topic "critique: {{path}}" --extract {{args}} \
        "Adversarially review the design doc at {{path}}. Read the actual repo code to ground every claim; do not speculate about files not in context."
    echo "drill:    just review-gate rank --review-dir .model-review --json"
    echo "next:     fold verified findings → {{path}}"

# SAFE-lite factual precision check
[group('epistemic')]
safe-lite *args:
    uv run python3 scripts/safe-lite-eval.py {{args}}

# Tool-trace faithfulness from session transcripts
[group('epistemic')]
trace-faithfulness *args:
    uv run python3 scripts/trace-faithfulness.py {{args}}

# Pre-compaction nuance density summary
[group('epistemic')]
compaction-nuance *args:
    uv run python3 scripts/compaction-nuance.py {{args}}

# Small fixed calibration canary set
[group('epistemic')]
calibration-canary *args:
    uv run python3 scripts/calibration-canary.py {{args}}

# User #tag annotations from session transcripts
[group('epistemic')]
tags *args:
    uv run python3 ~/Projects/skills/improve/scripts/extract_user_tags.py {{args}}

# Hook trigger telemetry (default: last 7 days)
[group('epistemic')]
hook-telemetry *args:
    uv run python3 scripts/hook-telemetry-report.py {{args}}

# Hook ROI — fire/block triage; flags high-volume advisory NOISE to cull and over-aggressive gates to demote
hook-roi *args:
    uv run python3 scripts/hook-roi.py {{args}}

# Hook pesticide-paradox check — per-week trigger slope, flags decayed/plateaued hooks
[group('epistemic')]
hook-decay *args:
    uv run python3 scripts/hook-outcome-correlator.py --decay {{args}}

# Governance self-revision report — shrink candidates, contradictions, advisory-noise (report-only)
[group('epistemic')]
gov-report *args:
    uv run python3 scripts/gov.py report {{args}}

# Behavioral harness A/B smoke — steer-mining cases, harness-steer arms (v0; fork-B = cursor-agent replay)
behavioral-harness-smoke *args:
    uv run python3 scripts/behavioral_harness_replay.py {{args}}

# SHADOW: count high-blast-radius diffs that landed with no test + no review (demand probe for an auto-review gate; promote/cut ~2026-06-21)
[group('epistemic')]
risky-diff-shadow *args:
    uv run python3 scripts/risky_diff_review_shadow.py --days 30 --log {{args}}

# Consumer summary over the accumulated risky-diff shadow log (the promote/cut input)
[group('epistemic')]
risky-diff-report *args:
    uv run python3 scripts/risky_diff_review_shadow.py --report {{args}}

# Feature-work loop decompose-quality shadow (report-only; sibling to risky-diff-shadow).
# Reads live from agentlogs.db — no accumulation log, the DB is the durable substrate.
[group('epistemic')]
feature-loop-report *args:
    uv run python3 scripts/feature_loop_probe.py --report {{args}}

# Learning loop — classify captured session signals into FM dossiers + proposals (add --llm for $0 claude -p enrichment)
[group('epistemic')]
reflect-classify *args:
    uv run python3 scripts/reflect.py classify {{args}}

# Learning loop — review quarantined proposals (auto-record applied; enforcers/mints await you)
[group('epistemic')]
reflect-review:
    uv run python3 scripts/reflect.py review

# Learning loop — capture / cluster / quarantine stats
[group('epistemic')]
reflect-status:
    uv run python3 scripts/reflect.py status

# Learning loop — grade the pre-registered tests (compaction/PPV/throughput); --dry for safe preview
[group('epistemic')]
reflect-eval *args:
    uv run python3 scripts/reflect_eval.py {{args}}

# Full-corpus steer mining — incremental via scanned ledger (~$0.08/session, budget-capped)
[group('epistemic')]
steer-mine *args:
    uv run python3 ~/Projects/skills/observe/scripts/mine_steers.py --from-agentlogs --prompt-mode multi --budget 5 --workers 3 {{args}}

# Unified RSI control plane — phased motor + inbox surface.
#   just pulse-tick                 full tick (substrate→surface)
#   just pulse-tick --phase motor   motor-only (45m cadence)
#   just control-plane              refresh SessionStart inbox
#   just pulse status|funnel|canary subcommands
[group('epistemic')]
pulse-tick *args:
    uv run python3 scripts/pulse.py tick {{args}}

[group('epistemic')]
control-plane *args:
    uv run python3 scripts/pulse.py status --write-inbox {{args}}

[group('epistemic')]
pulse *args:
    uv run python3 scripts/pulse.py {{args}}

# Advanced motor passes (subtract/ablate/list) — direct script; scheduled path is pulse-tick.
[group('epistemic')]
maintain-tick *args:
    uv run python3 scripts/maintain_tick.py {{args}}

# ── Orchestrator-model tooling (canonical; see .claude/rules/orchestrator-tool-names.md) ──

[group('epistemic')]
operator-status-briefing target='.' *args='':
    uv run python3 scripts/operator_status_briefing.py --repo {{target}} {{args}}

[group('epistemic')]
baseline-since-last-green target='.' *args='':
    uv run python3 scripts/baseline_since_last_green.py --repo {{target}} {{args}}

[group('epistemic')]
audit-findings-consolidation audit_dir='docs/audit' *args='':
    uv run python3 scripts/audit_findings_consolidation.py {{audit_dir}} {{args}}

[group('epistemic')]
commit-slice-planning target='.' *args='':
    uv run python3 scripts/commit_slice_planning.py --repo {{target}} {{args}}

[group('epistemic')]
adversarial-debug-scout repo scope='recent' *args='':
    uv run python3 scripts/debug_scout.py {{repo}} --scope {{scope}} {{args}}

# Memo-driven wave loop: cheap cursor scouts find+verify off a shared audit memo until dry.
# Fire-and-forget (background it). Knobs: --max-waves --workers --scouts-per-wave --verifier cursor|opus|none
[group('epistemic')]
debug-until-dry repo scope='recent' *args='':
    uv run python3 scripts/debug_until_dry.py {{repo}} {{scope}} {{args}}

[group('epistemic')]
verification-gate-runner target='.' *args='':
    uv run python3 scripts/verification_gate_runner.py --repo {{target}} {{args}}

[group('epistemic')]
session-automation-telemetry *args='':
    uv run python3 scripts/session_automation_telemetry.py {{args}}

[group('epistemic')]
sensor-integration-ranking *args='':
    uv run python3 scripts/sensor_integration_ranking.py {{args}}

# WebVTT rolling-caption cleanup (youtube-transcript ingest)
[group('epistemic')]
clean-transcript input output='':
    #!/usr/bin/env bash
    set -euo pipefail
    out="${2:-}"
    if [ -z "$out" ]; then
      uv run python3 scripts/clean_vtt.py "{{input}}"
    else
      uv run python3 scripts/clean_vtt.py "{{input}}" -o "{{output}}"
    fi

# Legacy aliases (deprecated 2026-07-19)
[group('epistemic')]
debug repo scope='recent' *args='':
    @just adversarial-debug-scout {{repo}} {{scope}} {{args}}
[group('epistemic')]
debug-triage audit_dir='docs/audit' *args='':
    @just audit-findings-consolidation {{audit_dir}} --kind debug {{args}}
[group('epistemic')]
scout-triage audit_dir='docs/audit' *args='':
    @just audit-findings-consolidation {{audit_dir}} {{args}}
[group('epistemic')]
session-classify *args='':
    @just session-automation-telemetry {{args}}
[group('epistemic')]
audit-delta target='.' *args='':
    @just baseline-since-last-green {{target}} {{args}}
[group('epistemic')]
commit-prep target='.' *args='':
    @just commit-slice-planning {{target}} --status-only {{args}}
[group('epistemic')]
commit-plan target='.' *args='':
    @just commit-slice-planning {{target}} {{args}}

# Install git pre-commit hooks (chains no-large-binaries + append-only/protected guards + codebase-map refresh)
[group('epistemic')]
install-hooks:
    @rm -f .git/hooks/pre-commit
    @printf '%s\n' '#!/usr/bin/env bash' 'set -euo pipefail' \
      '"$HOME/Projects/skills/hooks/pre-commit-guards.sh"' \
      'bash "$HOME/Projects/agent-infra/scripts/pre-commit-architecture-render.sh"' \
      > .git/hooks/pre-commit
    @chmod +x .git/hooks/pre-commit
    @echo "  ✓ .git/hooks/pre-commit → guards + architecture-render (agent-infra)"
    @echo "    chains no-large-binaries + append-only/protected + codebase-map (from .precommit-guards.env)"
    @echo "  (bypass: GIT_ALLOW_BINARIES=1 / GIT_ALLOW_GUARD_BYPASS=1 / SKIP_CODEBASE_MAP_REFRESH=1)"

# Conformance check: is commit-time data/append-only protection LIVE in every repo?
[group('epistemic')]
guard-doctor *args:
    @uv run --no-project python3 scripts/guard_doctor.py {{args}}

# ── Governance ──────────────────────────────────────────────────

# Audit gotchas across all projects (manual prompt / ad-hoc research)
[group('governance')]
gotcha-audit:
    @echo "Use .claude/prompts/nightly-retro.md or a dedicated review prompt; no orchestrator path remains."

# ── Plans ────────────────────────────────────────────────────────

# Show plan status across all projects
[group('plans')]
plans *args:
    uv run python3 scripts/plan-status.py {{args}}

# Show only active (partial/running) plans
[group('plans')]
plans-active:
    uv run python3 scripts/plan-status.py --active

# Show plans as JSON (machine-readable)
[group('plans')]
plans-json:
    uv run python3 scripts/plan-status.py --json

# ── Sessions (agentlogs) ─────────────────────────────────────────

# Ingest new sessions from all vendors (Claude, Codex, Cursor, Gemini, Kimi) into agentlogs.db
[group('sessions')]
agentlogs-index *args:
    uv run agentlogs index {{args}}

# Search FTS across all vendors' sessions
[group('sessions')]
agentlogs-search *args:
    uv run agentlogs search {{args}}

# DB size + per-vendor counts + indexer health
[group('sessions')]
agentlogs-stats:
    uv run agentlogs stats

# Run a named analytical query (omit name to list available)
[group('sessions')]
agentlogs-query *args:
    uv run agentlogs query {{args}}

# Import git commits with Session-ID attribution (populates v_session_commits etc.)
[group('sessions')]
agentlogs-git-import days="30":
    uv run agentlogs git-import --days {{days}}

# Generic passthrough: agentlogs <any-subcommand>
[group('sessions')]
agentlogs *args:
    uv run agentlogs {{args}}

# ── Common Crawl ──────────────────────────────────────────────────

# One-time per release: download CC domain-ranks (~2.4GB) + convert to parquet
[group('cc')]
cc-ranks-refresh:
    scripts/cc-domain-ranks.sh refresh

# Look up harmonic centrality + pagerank for a domain (uses cached parquet)
[group('cc')]
cc-rank domain:
    scripts/cc-domain-ranks.sh lookup {{domain}}

# Cloud-hosted multi-agent review of current branch (CC 2.1.120+, billed)
[group('cc')]
review-branch *target:
    #!/usr/bin/env bash
    set -euo pipefail
    branch=$(git branch --show-current 2>/dev/null || echo HEAD)
    out="artifacts/ultrareview-${branch//\//-}-$(date +%Y%m%d-%H%M).json"
    mkdir -p artifacts
    echo "Running claude ultrareview ${1:-} → $out (timeout 30m)"
    claude ultrareview --json --timeout 30 {{target}} > "$out"
    echo "Findings: $(jq '.bugs | length' "$out" 2>/dev/null || echo unknown)"
    echo "Output:   $out"

# Delete all Claude Code state for a project (transcripts, tasks, history)
[group('cc')]
project-purge target:
    @echo "Dry-run first:"
    claude project purge {{target}} --dry-run
    @echo
    @echo "To confirm: claude project purge {{target}} --yes"

# ── Native Tools ───────────────────────────────────────────────────

# Quick operational state snapshot (branch, queue, plans, last receipt)
[group('dashboard')]
brief:
    #!/usr/bin/env bash
    set -euo pipefail
    branch=$(git branch --show-current 2>/dev/null || echo "detached")
    dirty=$(git status --porcelain 2>/dev/null)
    echo "=== meta ($branch) ==="
    if [ -n "$dirty" ]; then
        cnt=$(echo "$dirty" | wc -l | tr -d ' ')
        files=$(echo "$dirty" | head -5 | awk '{print $2}' | tr '\n' ', ' | sed 's/,$//')
        echo "Dirty: $cnt files ($files)"
    else
        echo "Dirty: clean"
    fi
    echo "Recent:"
    git log --oneline --since="midnight" -5 2>/dev/null | sed 's/^/  /' || echo "  (none)"
    echo "Prompts:"
    ls .claude/prompts/*.md 2>/dev/null | xargs -I{} basename {} | sed 's/^/  /' || echo "  (none)"
    plans=$(find .claude/plans -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$plans" -gt 0 ]; then
        echo "Plans: $plans active"
        ls -t .claude/plans/*.md 2>/dev/null | head -3 | xargs -I{} basename {} | sed 's/^/  /'
    fi
    receipts="$HOME/.claude/session-receipts.jsonl"
    if [ -f "$receipts" ]; then
        tail -1 "$receipts" 2>/dev/null | python3 -c 'import json,sys,datetime as dt; d=json.load(sys.stdin); ts=d.get("ts",""); cost=d.get("cost_usd",0); model=d.get("model","?"); ctx=d.get("context_pct",0); delta=int((dt.datetime.now()-dt.datetime.fromisoformat(ts)).total_seconds()/60) if ts else 0; ago=(f"{delta}m" if delta<60 else (f"{delta//60}h" if delta<1440 else f"{delta//1440}d")); print(f"Receipt: {ago} ago, ${cost:.2f}, {model}, {ctx}% ctx")' 2>/dev/null
    fi

# List unimplemented proposals (steward-proposals + observe patterns)
[group('dashboard')]
proposals:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Steward Proposals ==="
    shopt -s nullglob
    for f in ~/.claude/steward-proposals/*.md; do
        if ! grep -q "IMPLEMENTED" "$f"; then
            name=$(basename "$f" .md)
            echo "  [ ] $name"
        else
            name=$(basename "$f" .md)
            echo "  [x] $name"
        fi
    done
    echo ""
    echo "=== Design Review Patterns (actionable) ==="
    pj="artifacts/observe/patterns.jsonl"
    if [ -f "$pj" ]; then
        python3 -c "
    import json
    for line in open('$pj'):
        p = json.loads(line.strip())
        if p.get('type') in ('REINVENTED_LOGIC','TOOL_GAP','MANUAL_COORDINATION') and not p.get('status'):
            freq = p.get('frequency', '?')
            projs = ','.join(p.get('projects', []))
            print(f'  {p[\"name\"]} (freq={freq}, projects={projs})')
    " 2>/dev/null || echo "  (parse error)"
    else
        echo "  (no patterns.jsonl)"
    fi

# ── Code Quality ──────────────────────────────────────────────────

# Cyclomatic complexity report (radon) — top offenders + average
[group('health')]
complexity *args:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Cyclomatic Complexity (meta/scripts) ==="
    uvx radon cc scripts/ -a -nc -s 2>&1 | tail -25
    echo ""
    echo "=== Functions with complexity > 10 ==="
    uvx radon cc scripts/ -nc -n C 2>&1 | grep -E ' - [C-F]$' | sort -t'-' -k2 -r | head -15
    echo ""
    count=$(uvx radon cc scripts/ -nc -n C 2>&1 | grep -cE ' - [C-F]$' || true)
    echo "Total high-complexity functions (C+): $count"

# Cyclomatic complexity across meta + selve + genomics
[group('health')]
complexity-all:
    #!/usr/bin/env bash
    set -euo pipefail
    for repo in meta selve genomics; do
        dir="$HOME/Projects/$repo"
        if [ -d "$dir/scripts" ]; then
            echo "=== $repo ==="
            uvx radon cc "$dir/scripts/" -a -nc -s 2>&1 | tail -5
            count=$(uvx radon cc "$dir/scripts/" -nc -n C 2>&1 | grep -cE ' - [C-F]$' || true)
            echo "High-complexity (C+): $count"
            echo ""
        fi
    done

# ── Lint ───────────────────────────────────────────────────────────

# Check for raw sqlite3.connect or Path.home()/.claude outside common/
[group('health')]
lint-dupes:
    #!/usr/bin/env bash
    ok=true
    echo "Checking for raw sqlite3.connect..."
    hits=$(grep -rn "sqlite3\.connect" scripts/*.py scripts/**/*.py 2>/dev/null | grep -v "common/" | grep -v "^#")
    if [ -n "$hits" ]; then
        echo "WARN: raw sqlite3.connect found:"
        echo "$hits"
        ok=false
    else
        echo "  PASS: no raw sqlite3.connect"
    fi
    echo "Checking for raw Path.home()/.claude..."
    hits=$(grep -rn 'Path\.home.*"\.claude"' scripts/*.py scripts/**/*.py 2>/dev/null | grep -v "common/")
    if [ -n "$hits" ]; then
        echo "WARN: raw .claude paths found:"
        echo "$hits"
        ok=false
    else
        echo "  PASS: no raw .claude paths"
    fi
    echo "Checking for duplicate load_jsonl definitions..."
    hits=$(grep -rn "def load_jsonl" scripts/*.py 2>/dev/null)
    if [ -n "$hits" ]; then
        echo "WARN: duplicate load_jsonl found:"
        echo "$hits"
        ok=false
    else
        echo "  PASS: no duplicate load_jsonl"
    fi
    $ok && echo "All checks pass" || echo "Some checks failed (advisory)"

# ── Vendor Docs ──────────────────────────────────────────────────

# Sync vendor API docs (scite, fastmcp, claude-code, etc.)
[group('health')]
vendor-docs *args:
    ./scripts/sync-vendor-docs.sh {{args}}

# Deterministic surveillance fetch: vendor docs + CC binary skills, commit diffs.
# Runs daily via com.agent-infra.vendor-sweep; this is the manual entry point.
[group('health')]
vendor-sweep:
    bash scripts/vendor-sweep.sh

# Surveillance freshness — which sweeps are DUE (deterministic, zero-API).
# Consumed by /improve maintain to decide whether to run a semantic sweep.
# vendor-docs/binary are fetched by launchd daily; the agent runs the rest.
[group('health')]
freshness:
    #!/usr/bin/env bash
    # Calendar-day deltas only — normalize the stamp to midnight so a date-only
    # filename stamp doesn't fractionally undershoot a wall-clock "now".
    today_ep=$(date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%Y-%m-%d) 00:00:00" +%s)
    # Age from the date stamp IN the filename (the real "when run"); mtime is a
    # proxy git checkouts silently reset, so only fall back to it when no stamp.
    newest() {
      local glob="$1" best_d="" best_f=""
      for f in $glob; do
        [ -e "$f" ] || continue
        local d; d=$(basename "$f" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
        [ -z "$d" ] && d=$(date -r "$(stat -f %m "$f")" +%Y-%m-%d)
        if [ -z "$best_d" ] || [[ "$d" > "$best_d" ]]; then best_d="$d"; best_f="$f"; fi
      done
      echo "$best_d|$best_f"
    }
    row() {
      local name="$1" glob="$2" target="$3"
      local res; res=$(newest "$glob"); local d="${res%%|*}" f="${res##*|}"
      if [ -z "$f" ]; then printf "  %-20s %-16s %5s  %4sd  %s\n" "$name" "(none)" "-" "$target" "DUE"; return; fi
      local ep; ep=$(date -j -f "%Y-%m-%d %H:%M:%S" "$d 00:00:00" +%s 2>/dev/null || echo "$today_ep")
      local age=$(( (today_ep - ep) / 86400 ))
      local status="ok"; [ "$age" -ge "$target" ] && status="DUE"
      printf "  %-20s %-16s %4dd  %4sd  %s\n" "$name" "$(basename "$f" .md | cut -c1-16)" "$age" "$target" "$status"
    }
    echo "SURVEILLANCE FRESHNESS"
    printf "  %-20s %-16s %5s  %5s  %s\n" "source" "last" "age" "tgt" "status"
    row "vendor-docs"       "docs/vendor/*.json"               2
    row "binary-extract"    "research/binary-extracts/*.md"    7
    row "trending-scout"    "research/trending-scout-*.md"     2
    row "agent-infra-sweep" "research/*sweep*.md"              3

# ── Git ────────────────────────────────────────────────────────────

# Push all main workspace repos (also: `just -f ~/Projects/justfile push-all` from anywhere)
[group('git')]
push-all *args:
    bash scripts/git-push-all.sh {{args}}

[group('git')]
push-all-status:
    bash scripts/git-push-all.sh --status

# Top 20 most-changed files per repo (churn hotspots)
[group('git')]
churn-hotspots since="1 year ago":
    #!/usr/bin/env bash
    for repo in meta intel genomics selve skills; do
      results=$(git -C "$HOME/Projects/$repo" log --format=format: --name-only --since="{{since}}" \
        | sed '/^$/d' | sort | uniq -c | sort -nr | head -20 2>/dev/null)
      if [ -n "$results" ]; then
        echo "=== $repo ==="
        echo "$results"
        echo
      fi
    done

# Files most associated with fix/bug commits
[group('git')]
bug-hotspots since="1 year ago":
    #!/usr/bin/env bash
    for repo in meta intel genomics selve skills; do
      results=$(git -C "$HOME/Projects/$repo" log -i -E --grep="fix|bug|broken" \
        --name-only --format='' --since="{{since}}" \
        | sed '/^$/d' | sort | uniq -c | sort -nr | head -20 2>/dev/null)
      if [ -n "$results" ]; then
        echo "=== $repo ==="
        echo "$results"
        echo
      fi
    done

# Commit count by month per repo (velocity shape)
[group('git')]
velocity:
    #!/usr/bin/env bash
    for repo in meta intel genomics selve skills; do
      results=$(git -C "$HOME/Projects/$repo" log --format='%ad' --date=format:'%Y-%m' \
        | sort | uniq -c 2>/dev/null)
      if [ -n "$results" ]; then
        echo "=== $repo ==="
        echo "$results"
        echo
      fi
    done

# Search Rejected: trailers across all repos
[group('git')]
discarded:
    #!/usr/bin/env bash
    for repo in meta intel genomics selve skills; do
      results=$(git -C "$HOME/Projects/$repo" log --all --format='%C(yellow)%h%Creset %s%n  %b' --grep='Rejected:' -20 2>/dev/null | head -40)
      if [ -n "$results" ]; then
        echo "=== $repo ==="
        echo "$results"
        echo
      fi
    done

# Phase 6 phenome migration (substrate-v1)
[group('corpus')]
migrate-phenome *args:
    uv run python3 scripts/migrate_phenome_source_records.py {{args}}

# Phase 6.5 intel entity citation extraction (substrate-v1)
[group('corpus')]
extract-intel-citations *args:
    uv run python3 scripts/extract_intel_entity_citations.py {{args}}

# Deploy corpus-marker Modal app (Marker on T4 GPU + Gemini cleanup).
# Pre-req: `modal secret create gemini-api-key GEMINI_API_KEY=$GEMINI_API_KEY`.
[group('corpus')]
modal-deploy-marker:
    uv run modal deploy scripts/corpus_marker_modal.py

# Smoke-test the deployed corpus-marker app on a PDF.
[group('corpus')]
modal-smoke-marker pdf:
    uv run modal run scripts/corpus_marker_modal.py --pdf {{pdf}}

# Phase A bitemporal migration: MCP-aware DDL apply on corpus graph.duckdb.
# Filters lsof holders by AGENT_PATTERNS — human dev tools (DBeaver, IDE)
# get a warning, not a SIGKILL. SIGTERM→SIGKILL escalation for agent holders.
[group('corpus')]
bitemporal-migrate *args:
    bash scripts/bitemporal_migrate.sh {{args}}

# Lint: forbid raw `FROM annotations` outside writer allowlist.
[group('corpus')]
lint-no-bare-annotations *args:
    uv run python3 scripts/lint_no_bare_annotations_read.py {{args}}

# Run corpus-core tests from the right cwd (scripts/corpus has its own
# pyproject + venv; `uv run pytest` from agent-infra root fails to
# spawn because uv resolves to the wrong project).
[group('corpus')]
test-corpus *args:
    cd ../substrate && uv run pytest packages/corpus-core/tests/ {{args}}

# ── Knowledge ──────────────────────────────────────────────────────

# Regenerate per-repo codebase maps + summary caches across 5 projects.
# Zero-API (--no-llm), idempotent (no git churn on unchanged repos). Scheduled
# daily 06:30 via com.agent-infra.codebase-map-refresh; run manually after large
# script changes. Supersedes pipelines/repo-index-refresh.json (orchestrator gone).
[group('knowledge')]
refresh-maps:
    scripts/refresh-codebase-maps.sh

# Regenerate the compact governance index from the canonical sources (GOALS.md,
# CLAUDE.md constitution, vetoed-decisions.md). Single source for curated-governance
# injection + clash-detection; consumers LOAD it, never re-state it. Deterministic
# (no git churn unless a source changed). `--check` fails if the on-disk copy is stale.
[group('knowledge')]
governance-index *args:
    uv run python3 scripts/build_governance_index.py --repo "$(pwd)" {{args}}

# Offline governance clash-detection over captured directive-class user messages
# (Phase 2 SHADOW, ADR 2026-06-16-governance-clash-detection). Judges captures against
# .claude/governance-index.md, writes verdicts to ~/.claude/clash-shadow.jsonl — surfaces
# NOTHING (measure precision on real messages before promoting to the human back-queue).
# `just clash-detect` runs detection · `just clash-detect --summary` shows the tally.
[group('knowledge')]
clash-detect *args:
    uv run python3 scripts/clash_detect.py --repo "$(pwd)" {{args}}

# Focused "Questions for you" VIEW over the human-gated stores (decisions-pending +
# steward-proposals) — the VIEW-not-STORE deliverable (ADR 2026-06-16-agent-question-
# convergence). Reads + filters + renders only; adds NO store (reversible by deletion).
# Also surfaced at SessionStart via act_drain's digest. `--json` = machine lane.
[group('knowledge')]
questions *args:
    uv run python3 scripts/questions_view.py --repo "$(pwd)" {{args}}

# Find docs that may be stale after a correction — lexical scan for a term
# across the knowledge repos. Replaces propagate-correction.py's forward
# term-match leg (correction-sweep pipeline retired 2026-05-29).
[group('knowledge')]
propagate term:
    rg -n --type md "{{term}}" /Users/alien/Projects/phenome/docs /Users/alien/Projects/agent-infra/research /Users/alien/Projects/intel/analysis

# Find unresolved correction/retraction blockquotes across the knowledge
# repos. Replaces propagate-correction.py's @correction-scan leg.
[group('knowledge')]
scan-corrections:
    rg -n '^>\s*\*\*(CORRECTION|RETRACTION|REVISED|UPDATE)\b' --type md /Users/alien/Projects/phenome /Users/alien/Projects/agent-infra /Users/alien/Projects/intel

# Extract embedded skill/workflow prompts from the current Claude Code binary
# and show the diff vs the last extracted version. The inter-version prompt
# diff is an unpublished vendor changelog — run after each Claude Code update.
# Provenance: research/2026-06-12-vendor-binary-skill-archaeology.md
[group('knowledge')]
binary-skills-diff:
    uv run python3 scripts/binary_skills_extract.py
    @files=$(ls research/binary-extracts/*.md | tail -2); \
    set -- $files; \
    if [ "$#" -lt 2 ]; then echo "(single extraction — baseline)"; \
    else git --no-pager diff --no-index "$1" "$2" || true; fi

# Forced ranking of files most worth expensive review — focus-weighted commit
# frequency + size + near-dup + fan-in (code) / orphan-stale (md), import-cycle
# flag. Deterministic recall+ranking; read the top-N with max reasoning.
# Usage: just rank [repo] [--days N] [--top N]
# Provenance: research/2026-06-13-code-health-diagnostics-for-agents.md
[group('knowledge')]
rank *args:
    uv run python3 scripts/structure_debt_rank.py {{args}}

# ── Git-ecosystem leverage (survey 2026-06-19) ────────────────────

# Configure local merge drivers for THIS clone (idempotent; run once per clone).
# mergiraf = AST-aware merge (`brew install mergiraf`), paired with .gitattributes:
# auto-resolves structural conflicts, falls back to conflict markers when unsafe.
# The driver lives in .git/config (local, not shared) — this recipe is its repro.
[group('dev')]
setup-merge-drivers:
    git config --local merge.mergiraf.name "mergiraf AST merge driver"
    git config --local merge.mergiraf.driver "mergiraf merge --git %O %A %B -p %P -l %L"
    @echo "configured: mergiraf (AST, code+structured) + built-in union (append-only ledgers) — see .gitattributes"

# Binary-search history to the commit that regressed a metric — the ACTIVE half of
# "the git log is the learning". <cmd> exit!=0 = bad (an eval, or arc-agi's
# loop/heretic_audit.py). For slow evals, memoize results per commit-hash.
# Usage: just bisect-regression <good-rev> <bad-rev> <cmd...>
#   e.g. just bisect-regression HEAD~20 HEAD 'uv run python3 some_eval.py'
[group('dev')]
bisect-regression good bad +cmd:
    git bisect start {{bad}} {{good}}
    -git bisect run {{cmd}}
    git bisect reset
