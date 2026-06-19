#!/usr/bin/env bash
# Fail if architecture.template.mmd / inventory sources changed but architecture.mmd wasn't regenerated.
# Chained from skills/hooks/pre-commit-guards.sh on agent-infra only.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ "$ROOT" == *agent-infra ]] || exit 0

cd "$ROOT"
STAGED=$(git diff --cached --name-only 2>/dev/null || true)
needs=0
for pat in architecture.template.mmd config/system-kinds.json .claude/rules/orchestrator-tool-names.md ops/launchd/; do
  if echo "$STAGED" | grep -q "$pat"; then needs=1; break; fi
done
[[ "$needs" -eq 1 ]] || exit 0

if ! echo "$STAGED" | grep -q '^architecture\.mmd$'; then
  echo "pre-commit: architecture inputs staged — run: just render-architecture && git add architecture.mmd" >&2
  exit 1
fi

uv run python3 scripts/system_inventory.py --check || {
  echo "pre-commit: architecture.mmd stale vs template+inventory — run: just render-architecture" >&2
  exit 1
}
