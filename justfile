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

# Browse SQLite databases in web UI (runlogs, orchestrator)
[group('dashboard')]
datasette *args:
    uvx datasette ~/.claude/runlogs.db ~/.claude/orchestrator.db {{args}}

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

# ── Governance ──────────────────────────────────────────────────

# Audit gotchas across all projects (monthly via pipeline, or ad-hoc)
[group('governance')]
gotcha-audit:
    uv run python3 scripts/orchestrator.py submit gotcha-audit

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
    DB="$HOME/.claude/orchestrator.db"
    if [ -f "$DB" ]; then
        echo -n "Orch: "
        sqlite3 "$DB" "SELECT GROUP_CONCAT(status || ':' || n, ' ') FROM v_queue" 2>/dev/null || echo "(no views — run just orch-views)"
        stalled=$(sqlite3 "$DB" "SELECT COUNT(*) FROM v_stalled" 2>/dev/null || echo "0")
        [ "${stalled:-0}" -gt 0 ] && echo "  stalled: $stalled (>30min)"
        proposals=$(sqlite3 "$DB" "SELECT COUNT(*) FROM v_proposals" 2>/dev/null || echo "0")
        [ "${proposals:-0}" -gt 0 ] && echo "  proposals: $proposals actionable"
    fi
    plans=$(find .claude/plans -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$plans" -gt 0 ]; then
        echo "Plans: $plans active"
        ls -t .claude/plans/*.md 2>/dev/null | head -3 | xargs -I{} basename {} | sed 's/^/  /'
    fi
    receipts="$HOME/.claude/session-receipts.jsonl"
    if [ -f "$receipts" ]; then
        tail -1 "$receipts" 2>/dev/null | python3 -c 'import json,sys,datetime as dt; d=json.load(sys.stdin); ts=d.get("ts",""); cost=d.get("cost_usd",0); model=d.get("model","?"); ctx=d.get("context_pct",0); delta=int((dt.datetime.now()-dt.datetime.fromisoformat(ts)).total_seconds()/60) if ts else 0; ago=(f"{delta}m" if delta<60 else (f"{delta//60}h" if delta<1440 else f"{delta//1440}d")); print(f"Receipt: {ago} ago, ${cost:.2f}, {model}, {ctx}% ctx")' 2>/dev/null
    fi

# List unimplemented proposals (steward-proposals + design-review patterns)
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
    pj="artifacts/design-review/patterns.jsonl"
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

# Apply SQLite views to orchestrator DB
[group('orchestrator')]
orch-views:
    #!/usr/bin/env bash
    sqlite3 "$HOME/.claude/orchestrator.db" < scripts/views.sql
    echo "Views applied"

# Smoke test: all views return without error
[group('orchestrator')]
db-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    DB="$HOME/.claude/orchestrator.db"
    views="v_queue v_daily_cost v_stalled v_failures v_pipeline_health v_proposals"
    for v in $views; do
        sqlite3 "$DB" "SELECT * FROM $v LIMIT 1" > /dev/null 2>&1 || { echo "FAIL: $v"; exit 1; }
        echo "OK: $v"
    done
    echo "All views pass"

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
