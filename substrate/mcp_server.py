#!/usr/bin/env python3
"""Knowledge substrate MCP server.

Exposes registration, querying, and propagation as agent tools.
Each project gets its own DB at ~/.claude/knowledge/{project}.db.

Configure in .mcp.json:
    "knowledge-substrate": {
        "command": "uv",
        "args": ["run", "--directory", "/Users/alien/Projects/meta",
                 "python3", "substrate/mcp_server.py", "--project", "intel"]
    }
"""

import argparse
import json
import sys
from pathlib import Path

from fastmcp import FastMCP

# Add parent to path for substrate import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from substrate.core import KnowledgeDB

DB_DIR = Path.home() / ".claude" / "knowledge"


def create_server(project: str) -> FastMCP:
    db_path = DB_DIR / f"{project}.db"
    db = KnowledgeDB(db_path)

    # TelemetryMiddleware disabled — fastmcp 3.1.1 passes MiddlewareContext
    # to request_ctx.request in context.py:663, causing AttributeError.
    # Re-enable after fastmcp fixes middleware context propagation.

    mcp = FastMCP(
        f"knowledge-substrate-{project}",
        instructions=f"""Knowledge substrate for {project}. Use these tools to register
assertions, evidence, and artifacts with their dependencies. The substrate tracks
what depends on what — when evidence is invalidated, downstream assertions are
automatically marked stale.

Registration-first workflow: register assertions and evidence BEFORE writing
the markdown narrative. This ensures dependency tracking is complete.

ID conventions: use descriptive kebab-case IDs (e.g., 'hims-revenue-decline-thesis',
'ev-hims-10k-2025', 'memo-hims-deep-dive'). IDs should be greppable and
self-documenting.""",
    )

    @mcp.tool()
    def register_assertion(
        id: str,
        type: str,
        title: str,
        status: str = "active",
        source_file: str | None = None,
        payload: str = "{}",
    ) -> str:
        """Register or update an assertion (claim, thesis, prediction, classification).

        Args:
            id: Unique descriptive ID (kebab-case, e.g., 'hims-overvalued-thesis')
            type: Domain type — thesis, claim, prediction, finding, classification, ...
            title: Human-readable short description
            status: active, verified, stale, invalidated, superseded (default: active)
            source_file: Path to markdown file containing this assertion (relative to project root)
            payload: JSON string with domain-specific fields (confidence, forecast_class, ...)
        """
        db.register_assertion(id, type=type, status=status, title=title,
                              source_file=source_file, payload=json.loads(payload))
        deps = db.dependents(id)
        return f"Registered assertion '{id}'. {len(deps)} dependent(s)."

    @mcp.tool()
    def register_evidence(
        id: str,
        type: str,
        source: str,
        title: str | None = None,
        source_grade: str | None = None,
        payload: str = "{}",
    ) -> str:
        """Register or update a piece of evidence.

        Args:
            id: Unique ID (e.g., 'ev-hims-10k-2025', 'ev-clinvar-VCV000012345')
            type: paper, sec_filing, database, observation, computation, expert, ...
            source: Source reference — doi:..., url:..., file:..., clinvar:..., etc.
            title: Human-readable description
            source_grade: NATO Admiralty grade (e.g., 'A1', 'B2', 'C3') — optional
            payload: JSON string with additional fields
        """
        db.register_evidence(id, type=type, source=source, title=title,
                             source_grade=source_grade, payload=json.loads(payload))
        return f"Registered evidence '{id}'."

    @mcp.tool()
    def register_artifact(
        id: str,
        type: str,
        path: str | None = None,
        title: str | None = None,
        payload: str = "{}",
    ) -> str:
        """Register or update an artifact (memo, report, pipeline output, dataset).

        Args:
            id: Unique ID (e.g., 'memo-hims-deep-dive', 'dataset-sec-10k-2025')
            type: memo, report, pipeline_output, dataset, thesis_check, ...
            path: File path relative to project root
            title: Human-readable description
            payload: JSON string with additional fields
        """
        db.register_artifact(id, type=type, path=path, title=title,
                             payload=json.loads(payload))
        return f"Registered artifact '{id}'."

    @mcp.tool()
    def add_dependency(
        source_id: str,
        target_id: str,
        relation: str,
    ) -> str:
        """Add a dependency relation between two registered objects.

        The source depends on/is supported by the target. When the target is
        marked stale, the source will be marked stale too.

        Args:
            source_id: The dependent object (downstream)
            target_id: The dependency (upstream)
            relation: supported_by, depends_on, derived_from, contradicted_by, supersedes, ...
        """
        db.add_relation(source_id, target_id, relation)
        return f"Added relation: {source_id} —[{relation}]→ {target_id}"

    @mcp.tool()
    def mark_stale(
        object_id: str,
        reason: str | None = None,
    ) -> str:
        """Mark an object and all downstream dependents as stale.

        Use when evidence is retracted, data is updated, or a claim is invalidated.
        Propagates through dependency edges up to 5 levels deep.

        Args:
            object_id: ID of the object to mark stale
            reason: Why this is being marked stale (stored in changelog)
        """
        staled = db.mark_stale(object_id, reason=reason)
        if not staled:
            return f"Object '{object_id}' not found or already stale."
        result = f"Marked {len(staled)} object(s) stale:\n"
        for s in staled:
            obj = db.get(s)
            if obj:
                result += f"  [{obj['_type']}] {s} — {obj.get('title', '(no title)')}\n"
        return result

    @mcp.tool()
    def query_dependents(object_id: str) -> str:
        """Find all objects that directly depend on this one.

        Args:
            object_id: ID of the upstream object
        """
        deps = db.dependents(object_id)
        if not deps:
            return f"No dependents of '{object_id}'."
        result = f"{len(deps)} dependent(s) of '{object_id}':\n"
        for d in deps:
            result += f"  [{d['type']}] {d['id']} via {d['via']} ({d.get('relation', d.get('derivation_id', ''))})\n"
        return result

    @mcp.tool()
    def query_stale() -> str:
        """List all objects currently marked stale. Use to find what needs review."""
        items = db.stale_objects()
        if not items:
            return "No stale objects."
        result = f"{len(items)} stale object(s):\n"
        for item in items:
            result += f"  [{item['type']}] {item['id']} — {item.get('title', '(no title)')} (updated: {item['updated_at']})\n"
        return result

    @mcp.tool()
    def query_object(object_id: str) -> str:
        """Get full details of any registered object.

        Args:
            object_id: ID of the object to retrieve
        """
        obj = db.get(object_id)
        if not obj:
            return f"Not found: '{object_id}'"
        return json.dumps(obj, indent=2)

    @mcp.tool()
    def substrate_stats() -> str:
        """Show summary statistics for the knowledge substrate."""
        s = db.stats()
        result = f"Knowledge substrate ({project}):\n"
        for k, v in s.items():
            result += f"  {k}: {v}\n"
        return result

    @mcp.tool()
    def recent_changes(limit: int = 20) -> str:
        """Show recent changelog entries.

        Args:
            limit: Max entries to show (default 20)
        """
        entries = db.recent_changes(limit)
        if not entries:
            return "No changes recorded."
        result = f"Recent changes (last {len(entries)}):\n"
        for e in entries:
            ts = e["timestamp"][:16]
            result += f"  {ts}  {e['action']:20s}  [{e['object_type']}] {e['object_id']}\n"
            if e.get("reason"):
                result += f"           reason: {e['reason']}\n"
        return result

    @mcp.tool()
    def register_batch(
        assertions: str = "[]",
        evidence: str = "[]",
        dependencies: str = "[]",
    ) -> str:
        """Register multiple assertions, evidence, and dependencies in one call.

        Accepts JSON arrays. Executes all registrations, then all dependencies.
        Use this instead of calling register_assertion/evidence/add_dependency
        individually when you have multiple items to register.

        Args:
            assertions: JSON array of {id, type, title, status?, source_file?, payload?}
            evidence: JSON array of {id, type, source, title?, source_grade?, payload?}
            dependencies: JSON array of {source_id, target_id, relation}
        """
        a_list = json.loads(assertions)
        e_list = json.loads(evidence)
        d_list = json.loads(dependencies)
        counts = {"assertions": 0, "evidence": 0, "dependencies": 0}
        for a in a_list:
            db.register_assertion(
                a["id"], type=a["type"], title=a["title"],
                status=a.get("status", "active"),
                source_file=a.get("source_file"),
                payload=a.get("payload", {}),
            )
            counts["assertions"] += 1
        for e in e_list:
            db.register_evidence(
                e["id"], type=e["type"], source=e["source"],
                title=e.get("title"),
                source_grade=e.get("source_grade"),
                payload=e.get("payload", {}),
            )
            counts["evidence"] += 1
        for d in d_list:
            db.add_relation(d["source_id"], d["target_id"], d["relation"])
            counts["dependencies"] += 1
        return (
            f"Batch registered: {counts['assertions']} assertions, "
            f"{counts['evidence']} evidence, {counts['dependencies']} dependencies"
        )

    @mcp.tool()
    def reflect(query: str, max_results: int = 20) -> str:
        """Search the substrate and synthesize an answer using an LLM (Haiku).

        Recalls matching objects, expands 1-hop relations, then uses Claude Haiku
        to synthesize an answer with citations to object IDs. Falls back to raw
        context if the API is unavailable.

        Args:
            query: Natural language question about the knowledge substrate
            max_results: Max objects to recall before graph expansion (default 20)
        """
        result = db.reflect(query, max_results=max_results)
        output = result.text
        output += f"\n\n--- Metadata ---"
        output += f"\nRecalled: {len(result.recalled_ids)} | Cited: {result.cited_ids}"
        if result.hallucinated_ids:
            output += f"\nHallucinated IDs: {result.hallucinated_ids}"
        output += f"\nTokens: {result.input_tokens} in / {result.output_tokens} out"
        return output

    @mcp.tool()
    def search_objects(query: str, max_results: int = 20) -> str:
        """Search objects in the substrate by keyword matching.

        Scans assertions, evidence, and artifacts. Scores by term matches
        in id, title, type, and payload fields. Excludes stale objects.

        Args:
            query: Search terms (space-separated, matched against object fields)
            max_results: Maximum results to return (default 20)
        """
        results = db.search_objects(query, max_results=max_results)
        if not results:
            return f"No results for: {query}"
        output = f"{len(results)} result(s) for '{query}':\n"
        for obj in results:
            score = obj.get("_score", 0)
            output += f"  [{obj['_type']}] {obj['id']} (score={score}) — {obj.get('title') or '(no title)'}\n"
        return output

    @mcp.tool()
    def provenance_chain(object_id: str, max_depth: int = 10) -> str:
        """Trace the full downstream provenance tree from an object.

        Uses recursive CTE to follow relations transitively: what objects
        does this one feed into / support?

        Args:
            object_id: Starting object ID
            max_depth: Maximum traversal depth (default 10)
        """
        chain = db.provenance_chain(object_id, max_depth=max_depth)
        if not chain:
            return f"No downstream provenance for '{object_id}'."
        output = f"Provenance chain from '{object_id}' ({len(chain)} objects):\n"
        for item in chain:
            indent = "  " * item["depth"]
            output += f"{indent}[{item['type']}] {item['id']} via {item['relation']}\n"
        return output

    @mcp.tool()
    def impact_radius(object_id: str, max_depth: int = 5) -> str:
        """Trace the full upstream impact radius of an object.

        Uses recursive CTE to follow relations transitively: what does
        this object depend on?

        Args:
            object_id: Starting object ID
            max_depth: Maximum traversal depth (default 5)
        """
        chain = db.impact_radius(object_id, max_depth=max_depth)
        if not chain:
            return f"No upstream impact for '{object_id}'."
        output = f"Impact radius of '{object_id}' ({len(chain)} objects):\n"
        for item in chain:
            indent = "  " * item["depth"]
            output += f"{indent}[{item['type']}] {item['id']} via {item['relation']}\n"
        return output

    @mcp.tool()
    def query_shared_evidence(object_id: str) -> str:
        """Find other assertions that share evidence with this object.

        Discovers objects linked to the same evidence targets via
        supported_by, depends_on, or derived_from relations.

        Args:
            object_id: ID of the assertion to check
        """
        shared = db.shared_evidence(object_id)
        if not shared:
            return f"No shared evidence for '{object_id}'."
        output = f"Assertions sharing evidence with '{object_id}':\n"
        for item in shared:
            output += f"  [{item['type']}] {item['id']} — shared: {item['shared_evidence_id']} ({item['relation']})\n"
        return output

    @mcp.tool()
    def query_contradictions(object_id: str) -> str:
        """Find assertions linked via contradicted_by relations.

        Returns objects that contradict or are contradicted by this object.

        Args:
            object_id: ID of the object to check
        """
        contras = db.contradictory_assertions(object_id)
        if not contras:
            return f"No contradictions for '{object_id}'."
        output = f"Contradictions involving '{object_id}':\n"
        for item in contras:
            output += f"  [{item['type']}] {item['id']} ({item['direction']})\n"
        return output

    @mcp.tool()
    def query_orphans() -> str:
        """Find objects with zero relations -- not connected to any other object.

        Checks assertions, evidence, and artifacts that have no relations
        and are not part of any derivation.
        """
        orphan_list = db.orphans()
        if not orphan_list:
            return "No orphan objects."
        output = f"{len(orphan_list)} orphan(s):\n"
        for item in orphan_list:
            output += f"  [{item['_type']}] {item['id']} ({item['type']}, {item['status']}) — {item.get('title') or '(no title)'}\n"
        return output

    return mcp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=None,
                        help="Project name (determines DB path). Default: cwd basename.")
    args = parser.parse_args()

    project = args.project or Path.cwd().name
    server = create_server(project)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
