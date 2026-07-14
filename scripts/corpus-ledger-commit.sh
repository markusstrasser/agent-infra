#!/usr/bin/env bash
# corpus-ledger-commit.sh — daily commit of the corpus belief-change ledger.
#
# The configured corpus root git-tracks the source-of-truth text
# (annotations.jsonl + metadata.json + citances_*.jsonl + figures/*.md); heavy
# derivatives (graph.duckdb, *.pdf, parsed.*/, source.*) are gitignored. This
# snapshots the day's appends so "every correction is a commit" is literally
# true. Idempotent: no-op on days with no ledger change. Invoked by
# com.agent-infra.corpus-ledger-commit (launchd, daily). Local repo, no push.
#
# HISTORY: from 2026-06-26 to 2026-07-14 this job "ran, exited 0, committed
# nothing" while ~20.7K new source dirs went untracked. TWO root causes, both
# fixed here:
#   1. A 0-byte stale .git/index.lock (Jun 29) made every `git add` fail; the
#      old `2>/dev/null || true` swallowed the error, then the empty index
#      passed `git diff --cached --quiet` -> silent exit 0. Now: fail-loud
#      stale-lock guard (clears only a demonstrably-stale lock, else aborts).
#   2. `git add -- '*/annotations.jsonl'` matched almost nothing: git wildcard
#      pathspecs DO NOT recurse into fully-untracked directories, so every brand
#      new source dir was invisible. Now: enumerate ledger files with `find` and
#      stage via --pathspec-from-file (still never touches pdf/parsed/source —
#      those filenames aren't in the find set and are gitignored anyway).
set -euo pipefail

: "${CORPUS_ROOT:?set CORPUS_ROOT explicitly}"
CORPUS="$CORPUS_ROOT"
cd "$CORPUS" 2>/dev/null || exit 0
[ -d .git ] || exit 0

# --- fail-loud stale-lock guard -------------------------------------------
# A leftover index.lock silently breaks every write. Clear it ONLY when it is
# demonstrably stale: older than the 600s ThrottleInterval AND no live git
# process is running against this repo. Otherwise abort LOUDLY (stderr -> the
# job's .err log) rather than swallowing the failure.
LOCK=".git/index.lock"
if [ -e "$LOCK" ]; then
  lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK" 2>/dev/null || echo 0) ))
  if pgrep -f "git.*$CORPUS" >/dev/null 2>&1; then
    echo "corpus-ledger-commit: index.lock present and a git process is live in $CORPUS — aborting (retry next fire)." >&2
    exit 1
  elif [ "$lock_age" -lt 600 ]; then
    echo "corpus-ledger-commit: index.lock only ${lock_age}s old — too fresh to assume stale, aborting." >&2
    exit 1
  else
    echo "corpus-ledger-commit: clearing stale index.lock (${lock_age}s old, no live git proc)." >&2
    rm -f "$LOCK"
  fi
fi

# --- stage the curated ledger filetypes ------------------------------------
# find (not a git wildcard) because git add wildcards skip untracked dirs.
# Only these five filetypes; source.*/pdf/parsed are excluded by omission and
# by .gitignore. NUL-delimited to survive any odd path.
find . -type f \
  \( -name annotations.jsonl \
     -o -name metadata.json \
     -o -name citances_in.jsonl \
     -o -name citances_out.jsonl \
     -o \( -path '*/figures/*' -name '*.md' \) \) \
  -not -path './.git/*' -print0 \
| git add --pathspec-from-file=- --pathspec-file-nul --

if git diff --cached --quiet; then
  exit 0  # nothing changed today
fi

n=$(git diff --cached --name-only | wc -l | tr -d ' ')
git commit -q -m "ledger snapshot $(date +%F) — ${n} files changed"
echo "corpus-ledger-commit: committed ${n} ledger files." >&2
