# Meta — Agent infrastructure tooling
#
# Usage: just --list

# ── Dashboard ──────────────────────────────────────────────────────

# Session cost/activity dashboard (default: last 7 days)
[group('dashboard')]
dashboard *args:
    uv run python3 scripts/dashboard.py {{args}}

# Dashboard for last N days
[group('dashboard')]
dashboard-days days:
    uv run python3 scripts/dashboard.py --days {{days}}

# Normalize Codex/OpenAI run receipts
[group('dashboard')]
agent-receipts *args:
    uv run python3 scripts/agent_receipts.py {{args}}

# ── Health ─────────────────────────────────────────────────────────

# Cross-project health check
[group('health')]
doctor:
    uv run python3 scripts/doctor.py

# ── Skills ───────────────────────────────────────────────────────

# Validate all skills (frontmatter, tool refs, hooks, paths)
[group('health')]
skill-health *args:
    uv run python3 scripts/skill-validator.py {{args}}

# Generate skill docs from templates (--dry-run to check drift)
[group('health')]
skill-gen *args:
    uv run python3 scripts/gen-skill-docs.py {{args}}

# ── Epistemic Metrics ─────────────────────────────────────────────

# Sycophancy metric from session transcripts
[group('epistemic')]
pushback *args:
    uv run python3 scripts/pushback-index.py {{args}}

# Static analysis for unsourced claims
[group('epistemic')]
epistemic-lint *args:
    uv run python3 scripts/epistemic-lint.py {{args}}

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
    uv run python3 scripts/extract_user_tags.py {{args}}

# Hook trigger telemetry (default: last 7 days)
[group('epistemic')]
hook-telemetry *args:
    uv run python3 scripts/hook-telemetry-report.py {{args}}

# ── Orchestrator ─────────────────────────────────────────────────

# Submit + run pipeline synchronously (interactive mode)
[group('orchestrator')]
run-pipeline pipeline *args:
    uv run python3 scripts/orchestrator.py run-pipeline {{pipeline}} {{args}}

# Show orchestrator task queue
[group('orchestrator')]
orch-status:
    uv run python3 scripts/orchestrator.py status

# Show pipeline cost/status rollup
[group('orchestrator')]
orch-pipelines:
    uv run python3 scripts/orchestrator.py pipelines

# Run one queued task (manual tick)
[group('orchestrator')]
orch-tick:
    uv run python3 scripts/orchestrator.py tick

# Show orchestrator event log
[group('orchestrator')]
orch-log *args:
    uv run python3 scripts/orchestrator.py log {{args}}

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

# ── Sessions ─────────────────────────────────────────────────────

# Import vendor logs into runlogs.db
[group('sessions')]
runlog-import:
    uv run python3 scripts/runlog.py import

# Session search & dispatch (index, list, search, show, dispatch)
[group('sessions')]
sessions *args:
    uv run python3 scripts/sessions.py {{args}}

# ── Git ────────────────────────────────────────────────────────────

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
