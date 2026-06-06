#!/usr/bin/env python3
"""Report always-loaded skill description budget by repo."""

from __future__ import annotations

import argparse
import json

from common.skill_objects import collect_skill_objects, iter_default_roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill description budget")
    parser.add_argument("--repo", action="append", choices=["skills", "agent-infra", "genomics", "phenome", "intel"])
    parser.add_argument("--max-description", type=int, default=1024)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = [obj.to_json() for obj in collect_skill_objects(iter_default_roots(args.repo), include_planned=False)]
    by_project: dict[str, dict] = {}
    for row in rows:
        if row.get("object_type") != "SkillEntrypoint":
            continue
        desc = row.get("description") or ""
        project = row["project"]
        bucket = by_project.setdefault(project, {"count": 0, "chars": 0, "over_budget": []})
        bucket["count"] += 1
        bucket["chars"] += len(desc)
        if len(desc) > args.max_description:
            bucket["over_budget"].append({"name": row["name"], "chars": len(desc)})

    if args.json:
        print(json.dumps(by_project, indent=2, sort_keys=True))
    else:
        for project, data in sorted(by_project.items()):
            print(f"{project}: {data['count']} descriptions, {data['chars']} chars")
            for item in data["over_budget"]:
                print(f"  over budget: {item['name']} ({item['chars']} chars)")

    return 1 if any(data["over_budget"] for data in by_project.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
