"""Knowledge substrate core — registration, querying, propagation.

Thin wrapper over SQLite. No ORM. Domain-specific logic stays in project profiles.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_SQL = Path(__file__).parent / "schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class KnowledgeDB:
    """Per-project knowledge substrate backed by SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
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
        payload_json = json.dumps(payload or {})
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
        payload_json = json.dumps(payload or {})
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
        payload_json = json.dumps(payload or {})
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

        payload_json = json.dumps(payload or {})
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
        payload_json = json.dumps(payload or {})
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
