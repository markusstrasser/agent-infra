#!/usr/bin/env python3
"""$0 in-process contract smoke for OUR MCP servers (corpus_mcp, agent_infra_mcp).

Catches the integration-regression class that has actually bitten this repo —
a tool dropped/renamed, an input schema corrupted, or a read-only/write
annotation flipped on a FastMCP or claude_agent_sdk bump (cf. commits
b08c67e / a9fc9dd / 6cfa894 / d499c9e, all MCP-wiring fixes). These servers
are wired into ~11 projects' .mcp.json, so a silent contract break has wide
blast radius. This runs deterministically: no LLM, no API keys, no network,
sub-second. Wired into `just smoke`.

WHY a plain script and NOT mcp-eval (mcpevals): that framework mandates a real
agent-in-the-loop LLM call per test (anthropic SDK core dep, default
claude-3-5-sonnet, ANTHROPIC_API_KEY secret required, ~$0.05-0.50/server/run,
no offline mode) and targets *behavioral* evals we have no incident history
for. It is also ~6 months stale (last commit 2025-11-19, 23 stars) and the
`pip install mcp-eval` line in its own README is a PyPI name-squat. Our
measured MCP pain is tool-call spin + token bloat (a runtime behavior) and
contract drift — neither needs a live model. This is the native-patterns
answer: pytest/justfile + the servers' own in-process introspection, no dep.
Full evaluation: .scratch/mcp-eval-evaluation-research.md.

Exit 0 = all contracts intact; exit 1 = at least one regression.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Our MCP servers live in scripts/ (this file's dir).
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}")


def check_corpus_mcp() -> list[str]:
    """Contract-check the corpus FastMCP server. Returns a list of failures."""
    fails: list[str] = []
    import corpus_mcp

    mcp = corpus_mcp.create_mcp()  # construct only — lifespan does not run here
    tools = asyncio.run(mcp.list_tools())
    by_name = {t.name: t for t in tools}

    # Minimum tool count (>=, not ==, so adding a tool never breaks the smoke).
    if len(tools) < 6:
        fails.append(f"corpus: expected >=6 tools, got {len(tools)}")

    # Structural integrity per tool: name + description + input schema + a
    # boolean readOnlyHint (the safety annotation agents route on).
    for t in tools:
        if not t.name:
            fails.append("corpus: a tool has an empty name")
        if not getattr(t, "description", None):
            fails.append(f"corpus:{t.name} missing description")
        # FastMCP 3.x FunctionTool exposes the JSON schema as `.parameters`;
        # keep MCP-wire names as forward-compat fallbacks.
        schema = (getattr(t, "parameters", None) or getattr(t, "inputSchema", None)
                  or getattr(t, "input_schema", None))
        if not schema:
            fails.append(f"corpus:{t.name} missing input schema")
        ann = getattr(t, "annotations", None)
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if not isinstance(ro, bool):
            fails.append(f"corpus:{t.name} readOnlyHint is not a bool ({ro!r})")

    # Safety-annotation regression guard: the unambiguous WRITE tool must not
    # be advertised read-only. (corpus_attest is intentionally NOT frozen here —
    # substrate v2 may retire it; we only demand sanity if it is present.)
    for w in ("corpus_ingest", "corpus_attest"):
        t = by_name.get(w)
        if t is not None:
            ann = getattr(t, "annotations", None)
            if getattr(ann, "readOnlyHint", None) is not False:
                fails.append(f"corpus:{w} must be readOnly=False (write tool)")

    # The two most stable documented read tools must stay present.
    for r in ("corpus_lookup", "corpus_graph_query"):
        if r not in by_name:
            fails.append(f"corpus: missing documented read tool {r}")

    if not fails:
        _ok(f"corpus_mcp: {len(tools)} tools, schemas + RO/WRITE annotations intact")
    return fails


def check_agent_infra_mcp() -> list[str]:
    """Contract-check the agent-infra claude_agent_sdk server. Returns failures."""
    fails: list[str] = []
    import agent_infra_mcp as aim

    # Server config shape (create_sdk_mcp_server ran at import — construct OK).
    srv = aim.agent_infra_server
    if not (isinstance(srv, dict) and srv.get("type") == "sdk"
            and srv.get("name") == "agent-infra" and srv.get("instance") is not None):
        fails.append(f"agent_infra: unexpected server config shape: "
                     f"{ {k: type(v).__name__ for k, v in srv.items()} if isinstance(srv, dict) else type(srv).__name__ }")

    # The 5 documented tools must exist as registered SdkMcpTool objects, each
    # with a name + description + input schema. (A decorator/registration break
    # or a renamed tool shows up here.)
    expected = (
        "search_sessions", "get_session", "search_improvement_log",
        "get_hook_metrics", "list_recent_findings",
    )
    found = 0
    for name in expected:
        tool = getattr(aim, name, None)
        if tool is None:
            fails.append(f"agent_infra: missing tool '{name}'")
            continue
        if getattr(tool, "name", None) != name:
            fails.append(f"agent_infra:{name} .name mismatch ({getattr(tool, 'name', None)!r})")
        if not getattr(tool, "description", None):
            fails.append(f"agent_infra:{name} missing description")
        if not getattr(tool, "input_schema", None):
            fails.append(f"agent_infra:{name} missing input_schema")
        found += 1

    if not fails:
        _ok(f"agent_infra_mcp: {found} tools registered, names + schemas intact")
    return fails


def main() -> int:
    print("=== MCP contract smoke (in-process, $0, no LLM) ===")
    fails: list[str] = []
    for label, fn in (("corpus_mcp", check_corpus_mcp),
                      ("agent_infra_mcp", check_agent_infra_mcp)):
        try:
            fails.extend(fn())
        except Exception as exc:  # construction/import failure IS the regression
            _fail(f"{label}: raised {type(exc).__name__}: {exc}")
            fails.append(f"{label}: raised {type(exc).__name__}: {exc}")

    print("---")
    if fails:
        for f in fails:
            _fail(f)
        print(f"{len(fails)} contract failure(s)")
        return 1
    print("OK: all MCP server contracts intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
