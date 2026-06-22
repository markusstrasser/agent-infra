#!/bin/bash
# PostToolUse:Read — decision/ADR currency WHITELIST (advisory injection).
#
# THE GENERAL PREVENTION (not a one-off): fires whenever an agent reads ANY
# decision/ADR whose status is NOT current/accepted, warning it not to execute
# that decision as ratified without confirming it's the CURRENT decision on the
# spine. Whitelist semantics — only known-current statuses are silent; everything
# else (proposed/superseded/draft/dropped/retired/blocked) advises.
#
# Keys on the EXISTING status field (YAML `status:` OR prose `**Status:**`) — NO
# edge-graph, NO parser-migration, works on substrate ADRs that lack frontmatter.
# Advisory only (additionalContext, never exit 2): a hard block / fail-closed is
# the PROMOTION target after measuring, not the launch posture (v0.4.3: a red
# blocking gate is worse than advisory).
#
# Once per (session,file) to stay low-noise. agent-infra-first; global propagation
# is sign-off-gated (invariant #4). Decision:
# decisions/2026-06-21-decision-currency-whitelist.md
set -euo pipefail
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)
[ -z "$FILE" ] && exit 0
# Decision/ADR docs only.
case "$FILE" in
  */decisions/*.md|*/docs/decisions/*.md) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0
# Skip non-decision docs in those dirs.
case "${FILE##*/}" in .template.md|README.md|index.md|REFRAMINGS.md|deferred-and-open.md|glossary.md) exit 0 ;; esac

# Extract status: YAML frontmatter `status:` first, else prose `**Status:** X`.
STATUS=$(awk '
  /^---[[:space:]]*$/ { fm = !fm; next }
  fm && tolower($0) ~ /^status:/ { sub(/^[Ss]tatus:[[:space:]]*/, ""); print tolower($0); exit }
' "$FILE" 2>/dev/null || true)
if [ -z "$STATUS" ]; then
  STATUS=$(grep -m1 -oiE '\*\*status:\*\*[[:space:]]*[a-z-]+' "$FILE" 2>/dev/null \
    | sed -E 's/.*\*\*[Ss]tatus:\*\*[[:space:]]*//' | tr '[:upper:]' '[:lower:]' || true)
fi
STATUS=$(printf '%s' "$STATUS" | tr -d '`*. ' | tr -cd '[:alnum:]-')
[ -z "$STATUS" ] && exit 0

# Whitelist: only these are current/executable → silent.
case "$STATUS" in
  accepted|active|current|implemented|done|ratified) exit 0 ;;
esac

# Non-current → advise once per (session,file).
TRACKER="/tmp/claude-decision-currency-${PPID}"
grep -qxF "$FILE" "$TRACKER" 2>/dev/null && exit 0
printf '%s\n' "$FILE" >> "$TRACKER"

base="${FILE##*/}"
printf '{"additionalContext": "⚠ Decision currency: %s has status=%s (not accepted/current). Read/discuss freely, but do NOT execute its plan as a ratified decision without confirming it is the CURRENT decision on this spine — check for a superseding ADR or a REFRAMINGS entry. (decisions/2026-06-21-decision-currency-whitelist.md)"}\n' "$base" "$STATUS"
exit 0
