"""Reject stray stdout writes when running as a stdio MCP.

Bites every new MCP author once: a bare `print()` (debug, library log) corrupts
the JSON-RPC framing on stdout and the MCP client times out with a cryptic
parse error. This guard installs a sys.stdout proxy that raises on any write
not originating from the JSON-RPC framer.

Usage (in a stdio MCP entry point):

    from corpus_core.util.stdio_guard import install_stdio_guard
    install_stdio_guard()
    # ... mcp.run() ...

Off by default. `corpus-mcp` will install it unconditionally; downstream MCPs
opt in. To bypass for one write (the JSON-RPC framer), wrap in:

    with allow_stdout():
        sys.stdout.write(framed_message)

The guard is process-local, idempotent, and drops cleanly under
`--no-stdio-guard` (for local debugging).
"""
from __future__ import annotations

import contextlib
import os
import sys
import threading
from typing import IO, Iterator

_TLS = threading.local()
_INSTALLED: bool = False


class _StdoutGuard:
    """Wrap a stream; raise on write unless `_TLS.allow` is truthy."""

    def __init__(self, target: IO[str]):
        self._target = target

    def write(self, data: str) -> int:  # type: ignore[override]
        if not getattr(_TLS, "allow", False):
            raise RuntimeError(
                "stdio_guard: write to stdout outside the JSON-RPC stream "
                "(use sys.stderr for logs; see corpus_core.util.stdio_guard)"
            )
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def __getattr__(self, name: str):  # passthrough for less-common attrs
        return getattr(self._target, name)


@contextlib.contextmanager
def allow_stdout() -> Iterator[None]:
    """Permit stdout writes for the duration of the block."""
    prev = getattr(_TLS, "allow", False)
    _TLS.allow = True
    try:
        yield
    finally:
        _TLS.allow = prev


def install_stdio_guard() -> None:
    """Replace sys.stdout with a guarded proxy. Idempotent.

    Disabled by `CORPUS_STDIO_GUARD=0` or by passing `--no-stdio-guard` on a
    CLI before this is called.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    if os.environ.get("CORPUS_STDIO_GUARD") == "0":
        return
    sys.stdout = _StdoutGuard(sys.stdout)  # type: ignore[assignment]
    _INSTALLED = True
