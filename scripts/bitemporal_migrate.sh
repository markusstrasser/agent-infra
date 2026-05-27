#!/usr/bin/env bash
# Phase A — corpus graph.duckdb bitemporal migration with MCP-aware shutdown.
#
# DuckDB cross-process locks are EXCLUSIVE regardless of RO/RW mode (kernel
# fcntl F_SETLK at the file level). The MCP blocks ALTER simply by being
# connected, not by holding a writer lock. We must SIGTERM agent/MCP holders
# before applying DDL — but only those, not human dev tools.
#
# Phase A of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
# Reference: research/duckdb-mcp-ddl-migration-2026-05-27.md.

set -euo pipefail

GRAPH_DB="${CORPUS_GRAPH_DB:-$HOME/Projects/corpus/graph.duckdb}"

# v6 (per v5 critique #8): filter holders by process command. Only SIGTERM
# known agent/MCP infrastructure. Human dev tools (duckdb shell, DBeaver,
# IDE introspection) get a warning and abort — NEVER blind-killed.
#
# Plan-close finding #10 (CONFIRMED): patterns tightened with word
# boundaries to avoid matching unrelated shells whose path contains a
# substring like 'outbox' or 'drain'. Each pattern now requires either
# a .py extension, a /-separated path component, or a uvx-style
# invocation suffix.
AGENT_PATTERNS='(corpus_mcp\.py|corpus_core/|audit_corpus_sync\.py|/drain[._/]|/outbox[._/])'

# 1. Get ALL holders via kernel fcntl (robust across container/user boundaries).
ALL_HOLDERS=$(lsof -t "$GRAPH_DB" 2>/dev/null || true)
AGENT_HOLDERS=""
HUMAN_HOLDERS=""
if [[ -n "$ALL_HOLDERS" ]]; then
    for PID in $ALL_HOLDERS; do
        CMD=$(ps -p "$PID" -o command= 2>/dev/null || true)
        if [[ "$CMD" =~ $AGENT_PATTERNS ]]; then
            AGENT_HOLDERS="$AGENT_HOLDERS $PID"
        else
            HUMAN_HOLDERS="$HUMAN_HOLDERS $PID"
        fi
    done
fi

# 2. Warn loudly about human-tool holders; abort without killing them.
if [[ -n "$HUMAN_HOLDERS" ]]; then
    echo "WARN: human-tool processes hold $GRAPH_DB:" >&2
    for PID in $HUMAN_HOLDERS; do
        ps -p "$PID" -o pid=,command= >&2
    done
    echo "Close these tools manually, then re-run." >&2
    exit 1
fi

# 3. SIGTERM agent holders, wait up to 10s for graceful shutdown.
if [[ -n "$AGENT_HOLDERS" ]]; then
    echo "TERM agent holders:$AGENT_HOLDERS"
    kill -TERM $AGENT_HOLDERS 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        REMAINING=$(lsof -t "$GRAPH_DB" 2>/dev/null || true)
        [[ -z "$REMAINING" ]] && break
        sleep 1
    done
    # 4. SIGKILL escalation ONLY for agent-pattern processes still alive.
    STILL=$(lsof -t "$GRAPH_DB" 2>/dev/null || true)
    for PID in $STILL; do
        CMD=$(ps -p "$PID" -o command= 2>/dev/null || true)
        if [[ "$CMD" =~ $AGENT_PATTERNS ]]; then
            echo "KILL hung agent: $PID ($CMD)" >&2
            kill -KILL "$PID" 2>/dev/null || true
        else
            echo "Unexpected non-agent holder $PID ($CMD); aborting." >&2
            exit 1
        fi
    done
    sleep 1
fi

# 5. Verify lock-free before DDL.
STILL=$(lsof -t "$GRAPH_DB" 2>/dev/null || true)
if [[ -n "$STILL" ]]; then
    echo "FAIL: process $STILL still holds $GRAPH_DB after kill cascade" >&2
    exit 1
fi

# 6. Apply migration (idempotent — schema_sql via bootstrap is no-op
#    for already-current DBs, ALTERs new columns for legacy).
echo "Applying graph_schema.sql migration to $GRAPH_DB"
uv run corpus maintain --bootstrap-schema-meta "$@"

# 7. Caller MUST restart agent infrastructure (corpus MCP, drain workers).
#    We don't auto-restart because launchd plist names diverge across hosts.
echo "Migration complete. Restart corpus-mcp / drain workers if applicable."
