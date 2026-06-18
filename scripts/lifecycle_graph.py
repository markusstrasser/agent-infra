#!/usr/bin/env python3
"""Rederivable RSI-lifecycle neighborhood graph (Phase C).

A read-only, *rederivable* graph over the harness-lifecycle artifacts. There is
NO disk DB and NO persistent store: nodes + edges are built fresh in-process on
every call (the ephemeral `:memory:` discipline of `scripts/gov.py:build_projection`
— prove we CAN join, keep nothing). Git/markdown stays authoritative.

Nodes come from THREE sources (the resolver MUST span all three — a
decisions-only resolver resolves only ~25% of edge targets):
  (1) decisions/*.md     → node id = frontmatter `id:` (fallback: filename stem)
  (2) research/*.md      → node id = filename stem
  (3) predictions.jsonl  → node id = the row's `id`

Edges come from each decision's frontmatter `relations:` block (`- type:` /
`target:`). Every edge type is normalized THROUGH the canonical vocabulary
(`scripts/lifecycle_relations.json`, Phase A — LOADED, never restated here):
  * fold[type] → canonical[type].to; if fold[type].invert, SWAP subject/target
    (`A superseded_by B`  ==>  edge `B supersedes A`). Correctness requirement.
  * canonical[type].traversable == false (i.e. `relates_to`) → the edge goes in a
    SEPARATE weak / non-traversable bucket, never in the graph used for bundling.
  * `target` is resolved against the 3 node sources; unresolved => `dangling`
    (recorded, never crashes). The improvement-log→decision join is known-sparse
    (~25%) and ACCEPTED — resolution rate is NOT a gate.

Predictions contribute best-effort `commit` edges (a prediction's `commit` field,
when it names a node, is a weak provenance edge). improvement-log.md
`[>] superseded-by <id>` / `[~]` lines are BEST-EFFORT only, never a gate.

CLI:
  lifecycle_graph.py --build          # node counts (per source) + edge counts
  lifecycle_graph.py <node-id>        # node's neighborhood (traversable + weak)
  lifecycle_graph.py <node-id> --json # machine-readable neighborhood
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VOCAB_PATH = REPO / "scripts" / "lifecycle_relations.json"
DECISIONS = REPO / "decisions"
RESEARCH = REPO / "research"
PREDICTIONS = REPO / "predictions.jsonl"
IMPROVEMENT_LOG = REPO / "improvement-log.md"


# ── Vocabulary (Phase A — LOAD, never restate) ─────────────────────────────────
def load_vocab() -> dict:
    return json.loads(VOCAB_PATH.read_text())


def normalize_type(rtype: str, vocab: dict) -> tuple[str, bool, bool]:
    """Resolve a raw relation string to (canonical_type, invert, traversable).

    A fold key maps to its canonical target and carries the invert flag. An
    already-canonical type maps to itself (invert=False). An UNKNOWN string is
    returned as-is, non-traversable, so a vocab gap is recorded — not crashed on
    (the drift-test in test_lifecycle_relations.py is the hard gate on unknowns).
    """
    canonical = vocab["canonical"]
    fold = vocab["fold"]
    invert = False
    if rtype in fold:
        invert = bool(fold[rtype].get("invert", False))
        rtype = fold[rtype]["to"]
    if rtype in canonical:
        # `traversable` absent defaults True (per the vocab _doc convention).
        traversable = canonical[rtype].get("traversable", True)
        return rtype, invert, bool(traversable)
    # Unknown: not in canonical or fold — keep it visible but out of traversal.
    return rtype, invert, False


# ── Frontmatter / relations parsing (mirror Phase A's line-based parser) ────────
def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two '---'), or ''."""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def _frontmatter_id(fm: str) -> str | None:
    """The top-level `id:` scalar, if present."""
    for raw in fm.splitlines():
        m = re.match(r"^id:\s*(\S+)", raw)
        if m:
            return m.group(1)
    return None


def parse_relations(fm: str) -> list[dict]:
    """Extract `{type, target}` pairs from a `relations:` block.

    Line-based (not full YAML) on purpose — same rationale as Phase A's
    `_relation_types`: it skips commented template lines and survives
    malformed/alternative frontmatter that a strict YAML parse would crash on.
    A `- type:` opens an item; the next `target:` under it fills the pair.
    """
    out: list[dict] = []
    in_block = False
    cur: dict | None = None
    for raw in fm.splitlines():
        line = raw.rstrip()
        if re.match(r"^relations:", line):
            in_block = True
            continue
        if not in_block:
            continue
        # A new top-level key (no leading whitespace, has a colon) ends the block.
        if line and not line[0].isspace() and re.match(r"^\S+:", line):
            break
        mt = re.match(r"^\s*-\s*type:\s*(\S+)", line)
        if mt:
            if cur is not None:
                out.append(cur)
            cur = {"type": mt.group(1), "target": None}
            continue
        mtarget = re.match(r"^\s*target:\s*(\S+)", line)
        if mtarget and cur is not None:
            cur["target"] = mtarget.group(1)
    if cur is not None:
        out.append(cur)
    return out


