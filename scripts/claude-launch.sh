#!/usr/bin/env bash
# claude-launch — launch-time peer notice for shared checkouts
# (decisions/2026-06-16-shared-checkout-isolation-by-default.md).
#
# At INTERACTIVE launch, detect a LIVE peer on this checkout (via checkout_claim.py),
# name it in one line, and share the checkout. It never prompts and never switches
# into a worktree: isolation is opt-in with `claude --worktree <name>`. The ADR's
# 2026-10-14 (later) revision explains why sharing is the default.
#
# Adopt via an ALIAS (never a PATH shadow — aliases are not seen inside scripts, so
# the wrapper's `claude` always resolves to the REAL binary → recursion impossible):
#     alias claude="$HOME/Projects/agent-infra/scripts/claude-launch.sh"
#
# Fail-open by construction: every path we don't explicitly handle execs real claude.
# Inspect without launching: CLAUDE_LAUNCH_DRYRUN=1 claude [args] (prints the decision).

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRYRUN="${CLAUDE_LAUNCH_DRYRUN:-}"
REAL_CLAUDE="$(command -v claude || true)"
PY="uv run --no-project python3"
CLAIM="$HERE/checkout_claim.py"

say() { echo "$@" >&2; }
do_exec() {
  if [ -n "$DRYRUN" ]; then echo "[dry-run] exec: ${REAL_CLAUDE:-claude} $*"; exit 0; fi
  exec "$REAL_CLAUDE" "$@"
}

# Need a real binary (except in dry-run, where we never exec).
[ -n "$REAL_CLAUDE" ] || [ -n "$DRYRUN" ] || { say "claude-launch: real 'claude' not on PATH"; exit 127; }

# --- Passthrough conditions: no prompt, no worktree, just run claude ---
# Headless (-p/--print) or an explicit --worktree the user already chose.
for a in "$@"; do
  case "$a" in
    -p|--print|--worktree) do_exec "$@" ;;
  esac
done
# Non-interactive stdin (piped/headless dispatch). DRYRUN forces past this so the
# decision logic is testable under a pipe.
{ [ -t 0 ] || [ -n "$DRYRUN" ]; } || do_exec "$@"
# Not inside a git repo → nothing to isolate.
CHECKOUT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$CHECKOUT" ] || do_exec "$@"

SID="${CLAUDE_SESSION_ID:-launch-$$}"

# --- Precise peer detection (exit 0 ⇒ a LIVE peer holds THIS checkout) ---
# A live peer gets a notice and this session shares main. Until 2026-10-14 Enter at a
# prompt chose a worktree (operator decision 2026-06-19), but the lock never named a
# live peer, so every session shared in practice; once detection worked, the prompt
# stopped every second session in a repo (operator 2026-10-14: "all on main").
PEER=""
if $PY "$CLAIM" -C "$CHECKOUT" peer --session "$SID" >/dev/null 2>&1; then
  PEER=1
  say "●  live peer on $CHECKOUT; sharing main (claude --worktree <name> isolates):"
  $PY "$CLAIM" -C "$CHECKOUT" status >&2 2>/dev/null || true
  [ -z "$DRYRUN" ] || echo "[dry-run] live peer → notice, share"
fi

# --- Share path: claim the checkout unless a live peer holds it, then run ---
# The lock is written with $$ and its start time; `exec` keeps both, so the lock
# names the running claude and a recycled pid reads as stale. (Until 2026-10-14
# the helper recorded its own pid, which exited at once.) A live peer's claim is
# left alone: the lock names one session, and overwriting it would hide that peer
# once this session exits. A failed claim is reported, never fatal. Skipped in
# dry-run so smoke tests have no side effects.
if [ -z "$DRYRUN" ] && [ -z "$PEER" ]; then
  $PY "$CLAIM" -C "$CHECKOUT" claim --session "$SID" --pid "$$" >/dev/null \
    || say "claude-launch: checkout claim failed (rc=$?); peers will not see this session"
fi
do_exec "$@"
