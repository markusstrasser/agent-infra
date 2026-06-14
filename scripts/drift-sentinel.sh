#!/usr/bin/env bash
# drift-sentinel.sh — daily zero-API self-monitor.
#
# The autonomy lever (session-end review 2026-06-14 #1): the repo's deterministic
# report-only checks (freshness, orphan-findings, orphan-check, doc-vs-reality)
# previously ran ONLY inside the interactive `/improve maintain` loop — so when
# nobody was looping, drift accumulated unseen. This runs them on a launchd
# cadence and writes a digest the NEXT agent-infra session surfaces at SessionStart.
#
# Decouples DETECTION (autonomous, $0, here) from CONSUMPTION (judged, interactive).
# Writes .claude/drift-digest.md ONLY when something needs attention; removes it
# when all green (no-noise: a stale all-clear digest is itself drift).
#
# Scheduled: com.agent-infra.drift-sentinel (daily). Manual: just drift-sentinel.

set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
DIGEST="$REPO/.claude/drift-digest.md"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

section() {
  # section "Title" "command..." "needs-attention-grep"
  local title="$1" cmd="$2" pat="$3" out
  out="$(eval "$cmd" 2>/dev/null | grep -iE "$pat" || true)"
  if [ -n "$out" ]; then
    printf '\n## %s\n```\n%s\n```\n' "$title" "$out" >> "$TMP"
  fi
}

section "Surveillance freshness (DUE)" \
  "just -f '$REPO/justfile' freshness" "DUE"
section "Orphaned findings (un-harvested)" \
  "uv run python3 '$REPO/scripts/orphan_findings.py'" "un-harvested in [1-9]"
section "Orphaned generators" \
  "uv run python3 '$REPO/scripts/orphan_check.py'" "candidate orphan"
section "Doc-vs-reality drift" \
  "uv run python3 '$REPO/scripts/orient.py' --drift" "✗"
section "Context budget — always-loaded over ceiling" \
  "uv run python3 '$REPO/scripts/context-budget.py' --check" "OVER"
section "Predictions DUE — resolve the verdict (confirmed/refuted)" \
  "uv run python3 '$REPO/scripts/predictions.py' due" "DUE"

if [ -s "$TMP" ]; then
  { printf '# Drift digest — %s\n' "$(date +%Y-%m-%d)"; \
    printf '_Daily self-monitor (drift-sentinel). Triage in the next /improve tick; '; \
    printf 'this file auto-clears when all green._\n'; cat "$TMP"; } > "$DIGEST"
  echo "[drift-sentinel] wrote digest: $(grep -c '^##' "$DIGEST") section(s)"
else
  rm -f "$DIGEST"
  echo "[drift-sentinel] all green — no digest."
fi

# Refresh the Top-N priorities digest (the loop's headline output) so it surfaces
# at SessionStart even on days the conductor is never invoked — the demand-test
# insight (surface where attention already is, don't depend on typing /loop).
uv run python3 "$REPO/scripts/top_priorities.py" --top 10 >/dev/null 2>&1 \
  && echo "[drift-sentinel] refreshed PRIORITIES.md" || true
