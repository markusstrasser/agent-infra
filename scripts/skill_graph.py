#!/usr/bin/env python3
"""Emit a workflow -> module/lens graph from skill manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.skill_objects import collect_skill_objects, iter_default_roots, load_manifest


def _rows_from_args(args: argparse.Namespace) -> list[dict]:
    if args.manifest:
        rows: list[dict] = []
        for path in args.manifest:
            rows.extend(load_manifest(path))
        return rows
    return [obj.to_json() for obj in collect_skill_objects(iter_default_roots(args.repo))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build skill object graph")
    parser.add_argument("--repo", action="append", choices=["skills", "agent-infra", "genomics", "phenome", "intel"])
    parser.add_argument("--manifest", action="append", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = _rows_from_args(args)
    graph: dict[str, list[str]] = {}
    orphans: list[str] = []
    packages = {row["object_id"] for row in rows if row.get("object_type") == "SkillEntrypoint"}
    by_package_name = {
        (row.get("project"), row.get("package")): row["object_id"]
        for row in rows
        if row.get("object_type") == "SkillEntrypoint"
    }
    by_skill_name = {
        (row.get("project"), row.get("name")): row["object_id"]
        for row in rows
        if row.get("object_type") == "SkillEntrypoint"
    }

    for row in rows:
        object_id = row["object_id"]
        graph.setdefault(object_id, [])
        for used in row.get("uses", []):
            graph[object_id].append(used)
        if row.get("object_type") in {"ModuleDoc", "LensDoc", "RoleAgentContract"}:
            parent = (
                by_package_name.get((row.get("project"), row.get("package")))
                or by_skill_name.get((row.get("project"), row.get("package")))
            )
            if parent:
                graph.setdefault(parent, []).append(object_id)
            else:
                orphans.append(object_id)

    if args.json:
        print(json.dumps({"graph": graph, "orphans": orphans}, indent=2, sort_keys=True))
    else:
        for source in sorted(graph):
            targets = sorted(set(graph[source]))
            if targets:
                print(source)
                for target in targets:
                    print(f"  -> {target}")
        if orphans:
            print("\nOrphans:")
            for object_id in orphans:
                print(f"  {object_id}")

    return 1 if orphans else 0


if __name__ == "__main__":
    raise SystemExit(main())
