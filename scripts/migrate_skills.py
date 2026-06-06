#!/usr/bin/env python3
"""Dry-run skill migration planner from manifest deltas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.skill_objects import collect_skill_objects, iter_default_roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan skill migrations")
    parser.add_argument("--repo", action="append", choices=["skills", "agent-infra", "genomics", "phenome", "intel"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Reserved; currently refuses to mutate")
    args = parser.parse_args()

    if args.execute:
        raise SystemExit("--execute is intentionally not implemented until loader probes and reference closure pass")

    rows = [obj.to_json() for obj in collect_skill_objects(iter_default_roots(args.repo))]
    actions: list[dict] = []
    for row in rows:
        if row.get("object_type") != "SkillEntrypoint":
            continue
        if row.get("stored_filename") and row.get("stored_filename") != "SKILL.md":
            actions.append({
                "action": "normalize_case",
                "object_id": row["object_id"],
                "path": row["path"],
                "from": row["stored_filename"],
                "to": "SKILL.md",
            })
        if row.get("replaced_by"):
            actions.append({
                "action": "alias_lifecycle",
                "object_id": row["object_id"],
                "replaced_by": row["replaced_by"],
                "boundary": row.get("boundary"),
            })

    if args.json:
        print(json.dumps({"actions": actions}, indent=2, sort_keys=True))
    else:
        if not actions:
            print("No migration actions proposed.")
        for action in actions:
            print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
