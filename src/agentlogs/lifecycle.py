"""RSI-lifecycle edge index — agentlogs-native home (Phase C).

The graph SEMANTICS are the oracle (`scripts/lifecycle_graph.py`, deleted by this
port): node collection over decisions/ ∪ research/ ∪ predictions, edge extraction
from decision frontmatter `relations:`, and `normalize_type` (fold→canonical;
invert ⇒ subject/target SWAP; canonical `traversable:false` ⇒ weak/non-traversable
association edge). This module reuses that behavior verbatim; it changes only the
storage/query HOME — from a standalone in-process `:memory:` projection to a
`lifecycle_edges` table inside the live `agentlogs.db`, queried through the named-
query substrate (`queries/lifecycle_neighbors.sql`).

The edge table is **rederivable**: `build_edges` rebuilds it DELETE-then-INSERT on
every call (markdown + `scripts/lifecycle_relations.json` stay authoritative). It is
self-contained — `CREATE TABLE IF NOT EXISTS` lives here, NOT in a formal migration
file, because the rows are derived bookkeeping, not durable agentlogs facts.

Three node sources (the resolver MUST span all three — a decisions-only resolver
resolves only ~25% of edge targets):
  (1) decisions/*.md     → node id = frontmatter `id:` (fallback: filename stem)
  (2) research/*.md      → node id = filename stem
  (3) predictions.jsonl  → node id = the row's `id`

Edge rows ⟨subject, type, target, traversable, dangling, source⟩:
  * `type` is the CANONICAL relation (fold-resolved); an `invert:true` fold has
    already swapped subject/target (`A superseded_by B` ⇒ row `B supersedes A`).
  * `traversable` is 0 for `relates_to` (the only canonical `traversable:false`)
    and for any UNKNOWN string (vocab gap kept visible, never crashed on).
  * `dangling` is 1 when `target` resolves to no node (recorded, never fatal; the
    improvement-log→decision join is known-sparse ~25% and ACCEPTED, not gated).
  * `source` is the provenance ("decision-relation" | "prediction-commit").
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import time
from pathlib import Path

# repo_root is passed in by callers; these are resolved relative to it.
VOCAB_RELPATH = Path("scripts") / "lifecycle_relations.json"


def default_repo_root() -> Path:
    """The agent-infra checkout holding decisions/ ∪ research/ ∪ predictions.

    agentlogs ships NON-editable inside the agent-infra wheel, so the installed
    `__file__` lives under site-packages and CANNOT locate the source repo. The
    lifecycle DATA lives in the working tree, and `lifecycle-reindex` / `just
    graph` are always invoked from within the agent-infra checkout — so resolve
    the root the same way provenance.py does: `git rev-parse --show-toplevel`
    from cwd. Falls back to cwd if git is unavailable (caller may pass --repo-root).
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return Path.cwd()


# ── Vocabulary (Phase A — LOAD, never restate) ─────────────────────────────────
def load_vocab(repo_root: Path) -> dict:
    return json.loads((repo_root / VOCAB_RELPATH).read_text())


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
def collect_nodes(repo_root: Path) -> dict[str, dict]:
    """node_id -> {source, path}. Decisions keyed by frontmatter id (fallback
    stem); research by stem; predictions by row id."""
    decisions = repo_root / "decisions"
    research = repo_root / "research"
    predictions = repo_root / "predictions.jsonl"

    nodes: dict[str, dict] = {}
    for f in sorted(decisions.glob("*.md")):
        if f.name.startswith("."):  # .template.md
            continue
        nid = _frontmatter_id(_frontmatter(f.read_text())) or f.stem
        nodes[nid] = {"source": "decision", "path": str(f.relative_to(repo_root))}
    for f in sorted(research.glob("*.md")):
        if f.name.startswith("."):
            continue
        nodes.setdefault(f.stem, {"source": "research",
                                  "path": str(f.relative_to(repo_root))})
    if predictions.exists():
        for line in predictions.read_text().splitlines():
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


