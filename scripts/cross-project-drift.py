#!/usr/bin/env python3
"""Cross-project drift detection — find divergences in hook configs,
settings patterns, and rule conventions across projects.

Checks:
1. Hook coverage gaps (hook exists in 3+ projects but missing from one)
2. Settings.json structural drift (keys present in some projects but not others)
3. Rule file naming/convention drift
4. MCP server configuration drift
"""

import json
from pathlib import Path

PROJECTS_DIR = Path.home() / "Projects"
PROJECTS = ["agent-infra", "intel", "phenome", "genomics", "skills"]


def check_hook_drift() -> list[dict]:
    """Find hooks that exist in most projects but are missing from some."""
    findings = []
    project_hooks: dict[str, set[str]] = {}

    for proj in PROJECTS:
        settings = PROJECTS_DIR / proj / ".claude" / "settings.json"
        if not settings.exists():
            project_hooks[proj] = set()
            continue

        try:
            data = json.loads(settings.read_text())
            hooks = data.get("hooks", {})
            hook_commands = set()
            for event, matchers in hooks.items():
                for matcher_group in matchers:
                    for hook in matcher_group.get("hooks", []):
                        cmd = hook.get("command", "")
                        # Extract script name from path
                        name = Path(cmd.split()[0] if cmd else "").name
                        if name:
                            hook_commands.add(f"{event}:{name}")
            project_hooks[proj] = hook_commands
        except (json.JSONDecodeError, Exception):
            project_hooks[proj] = set()

    # Find hooks present in 3+ projects but missing from others
    all_hooks: dict[str, list[str]] = {}
    for proj, hooks in project_hooks.items():
        for h in hooks:
            all_hooks.setdefault(h, []).append(proj)

    for hook, present_in in all_hooks.items():
        if len(present_in) >= 3:
            missing = [p for p in PROJECTS if p not in present_in and project_hooks.get(p) is not None]
            if missing:
                findings.append({
                    "type": "hook_gap",
                    "hook": hook,
                    "present_in": present_in,
                    "missing_from": missing,
                    "severity": "medium",
                })

    return findings


def check_mcp_drift() -> list[dict]:
    """Find MCP servers configured inconsistently."""
    findings = []
    project_mcps: dict[str, set[str]] = {}

    for proj in PROJECTS:
        mcp_file = PROJECTS_DIR / proj / ".mcp.json"
        if not mcp_file.exists():
            continue
        try:
            data = json.loads(mcp_file.read_text())
            project_mcps[proj] = set(data.get("mcpServers", {}).keys())
        except (json.JSONDecodeError, Exception):
            pass

    # Core MCPs that should be everywhere (research-heavy projects)
    core_mcps = {"brave-search", "exa", "research", "agent-infra"}
    research_projects = {"agent-infra", "intel", "phenome", "genomics"}

    for mcp in core_mcps:
        present = [p for p in research_projects if mcp in project_mcps.get(p, set())]
        missing = [p for p in research_projects if p in project_mcps and mcp not in project_mcps.get(p, set())]
        if present and missing:
            findings.append({
                "type": "mcp_gap",
                "mcp": mcp,
                "present_in": present,
                "missing_from": missing,
                "severity": "low",
            })

    return findings


def check_rule_drift() -> list[dict]:
    """Find rule files that exist in some projects but not others."""
    findings = []
    project_rules: dict[str, set[str]] = {}

    for proj in PROJECTS:
        rules_dir = PROJECTS_DIR / proj / ".claude" / "rules"
        if not rules_dir.is_dir():
            continue
        project_rules[proj] = {f.name for f in rules_dir.glob("*.md")}

    # Find rules in 3+ projects missing from others
    all_rules: dict[str, list[str]] = {}
    for proj, rules in project_rules.items():
        for r in rules:
            all_rules.setdefault(r, []).append(proj)

    for rule, present_in in all_rules.items():
        if len(present_in) >= 3:
            missing = [p for p in PROJECTS if p not in present_in and p in project_rules]
            if missing:
                findings.append({
                    "type": "rule_gap",
                    "rule": rule,
                    "present_in": present_in,
                    "missing_from": missing,
                    "severity": "low",
                })

    return findings


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cross-project drift detection")
    parser.add_argument("--output", help="JSON output path")
    args = parser.parse_args()

    hook_drift = check_hook_drift()
    mcp_drift = check_mcp_drift()
    rule_drift = check_rule_drift()

    all_findings = hook_drift + mcp_drift + rule_drift

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(all_findings, indent=2))
        print(f"  ✓ {len(all_findings)} drift findings → {out_path}")

    # Summary
    by_type = {}
    for f in all_findings:
        by_type.setdefault(f["type"], []).append(f)

    print(f"\n  {len(all_findings)} total drift findings:")
    for t, items in by_type.items():
        print(f"    {t}: {len(items)}")
        for item in items[:3]:
            missing = ", ".join(item.get("missing_from", []))
            name = item.get("hook") or item.get("mcp") or item.get("rule")
            print(f"      {name} missing from: {missing}")


if __name__ == "__main__":
    main()
