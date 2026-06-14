#!/usr/bin/env bash
# hetzner-reap.sh — operator-gated teardown of ONE non-hutter Hetzner box (snapshot-then-delete).
#
# Mirrors hutter/scripts/idle_reaper.sh's safety, but for the cross-project (genomics) boxes the
# hutter reaper refuses to touch. Snapshots the box (preserves everything, recreatable) BEFORE
# deleting, and only deletes if the snapshot succeeded.
#
#   hetzner-reap.sh <name>                              DRY-RUN — show box + plan (default, safe)
#   BUDGET_APPROVED=1 hetzner-reap.sh <name>            snapshot + delete
#   BUDGET_APPROVED=1 hetzner-reap.sh <name> --no-snapshot   delete WITHOUT snapshot (already captured)
#
# REFUSES any hutter-* box — those are the other fleet (use hutter/scripts/idle_reaper.sh).
# Gating is BUDGET_APPROVED=1 (env var, not a flag) per the destructive-script-gating convention.
set -u
NAME="${1:-}"
[ -z "$NAME" ] && { echo "usage: [BUDGET_APPROVED=1] hetzner-reap.sh <name> [--no-snapshot]"; exit 2; }
case "$NAME" in hutter-*) echo "REFUSED: '$NAME' is a hutter fleet box — use hutter/scripts/idle_reaper.sh"; exit 1;; esac
snapshot=1; [ "${2:-}" = "--no-snapshot" ] && snapshot=0
ENVF="$HOME/.config/hcloud/env"; [ -f "$ENVF" ] || { echo "no hcloud env ($ENVF)"; exit 1; }
set -a; . "$ENVF"; set +a

id=$(hcloud server list -o json 2>/dev/null | NAME="$NAME" python3 -c 'import json,os,sys; print(next((str(s["id"]) for s in json.load(sys.stdin) if s["name"]==os.environ["NAME"]), ""))')
[ -z "$id" ] && { echo "no server named '$NAME' on the account"; exit 1; }
echo "target: $NAME (id $id)  snapshot=$snapshot"

if [ -z "${BUDGET_APPROVED:-}" ]; then
  echo "DRY-RUN — would:"
  [ "$snapshot" = "1" ] && echo "  1. hcloud server create-image --type snapshot $id"
  echo "  2. hcloud server delete $id"
  echo "Re-run with BUDGET_APPROVED=1 to execute. (Capture any SSD-bound deliverables first.)"
  exit 0
fi

if [ "$snapshot" = "1" ]; then
  echo "snapshotting $NAME ..."
  hcloud server create-image --type snapshot --description "reap-$NAME-$(date -u +%Y%m%dT%H%M%SZ)" "$id" \
    || { echo "snapshot FAILED — aborting, box NOT deleted"; exit 1; }
fi
echo "deleting $NAME ..."
hcloud server delete "$id"
