#!/usr/bin/env python3
"""Lightweight code structure tools for agent navigation.

Four modes:
  outline  — TOC of classes/functions with signatures, one line each
  callgraph — same-file calls from the canonical relation graph
  xrefs    — resolved cross-file calls from the canonical relation graph
  symbol   — extract and print the full source of a named function/class

Uses only stdlib `ast`. Zero deps, zero index, reads live code.
Python-only — non-Python files are not supported.

Usage:
  repo-outline.py outline <path>          # file or directory
  repo-outline.py outline <path> --depth 1  # classes only, skip methods
  repo-outline.py callgraph <path>        # call edges within scope
  repo-outline.py callgraph <path> --external  # include imported/unresolved calls
  repo-outline.py xrefs <path>            # cross-file call edges
  repo-outline.py xrefs <path> --for NAME # who calls NAME across the project?
  repo-outline.py symbol <file> <name>    # print full source of class/function
"""
import ast
import sys
from pathlib import Path
from collections import defaultdict

from code_relations import Confidence, build_code_relations, gather_python_files


def _log_usage(script: str, subcommand: str, path: Path):
    """Append one line to usage log. Fire-and-forget."""
    import json
    import time
    log = Path.home() / ".cache" / "repo-tools-usage.jsonl"
    try:
        with open(log, "a") as f:
            f.write(json.dumps({"ts": time.time(), "script": script,
                                "cmd": subcommand, "path": str(path)}) + "\n")
    except Exception:
        pass


def format_args(node: ast.FunctionDef) -> str:
    """Compact argument signature."""
    parts = []
    args = node.args

    # positional args
    defaults_offset = len(args.args) - len(args.defaults)
    for i, arg in enumerate(args.args):
        if arg.arg == "self" or arg.arg == "cls":
            continue
        s = arg.arg
        if arg.annotation:
            s += f": {ast.unparse(arg.annotation)}"
        di = i - defaults_offset
        if di >= 0 and di < len(args.defaults):
            s += f"={ast.unparse(args.defaults[di])}"
        parts.append(s)

    if args.vararg:
        s = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            s += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(s)

    for i, arg in enumerate(args.kwonlyargs):
        s = arg.arg
        if arg.annotation:
            s += f": {ast.unparse(arg.annotation)}"
        if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
            s += f"={ast.unparse(args.kw_defaults[i])}"
        parts.append(s)

    if args.kwarg:
        s = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            s += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(s)

    return ", ".join(parts)


def format_return(node: ast.FunctionDef) -> str:
    if node.returns:
        return f" -> {ast.unparse(node.returns)}"
    return ""


