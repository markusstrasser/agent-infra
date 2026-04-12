#!/bin/bash
# PostToolUse:Edit|Write — advisory freshness check for claim-bound files.
#
# Reads claim_bench.toml from the project root, checks if the edited file
# is bound to any claims, and warns if any bound claims are stale.
#
# Install: add to project .claude/settings.json:
# {"event":"PostToolUse","pattern":"Edit|Write",
#  "command":"~/Projects/agent-infra/claim_bench/hooks/freshness_advisory.sh",
#  "timeout":10000}

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))
" 2>/dev/null) || exit 0

[ -z "$FILE_PATH" ] && exit 0

# Find project root (walk up to find claim_bench.toml)
DIR=$(dirname "$FILE_PATH")
CONFIG=""
while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/claim_bench.toml" ]; then
        CONFIG="$DIR/claim_bench.toml"
        break
    fi
    DIR=$(dirname "$DIR")
done

[ -z "$CONFIG" ] && exit 0

# Run the freshness check
exec python3 - "$FILE_PATH" "$CONFIG" <<'PYTHON'
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

file_path = sys.argv[1]
config_path = Path(sys.argv[2])
project_root = config_path.parent

# Parse TOML (minimal — stdlib tomllib in 3.11+)
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)

config = tomllib.loads(config_path.read_text())
cb = config.get("claim_bench", {})

bindings_path = project_root / cb.get("bindings", "config/claim_bindings.json")
registry_path = project_root / cb.get("registry", "config/claim_registry.json")
vledger_path_str = cb.get("verification_ledger", "")
vledger_path = project_root / vledger_path_str if vledger_path_str else None

if not bindings_path.exists() or not registry_path.exists():
    sys.exit(0)

# Optional: load verification_ledger for date lookups (genomics pattern)
vledger = {}
if vledger_path and vledger_path.exists():
    vledger = json.loads(vledger_path.read_text())
    vledger.pop("_meta", None)

# Load bindings — find claims bound to the edited file
bindings_data = json.loads(bindings_path.read_text())
bindings_list = bindings_data.get("bindings", bindings_data) if isinstance(bindings_data, dict) else bindings_data
if isinstance(bindings_list, dict):
    # flat dict keyed by index
    bindings_list = list(bindings_list.values())

# Normalize file_path to be relative to project root
try:
    rel_path = str(Path(file_path).resolve().relative_to(project_root.resolve()))
except ValueError:
    rel_path = file_path

bound_claim_ids = set()
for b in bindings_list:
    if not isinstance(b, dict):
        continue
    bp = b.get("file_path", "")
    if bp and (rel_path.endswith(bp) or bp.endswith(rel_path) or Path(bp).name == Path(rel_path).name):
        cid = b.get("claim_id", "")
        if cid:
            bound_claim_ids.add(cid)

if not bound_claim_ids:
    sys.exit(0)

# Load registry — check freshness
registry_data = json.loads(registry_path.read_text())
claims = registry_data.get("claims", [])

ttl_defaults = cb.get("ttl", {})
default_ttl = ttl_defaults.get("database", 90)
now = datetime.now(timezone.utc)

stale = []
for claim in claims:
    cid = claim.get("claim_id", "")
    if cid not in bound_claim_ids:
        continue

    verified_at_str = claim.get("verified_at") or claim.get("verification_date", "")

    # Fallback: try verification_ledger by extracting rsID from claim_id
    if not verified_at_str and vledger:
        # Try claim_id parts as ledger keys (e.g., "variant_registry.rs123.coords" → "rs123")
        for part in cid.split("."):
            if part in vledger:
                facets = vledger[part]
                if isinstance(facets, dict):
                    dates = [f.get("date", "") for f in facets.values() if isinstance(f, dict) and f.get("date")]
                    if dates:
                        verified_at_str = max(dates)  # most recent facet date
                break

    if not verified_at_str:
        stale.append((cid, "never verified"))
        continue

    try:
        verified_at = datetime.strptime(verified_at_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        stale.append((cid, f"unparseable date: {verified_at_str}"))
        continue

    ttl = default_ttl
    age_days = (now - verified_at).days
    if age_days > ttl:
        stale.append((cid, f"verified {verified_at_str[:10]} ({age_days}d ago, TTL {ttl}d)"))

if not stale:
    sys.exit(0)

# Emit advisory
lines = [f"Stale claims bound to {Path(rel_path).name}:"]
for cid, reason in stale[:8]:
    lines.append(f"  {cid} — {reason}")
if len(stale) > 8:
    lines.append(f"  ... and {len(stale) - 8} more")
lines.append("Run: /bio-verify " + rel_path)

msg = "\\n".join(lines)
print(json.dumps({"additionalContext": msg}))
PYTHON
