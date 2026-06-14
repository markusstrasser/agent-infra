#!/usr/bin/env bash
# blindspot-miner.sh — daily standing run of the RSI blindspot miner.
#
# Runs scripts/blindspot_miner.py IN EMB'S ENV (`uv run --project ~/Projects/emb`)
# so the emb-contrastive detection has torch/sentence-transformers without dragging
# them into agent-infra. Writes .claude/blindspot-digest.md (removed when no flags);
# the next agent-infra SessionStart surfaces it via blindspot-surface.sh.
#
# Decouples the RSI detector from the interactive loop (it runs even on no-loop days
# — the whole point: the loop notices its own misses across sessions autonomously).
# Scheduled: com.agent-infra.blindspot-miner (daily 06:50). Manual: just blindspot.
set -uo pipefail
export PATH="/Users/alien/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
EMB="$HOME/Projects/emb"
cd "$REPO"
if [ ! -d "$EMB" ]; then
  echo "[blindspot-miner] emb not found at $EMB — skipping (detection needs it)."
  exit 0
fi
if uv run --project "$EMB" python3 "$REPO/scripts/blindspot_miner.py" --days 7 >/dev/null 2>&1; then
  if [ -f "$REPO/.claude/blindspot-digest.md" ]; then
    echo "[blindspot-miner] wrote digest: $(grep -c '^- ' "$REPO/.claude/blindspot-digest.md") flag(s)"
  else
    echo "[blindspot-miner] no flags — clean window."
  fi
else
  echo "[blindspot-miner] run failed (emb env / model load?) — see logs."
fi
