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

# ── Sessions ─────────────────────────────────────────────────────

# Session search & dispatch (index, list, search, show, dispatch)
[group('sessions')]
sessions *args:
    uv run python3 scripts/sessions.py {{args}}