# ── Edge assembly (returns rows ready for INSERT into lifecycle_edges) ──────────
def _assemble_edges(repo_root: Path, nodes: dict[str, dict], vocab: dict) -> dict:
    """Build the edge rows + the manifest (counts, unknown vocab strings).

    Each row is ⟨subject, type, target, traversable, dangling, source, raw_type,
    from_file⟩ — the last two are kept for the manifest/debug columns; the named
    query selects the first six.
    """
    rows: list[dict] = []
    n_traversable = n_weak = n_dangling = 0
    unknown_strings: dict[str, list[str]] = {}

    decisions = repo_root / "decisions"
    for f in sorted(decisions.glob("*.md")):
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
            dangling = tgt not in nodes
            rows.append({
                "subject": subj,
                "type": canon,
                "target": tgt,
                "traversable": 1 if traversable_flag else 0,
                "dangling": 1 if dangling else 0,
                "source": "decision-relation",
                "raw_type": raw_type,
                "from_file": str(f.relative_to(repo_root)),
            })
            # Record unknowns (not in canonical/fold) for the manifest.
            if canon not in vocab["canonical"]:
                unknown_strings.setdefault(raw_type, []).append(f.name)
            if dangling:
                n_dangling += 1
            if traversable_flag:
                n_traversable += 1
            else:
                n_weak += 1

    # Best-effort prediction → commit/node edges (weak provenance).
    for nid, meta in nodes.items():
        if meta.get("source") != "prediction":
            continue
        commit = (meta.get("commit") or "").strip()
        if commit and commit in nodes:
            rows.append({
                "subject": nid,
                "type": "predicts_about",
                "target": commit,
                "traversable": 0,
                "dangling": 0,
                "source": "prediction-commit",
                "raw_type": "prediction-commit",
                "from_file": "predictions.jsonl",
            })
            n_weak += 1

    return {
        "rows": rows,
        "edges_traversable": n_traversable,
        "edges_weak": n_weak,
        "edges_dangling": n_dangling,
        "unknown_strings": unknown_strings,
    }


# ── Commit-body pass (Phase B1 — recover commit --implements--> decision) ──────
# The git_commits.body column (populated by git_import) carries two signals that a
# code commit realized a decision:
#   (1) an explicit `Implements: <slug>` trailer  → source='commit-trailer' (the
#       forward/authored path; 0 in history today, the densifying path going fwd);
#   (2) a best-effort prose mention of a `YYYY-MM-DD-slug` that RESOLVES to a
#       decision node → source='commit-mention' (recovers ~31 edges from existing
#       agent-infra history; resolution IS the precision filter).
# `implements` is directed commit→decision: subject=<commit-hash>, target=<slug>.
# The commit hash is a valid subject without being in collect_nodes — the
# lifecycle_neighbors query matches subject OR target, so a decision's INCOMING
# implements edges surface when the decision is queried.
_IMPLEMENTS_TRAILER_RE = re.compile(r"^Implements:\s*(\S+)\s*$", re.MULTILINE)
# Date-slug shape: a decision filename stem (2026-06-18-foo-bar). Anchored on a
# word boundary; the trailing run is lowercase-alnum + hyphen (matches decisions/
# stems). A trailing `.md` is stripped before resolution.
_DATE_SLUG_RE = re.compile(r"\b(20\d\d-\d\d-\d\d-[a-z0-9][a-z0-9-]+)\b")


def _commit_implements_edges(
    con: sqlite3.Connection, nodes: dict[str, dict]
) -> tuple[list[dict], int, int]:
    """Scan agent-infra commit bodies for commit→decision `implements` edges.

    Returns (rows, n_resolved, n_unresolved_trailers). For each agent-infra commit
    with a non-empty body:
      * every `Implements:` trailer → an edge (source='commit-trailer'); if the
        target resolves to no decision node it is emitted dangling (explicit author
        intent is preserved, never crashed on);
      * every resolving date-slug prose mention → an edge (source='commit-mention');
        NON-resolving mentions are SKIPPED (124 slug-shaped date strings in history
        — e.g. `2026-03-19-late`, deleted/renamed decisions — would be false-positive
        noise; resolution is the precision filter for the best-effort path).
    Dedup: a commit that BOTH carries an `Implements:` trailer AND prose-mentions the
    same slug yields ONE edge, preferring the explicit trailer.
    """
    rows: list[dict] = []
    n_resolved = 0
    n_unresolved_trailers = 0
    try:
        cur = con.execute(
            "SELECT hash, body FROM git_commits "
            "WHERE project = 'agent-infra' AND body IS NOT NULL AND body <> ''"
        )
    except sqlite3.OperationalError:
        # git_commits absent (fresh/synthetic db) — no commit edges to add.
        return rows, n_resolved, n_unresolved_trailers

    for chash, body in cur.fetchall():
        if not body:
            continue
        # slug -> source, preferring 'commit-trailer' over 'commit-mention' on dedup.
        per_commit: dict[str, str] = {}
        for m in _IMPLEMENTS_TRAILER_RE.finditer(body):
            slug = m.group(1)
            slug = slug[:-3] if slug.endswith(".md") else slug
            per_commit[slug] = "commit-trailer"  # trailer always wins
        for m in _DATE_SLUG_RE.finditer(body):
            slug = m.group(1)
            slug = slug[:-3] if slug.endswith(".md") else slug
            if slug in nodes and slug not in per_commit:
                per_commit[slug] = "commit-mention"

        for slug, source in per_commit.items():
            resolves = slug in nodes
            if source == "commit-mention" and not resolves:
                continue  # unreachable (we only added resolving mentions) — defensive
            if not resolves:
                n_unresolved_trailers += 1  # explicit trailer to a missing decision
            else:
                n_resolved += 1
            rows.append({
                "subject": chash,
                "type": "implements",
                "target": slug,
                "traversable": 1,
                "dangling": 0 if resolves else 1,
                "source": source,
                "raw_type": "implements",
                "from_file": f"git_commits:{chash[:12]}",
            })
    return rows, n_resolved, n_unresolved_trailers


