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

# Auto-loaded context token budget (current project or --compare all)
[group('dashboard')]
context-budget *args:
    uv run python3 scripts/context-budget.py {{args}}

# Harness changelog — tracked changes to rules/hooks with quality scores
[group('dashboard')]
harness-changelog *args:
    uv run python3 scripts/harness-changelog.py {{args}}

# Enrich sessions.db with quality scores
[group('dashboard')]
enrich-quality:
    uv run python3 scripts/session-features.py --enrich-db

# ── Health ─────────────────────────────────────────────────────────

# Fast smoke test (<1m) — indexes, frontmatter, views
[group('health')]
smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Index check (informational) ==="
    uv run python3 scripts/generate-indexes.py --check 2>&1 | tail -5 || true
    echo "=== Research index frontmatter ==="
    head -1 .claude/rules/research-index.md | grep -q '^---$' || { echo "FAIL: research-index.md missing YAML frontmatter"; exit 1; }
    echo "OK: frontmatter intact"
    echo "=== Runlogs DB ==="
    sqlite3 "$HOME/.claude/runlogs.db" "SELECT COUNT(*) FROM sessions" > /dev/null 2>&1 || { echo "FAIL: runlogs sessions"; exit 1; }
    echo "OK: runlogs readable"

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

# Analyze always-exposed instruction / skill / MCP surface
[group('health')]
context-health *args:
    uv run python3 scripts/agent_surface.py {{args}}

# Maintainability metrics for conservatively agent-attributed commits
[group('health')]
maintainability *args:
    uv run python3 scripts/agent_maintainability.py {{args}}

# Smoke test the new agent-infra tooling end-to-end
[group('health')]
agent-infra-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    tmpdir=$(mktemp -d)
    trap 'rm -rf "$tmpdir"' EXIT
    echo "=== Unit tests ==="
    uv run python3 -m unittest tests.test_agent_surface tests.test_agent_maintainability tests.test_research_verifier
    echo "=== Surface analyzer ==="
    uv run python3 scripts/agent_surface.py --top 5 --write "$tmpdir/surface.txt" > /dev/null
    grep -q "Agent Surface Report" "$tmpdir/surface.txt"
    grep -q "MCP exposure" "$tmpdir/surface.txt"
    echo "=== Maintainability analyzer ==="
    uv run python3 scripts/agent_maintainability.py --repo meta --write "$tmpdir/maintainability.txt" > /dev/null
    grep -q "Agent Maintainability Report" "$tmpdir/maintainability.txt"
    grep -q "Repo: meta" "$tmpdir/maintainability.txt"
    echo "=== Research verifier ==="
    uv run python3 scripts/research_verifier.py research/weekly-agent-infra-sweep-2026-04-02.md --write-companion --artifact-dir "$tmpdir/research-verification" > /dev/null
    test -s "$tmpdir/research-verification/weekly-agent-infra-sweep-2026-04-02.verification.md"
    grep -q "Verification Artifact" "$tmpdir/research-verification/weekly-agent-infra-sweep-2026-04-02.verification.md"
    echo "OK: agent-infra tooling smoke test passed"

# Canonical runner for standalone review-tool tests
[group('health')]
review-tool-tests:
    python3 ~/Projects/skills/review/scripts/test_build_plan_close_context.py
    python3 ~/Projects/skills/review/scripts/test_model_review.py

# Browse SQLite database in web UI
[group('dashboard')]
datasette *args:
    uvx datasette ~/.claude/runlogs.db {{args}}

# ── Skills ───────────────────────────────────────────────────────

# Validate all skills (frontmatter, tool refs, hooks, paths)
[group('health')]
skill-health *args:
    uv run python3 scripts/skill-validator.py {{args}}

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

# ── Sessions ─────────────────────────────────────────────────────

# Import vendor logs into runlogs.db
[group('sessions')]
runlog-import:
    uv run python3 scripts/runlog.py import

# Import git commits with session attribution into runlogs.db
[group('sessions')]
git-import days="30":
    uv run python3 scripts/runlog.py git-import --days {{days}}

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

# ── Git ────────────────────────────────────────────────────────────

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