# ── Node collection (THREE sources — resolver spans all three) ─────────────────
def collect_nodes() -> dict[str, dict]:
    """node_id -> {source, path}. Decisions keyed by frontmatter id (fallback
    stem); research by stem; predictions by row id."""
    nodes: dict[str, dict] = {}
    for f in sorted(DECISIONS.glob("*.md")):
        if f.name.startswith("."):  # .template.md
            continue
        nid = _frontmatter_id(_frontmatter(f.read_text())) or f.stem
        nodes[nid] = {"source": "decision", "path": str(f.relative_to(REPO))}
    for f in sorted(RESEARCH.glob("*.md")):
        if f.name.startswith("."):
            continue
        nodes.setdefault(f.stem, {"source": "research", "path": str(f.relative_to(REPO))})
    if PREDICTIONS.exists():
        for line in PREDICTIONS.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = row.get("id")
            if pid:
                nodes.setdefault(pid, {"source": "prediction",
                                       "commit": row.get("commit", "")})
    return nodes


def _node_counts(nodes: dict[str, dict]) -> dict[str, int]:
    c = {"decision": 0, "research": 0, "prediction": 0}
    for v in nodes.values():
        c[v["source"]] = c.get(v["source"], 0) + 1
    return c


# ── Edge assembly ──────────────────────────────────────────────────────────────
def collect_edges(nodes: dict[str, dict], vocab: dict) -> dict:
    """Build the traversable + weak edge buckets from decision relations and
    best-effort prediction `commit` edges.

    Each edge: {subject, type (canonical), target, resolved, source}.
    `resolved` False => dangling target (recorded, not fatal).
    """
    traversable: list[dict] = []
    weak: list[dict] = []
    dangling: list[dict] = []
    unknown_strings: dict[str, list[str]] = {}

    for f in sorted(DECISIONS.glob("*.md")):
        if f.name.startswith("."):
            continue
        fm = _frontmatter(f.read_text())
        if not fm:
            continue
        subject = _frontmatter_id(fm) or f.stem
        for rel in parse_relations(fm):
            raw_type, target = rel["type"], rel["target"]
            if target is None:
                continue
            canon, invert, traversable_flag = normalize_type(raw_type, vocab)
            # invert SWAPS subject/target (A superseded_by B => B supersedes A).
            subj, tgt = (target, subject) if invert else (subject, target)
            resolved = tgt in nodes
            edge = {
                "subject": subj,
                "type": canon,
                "raw_type": raw_type,
                "target": tgt,
                "resolved": resolved,
                "source": "decision-relation",
                "from_file": str(f.relative_to(REPO)),
            }
            # Record unknowns (not in canonical/fold) for the manifest.
            if canon not in vocab["canonical"]:
                unknown_strings.setdefault(raw_type, []).append(f.name)
            if not resolved:
                dangling.append(edge)
            if traversable_flag:
                traversable.append(edge)
            else:
                weak.append(edge)

    # Best-effort prediction → commit/node edges (weak provenance).
    for nid, meta in nodes.items():
        if meta.get("source") != "prediction":
            continue
        commit = (meta.get("commit") or "").strip()
        if commit and commit in nodes:
            weak.append({
                "subject": nid,
                "type": "predicts_about",
                "raw_type": "prediction-commit",
                "target": commit,
                "resolved": True,
                "source": "prediction-commit",
                "from_file": "predictions.jsonl",
            })

    return {
        "traversable": traversable,
        "weak": weak,
        "dangling": dangling,
        "unknown_strings": unknown_strings,
    }


def build_graph() -> dict:
    """Assemble the full rederivable graph (nodes + edge buckets). No disk."""
    vocab = load_vocab()
    nodes = collect_nodes()
    edges = collect_edges(nodes, vocab)
    return {"nodes": nodes, "node_counts": _node_counts(nodes), **edges}


