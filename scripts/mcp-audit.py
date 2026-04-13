"""MCP tool loading overhead audit across projects.

Reads .mcp.json from each project, counts servers, estimates tool/token overhead,
and checks for deferred loading configuration in settings.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.console import con, dim

PROJECTS_DIR = Path.home() / "Projects"

PROJECTS = ["agent-infra", "phenome", "genomics", "intel"]

# Rough estimates — calibrated against observed tool counts in system reminders
TOKENS_PER_TOOL = 200
DEFAULT_TOOLS_PER_SERVER = 10

# Servers where we know the tool count from URLs or documentation
KNOWN_TOOL_COUNTS: dict[str, int] = {
    "exa": 7,  # enumerated in URL params
    "brave-search": 2,  # brave_web_search, brave_local_search
    "context7": 2,  # resolve-library-id, query-docs
    "domains": 1,  # instant domain search
    "scite": 1,  # search_literature
}


def load_mcp_json(path: Path) -> dict:
    """Load .mcp.json, return mcpServers dict or empty."""
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("mcpServers", {})


def estimate_tools(server_name: str) -> int:
    """Estimate tool count for a server."""
    return KNOWN_TOOL_COUNTS.get(server_name, DEFAULT_TOOLS_PER_SERVER)


def main():
    con.header("MCP Tool Loading Audit")

    rows: list[list[str]] = []
    total_servers = 0
    total_tools = 0
    total_tokens = 0

    # Track unique servers across all projects
    all_servers: dict[str, set[str]] = {}  # server_name -> set of projects

    for project in PROJECTS:
        mcp_path = PROJECTS_DIR / project / ".mcp.json"
        servers = load_mcp_json(mcp_path)

        if not servers:
            rows.append([project, "—", "—", "—", "no .mcp.json"])
            continue

        server_names = sorted(servers.keys())
        est_tools = sum(estimate_tools(s) for s in server_names)
        est_tokens = est_tools * TOKENS_PER_TOOL

        total_servers += len(server_names)
        total_tools += est_tools
        total_tokens += est_tokens

        for s in server_names:
            all_servers.setdefault(s, set()).add(project)

        abbrev = ", ".join(server_names[:4])
        if len(server_names) > 4:
            abbrev += f" +{len(server_names) - 4}"

        rows.append([
            project,
            str(len(server_names)),
            f"~{est_tools}",
            f"~{est_tokens:,}",
            abbrev,
        ])

    # Also check global ~/.claude/.mcp.json
    global_mcp = Path.home() / ".claude" / ".mcp.json"
    global_servers = load_mcp_json(global_mcp)
    if global_servers:
        server_names = sorted(global_servers.keys())
        est_tools = sum(estimate_tools(s) for s in server_names)
        est_tokens = est_tools * TOKENS_PER_TOOL
        total_servers += len(server_names)
        total_tools += est_tools
        total_tokens += est_tokens
        abbrev = ", ".join(server_names[:4])
        rows.append(["~global", str(len(server_names)), f"~{est_tools}",
                      f"~{est_tokens:,}", abbrev])
    else:
        rows.append(["~global", "—", "—", "—", "no .mcp.json"])

    con.table(
        ["Project", "Servers", "Est. Tools", "Est. Tokens", "Names"],
        rows,
        widths=[12, 10, 12, 13, 40],
    )

    print()
    con.kv("Total servers (sum)", str(total_servers))
    con.kv("Total est. tools", f"~{total_tools}")
    con.kv("Total est. tokens", f"~{total_tokens:,}")

    # Duplication analysis
    con.header("Server Duplication")
    shared = {s: ps for s, ps in all_servers.items() if len(ps) > 1}
    if shared:
        dup_rows = []
        for s, ps in sorted(shared.items(), key=lambda x: -len(x[1])):
            dup_rows.append([s, str(len(ps)), ", ".join(sorted(ps))])
        con.table(
            ["Server", "Count", "Projects"],
            dup_rows,
            widths=[20, 8, 40],
        )
        unique_servers = len(all_servers)
        con.kv("Unique servers", str(unique_servers))
        con.kv("Deduplicated tools", f"~{sum(estimate_tools(s) for s in all_servers)}")
    else:
        con.ok("No server duplication across projects")

    # Deferred loading check
    con.header("Deferred Loading")
    con.ok("Claude Code has built-in deferred tool loading (ToolSearch)")
    print(f"  {dim('Cannot determine deferred % without runtime inspection')}")
    print(f"  {dim('Deferred tools visible in session as ToolSearch-resolvable names')}")

    # Per-project settings.json hooks summary
    con.header("Settings Hook Counts")
    hook_rows = []
    for project in PROJECTS:
        settings_path = PROJECTS_DIR / project / ".claude" / "settings.json"
        if not settings_path.exists():
            hook_rows.append([project, "—", "no settings.json"])
            continue
        with open(settings_path) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})
        total_hooks = sum(
            sum(len(group.get("hooks", [])) for group in groups)
            for groups in hooks.values()
        )
        events = ", ".join(sorted(hooks.keys()))
        hook_rows.append([project, str(total_hooks), events])

    # Global settings
    global_settings = Path.home() / ".claude" / "settings.json"
    if global_settings.exists():
        with open(global_settings) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})
        total_hooks = sum(
            sum(len(group.get("hooks", [])) for group in groups)
            for groups in hooks.values()
        )
        hook_rows.append(["~global", str(total_hooks), f"{len(hooks)} event types"])

    con.table(
        ["Project", "Hooks", "Events"],
        hook_rows,
        widths=[12, 8, 60],
    )


if __name__ == "__main__":
    main()