def outline_file(filepath: Path, base: Path, max_depth: int = 99) -> list[str]:
    """Generate outline lines for a single file."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    rel = filepath.relative_to(base) if base != filepath else filepath.name
    lines = [f"\n## {rel}"]

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            bases_str = f"({bases})" if bases else ""
            lines.append(f"  L{node.lineno:>4}  class {node.name}{bases_str}")

            if max_depth >= 2:
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                        prefix = "async " if isinstance(child, ast.AsyncFunctionDef) else ""
                        args = format_args(child)
                        ret = format_return(child)
                        lines.append(
                            f"  L{child.lineno:>4}    {prefix}def {child.name}({args}){ret}"
                        )

        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            args = format_args(node)
            ret = format_return(node)
            lines.append(f"  L{node.lineno:>4}  {prefix}def {node.name}({args}){ret}")

    # Only return if there's actual content beyond the header
    return lines if len(lines) > 1 else []


def outline(path: Path, max_depth: int = 99):
    files = gather_python_files(path)
    if not files:
        print(f"No Python files found in {path}")
        return

    base = path if path.is_dir() else path.parent
    total_lines = []
    for f in files:
        total_lines.extend(outline_file(f, base, max_depth))

    print(f"# Outline: {path}")
    print(f"# {len(files)} files")
    for line in total_lines:
        print(line)


def callgraph(path: Path, include_external: bool = False):
    files = gather_python_files(path)
    if not files:
        print(f"No Python files found in {path}")
        return

    base = path if path.is_dir() else path.parent
    graph = build_code_relations(
        base,
        python_source_dirs=[base],
        include_operational=False,
        include_unresolved_calls=include_external,
    )
    graph.require_complete()
    selected = {f.relative_to(base).as_posix() for f in files}
    by_file: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for edge in graph.relations_of_type("calls"):
        source = graph.nodes[edge.source]
        target = graph.nodes[edge.target]
        if not source.path or source.path not in selected:
            continue
        if edge.confidence is Confidence.AMBIGUOUS:
            continue
        if not include_external and target.path != source.path:
            continue
        caller = source.qualname or "<module>"
        callee = target.qualname or target.label
        by_file[source.path][caller].add(callee)

    print(f"# Call graph: {path}")
    print(f"# {len(files)} files, {'including' if include_external else 'excluding'} external calls")
    for rel in sorted(by_file):
        print(f"\n## {rel}")
        for caller in sorted(by_file[rel]):
            print(f"  {caller} -> {', '.join(sorted(by_file[rel][caller]))}")


def symbol(filepath: Path, name: str):
    """Extract and print the full source of a named function/class."""
    source = filepath.read_text()

    # Try AST first
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        # Fallback: grep for def/class lines
        lines = source.splitlines()
        matches = []
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if (stripped.startswith(f"def {name}(") or
                stripped.startswith(f"def {name} (") or
                stripped.startswith(f"class {name}(") or
                stripped.startswith(f"class {name}:") or
                stripped.startswith(f"class {name} ") or
                stripped.startswith(f"async def {name}(") or
                stripped.startswith(f"async def {name} (")):
                matches.append(i)
        if not matches:
            print(f"No symbol '{name}' found in {filepath} (AST failed, grep fallback)")
            sys.exit(1)
        print(f"# SyntaxError — showing grep matches for '{name}' in {filepath}")
        for lineno in matches:
            start = max(0, lineno - 1)
            end = min(len(lines), lineno + 20)
            for i in range(start, end):
                print(f"  {i+1:>5}  {lines[i]}")
            print()
        return

    # Walk AST to find matching nodes (top-level and nested)
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                matches.append(node)

    if not matches:
        print(f"No symbol '{name}' found in {filepath}")
        sys.exit(1)

    if len(matches) > 1:
        print(f"# {len(matches)} matches for '{name}' in {filepath}:")
        for node in matches:
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            print(f"  L{node.lineno:>5}  {kind} {node.name}")
        print(f"\n# Showing all {len(matches)} definitions:\n")

    source_lines = source.splitlines()
    for node in matches:
        start = node.lineno - 1
        end = node.end_lineno  # end_lineno is 1-based inclusive
        print(f"# {filepath}:{node.lineno}")
        for i in range(start, end):
            print(f"  {i+1:>5}  {source_lines[i]}")
        print()

    _log_usage("repo-outline", "symbol", filepath)


def xrefs(path: Path, target: str = ""):
    """Cross-file calls from the canonical evidence-bound relation graph."""
    base = path if path.is_dir() else path.parent
    graph = build_code_relations(
        base,
        python_source_dirs=[base],
        include_operational=False,
    )
    graph.require_complete()
    files = gather_python_files(path)

    def module_label(rel: str) -> str:
        return rel.removesuffix(".py").replace("/", ".")

    cross_edges = []  # (src_mod, caller, dst_mod, dst_name, lineno)
    for edge in graph.relations_of_type("calls"):
        source = graph.nodes[edge.source]
        destination = graph.nodes[edge.target]
        if edge.confidence is Confidence.AMBIGUOUS:
            continue
        if not source.path or not destination.path or source.path == destination.path:
            continue
        cross_edges.append(
            (
                module_label(source.path),
                source.qualname or "<module>",
                module_label(destination.path),
                destination.qualname or destination.label,
                edge.evidence.line,
            )
        )

    # Output
    if target:
        matches = [
            edge
            for edge in cross_edges
            if edge[3] == target or edge[3].split(".")[-1] == target
        ]
        if not matches:
            print(f"# No cross-file callers of '{target}' found")
            return
        print(f"# Who calls '{target}'?\n")
        for src, caller, dst, name, lineno in sorted(matches):
            print(f"  {src}.{caller} (L{lineno}) -> {dst}.{name}")
    else:
        print(f"# Cross-file calls: {path}")
        print(f"# {len(files)} files, {len(cross_edges)} cross-file edges\n")
        by_source = defaultdict(lambda: defaultdict(list))
        for src, caller, dst, name, _ln in cross_edges:
            by_source[src][caller].append(f"{dst}.{name}")
        for src in sorted(by_source):
            for caller in sorted(by_source[src]):
                targets = sorted(set(by_source[src][caller]))
                print(f"  {src}.{caller} -> {', '.join(targets)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    path = Path(sys.argv[2]).resolve()

    if not path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    if mode == "outline":
        depth = 99
        if "--depth" in sys.argv:
            idx = sys.argv.index("--depth")
            depth = int(sys.argv[idx + 1])
        outline(path, max_depth=depth)
        _log_usage("repo-outline", "outline", path)

    elif mode == "callgraph":
        include_external = "--external" in sys.argv
        callgraph(path, include_external=include_external)
        _log_usage("repo-outline", "callgraph", path)

    elif mode == "xrefs":
        target_name = ""
        if "--for" in sys.argv:
            idx = sys.argv.index("--for")
            target_name = sys.argv[idx + 1]
        xrefs(path, target=target_name)
        _log_usage("repo-outline", "xrefs", path)

    elif mode == "symbol":
        if len(sys.argv) < 4:
            print("Usage: repo-outline.py symbol <file> <name>")
            sys.exit(1)
        sym_name = sys.argv[3]
        symbol(path, sym_name)

    else:
        print(f"Unknown mode: {mode}. Use 'outline', 'callgraph', 'xrefs', or 'symbol'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
