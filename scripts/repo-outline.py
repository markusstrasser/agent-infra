#!/usr/bin/env python3
"""Lightweight code structure tools for agent navigation.

Two modes:
  outline  — TOC of classes/functions with signatures, one line each
  callgraph — who-calls-what within a file or directory

Uses only stdlib `ast`. Zero deps, zero index, reads live code.

Usage:
  repo-outline.py outline <path>          # file or directory
  repo-outline.py outline <path> --depth 1  # classes only, skip methods
  repo-outline.py callgraph <path>        # call edges within scope
  repo-outline.py callgraph <path> --external  # include calls to imported names
"""
import ast
import sys
import os
from pathlib import Path
from collections import defaultdict


def gather_py_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    files = sorted(path.rglob("*.py"))
    # skip hidden dirs, __pycache__, .venv, node_modules
    skip = {".git", "__pycache__", ".venv", "node_modules", ".tox", ".mypy_cache"}
    return [f for f in files if not any(p in skip for p in f.parts)]


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
    files = gather_py_files(path)
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


class CallGraphVisitor(ast.NodeVisitor):
    """Extract call edges from a function/method body."""

    def __init__(self):
        self.current_scope = None
        self.edges = []  # (caller, callee)
        self.defined = set()  # names defined in this scope

    def visit_FunctionDef(self, node):
        self.defined.add(node.name)
        old_scope = self.current_scope
        self.current_scope = node.name
        self.generic_visit(node)
        self.current_scope = old_scope

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.defined.add(node.name)
        old_scope = self.current_scope
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                method_name = f"{node.name}.{child.name}"
                self.defined.add(method_name)
                self.current_scope = method_name
                self.generic_visit(child)
        self.current_scope = old_scope

    def visit_Call(self, node):
        if self.current_scope is None:
            self.generic_visit(node)
            return

        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # obj.method — try to resolve
            if isinstance(node.func.value, ast.Name):
                callee = f"{node.func.value.id}.{node.func.attr}"
            else:
                callee = f"?.{node.func.attr}"

        if callee:
            self.edges.append((self.current_scope, callee))

        self.generic_visit(node)


def callgraph_file(filepath: Path, base: Path, include_external: bool) -> list[str]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = CallGraphVisitor()
    visitor.visit(tree)

    if not visitor.edges:
        return []

    rel = filepath.relative_to(base) if base != filepath else filepath.name
    lines = [f"\n## {rel}"]

    # Group by caller
    by_caller = defaultdict(list)
    for caller, callee in visitor.edges:
        if not include_external and callee not in visitor.defined:
            # Check if it's a method of a defined class
            if "." in callee:
                cls = callee.split(".")[0]
                if cls not in visitor.defined:
                    continue
        by_caller[caller].append(callee)

    for caller in sorted(by_caller):
        callees = sorted(set(by_caller[caller]))
        lines.append(f"  {caller} -> {', '.join(callees)}")

    return lines if len(lines) > 1 else []


def callgraph(path: Path, include_external: bool = False):
    files = gather_py_files(path)
    if not files:
        print(f"No Python files found in {path}")
        return

    base = path if path.is_dir() else path.parent
    total_lines = []
    for f in files:
        total_lines.extend(callgraph_file(f, base, include_external))

    print(f"# Call graph: {path}")
    print(f"# {len(files)} files, {'including' if include_external else 'excluding'} external calls")
    for line in total_lines:
        print(line)


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

    elif mode == "callgraph":
        include_external = "--external" in sys.argv
        callgraph(path, include_external=include_external)

    else:
        print(f"Unknown mode: {mode}. Use 'outline' or 'callgraph'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
