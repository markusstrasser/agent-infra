# Meta — Agent infrastructure tooling
#
# Usage: just --list

# ── Dashboard ──────────────────────────────────────────────────────

# Session cost/activity dashboard (default: last 7 days)
dashboard *args:
    uv run python3 scripts/dashboard.py {{args}}

# Dashboard for last N days
dashboard-days days:
    uv run python3 scripts/dashboard.py --days {{days}}

# ── Health ─────────────────────────────────────────────────────────

# Cross-project health check
doctor:
    uv run python3 scripts/doctor.py

# ── Epistemic Metrics ─────────────────────────────────────────────

# Sycophancy metric from session transcripts
pushback *args:
    uv run python3 scripts/pushback-index.py {{args}}

# Static analysis for unsourced claims
epistemic-lint *args:
    uv run python3 scripts/epistemic-lint.py {{args}}

# SAFE-lite factual precision check
safe-lite *args:
    uv run python3 scripts/safe-lite-eval.py {{args}}

# User #tag annotations from session transcripts
tags *args:
    uv run python3 scripts/extract_user_tags.py {{args}}

# ── Sessions ─────────────────────────────────────────────────────

# Session search & dispatch (index, list, search, show, dispatch)
sessions *args:
    uv run python3 scripts/sessions.py {{args}}

# ── Cross-Project ────────────────────────────────────────────────

# Scan all project backlogs (--counts for summary)
todos *args:
    bash scripts/todos.sh {{args}}
