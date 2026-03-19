"""Knowledge substrate core — registration, querying, propagation.

Thin wrapper over SQLite. No ORM. Domain-specific logic stays in project profiles.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path


class _DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

SCHEMA_SQL = Path(__file__).parent / "schema.sql"


@dataclass
class ReflectResult:
    """Result of a reflect() call -- LLM synthesis over recalled knowledge."""
    text: str
    cited_ids: list[str] = field(default_factory=list)
    hallucinated_ids: list[str] = field(default_factory=list)
    recalled_ids: list[str] = field(default_factory=list)
    query: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class KnowledgeDB:
    """Per-project knowledge substrate backed by SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL.read_text())

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # --- Registration ---

    def register_assertion(self, id: str, *, type: str, status: str = "active",
                           title: str | None = None, source_file: str | None = None,
                           payload: dict | None = None) -> None:
        now = _now()
        payload_json = json.dumps(payload or {}, cls=_DateEncoder)
        existing = self.conn.execute(
            "SELECT status FROM assertions WHERE id = ?", (id,)
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE assertions SET type=?, status=?, title=?, source_file=?,
                   payload=?, updated_at=? WHERE id=?""",
                (type, status, title, source_file, payload_json, now, id),
            )
            self._log(id, "assertion", "updated", old_value=dict(existing), reason="re-registered")
        else:
            self.conn.execute(
                """INSERT INTO assertions (id, type, status, title, source_file, payload,
                   created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (id, type, status, title, source_file, payload_json, now, now),
            )
            self._log(id, "assertion", "created")
        self.conn.commit()

    def register_evidence(self, id: str, *, type: str, source: str,
                          title: str | None = None, source_grade: str | None = None,
                          payload: dict | None = None) -> None:
        now = _now()
        payload_json = json.dumps(payload or {}, cls=_DateEncoder)
        existing = self.conn.execute(
            "SELECT id FROM evidence WHERE id = ?", (id,)
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE evidence SET type=?, source=?, title=?, source_grade=?,
                   payload=?, updated_at=? WHERE id=?""",
                (type, source, title, source_grade, payload_json, now, id),
            )
            self._log(id, "evidence", "updated")
        else:
            self.conn.execute(
                """INSERT INTO evidence (id, type, source, title, source_grade, payload,
                   created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (id, type, source, title, source_grade, payload_json, now, now),
            )
            self._log(id, "evidence", "created")
        self.conn.commit()

    def register_artifact(self, id: str, *, type: str, path: str | None = None,
                          title: str | None = None, payload: dict | None = None) -> None:
        now = _now()
        payload_json = json.dumps(payload or {}, cls=_DateEncoder)
        existing = self.conn.execute(
            "SELECT id FROM artifacts WHERE id = ?", (id,)
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE artifacts SET type=?, path=?, title=?, payload=?, updated_at=?
                   WHERE id=?""",
                (type, path, title, payload_json, now, id),
            )
            self._log(id, "artifact", "updated")
        else:
            self.conn.execute(
                """INSERT INTO artifacts (id, type, path, title, payload,
                   created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (id, type, path, title, payload_json, now, now),
            )
            self._log(id, "artifact", "created")
        self.conn.commit()

    # --- Relations ---

    def add_relation(self, source_id: str, target_id: str, relation: str,
                     *, source_type: str | None = None, target_type: str | None = None,
                     payload: dict | None = None) -> None:
        """Add a typed relation. Auto-detects source/target types if not specified."""
        if source_type is None:
            source_type = self._detect_type(source_id)
        if target_type is None:
            target_type = self._detect_type(target_id)
        if not source_type or not target_type:
            raise ValueError(f"Cannot detect types for {source_id} -> {target_id}. "
                             "Register objects first or specify types explicitly.")

        payload_json = json.dumps(payload or {}, cls=_DateEncoder)
        self.conn.execute(
            """INSERT OR IGNORE INTO relations
               (source_id, source_type, target_id, target_type, relation, payload)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source_id, source_type, target_id, target_type, relation, payload_json),
        )
        self.conn.commit()

    def add_cross_project_ref(self, local_id: str, local_type: str,
                              remote_project: str, remote_id: str,
                              remote_type: str, relation: str) -> None:
        self.conn.execute(
            """INSERT OR IGNORE INTO cross_project_refs
               (local_id, local_type, remote_project, remote_id, remote_type, relation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (local_id, local_type, remote_project, remote_id, remote_type, relation),
        )
        self.conn.commit()

    # --- Derivations ---

    def register_derivation(self, id: str, *, process: str,
                            inputs: list[tuple[str, str]],
                            outputs: list[tuple[str, str]],
                            description: str | None = None,
                            payload: dict | None = None) -> None:
        """Register a derivation with its inputs and outputs.

        inputs/outputs: list of (object_id, object_type) tuples.
        """
        payload_json = json.dumps(payload or {}, cls=_DateEncoder)
        self.conn.execute(
            """INSERT OR REPLACE INTO derivations (id, process, description, payload, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (id, process, description, payload_json, _now()),
        )
        # Clear and re-insert links
        self.conn.execute("DELETE FROM derivation_inputs WHERE derivation_id = ?", (id,))
        self.conn.execute("DELETE FROM derivation_outputs WHERE derivation_id = ?", (id,))

        for obj_id, obj_type in inputs:
            self.conn.execute(
                "INSERT INTO derivation_inputs (derivation_id, input_id, input_type) VALUES (?, ?, ?)",
                (id, obj_id, obj_type),
            )
        for obj_id, obj_type in outputs:
            self.conn.execute(
                "INSERT INTO derivation_outputs (derivation_id, output_id, output_type) VALUES (?, ?, ?)",
                (id, obj_id, obj_type),
            )
        self._log(id, "derivation", "created")
        self.conn.commit()

    # --- Propagation ---

    def mark_stale(self, object_id: str, *, reason: str | None = None,
                   max_depth: int = 5) -> list[str]:
        """Mark an object and its downstream dependents as stale.

        Returns list of all object IDs marked stale (including the original).
        max_depth prevents runaway cascades.
        """
        stale_ids = []
        self._propagate_stale(object_id, reason or "upstream marked stale",
                              stale_ids, depth=0, max_depth=max_depth)
        return stale_ids

    def _propagate_stale(self, object_id: str, reason: str,
                         stale_ids: list[str], depth: int, max_depth: int) -> None:
        if depth > max_depth or object_id in stale_ids:
            return

        obj_type = self._detect_type(object_id)
        if not obj_type:
            return

        # Mark this object stale
        table = {"assertion": "assertions", "evidence": "evidence", "artifact": "artifacts"}
        if obj_type in table:
            old = self.conn.execute(
                f"SELECT status FROM {table[obj_type]} WHERE id = ?", (object_id,)
            ).fetchone()
            if old and old["status"] != "stale":
                self.conn.execute(
                    f"UPDATE {table[obj_type]} SET status = 'stale', updated_at = ? WHERE id = ?",
                    (_now(), object_id),
                )
                self._log(object_id, obj_type, "status_changed",
                          old_value={"status": old["status"]},
                          new_value={"status": "stale"},
                          reason=reason)
                stale_ids.append(object_id)
                self.conn.commit()

        # Find downstream via relations
        downstream = self.conn.execute(
            """SELECT source_id, source_type FROM relations
               WHERE target_id = ? AND relation IN ('supported_by', 'depends_on', 'derived_from')""",
            (object_id,),
        ).fetchall()

        # Find downstream via derivations
        derivation_ids = self.conn.execute(
            "SELECT derivation_id FROM derivation_inputs WHERE input_id = ?",
            (object_id,),
        ).fetchall()
        for row in derivation_ids:
            outputs = self.conn.execute(
                "SELECT output_id FROM derivation_outputs WHERE derivation_id = ?",
                (row["derivation_id"],),
            ).fetchall()
            for out in outputs:
                self._propagate_stale(out["output_id"], reason, stale_ids,
                                      depth + 1, max_depth)

        for row in downstream:
            self._propagate_stale(row["source_id"], reason, stale_ids,
                                  depth + 1, max_depth)

    # --- Querying ---

    def get(self, object_id: str) -> dict | None:
        """Get any object by ID."""
        for table in ("assertions", "evidence", "artifacts"):
            row = self.conn.execute(f"SELECT * FROM {table} WHERE id = ?", (object_id,)).fetchone()
            if row:
                d = dict(row)
                d["_type"] = table.rstrip("s") if table != "evidence" else "evidence"
                if "payload" in d:
                    d["payload"] = json.loads(d["payload"])
                return d
        return None

    def dependents(self, object_id: str) -> list[dict]:
        """Find all objects that depend on this one (direct, not transitive)."""
        results = []

        # Via relations
        rows = self.conn.execute(
            """SELECT source_id, source_type, relation FROM relations
               WHERE target_id = ?""",
            (object_id,),
        ).fetchall()
        for r in rows:
            results.append({"id": r["source_id"], "type": r["source_type"],
                            "via": "relation", "relation": r["relation"]})

        # Via derivations
        deriv_ids = self.conn.execute(
            "SELECT derivation_id FROM derivation_inputs WHERE input_id = ?",
            (object_id,),
        ).fetchall()
        for d in deriv_ids:
            outputs = self.conn.execute(
                "SELECT output_id, output_type FROM derivation_outputs WHERE derivation_id = ?",
                (d["derivation_id"],),
            ).fetchall()
            for o in outputs:
                results.append({"id": o["output_id"], "type": o["output_type"],
                                "via": "derivation", "derivation_id": d["derivation_id"]})

        return results

    def stale_objects(self) -> list[dict]:
        """List all objects currently marked stale."""
        results = []
        for table, obj_type in [("assertions", "assertion"), ("evidence", "evidence"),
                                ("artifacts", "artifact")]:
            rows = self.conn.execute(
                f"SELECT id, title, updated_at FROM {table} WHERE status = 'stale'"
            ).fetchall()
            for r in rows:
                results.append({"id": r["id"], "type": obj_type,
                                "title": r["title"], "updated_at": r["updated_at"]})
        return results

    def stats(self) -> dict:
        """Quick summary stats."""
        s = {}
        for table in ("assertions", "evidence", "artifacts", "derivations", "relations"):
            s[table] = self.conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()["c"]
        s["stale"] = sum(
            self.conn.execute(
                f"SELECT COUNT(*) as c FROM {table} WHERE status = 'stale'"
            ).fetchone()["c"]
            for table in ("assertions", "evidence", "artifacts")
        )
        s["changelog_entries"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM changelog"
        ).fetchone()["c"]
        return s

    def recent_changes(self, limit: int = 20) -> list[dict]:
        """Recent changelog entries."""
        rows = self.conn.execute(
            "SELECT * FROM changelog ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Search ---

    def search_objects(self, query: str, *, max_results: int = 20) -> list[dict]:
        """LIKE-based scan across assertions, evidence, artifacts.

        Tokenizes query, scores matches in id/title/type/payload.
        Returns top-K results with _type and _score fields.
        Excludes stale objects.
        """
        tokens = [t.lower() for t in re.split(r'\s+', query.strip()) if t]
        if not tokens:
            return []

        scored: list[tuple[float, dict]] = []
        tables = [
            ("assertions", "assertion"),
            ("evidence", "evidence"),
            ("artifacts", "artifact"),
        ]
        for table, obj_type in tables:
            rows = self.conn.execute(
                f"SELECT * FROM {table} WHERE status != 'stale'"
            ).fetchall()
            for row in rows:
                d = dict(row)
                d["_type"] = obj_type
                if "payload" in d:
                    d["payload"] = json.loads(d["payload"])

                # Build searchable text from key fields
                fields = [
                    d.get("id", ""),
                    d.get("title", "") or "",
                    d.get("type", ""),
                ]
                # Extract key fields from payload instead of raw JSON
                payload = d.get("payload", {})
                if isinstance(payload, dict):
                    for _k, v in payload.items():
                        if isinstance(v, str):
                            fields.append(v)
                        elif isinstance(v, (list, tuple)):
                            fields.extend(str(x) for x in v)

                searchable = " ".join(fields).lower()
                score = sum(searchable.count(t) for t in tokens)
                if score > 0:
                    d["_score"] = score
                    scored.append((score, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:max_results]]

    # --- Reflect (LLM synthesis) ---

    def reflect(self, query: str, *, max_results: int = 20,
                model: str = "claude-haiku-4-5-20251001",
                max_tokens: int = 1024,
                max_context_objects: int = 40) -> ReflectResult:
        """Search the substrate and synthesize an answer using an LLM.

        1. Recall: LIKE search across assertions+evidence+artifacts
        2. Graph expand: 1-hop relations for each recalled object
        3. Assemble context: Format for LLM
        4. Synthesize: Single Anthropic SDK call
        5. Return: ReflectResult with citations

        Falls back to plain recalled context if Anthropic API fails.
        """
        # Step 1: Recall
        recalled = self.search_objects(query, max_results=max_results)
        recalled_ids = [obj["id"] for obj in recalled]

        if not recalled:
            return ReflectResult(
                text="No relevant objects found in the knowledge substrate.",
                cited_ids=[], hallucinated_ids=[], recalled_ids=[],
                query=query, model=model, input_tokens=0, output_tokens=0,
            )

        # Step 2: Graph expand -- 1-hop relations for each recalled object
        expanded: dict[str, dict] = {obj["id"]: obj for obj in recalled}
        for obj in recalled:
            oid = obj["id"]
            # Outgoing relations (this object depends on target)
            out_rows = self.conn.execute(
                "SELECT target_id FROM relations WHERE source_id = ?",
                (oid,),
            ).fetchall()
            for r in out_rows:
                tid = r["target_id"]
                if tid not in expanded:
                    neighbor = self.get(tid)
                    if neighbor and neighbor.get("status") != "stale":
                        neighbor["_score"] = 0
                        expanded[tid] = neighbor

            # Incoming relations (other objects depend on this)
            in_rows = self.conn.execute(
                "SELECT source_id FROM relations WHERE target_id = ?",
                (oid,),
            ).fetchall()
            for r in in_rows:
                sid = r["source_id"]
                if sid not in expanded:
                    neighbor = self.get(sid)
                    if neighbor and neighbor.get("status") != "stale":
                        neighbor["_score"] = 0
                        expanded[sid] = neighbor

        # Cap total objects at max_context_objects, prune lowest-scored
        all_objects = list(expanded.values())
        all_objects.sort(key=lambda x: x.get("_score", 0), reverse=True)
        all_objects = all_objects[:max_context_objects]
        all_ids = {obj["id"] for obj in all_objects}

        # Step 3: Assemble context
        context_parts = []
        for obj in all_objects:
            obj_type = obj.get("_type", "unknown")
            oid = obj["id"]
            title = obj.get("title") or "(no title)"
            status = obj.get("status", "")

            # Extract key payload fields
            payload = obj.get("payload", {})
            payload_summary = ""
            if isinstance(payload, dict) and payload:
                key_fields = []
                for k, v in list(payload.items())[:8]:
                    if isinstance(v, str) and len(v) > 200:
                        v = v[:200] + "..."
                    key_fields.append(f"  {k}: {v}")
                if key_fields:
                    payload_summary = "\n".join(key_fields)

            part = f"[{obj_type}] {oid}: {title} (status: {status})"
            if payload_summary:
                part += f"\n{payload_summary}"
            context_parts.append(part)

        assembled_context = "\n\n".join(context_parts)

        # Step 4: Synthesize via Anthropic SDK
        prompt = (
            "Based on the following retrieved knowledge from a knowledge substrate, "
            "answer the query.\n\n"
            f"Query: {query}\n\n"
            f"Retrieved knowledge ({len(all_objects)} objects):\n"
            f"{assembled_context}\n\n"
            "Instructions:\n"
            "- Cite specific object IDs when making claims "
            "(use the exact IDs from the retrieved knowledge).\n"
            "- If the retrieved knowledge doesn't contain enough information, say so.\n"
            "- Be concise and precise.\n"
            "- Do not invent information not present in the retrieved knowledge."
        )

        try:
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
        except Exception:
            # Graceful fallback: return assembled context as plain text
            return ReflectResult(
                text=(
                    "[API unavailable -- returning raw recalled context]\n\n"
                    + assembled_context
                ),
                cited_ids=[], hallucinated_ids=[], recalled_ids=recalled_ids,
                query=query, model=model, input_tokens=0, output_tokens=0,
            )

        # Step 5: Extract cited IDs and detect hallucinated ones
        # IDs are kebab-case, often prefixed with ev-, memo-, etc.
        cited_ids: list[str] = []
        hallucinated_ids: list[str] = []
        for candidate in re.findall(r'[a-z][a-z0-9_-]{2,}(?:-[a-z0-9_-]+)+', text):
            if candidate in all_ids:
                if candidate not in cited_ids:
                    cited_ids.append(candidate)
            elif candidate not in hallucinated_ids:
                # Check if it's actually a registered object we pruned
                if self.get(candidate) is not None:
                    if candidate not in cited_ids:
                        cited_ids.append(candidate)
                else:
                    hallucinated_ids.append(candidate)

        return ReflectResult(
            text=text,
            cited_ids=cited_ids,
            hallucinated_ids=hallucinated_ids,
            recalled_ids=recalled_ids,
            query=query,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # --- CTE Graph Queries ---

    def provenance_chain(self, object_id: str, *, max_depth: int = 10) -> list[dict]:
        """Full downstream provenance tree using recursive CTE.

        Follows target->source direction: what does this object support/feed into?
        Returns list of dicts with id, type, depth, relation, path info.
        """
        rows = self.conn.execute(
            """
            WITH RECURSIVE chain(id, type, depth, relation, path) AS (
                -- Base case: the starting object
                SELECT ?, '', 0, '', ?
                UNION ALL
                -- Recursive: follow relations where this object is a target
                SELECT r.source_id, r.source_type, c.depth + 1, r.relation,
                       c.path || ' -> ' || r.source_id
                FROM relations r
                JOIN chain c ON r.target_id = c.id
                WHERE c.depth < ?
            )
            SELECT DISTINCT id, type, depth, relation, path
            FROM chain
            WHERE depth > 0
            ORDER BY depth, id
            """,
            (object_id, object_id, max_depth),
        ).fetchall()
        return [dict(r) for r in rows]

    def impact_radius(self, object_id: str, *, max_depth: int = 5) -> list[dict]:
        """Full upstream impact -- what does this object depend on, transitively?

        Follows source->target direction: what are this object's transitive inputs?
        """
        rows = self.conn.execute(
            """
            WITH RECURSIVE chain(id, type, depth, relation, path) AS (
                SELECT ?, '', 0, '', ?
                UNION ALL
                SELECT r.target_id, r.target_type, c.depth + 1, r.relation,
                       c.path || ' -> ' || r.target_id
                FROM relations r
                JOIN chain c ON r.source_id = c.id
                WHERE c.depth < ?
            )
            SELECT DISTINCT id, type, depth, relation, path
            FROM chain
            WHERE depth > 0
            ORDER BY depth, id
            """,
            (object_id, object_id, max_depth),
        ).fetchall()
        return [dict(r) for r in rows]

    def shared_evidence(self, object_id: str) -> list[dict]:
        """Other assertions sharing evidence with this object via relations.

        Finds assertions linked to the same evidence targets.
        """
        rows = self.conn.execute(
            """
            SELECT DISTINCT r2.source_id AS id, r2.source_type AS type,
                   r1.target_id AS shared_evidence_id, r1.relation
            FROM relations r1
            JOIN relations r2 ON r1.target_id = r2.target_id
                AND r1.relation = r2.relation
            WHERE r1.source_id = ?
              AND r2.source_id != ?
              AND r1.relation IN ('supported_by', 'depends_on', 'derived_from')
            ORDER BY r2.source_id
            """,
            (object_id, object_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def contradictory_assertions(self, object_id: str) -> list[dict]:
        """Assertions linked via contradicted_by relations.

        Returns objects that contradict or are contradicted by this object.
        """
        rows = self.conn.execute(
            """
            SELECT source_id AS id, source_type AS type,
                   'contradicts_this' AS direction, relation
            FROM relations
            WHERE target_id = ? AND relation = 'contradicted_by'
            UNION ALL
            SELECT target_id AS id, target_type AS type,
                   'contradicted_by_this' AS direction, relation
            FROM relations
            WHERE source_id = ? AND relation = 'contradicted_by'
            ORDER BY id
            """,
            (object_id, object_id),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Orphan Sweeper ---

    def orphans(self) -> list[dict]:
        """Find objects with zero relations (not referenced by any relation)."""
        results = []
        for table, obj_type in [("assertions", "assertion"),
                                ("evidence", "evidence"),
                                ("artifacts", "artifact")]:
            rows = self.conn.execute(
                f"""
                SELECT t.id, t.title, t.type, t.status
                FROM {table} t
                WHERE NOT EXISTS (
                    SELECT 1 FROM relations r
                    WHERE r.source_id = t.id OR r.target_id = t.id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM derivation_inputs di
                    WHERE di.input_id = t.id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM derivation_outputs do2
                    WHERE do2.output_id = t.id
                )
                ORDER BY t.id
                """,
            ).fetchall()
            for r in rows:
                results.append({
                    "id": r["id"], "_type": obj_type, "type": r["type"],
                    "title": r["title"], "status": r["status"],
                })
        return results

    # --- Internals ---

    def _detect_type(self, object_id: str) -> str | None:
        for table, type_name in [("assertions", "assertion"), ("evidence", "evidence"),
                                 ("artifacts", "artifact")]:
            if self.conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (object_id,)).fetchone():
                return type_name
        return None

    def _log(self, object_id: str, object_type: str, action: str,
             old_value: dict | None = None, new_value: dict | None = None,
             reason: str | None = None) -> None:
        self.conn.execute(
            """INSERT INTO changelog (object_id, object_type, action, old_value,
               new_value, reason, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (object_id, object_type, action,
             json.dumps(old_value) if old_value else None,
             json.dumps(new_value) if new_value else None,
             reason, _now()),
        )
