"""Shared MCP telemetry middleware for meta project servers."""

import logging
import time

from fastmcp.server.middleware import Middleware, MiddlewareContext

log = logging.getLogger("mcp.telemetry")


class TelemetryMiddleware(Middleware):
    """Logs every tool call with timing and error status."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.request.params.name
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed = time.monotonic() - start
            log.info("tool=%s elapsed=%.3fs status=ok", tool_name, elapsed)
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            log.warning("tool=%s elapsed=%.3fs status=error error=%s", tool_name, elapsed, e)
            raise