# ── Schema (self-contained — rederivable rows, NOT a formal migration) ─────────
_DDL = """
CREATE TABLE IF NOT EXISTS lifecycle_edges (
    subject     TEXT NOT NULL,
    type        TEXT NOT NULL,
    target      TEXT NOT NULL,
    traversable INTEGER NOT NULL,
    dangling    INTEGER NOT NULL,
    source      TEXT NOT NULL,
    raw_type    TEXT,
    from_file   TEXT
)
"""


def build_edges(con: sqlite3.Connection, repo_root: Path) -> dict:
    """Rebuild the lifecycle_edges table from markdown + the vocab.

    DELETE-then-INSERT (the table is fully rederivable; nothing else owns it).
    Returns the manifest: node counts per source + traversable/weak/dangling edge
    counts + any unknown vocab strings (the gate's 0-unknown assertion).
    """
    repo_root = Path(repo_root).resolve()
    vocab = load_vocab(repo_root)
    nodes = collect_nodes(repo_root)
    assembled = _assemble_edges(repo_root, nodes, vocab)

    # Phase B1: recover commit --implements--> decision edges from commit bodies
    # (same `con`, after the frontmatter pass). These are traversable lifecycle
    # edges; they raise edges_traversable without touching node collection.
    commit_rows, n_impl_resolved, n_impl_dangling = _commit_implements_edges(con, nodes)
    assembled["rows"].extend(commit_rows)
    assembled["edges_traversable"] += len(commit_rows)
    assembled["edges_dangling"] += n_impl_dangling
    assembled["edges_commit_implements"] = n_impl_resolved

    con.execute(_DDL)
    # The DELETE+INSERT must be ONE atomic swap against the shared live agentlogs.db
    # — the launchd indexer can hold the WAL writer lock through a long bulk-import
    # transaction that exceeds connect()'s 30s busy_timeout (observed). BEGIN
    # IMMEDIATE takes the writer lock up front; a bounded retry waits the indexer
    # out instead of failing the whole recipe (fix the transport, keep the
    # capability). connect() runs in autocommit (isolation_level=None), so the
    # transaction is driven explicitly here.
    last_exc: sqlite3.OperationalError | None = None
    for attempt in range(6):
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM lifecycle_edges")
            con.executemany(
                "INSERT INTO lifecycle_edges "
                "(subject, type, target, traversable, dangling, source, raw_type, "
                "from_file) VALUES (:subject, :type, :target, :traversable, "
                ":dangling, :source, :raw_type, :from_file)",
                assembled["rows"],
            )
            con.execute("COMMIT")
            break
        except sqlite3.OperationalError as exc:
            # ROLLBACK only if a txn actually opened (BEGIN IMMEDIATE may have been
            # the statement that failed on the lock — then no txn is active).
            if con.in_transaction:
                con.execute("ROLLBACK")
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))  # linear backoff: up to ~10.5s total
    else:
        raise RuntimeError(
            "lifecycle_edges rebuild could not acquire the writer lock after 6 "
            f"attempts (indexer holding it?): {last_exc}"
        )

    return {
        "nodes_total": len(nodes),
        "nodes_by_source": _node_counts(nodes),
        "edges_total": len(assembled["rows"]),
        "edges_traversable": assembled["edges_traversable"],
        "edges_weak": assembled["edges_weak"],
        "edges_dangling": assembled["edges_dangling"],
        "edges_commit_implements": len(commit_rows),
        "edges_commit_implements_resolved": n_impl_resolved,
        "edges_commit_implements_dangling": n_impl_dangling,
        "unknown_strings": assembled["unknown_strings"],
    }
