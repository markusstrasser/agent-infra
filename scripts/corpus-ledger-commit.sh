#!/usr/bin/env bash
# corpus-ledger-commit.sh — daily commit of the corpus belief-change ledger.
#
# The configured corpus root git-tracks the source-of-truth text
# (annotations.jsonl + metadata.json + citances_*.jsonl); heavy derivatives
# (graph.duckdb, *.pdf, parsed.*/) are gitignored. This snapshots the day's
# appends so "every correction is a commit" is literally true. Idempotent:
# no-op on days with no ledger change. Invoked by
# com.agent-infra.corpus-ledger-commit (launchd, daily). Local repo, no push.
set -euo pipefail

: "${CORPUS_ROOT:?set CORPUS_ROOT explicitly}"
CORPUS="$CORPUS_ROOT"
cd "$CORPUS" 2>/dev/null || exit 0
[ -d .git ] || exit 0

# Stage only the tracked source-of-truth pathspecs (never `git add -A`), incl.
# any newly-ingested source dirs. `figures/*.md` are on-demand figure-extraction
# sidecars (paid vision output, not cheaply byte-rederivable) — small text, kept.
git add -- \
  '*/annotations.jsonl' \
  '*/metadata.json' \
  '*/citances_in.jsonl' \
  '*/citances_out.jsonl' \
  '*/figures/*.md' 2>/dev/null || true

if git diff --cached --quiet; then
  exit 0  # nothing changed today
fi

n=$(git diff --cached --name-only | wc -l | tr -d ' ')
git commit -q -m "ledger snapshot $(date +%F) — ${n} files changed" || true
