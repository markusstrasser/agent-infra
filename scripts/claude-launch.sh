#!/usr/bin/env bash
# claude-launch — Phase 3 of isolate-by-default
# (decisions/2026-06-16-shared-checkout-isolation-by-default.md).
#
# At INTERACTIVE launch, detect a LIVE peer on this checkout (via checkout_claim.py)
# and PROMPT: isolate in a worktree, or share. NOT a silent auto-wrapper — the
# Revisions note in the ADR explains why (surprise context switch, headless breakage,
# path-keyed-infra blindness). This asks; it never switches behind your back.
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
if $PY "$CLAIM" -C "$CHECKOUT" peer --session "$SID" >/dev/null 2>&1; then
  say "⚠  live peer on $CHECKOUT:"
  $PY "$CLAIM" -C "$CHECKOUT" status >&2 2>/dev/null || true
  if [ -n "$DRYRUN" ]; then echo "[dry-run] live peer → would prompt; default [w]orktree (Enter), [s] to share"; exit 0; fi
  printf "   [W] isolate in a worktree (default)   [s] share anyway  > " >&2
  # Default-ISOLATE (operator decision 2026-06-19): Enter / empty / anything-but-share
  # → worktree, so isolation is the path of least resistance. Only an explicit [s]
  # shares. A read FAILURE (no tty) still defaults to SHARE — never auto-switch into a
  # worktree without a real answer (ADR 2026-06-16: ask, do not switch silently).
  read -r ans </dev/tty || ans="s"
  case "$ans" in
    s|S|share|SHARE) : ;;   # explicit share → fall through to the share path below
    *)
      wt="$(basename "$CHECKOUT")-wt$$"
      say "   → claude --worktree $wt"
      do_exec --worktree "$wt" "$@" ;;
  esac
fi

# --- Share path (no peer, or you chose share): claim, then run ---
# The lock is written with $$; `exec` preserves the pid, so the lock's pid becomes
# the running claude's pid → later liveness checks on it are accurate. Skipped in
# dry-run so smoke tests have no side effects.
[ -n "$DRYRUN" ] || $PY "$CLAIM" -C "$CHECKOUT" claim --session "$SID" >/dev/null 2>&1 || true
do_exec "$@"
