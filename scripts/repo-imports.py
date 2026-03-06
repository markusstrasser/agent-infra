#!/usr/bin/env python3
"""Cross-file import graph for Python projects.

Shows who imports what from where — the missing link between
repo-outline (per-file structure) and callgraph (per-file calls).

Usage:
  repo-imports.py <path>              # full import graph
  repo-imports.py <path> --internal   # only imports between project files
  repo-imports.py <path> --for <module>  # what imports this module?
  repo-imports.py <path> --deps       # group by external dependency

Examples:
  repo-imports.py src/                         # all imports
  repo-imports.py src/ --internal              # just cross-file refs
  repo-imports.py src/ --for db                # who uses db module?
  repo-imports.py ~/Projects/papers-mcp --deps # external dep usage map
"""
import ast
import sys
from pathlib import Path
from collections import defaultdict


def gather_py_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    skip = {".git", "__pycache__", ".venv", "node_modules", ".tox", ".mypy_cache"}
    return sorted(
        f for f in path.rglob("*.py")
        if not any(p in skip for p in f.parts)
    )


def module_name(filepath: Path, base: Path) -> str:
    """Convert file path to dotted module name."""
    rel = filepath.relative_to(base)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def extract_imports(filepath: Path) -> list[dict]:
    """Extract all imports from a Python file."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "name": None,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append({
                    "module": mod,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
    return imports


def is_stdlib(module: str) -> bool:
    """Rough check if a module is stdlib."""
    # Top-level stdlib modules (Python 3.12+). Not exhaustive but covers common ones.
    STDLIB = {
        "abc", "argparse", "ast", "asyncio", "base64", "binascii", "bisect",
        "builtins", "calendar", "cgi", "cmd", "codecs", "collections",
        "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "csv", "ctypes", "dataclasses",
        "datetime", "dbm", "decimal", "difflib", "dis", "email", "encodings",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
        "fnmatch", "fractions", "ftplib", "functools", "gc", "getpass",
        "gettext", "glob", "gzip", "hashlib", "heapq", "hmac", "html",
        "http", "imaplib", "importlib", "inspect", "io", "ipaddress",
        "itertools", "json", "keyword", "linecache", "locale", "logging",
        "lzma", "mailbox", "math", "mimetypes", "mmap", "multiprocessing",
        "numbers", "operator", "os", "pathlib", "pdb", "pickle", "pkgutil",
        "platform", "plistlib", "poplib", "posixpath", "pprint", "profile",
        "pstats", "queue", "quopri", "random", "re", "readline", "reprlib",
        "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
        "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtplib",
        "socket", "socketserver", "sqlite3", "ssl", "stat", "statistics",
        "string", "struct", "subprocess", "sys", "sysconfig", "syslog",
        "tarfile", "tempfile", "termios", "textwrap", "threading", "time",
        "timeit", "token", "tokenize", "tomllib", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "types", "typing", "unicodedata",
        "unittest", "urllib", "uuid", "venv", "warnings", "wave", "weakref",
        "webbrowser", "xml", "xmlrpc", "zipfile", "zipimport", "zlib",
        "_thread", "__future__",
    }
    top = module.split(".")[0]
    return top in STDLIB


def build_import_graph(path: Path):
    files = gather_py_files(path)
    if not files:
        print(f"No Python files found in {path}")
        return None

    base = path if path.is_dir() else path.parent

    # Build module name -> file mapping
    internal_modules = {}
    for f in files:
        mod = module_name(f, base)
        internal_modules[mod] = f

    # Build import graph
    graph = {}  # {file_module: [import_records]}
    for f in files:
        mod = module_name(f, base)
        imps = extract_imports(f)
        for imp in imps:
            # Classify: internal, stdlib, or external
            target = imp["module"]
            top = target.split(".")[0]
            if top in internal_modules or target in internal_modules:
                imp["kind"] = "internal"
            elif is_stdlib(target):
                imp["kind"] = "stdlib"
            else:
                imp["kind"] = "external"
        graph[mod] = imps

    return graph, internal_modules, files, base


def cmd_full(path: Path):
    result = build_import_graph(path)
    if not result:
        return
    graph, internal_modules, files, base = result

    print(f"# Import graph: {path}")
    print(f"# {len(files)} files\n")

    for mod in sorted(graph):
        imps = graph[mod]
        if not imps:
            continue
        print(f"## {mod}")
        for imp in sorted(imps, key=lambda x: (x["kind"], x["module"])):
            name_part = f".{imp['name']}" if imp["name"] else ""
            kind_tag = f"[{imp['kind'][:3]}]"
            print(f"  L{imp['line']:>4}  {kind_tag} {imp['module']}{name_part}")
        print()


def cmd_internal(path: Path):
    result = build_import_graph(path)
    if not result:
        return
    graph, internal_modules, files, base = result

    print(f"# Internal import graph: {path}")
    print(f"# {len(files)} files\n")

    edges = defaultdict(set)
    for mod, imps in graph.items():
        for imp in imps:
            if imp["kind"] == "internal":
                target = imp["module"]
                name = imp["name"]
                label = f"{target}.{name}" if name else target
                edges[mod].add(label)

    for mod in sorted(edges):
        targets = sorted(edges[mod])
        print(f"  {mod} -> {', '.join(targets)}")


def cmd_for_module(path: Path, target: str):
    result = build_import_graph(path)
    if not result:
        return
    graph, internal_modules, files, base = result

    print(f"# Who imports '{target}'?\n")

    for mod, imps in sorted(graph.items()):
        matches = [
            imp for imp in imps
            if target in imp["module"] or (imp["name"] and target in imp["name"])
        ]
        if matches:
            for imp in matches:
                name_part = f".{imp['name']}" if imp["name"] else ""
                print(f"  {mod} (L{imp['line']}) <- {imp['module']}{name_part}")


def cmd_deps(path: Path):
    result = build_import_graph(path)
    if not result:
        return
    graph, internal_modules, files, base = result

    print(f"# External dependencies: {path}")
    print(f"# {len(files)} files\n")

    # Group by top-level package
    dep_usage = defaultdict(lambda: defaultdict(set))  # {pkg: {module: {names}}}
    for mod, imps in graph.items():
        for imp in imps:
            if imp["kind"] == "external":
                top = imp["module"].split(".")[0]
                name = imp["name"] or imp["module"]
                dep_usage[top][mod].add(name)

    for pkg in sorted(dep_usage):
        users = dep_usage[pkg]
        all_names = set()
        for names in users.values():
            all_names |= names
        print(f"  {pkg}")
        print(f"    used by: {', '.join(sorted(users))}")
        print(f"    imports: {', '.join(sorted(all_names))}")
        print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="File or directory to analyze")
    parser.add_argument("--internal", action="store_true", help="Only show cross-file imports within the project")
    parser.add_argument("--for", dest="for_module", metavar="MODULE", help="Show who imports this module/name")
    parser.add_argument("--deps", action="store_true", help="Group by external dependency")
    args = parser.parse_args()

    path = args.path.resolve()
    if not path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    if args.internal:
        cmd_internal(path)
    elif args.for_module:
        cmd_for_module(path, args.for_module)
    elif args.deps:
        cmd_deps(path)
    else:
        cmd_full(path)


if __name__ == "__main__":
    main()