# ── Ephemeral :memory: projection (prove the join path; discard) ───────────────
def build_projection(graph: dict) -> sqlite3.Connection:
    """Materialize the graph into an in-memory sqlite — proves the node/edge join
    works for a neighborhood query, then is discarded. No DB ever touches disk."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE node(id TEXT PRIMARY KEY, source TEXT, path TEXT)")
    con.execute("CREATE TABLE edge(subject TEXT, type TEXT, target TEXT, "
                "resolved INT, traversable INT, raw_type TEXT, from_file TEXT)")
    con.executemany(
        "INSERT OR IGNORE INTO node VALUES (?,?,?)",
        [(nid, m["source"], m.get("path", "")) for nid, m in graph["nodes"].items()],
    )
    rows = ([(e["subject"], e["type"], e["target"], int(e["resolved"]), 1,
              e["raw_type"], e["from_file"]) for e in graph["traversable"]]
            + [(e["subject"], e["type"], e["target"], int(e["resolved"]), 0,
                e["raw_type"], e["from_file"]) for e in graph["weak"]])
    con.executemany("INSERT INTO edge VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()
    return con


# ── Neighborhood query ─────────────────────────────────────────────────────────
def neighborhood(node_id: str, graph: dict | None = None) -> dict:
    """node_id's neighborhood: traversable out/in edges + weak (relates_to) edges,
    each annotated with canonical type and resolved/dangling target."""
    if graph is None:
        graph = build_graph()
    nodes = graph["nodes"]

    def _fmt(e: dict, direction: str) -> dict:
        other = e["target"] if direction == "out" else e["subject"]
        return {
            "type": e["type"],
            "raw_type": e["raw_type"],
            "other": other,
            "direction": direction,
            "resolved": e["resolved"] if direction == "out" else (e["subject"] in nodes),
            "from_file": e["from_file"],
        }

    trav_out = [_fmt(e, "out") for e in graph["traversable"] if e["subject"] == node_id]
    trav_in = [_fmt(e, "in") for e in graph["traversable"] if e["target"] == node_id]
    weak_edges = [
        _fmt(e, "out") if e["subject"] == node_id else _fmt(e, "in")
        for e in graph["weak"]
        if e["subject"] == node_id or e["target"] == node_id
    ]
    return {
        "node": node_id,
        "exists": node_id in nodes,
        "meta": nodes.get(node_id, {}),
        "traversable_out": trav_out,
        "traversable_in": trav_in,
        "weak": weak_edges,
    }


# ── Rendering ──────────────────────────────────────────────────────────────────
def _edge_line(e: dict) -> str:
    arrow = "->" if e["direction"] == "out" else "<-"
    tag = "" if e["resolved"] else "  [dangling]"
    raw = f"  (raw: {e['raw_type']})" if e["raw_type"] != e["type"] else ""
    return f"  {e['type']:14s} {arrow} {e['other']}{tag}{raw}"


def render_neighborhood(nb: dict) -> str:
    L: list[str] = []
    mark = "" if nb["exists"] else "  [NODE NOT IN GRAPH]"
    src = nb["meta"].get("source", "?")
    L.append(f"# node: {nb['node']}  (source: {src}){mark}")
    L.append("")
    L.append("## traversable (lifecycle) edges")
    if not nb["traversable_out"] and not nb["traversable_in"]:
        L.append("  (none)")
    for e in nb["traversable_out"]:
        L.append(_edge_line(e))
    for e in nb["traversable_in"]:
        L.append(_edge_line(e))
    L.append("")
    L.append("## weak / non-traversable (relates_to + provenance) edges")
    L.append("# excluded from bundling/traversal — association only")
    if not nb["weak"]:
        L.append("  (none)")
    for e in nb["weak"]:
        L.append(_edge_line(e))
    return "\n".join(L)


# ── CLI ────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("node", nargs="?", help="node id to show the neighborhood of")
    ap.add_argument("--build", action="store_true",
                    help="build the graph and print node/edge counts")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    graph = build_graph()
    # Prove the in-memory join works for a neighborhood query, then discard.
    build_projection(graph).close()

    if args.build or not args.node:
        nc = graph["node_counts"]
        n_unknown = len(graph["unknown_strings"])
        summary = {
            "nodes_total": len(graph["nodes"]),
            "nodes_by_source": nc,
            "edges_traversable": len(graph["traversable"]),
            "edges_weak": len(graph["weak"]),
            "edges_dangling": len(graph["dangling"]),
            "unknown_relation_strings": graph["unknown_strings"],
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print("lifecycle-graph (rederivable; no disk store)")
            print(f"  nodes: {summary['nodes_total']} total — "
                  f"decisions={nc['decision']} research={nc['research']} "
                  f"predictions={nc['prediction']}")
            print(f"  edges: traversable={summary['edges_traversable']} "
                  f"weak/non-traversable={summary['edges_weak']} "
                  f"dangling={summary['edges_dangling']}")
            print(f"  unknown relation strings (vocab gaps): {n_unknown}"
                  + (f" -> {sorted(graph['unknown_strings'])}" if n_unknown else ""))
        if not args.node:
            return 0

    nb = neighborhood(args.node, graph)
    if args.json:
        print(json.dumps(nb, indent=2))
    else:
        print(render_neighborhood(nb))
    return 0


if __name__ == "__main__":
    sys.exit(main())
