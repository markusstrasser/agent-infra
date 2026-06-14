#!/usr/bin/env bash
# hetzner-idle-watch.sh — flag NON-hutter Hetzner boxes idling on the shared hcloud account.
#
# WHY: hutter/scripts/idle_reaper.sh has a cross-project guard — it lists non-hutter boxes as
# "never touch" and refuses to reap them (it literally names `sbayesrc-validate = genomics`).
# So genomics weight-compute boxes (sbayesrc-*) have NO auto-watcher; two idled 17h once
# (~€16 wasted, 2026-06-14). This is that watcher.
#
# READ-ONLY. Never deletes. Teardown is the operator-gated hetzner-reap.sh.
#   hetzner-idle-watch.sh            print table of non-hutter boxes + age + est €
#   hetzner-idle-watch.sh --notify   + macOS notification if any is up > threshold (launchd uses this)
#
# Env: HETZNER_IDLE_THRESHOLD_HOURS (default 12), HETZNER_IDLE_IGNORE (comma-separated names to skip)
set -u
THRESH=${HETZNER_IDLE_THRESHOLD_HOURS:-12}
IGNORE=${HETZNER_IDLE_IGNORE:-}
ENVF="$HOME/.config/hcloud/env"
[ -f "$ENVF" ] || { echo "no hcloud env ($ENVF) — nothing to check"; exit 0; }
set -a; . "$ENVF"; set +a
notify=0; [ "${1:-}" = "--notify" ] && notify=1

report=$(hcloud server list -o json 2>/dev/null | THRESH="$THRESH" IGNORE="$IGNORE" python3 -c '
import json, os, sys, datetime
thresh = float(os.environ["THRESH"]); ignore = {x for x in os.environ["IGNORE"].split(",") if x}
rate = {"ccx13":0.0600,"ccx23":0.1233,"ccx33":0.2467,"ccx43":0.3489,"ccx53":0.4944,"ccx63":0.7732}
now = datetime.datetime.now(datetime.timezone.utc)
try:
    servers = json.load(sys.stdin)
except Exception:
    servers = []
rows = []
for s in servers:
    name = s["name"]
    if name.startswith("hutter-") or name in ignore:
        continue
    typ = s["server_type"]["name"]
    created = datetime.datetime.fromisoformat(s["created"].replace("Z", "+00:00"))
    age = (now - created).total_seconds() / 3600.0
    rows.append((name, typ, age, age * rate.get(typ, 0.0), age > thresh))
rows.sort(key=lambda r: -r[2])
flagged = [r for r in rows if r[4]]
print("COUNT", len(rows), len(flagged))
for n, t, a, e, f in rows:
    print("ROW", n, t, f"{a:.1f}", f"{e:.2f}", "FLAG" if f else "ok")
if flagged:
    print("MSG", "; ".join(f"{n} {a:.0f}h ~EUR{e:.0f}" for n, t, a, e, f in flagged[:3]))
')

counts=$(printf '%s\n' "$report" | awk '/^COUNT/{print $2, $3}')
total=$(echo "$counts" | awk '{print $1}'); nflag=$(echo "$counts" | awk '{print $2}')

if [ "${total:-0}" = "0" ]; then echo "✓ no non-hutter boxes on the account."; exit 0; fi
printf '%-22s %-7s %8s %9s\n' NAME TYPE AGE-H EST-EUR
printf '%s\n' "$report" | awk '/^ROW/{printf "%-22s %-7s %8s %9s  %s\n",$2,$3,$4,$5,$6}'

if [ "${nflag:-0}" != "0" ]; then
  msg=$(printf '%s\n' "$report" | sed -n 's/^MSG //p')
  echo
  echo "⚠️  $nflag non-hutter box(es) idle > ${THRESH}h — reap: ~/Projects/agent-infra/scripts/hetzner-reap.sh <name>"
  if [ "$notify" = "1" ]; then
    osascript -e "display notification \"$msg\" with title \"Hetzner idle spend\" sound name \"Basso\"" >/dev/null 2>&1 || true
  fi
fi
