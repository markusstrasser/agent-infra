"""Shared MCP telemetry middleware for meta project servers."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.server.middleware import Middleware, MiddlewareContext

log = logging.getLogger("mcp.telemetry")

SEQUENCE_LOG = Path.home() / ".claude" / "tool-sequences.jsonl"


def _extract_project(args: dict | None) -> str:
    """Extract project name from tool arguments (path-based heuristic)."""
    if not args:
        return ""
    path = args.get("path", "")
    if not path:
        return ""
    # Extract project name: ~/Projects/<project>/... -> project
    parts = Path(path).parts
    try:
        idx = parts.index("Projects")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    except ValueError:
        pass
    return ""


class TelemetryMiddleware(Middleware):
    """Logs every tool call with timing, error status, and sequence order.

    Tracks call sequences per session by appending to tool-sequences.jsonl.
    Session identity uses MCP_SESSION_ID env var (set by Claude Code) or
    falls back to process ID for grouping.
    """

    def __init__(self):
        super().__init__()
        self._seq = 0  # monotonic sequence counter within this server lifetime

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = getattr(context.message, "name", "unknown")
        tool_args = getattr(context.message, "arguments", None) or {}
        start = time.monotonic()

        self._seq += 1
        seq = self._seq

        try:
            result = await call_next(context)
            elapsed = time.monotonic() - start
            log.info("tool=%s seq=%d elapsed=%.3fs status=ok", tool_name, seq, elapsed)
            self._log_sequence(tool_name, tool_args, seq, "ok", elapsed)
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            log.warning(
                "tool=%s seq=%d elapsed=%.3fs status=error error=%s",
                tool_name, seq, elapsed, e,
            )
            self._log_sequence(tool_name, tool_args, seq, "error", elapsed)
            raise

    def _log_sequence(
        self, tool: str, args: dict, seq: int, status: str, elapsed: float,
    ) -> None:
        """Append a sequence entry to tool-sequences.jsonl."""
        project = _extract_project(args)
        session_id = os.environ.get("MCP_SESSION_ID", f"pid-{os.getpid()}")

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "project": project,
            "seq": seq,
            "session_id": session_id,
            "status": status,
            "elapsed_s": round(elapsed, 3),
        }

        try:
            SEQUENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(SEQUENCE_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            log.debug("Failed to write sequence log to %s", SEQUENCE_LOG)
