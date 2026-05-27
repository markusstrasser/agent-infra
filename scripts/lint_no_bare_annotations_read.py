#!/usr/bin/env python3
"""Caller-migration lint — Phase A.

Forbids string-literal `FROM annotations` (raw table) outside a writer
allowlist. New code should read from `annotations_current` (chain-aware
view); raw `annotations` is the append-only event log, only the writer
and replay verifier touch it directly.

Greppable. Exits 1 on violation with `path:line:context`.

Usage:
    uv run python3 scripts/lint_no_bare_annotations_read.py [--fix] [PATH ...]

Allowlisted writer files / patterns (raw FROM annotations is correct):
  - corpus_core/index.py            (writer: DELETE FROM annotations,
                                     bulk INSERT, idempotency lookups)
  - corpus_core/replay.py           (byte-exact compare vs live)
  - corpus_core/maintain.py         (stats — event count, raw is right)
  - tests/test_replay.py            (replay validation: count raw rows)
  - tests/test_annotations_index.py (projection unit tests)
  - tests/test_schema_version.py    (legacy-DB fixtures)
  - scripts/audit_corpus_sync.py    (legacy migration SQL only — must be
                                     migrated separately; new audit reads
                                     annotations_current)

Phase A of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


# Files that legitimately touch raw `annotations` (writers, replay
# verifier, projection unit tests). Matched as path suffix.
ALLOWLIST_SUFFIXES = (
    "corpus_core/index.py",
    "corpus_core/replay.py",
    "corpus_core/maintain.py",
    "tests/test_replay.py",
    "tests/test_annotations_index.py",
    "tests/test_schema_version.py",
    "tests/test_graph_rebuild_idempotent.py",
    "tests/test_bitemporal.py",      # asserts BOTH raw + view contents
    # The lint itself contains references in docstrings/strings.
    "scripts/lint_no_bare_annotations_read.py",
    # Lint test fixtures intentionally include violating snippets.
    "scripts/tests/test_lint_no_bare_annotations.py",
)

# Match SQL fragments that read from `annotations` but NOT
# `annotations_current` (the view). Word-boundary terminator prevents
# matching `annotations_current`, `annotations_history`, etc.
_PATTERN = re.compile(r"\bFROM\s+annotations\b(?!_)", re.IGNORECASE)


def _is_allowlisted(path: Path) -> bool:
    posix = path.as_posix()
    return any(posix.endswith(s) for s in ALLOWLIST_SUFFIXES)


def _iter_string_literals(source: str) -> list[tuple[int, str]]:
    """Yield (lineno, string_value) for every string literal in the source.

    Uses ast so we ignore comments and don't match `FROM annotations` in
    a function name. Falls back to regex on syntax errors (non-Python files).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Non-Python or invalid; line-by-line scan.
        return [(i + 1, line) for i, line in enumerate(source.splitlines())]

    out: list[tuple[int, str]] = []

    class StringVisitor(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str):
                out.append((node.lineno, node.value))
            self.generic_visit(node)

        def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
            # f-string: collect literal segments BUT do NOT recurse into
            # children via generic_visit (would double-count via visit_Constant).
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append((v.lineno, v.value))
                elif isinstance(v, ast.FormattedValue):
                    # The interpolated expression — walk it (rare nested
                    # f-strings) but skip duplicating its raw constants.
                    self.visit(v)

    StringVisitor().visit(tree)
    return out


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Returns [(lineno, matched_text), ...] for violations in this file."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    violations: list[tuple[int, str]] = []
    for lineno, literal in _iter_string_literals(source):
        for match in _PATTERN.finditer(literal):
            # Capture surrounding context (the literal it appears in).
            start = max(0, match.start() - 20)
            end = min(len(literal), match.end() + 30)
            violations.append((lineno, literal[start:end].strip()))
    return violations


def scan_paths(paths: list[Path]) -> dict[Path, list[tuple[int, str]]]:
    out: dict[Path, list[tuple[int, str]]] = {}
    for root in paths:
        if root.is_file():
            files = [root]
        else:
            files = list(root.rglob("*.py"))
        for fpath in files:
            if _is_allowlisted(fpath):
                continue
            if "__pycache__" in fpath.parts or ".venv" in fpath.parts:
                continue
            violations = scan_file(fpath)
            if violations:
                out[fpath] = violations
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="Files or dirs to scan (default: scripts/ + packages/)",
    )
    args = parser.parse_args()

    if not args.paths:
        repo_root = Path(__file__).resolve().parent.parent
        args.paths = [
            repo_root / "scripts",
            repo_root / "scripts" / "corpus" / "packages",
        ]

    violations = scan_paths(args.paths)
    if not violations:
        return 0

    print("Violation: raw `FROM annotations` outside writer allowlist.", file=sys.stderr)
    print("Read paths should use the chain-aware `annotations_current` view.", file=sys.stderr)
    print(file=sys.stderr)
    for path, vs in violations.items():
        for lineno, ctx in vs:
            print(f"  {path}:{lineno}: {ctx}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
