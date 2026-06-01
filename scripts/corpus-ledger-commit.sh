#!/usr/bin/env bash
# corpus-ledger-commit.sh — daily commit of the corpus belief-change ledger.
#
# The corpus (~/Projects/corpus) git-tracks the source-of-truth text
# (annotations.jsonl + metadata.json + citances_*.jsonl); heavy derivatives
# (graph.duckdb, *.pdf, parsed.*/) are gitignored. This snapshots the day's
# appends so "every correction is a commit" is literally true. Idempotent:
# no-op on days with no ledger change. Invoked by
# com.agent-infra.corpus-ledger-commit (launchd, daily). Local repo, no push.
set -euo pipefail

CORPUS="${CORPUS_ROOT:-$HOME/Projects/corpus}"
cd "$CORPUS" 2>/dev/null || exit 0
[ -d .git ] || exit 0

# Stage only the tracked source-of-truth pathspecs (never `git add -A`), incl.
# any newly-ingested source dirs.
git add -- \
  '*/annotations.jsonl' \
  '*/metadata.json' \
  '*/citances_in.jsonl' \
  '*/citances_out.jsonl' 2>/dev/null || true

if git diff --cached --quiet; then
  exit 0  # nothing changed today
fi

n=$(git diff --cached --name-only | wc -l | tr -d ' ')
git commit -q -m "ledger snapshot $(date +%F) — ${n} files changed" || true
