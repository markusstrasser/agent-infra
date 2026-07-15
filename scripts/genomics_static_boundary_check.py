#!/usr/bin/env python3
"""Verify the staged genomics static-data boundary from neutral orchestration."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

DEFAULT_GENOMICS_ROOT = Path.home() / "Projects" / "genomics"
RETIRED_GENOMICS_RESYNC_LABEL = "bio.synthoria.phenome.genomics-resync"
RETIRED_PYTHON_TOKENS = (
    "phenome_behavior_bridge",
    "validate_phenome_schema_sync",
)
RETIRED_GENOMICS_PATHS = (
    "scripts/phenome_behavior_bridge.py",
    "scripts/validate_phenome_schema_sync.py",
    "tests/test_bridge_contract_parity.py",
    "tests/test_bridge_registry_parity.py",
)
IGNORED_PYTHON_PARTS = frozenset({"archive", "archives", "fixtures"})
MISSING_LAUNCHD_MARKERS = (
    "could not find service",
    "service not found",
)

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class StaticBoundaryError(RuntimeError):
    """The staged producer tree or retired runtime violates the static boundary."""


def _run(
    command: Sequence[str], *, runner: CommandRunner | None = None
) -> subprocess.CompletedProcess[str]:
    if runner is not None:
        return runner(command)
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise StaticBoundaryError(f"cannot run {command[0]}: {exc}") from exc


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", "-C", os.fspath(repo), *args])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise StaticBoundaryError(
            f"git {' '.join(args)} failed for {repo}: {detail}"
        )
    return result.stdout.strip()


def _git_index_texts(repo: Path, paths: Sequence[Path]) -> dict[Path, str]:
    """Read exact stage-0 blobs in one binary Git transaction."""
    expressions: list[bytes] = []
    for path in paths:
        relative = path.as_posix()
        if "\n" in relative:
            raise StaticBoundaryError(
                f"cannot inspect newline-bearing Git path: {relative!r}"
            )
        expressions.append(f":{relative}\n".encode())
    try:
        result = subprocess.run(
            ["git", "-C", os.fspath(repo), "cat-file", "--batch"],
            input=b"".join(expressions),
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise StaticBoundaryError(f"cannot run git cat-file: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode(errors="replace").strip()
        raise StaticBoundaryError(f"git cat-file --batch failed for {repo}: {detail}")

    decoded: dict[Path, str] = {}
    offset = 0
    for path in paths:
        header_end = result.stdout.find(b"\n", offset)
        if header_end < 0:
            raise StaticBoundaryError(f"missing Git batch header for indexed path {path}")
        header = result.stdout[offset:header_end]
        if header.endswith(b" missing"):
            raise StaticBoundaryError(f"indexed path has no stage-0 blob: {path}")
        fields = header.rsplit(b" ", 2)
        if len(fields) != 3 or fields[1] != b"blob":
            raise StaticBoundaryError(
                f"unexpected Git batch header for indexed path {path}: "
                f"{header.decode(errors='replace')}"
            )
        try:
            byte_count = int(fields[2])
        except ValueError as exc:
            raise StaticBoundaryError(
                f"invalid Git batch size for indexed path {path}: {fields[2]!r}"
            ) from exc
        content_start = header_end + 1
        content_end = content_start + byte_count
        if result.stdout[content_end : content_end + 1] != b"\n":
            raise StaticBoundaryError(f"truncated Git batch blob for indexed path {path}")
        try:
            decoded[path] = result.stdout[content_start:content_end].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StaticBoundaryError(f"indexed path is not UTF-8: {path}") from exc
        offset = content_end + 1
    if offset != len(result.stdout):
        raise StaticBoundaryError("unexpected trailing bytes from git cat-file --batch")
    return decoded


def _tracked_python_files(repo: Path) -> list[Path]:
    output = _git(repo, "ls-files", "--", "*.py")
    files: list[Path] = []
    for raw in output.splitlines():
        relative = Path(raw)
        if relative.parts and relative.parts[0] == "docs":
            continue
        if any(part in IGNORED_PYTHON_PARTS for part in relative.parts):
            continue
        files.append(relative)
    return files


def _python_retired_references(path: Path, source: str) -> list[str]:
    try:
        tree = ast.parse(source, filename=os.fspath(path))
    except (SyntaxError, ValueError) as exc:
        raise StaticBoundaryError(f"cannot inspect active Python file {path}: {exc}") from exc
    found: set[str] = set()
    for node in ast.walk(tree):
        values: list[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                values.append(node.module)
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            values.append(node.id)
        elif isinstance(node, ast.Attribute):
            values.append(node.attr)
        for value in values:
            found.update(token for token in RETIRED_PYTHON_TOKENS if token in value)
    return sorted(found)


def verify_retired_genomics_resync_absent(
    *, runner: CommandRunner | None, uid: int
) -> dict[str, str]:
    domain = f"gui/{uid}"
    result = _run(
        ["launchctl", "print", f"{domain}/{RETIRED_GENOMICS_RESYNC_LABEL}"],
        runner=runner,
    )
    if result.returncode == 0:
        raise StaticBoundaryError(
            f"retired launchd job remains loaded: {RETIRED_GENOMICS_RESYNC_LABEL}"
        )
    detail = f"{result.stdout}\n{result.stderr}".lower()
    if not any(marker in detail for marker in MISSING_LAUNCHD_MARKERS):
        raise StaticBoundaryError(
            "cannot prove retired launchd job absent: "
            f"launchctl exited {result.returncode}: {detail.strip()}"
        )
    return {"label": RETIRED_GENOMICS_RESYNC_LABEL, "status": "absent"}


def verify_genomics_static_boundary(
    genomics_root: Path,
) -> dict[str, Any]:
    if genomics_root.is_symlink() or not genomics_root.is_dir():
        raise StaticBoundaryError(
            f"genomics repository is not a real directory: {genomics_root}"
        )
    tracked_paths = set(_git(genomics_root, "ls-files", "--cached").splitlines())
    for relative in RETIRED_GENOMICS_PATHS:
        if relative in tracked_paths:
            raise StaticBoundaryError(
                f"retired genomics file remains in Git index: {relative}"
            )
    if "justfile" not in tracked_paths:
        raise StaticBoundaryError("genomics justfile is missing from Git index")

    active_files = _tracked_python_files(genomics_root)
    indexed_text = _git_index_texts(genomics_root, [Path("justfile"), *active_files])
    recipe = re.compile(r"(?m)^prs-schema-sync(?:\s+[^:]*)?:\s*(?:#.*)?$")
    if recipe.search(indexed_text[Path("justfile")]):
        raise StaticBoundaryError("retired genomics recipe remains: prs-schema-sync")

    references: dict[str, list[str]] = {}
    for relative in active_files:
        found = _python_retired_references(relative, indexed_text[relative])
        if found:
            references[relative.as_posix()] = found
    if references:
        detail = "; ".join(
            f"{path}: {','.join(tokens)}" for path, tokens in sorted(references.items())
        )
        raise StaticBoundaryError(
            f"active genomics Python still references retired bridges: {detail}"
        )

    return {
        "root": os.fspath(genomics_root),
        "evidence_plane": "git_index",
        "active_python_files_scanned": len(active_files),
        "retired_files_absent": list(RETIRED_GENOMICS_PATHS),
        "retired_recipe_absent": "prs-schema-sync",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--genomics-root",
        type=Path,
        default=DEFAULT_GENOMICS_ROOT,
        help="genomics checkout or worktree whose Git index is authoritative",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    launchctl_runner: CommandRunner | None = None,
    uid: int | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        boundary = verify_genomics_static_boundary(args.genomics_root)
        retired_launchd = verify_retired_genomics_resync_absent(
            runner=launchctl_runner,
            uid=os.getuid() if uid is None else uid,
        )
    except StaticBoundaryError as exc:
        print(
            json.dumps(
                {"schema_version": 1, "status": "FAIL", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema_version": 1,
                "status": "PASS",
                "checks": {
                    "genomics_static_boundary": boundary,
                    "retired_genomics_resync": retired_launchd,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
