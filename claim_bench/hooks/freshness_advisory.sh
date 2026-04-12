#!/bin/bash
# PostToolUse:Edit|Write — advisory freshness check for claim-bound files.
#
# Reads claim_bench.toml from the project root, checks if the edited file
# is bound to any claims, and warns if any bound claims are stale.
# Tier-aware: reads epistemic_adapter.json and adjusts warnings by tier.
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
from datetime import datetime, timezone
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

# Load verification_ledger for date lookups and source freshness
vledger = {}
vledger_meta = {}
if vledger_path and vledger_path.exists():
    vledger_raw = json.loads(vledger_path.read_text())
    vledger_meta = vledger_raw.pop("_meta", {})
    vledger = vledger_raw

# Load epistemic adapter if available
adapter = None
adapter_paths = [
    project_root / "config" / "epistemic_adapters" / "genomics.json",
    project_root / "config" / "epistemic_adapter.json",
]
for ap in adapter_paths:
    if ap.exists():
        adapter = json.loads(ap.read_text())
        break

# Load bindings — find claims bound to the edited file
bindings_data = json.loads(bindings_path.read_text())
bindings_list = bindings_data.get("bindings", bindings_data) if isinstance(bindings_data, dict) else bindings_data
if isinstance(bindings_list, dict):
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

# Source freshness check (from _meta.sources)
sources_meta = vledger_meta.get("sources", {})
stale_sources = []
for src_name, src_info in sources_meta.items():
    checked = src_info.get("release_checked", "")
    cadence = src_info.get("check_cadence_days", 90)
    if checked:
        try:
            checked_dt = datetime.strptime(checked[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - checked_dt).days > cadence:
                stale_sources.append(src_name)
        except ValueError:
            pass

issues = []
for claim in claims:
    cid = claim.get("claim_id", "")
    if cid not in bound_claim_ids:
        continue

    tier = claim.get("confidence_tier")
    status = claim.get("verification_status", "unknown")

    # Tier-aware advisory logic
    # Refuted: always block
    if status == "refuted":
        issues.append(("block", cid, "Refuted claim — do not use", tier))
        continue

    # Conflict: always warn
    if claim.get("conflict"):
        issues.append(("warn", cid, "Conflicting evidence — resolve before using", tier))
        continue

    # Unknown/asserted: always warn
    if status in ("unknown", "asserted") or tier == 0:
        issues.append(("warn", cid, "Unverified claim", tier))
        continue

    # Tier 3: no warning unless a source in stale_sources
    if tier == 3:
        # Only warn if a source this claim depends on has new data
        claim_sources = claim.get("source_ids", [])
        relevant_stale = [s for s in stale_sources if any(s in sid for sid in claim_sources)]
        if relevant_stale:
            issues.append(("info", cid, f"T3, source update available: {', '.join(relevant_stale)}", tier))
        continue

    # Tier 2: warn if source reports new data
    if tier == 2:
        if stale_sources:
            issues.append(("info", cid, f"T2, sources may have new data: {', '.join(stale_sources[:2])}", tier))
        continue

    # Tier 1: warn if past TTL
    verified_at_str = claim.get("verified_at") or claim.get("verification_date", "")

    # Fallback: try verification_ledger
    if not verified_at_str and vledger:
        for part in cid.split("."):
            if part in vledger:
                facets = vledger[part]
                if isinstance(facets, dict):
                    dates = [f.get("date", "") for f in facets.values() if isinstance(f, dict) and f.get("date")]
                    if dates:
                        verified_at_str = max(dates)
                break

    if not verified_at_str:
        issues.append(("warn", cid, "T1, never verified — run /bio-verify", tier))
        continue

    try:
        verified_at = datetime.strptime(verified_at_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        issues.append(("warn", cid, f"T1, unparseable date: {verified_at_str}", tier))
        continue

    # Use adapter cadence if available, else default TTL
    ttl = default_ttl
    if adapter and "cadence" in adapter and isinstance(adapter["cadence"], dict):
        # Use the shortest relevant cadence
        cadences = list(adapter["cadence"].values())
        if cadences:
            ttl = min(cadences)

    age_days = (now - verified_at).days
    if age_days > ttl:
        issues.append(("warn", cid, f"T1, stale {age_days}d — run /bio-verify", tier))

if not issues:
    sys.exit(0)

# Emit advisory with tier-appropriate symbols
symbols = {"block": "\U0001f6d1", "warn": "\u26a0\ufe0f", "info": "\u2139\ufe0f"}
lines = [f"Claim freshness check for {Path(rel_path).name}:"]
for severity, cid, reason, tier in issues[:8]:
    sym = symbols.get(severity, "\u26a0\ufe0f")
    tier_label = f"[T{tier}]" if tier is not None else ""
    lines.append(f"  {sym} {tier_label} {cid} — {reason}")
if len(issues) > 8:
    lines.append(f"  ... and {len(issues) - 8} more")

# Append action suggestion
has_blocks = any(s == "block" for s, _, _, _ in issues)
if has_blocks:
    lines.append("BLOCKED: refuted claims detected. Remove or replace before proceeding.")
else:
    lines.append("Run: /bio-verify " + rel_path)

msg = "\\n".join(lines)
print(json.dumps({"additionalContext": msg}))
PYTHON
