#!/usr/bin/env python3
"""Probe skill-loader filesystem assumptions.

This is a deterministic preflight, not a substitute for vendor-specific live
agent tests. It catches the case-sensitive failure class by inspecting stored
directory entries exactly instead of relying on macOS case-insensitive path
resolution.
"""

from __future__ import annotations

import argparse
import json

from common.skill_objects import collect_skill_objects, iter_default_roots
from common.project_registry import SKILL_REPOS


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe skill loader assumptions")
    parser.add_argument("--repo", action="append", choices=list(SKILL_REPOS))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = [
        obj.to_json()
        for obj in collect_skill_objects(iter_default_roots(args.repo), include_planned=False)
        if obj.object_type == "SkillEntrypoint"
    ]
    probes = []
    for row in rows:
        stored = row.get("stored_filename")
        probes.append({
            "object_id": row["object_id"],
            "profile": "canonical-case-sensitive",
            "passed": stored == "SKILL.md",
            "detail": f"stored_filename={stored}",
        })
        probes.append({
            "object_id": row["object_id"],
            "profile": "lowercase-compat-required",
            "passed": stored in {"SKILL.md", "skill.md"},
            "detail": f"stored_filename={stored}",
        })

    failures = [probe for probe in probes if not probe["passed"]]
    result = {"probes": probes, "failures": failures}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for failure in failures:
            print(f"FAIL {failure['profile']} {failure['object_id']}: {failure['detail']}")
        if not failures:
            print("Loader probe OK.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
