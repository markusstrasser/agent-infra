#!/usr/bin/env python3
"""Evidence-bound static relationships for repository code and operations.

The graph is rebuilt from source for each consumer. It is a locator, not an
execution oracle: every edge names the source line that justified it and marks
whether the target was extracted, uniquely resolved, or ambiguous.

Supported relationships:

- Python definitions, imports, direct calls, and subprocess/script execution
- shell script execution and sourcing
- Just recipe execution
- launchd ProgramArguments

Usage:
  code_relations.py impact <repo> <target> [--source-dirs scripts,src]
  code_relations.py validate <repo> [--source-dirs scripts,src] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import plistlib
import re
import sys
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator


SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
CODE_SUFFIXES = {".py", ".sh"}
EXEC_CALLS = {
    "Popen",
    "call",
    "check_call",
    "check_output",
    "execv",
    "execve",
    "run",
    "system",
}
TRAVERSAL_RELATIONS = {
    "calls",
    "executes",
    "imports",
    "invokes_recipe",
    "launches",
    "sources",
}


class Confidence(str, Enum):
    EXTRACTED = "EXTRACTED"
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class CodeNode:
    id: str
    kind: str
    label: str
    path: str | None = None
    line: int | None = None
    qualname: str | None = None


@dataclass(frozen=True)
class Evidence:
    path: str
    line: int
    snippet: str


@dataclass(frozen=True)
class CodeRelation:
    source: str
    target: str
    relation: str
    confidence: Confidence
    evidence: Evidence


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    path: str | None = None
    line: int | None = None
    severity: str = "warning"


@dataclass(frozen=True)
class ImpactHop:
    depth: int
    relation: CodeRelation


class AmbiguousTargetError(ValueError):
    """Raised when a short query matches multiple stable node identities."""


def _relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def file_node_id(path: str) -> str:
    return f"file:{path}"


def symbol_node_id(path: str, qualname: str, line: int) -> str:
    return f"symbol:{path}::{qualname}@{line}"


def recipe_node_id(name: str) -> str:
    return f"recipe:justfile::{name}"


def launchd_node_id(path: str, label: str) -> str:
    return f"launchd:{path}::{label}"


class CodeRelationGraph:
    """In-memory relation graph with stable identities and source evidence."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.nodes: dict[str, CodeNode] = {}
        self.relations: list[CodeRelation] = []
        self.diagnostics: list[Diagnostic] = []
        self._relation_keys: set[tuple[object, ...]] = set()

    def add_node(self, node: CodeNode) -> str:
        existing = self.nodes.get(node.id)
        if (
            existing is not None
            and existing.kind == node.kind
            and existing.path == node.path
            and existing.qualname == node.qualname
            and existing.line is None
            and node.line is not None
        ):
            self.nodes[node.id] = node
            return node.id
        if existing is not None and existing != node:
            self.add_diagnostic(
                "node_identity_collision",
                f"node id {node.id!r} maps to conflicting definitions",
                path=node.path,
                line=node.line,
                severity="error",
            )
        else:
            self.nodes[node.id] = node
        return node.id

    def add_file(self, path: str, *, line: int = 1) -> str:
        return self.add_node(CodeNode(file_node_id(path), "file", path, path, line))

    def add_symbol(self, path: str, qualname: str, line: int, kind: str) -> str:
        return self.add_node(
            CodeNode(
                symbol_node_id(path, qualname, line),
                kind,
                qualname,
                path,
                line,
                qualname,
            )
        )

    def add_diagnostic(
        self,
        code: str,
        message: str,
        *,
        path: str | None = None,
        line: int | None = None,
        severity: str = "warning",
    ) -> None:
        diagnostic = Diagnostic(code, message, path, line, severity)
        if diagnostic not in self.diagnostics:
            self.diagnostics.append(diagnostic)

    def add_relation(
        self,
        source: str,
        target: str,
        relation: str,
        confidence: Confidence,
        *,
        path: str,
        line: int,
        snippet: str,
    ) -> None:
        evidence = Evidence(path, line, snippet.strip())
        key = (source, target, relation, confidence, path, line, evidence.snippet)
        if key in self._relation_keys:
            return
        self._relation_keys.add(key)
        self.relations.append(
            CodeRelation(source, target, relation, confidence, evidence)
        )

    def validate(self) -> list[Diagnostic]:
        """Return parse/resolution diagnostics plus structural integrity errors."""
        out = list(self.diagnostics)
        seen: set[tuple[object, ...]] = set()
        for relation in self.relations:
            key = (
                relation.source,
                relation.target,
                relation.relation,
                relation.confidence,
                relation.evidence,
            )
            if key in seen:
                out.append(
                    Diagnostic(
                        "duplicate_relation",
                        f"duplicate {relation.relation} relation",
                        relation.evidence.path,
                        relation.evidence.line,
                        "error",
                    )
                )
            seen.add(key)
            for endpoint_name, endpoint in (
                ("source", relation.source),
                ("target", relation.target),
            ):
                if endpoint not in self.nodes:
                    out.append(
                        Diagnostic(
                            "dangling_endpoint",
                            f"{endpoint_name} node {endpoint!r} does not exist",
                            relation.evidence.path,
                            relation.evidence.line,
                            "error",
                        )
                    )
            if not relation.evidence.path or relation.evidence.line < 1 or not relation.evidence.snippet:
                out.append(
                    Diagnostic(
                        "missing_evidence",
                        f"{relation.relation} relation lacks complete source evidence",
                        relation.evidence.path or None,
                        relation.evidence.line or None,
                        "error",
                    )
                )
        return list(dict.fromkeys(out))

    def relations_of_type(self, *relation_types: str) -> list[CodeRelation]:
        wanted = set(relation_types)
        return [r for r in self.relations if r.relation in wanted]

    def file_edges(
        self,
        *relation_types: str,
        include_ambiguous: bool = False,
    ) -> dict[str, set[str]]:
        """Return repo-relative file-to-file edges for the selected relation types."""
        wanted = set(relation_types)
        edges: dict[str, set[str]] = defaultdict(set)
        for relation in self.relations:
            if wanted and relation.relation not in wanted:
                continue
            if not include_ambiguous and relation.confidence is Confidence.AMBIGUOUS:
                continue
            source = self.nodes.get(relation.source)
            target = self.nodes.get(relation.target)
            if not source or not target or not source.path or not target.path:
                continue
            if source.path != target.path:
                edges[source.path].add(target.path)
        return dict(edges)

    def fan_in(self, *relation_types: str) -> dict[str, int]:
        edges = self.file_edges(*relation_types)
        inbound: dict[str, int] = defaultdict(int)
        for targets in edges.values():
            for target in targets:
                inbound[target] += 1
        return dict(inbound)

    def nodes_in_cycles(self, *relation_types: str) -> set[str]:
        edges = self.file_edges(*relation_types)
        for node in {
            n.path for n in self.nodes.values() if n.kind == "file" and n.path
        }:
            edges.setdefault(node, set())
        return _nodes_in_cycles(edges)

    def resolve(self, query: str) -> list[str]:
        """Resolve an exact id/path/label; reject ambiguous basename shortcuts."""
        if query in self.nodes:
            return [query]
        normalized = query.removeprefix("./")
        exact = [
            node.id
            for node in self.nodes.values()
            if node.path == normalized
            or node.label == normalized
            or node.qualname == normalized
        ]
        if exact:
            return sorted(set(exact))
        short = [
            node.id
            for node in self.nodes.values()
            if node.path and Path(node.path).name == normalized
        ]
        paths = {self.nodes[node_id].path for node_id in short}
        if len(paths) > 1:
            raise AmbiguousTargetError(
                f"{query!r} matches multiple paths: {', '.join(sorted(p for p in paths if p))}"
            )
        return sorted(set(short))

    def impact(
        self,
        target: str,
        *,
        max_depth: int = 3,
        relation_types: Iterable[str] = TRAVERSAL_RELATIONS,
    ) -> list[ImpactHop]:
        """Traverse incoming edges from a target and preserve the deciding evidence."""
        seeds = self.resolve(target)
        if not seeds:
            return []
        seed_paths = {
            self.nodes[node_id].path for node_id in seeds if self.nodes[node_id].path
        }
        for node in self.nodes.values():
            if node.path in seed_paths:
                seeds.append(node.id)

        wanted = set(relation_types)
        incoming: dict[str, list[CodeRelation]] = defaultdict(list)
        for relation in self.relations:
            if relation.relation in wanted:
                source = self.nodes.get(relation.source)
                target_node = self.nodes.get(relation.target)
                if (
                    source
                    and target_node
                    and source.path
                    and source.path == target_node.path
                ):
                    continue
                incoming[relation.target].append(relation)

        queue = deque((node_id, 0) for node_id in sorted(set(seeds)))
        best_depth = {node_id: 0 for node_id in seeds}
        hops: list[ImpactHop] = []
        hop_keys: set[tuple[object, ...]] = set()
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for relation in incoming.get(current, []):
                next_depth = depth + 1
                key = (next_depth, relation)
                if key not in hop_keys:
                    hop_keys.add(key)
                    hops.append(ImpactHop(next_depth, relation))
                previous = best_depth.get(relation.source)
                if previous is None or next_depth < previous:
                    best_depth[relation.source] = next_depth
                    queue.append((relation.source, next_depth))
        return sorted(
            hops,
            key=lambda hop: (
                hop.depth,
                hop.relation.evidence.path,
                hop.relation.evidence.line,
                hop.relation.relation,
            ),
        )


@dataclass
class _PythonUnit:
    path: Path
    rel: str
    source: str
    lines: list[str]
    tree: ast.AST
    modules: tuple[str, ...]
    primary_module: str
    symbols_by_short: dict[str, list[str]]
    symbols_by_qualname: dict[str, str]


@dataclass
class _Binding:
    files: list[str]
    symbols: list[str]


class _DefinitionVisitor(ast.NodeVisitor):
    def __init__(self, graph: CodeRelationGraph, rel: str, lines: list[str]):
        self.graph = graph
        self.rel = rel
        self.lines = lines
        self.stack: list[str] = []
        self.by_short: dict[str, list[str]] = defaultdict(list)
        self.by_qualname: dict[str, str] = {}

    def _visit_definition(self, node: ast.AST, name: str, kind: str) -> None:
        qualname = ".".join([*self.stack, name])
        node_id = self.graph.add_symbol(self.rel, qualname, node.lineno, kind)
        self.by_short[name].append(node_id)
        self.by_qualname[qualname] = node_id
        self.graph.add_relation(
            file_node_id(self.rel),
            node_id,
            "contains",
            Confidence.EXTRACTED,
            path=self.rel,
            line=node.lineno,
            snippet=self.lines[node.lineno - 1],
        )
        self.stack.append(name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node, node.name, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node, node.name, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node, node.name, "function")


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, on_call):
        self.on_call = on_call
        self.stack: list[str] = []

    @property
    def scope(self) -> str | None:
        return ".".join(self.stack) if self.stack else None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self.on_call(node, self.scope)
        self.generic_visit(node)


class CodeRelationBuilder:
    def __init__(
        self,
        root: Path,
        *,
        source_dirs: Iterable[Path | str] | None = None,
        python_files: Iterable[Path | str] | None = None,
        include_operational: bool = True,
    ):
        self.root = root.resolve()
        self.source_dirs = self._normalize_source_dirs(source_dirs)
        self.explicit_python_files = list(python_files) if python_files is not None else None
        self.include_operational = include_operational
        self.graph = CodeRelationGraph(self.root)
        self.units: dict[str, _PythonUnit] = {}
        self.module_index: dict[str, set[str]] = defaultdict(set)
        self.module_stem_index: dict[str, set[str]] = defaultdict(set)
        self.basename_index: dict[str, set[str]] = defaultdict(set)

    def _normalize_source_dirs(
        self, source_dirs: Iterable[Path | str] | None
    ) -> list[Path]:
        if source_dirs is None:
            return [self.root]
        out: list[Path] = []
        for source_dir in source_dirs:
            path = Path(source_dir)
            if not path.is_absolute():
                path = self.root / path
            path = path.resolve()
            if path.exists() and path not in out:
                out.append(path)
        return out or [self.root]

    def build(self) -> CodeRelationGraph:
        python_paths = self._python_paths()
        operational_paths = self._operational_paths() if self.include_operational else set()
        for path in sorted(set(python_paths) | operational_paths):
            rel = _relpath(self.root, path)
            self.graph.add_file(rel)
            self.basename_index[path.name].add(file_node_id(rel))
        self._parse_python(python_paths)
        self._extract_python_relations()
        if self.include_operational:
            self._extract_shell(operational_paths)
            self._extract_justfile()
            self._extract_launchd()
        return self.graph

    def _python_paths(self) -> list[Path]:
        if self.explicit_python_files is not None:
            paths: list[Path] = []
            for item in self.explicit_python_files:
                path = Path(item)
                if not path.is_absolute():
                    path = self.root / path
                if path.is_file() and path.suffix == ".py":
                    paths.append(path.resolve())
            return sorted(set(paths))
        paths = set()
        for source_dir in self.source_dirs:
            paths.update(gather_python_files(source_dir))
        return sorted(paths)

    def _operational_paths(self) -> set[Path]:
        paths: set[Path] = set()
        for path in self.root.rglob("*.sh"):
            if not any(part in SKIP_DIRS for part in path.parts):
                paths.add(path.resolve())
        justfile = self.root / "justfile"
        if justfile.is_file():
            paths.add(justfile.resolve())
        for path in (self.root / "ops" / "launchd").glob("*.plist"):
            if path.is_file():
                paths.add(path.resolve())
        return paths

    def _module_aliases(self, path: Path) -> tuple[str, ...]:
        aliases: set[str] = set()
        bases = [self.root, *self.source_dirs]
        for base in bases:
            try:
                rel = path.relative_to(base)
            except ValueError:
                continue
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1].removesuffix(".py")
            if parts:
                aliases.add(".".join(parts))
        return tuple(sorted(aliases, key=lambda value: (value.count("."), len(value), value)))

    def _parse_python(self, paths: list[Path]) -> None:
        pending: list[tuple[Path, str, str, list[str], ast.AST, tuple[str, ...]]] = []
        for path in paths:
            rel = _relpath(self.root, path)
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                self.graph.add_diagnostic(
                    "python_parse_error",
                    str(exc),
                    path=rel,
                    line=getattr(exc, "lineno", None),
                )
                continue
            lines = source.splitlines()
            modules = self._module_aliases(path)
            pending.append((path, rel, source, lines, tree, modules))
            for module in modules:
                self.module_index[module].add(file_node_id(rel))
            if path.name != "__init__.py":
                self.module_stem_index[path.stem].add(file_node_id(rel))

        for path, rel, source, lines, tree, modules in pending:
            visitor = _DefinitionVisitor(self.graph, rel, lines)
            visitor.visit(tree)
            primary = next((m for m in modules if "." in m), modules[0] if modules else path.stem)
            self.units[rel] = _PythonUnit(
                path,
                rel,
                source,
                lines,
                tree,
                modules,
                primary,
                dict(visitor.by_short),
                visitor.by_qualname,
            )

    def _extract_python_relations(self) -> None:
        bindings: dict[str, dict[str, _Binding]] = {}
        for unit in self.units.values():
            bindings[unit.rel] = self._extract_imports(unit)
        for unit in self.units.values():
            self._extract_calls(unit, bindings[unit.rel])

    def _source_line(self, unit: _PythonUnit, line: int) -> str:
        return unit.lines[line - 1] if 0 < line <= len(unit.lines) else "<unknown>"

    def _absolute_import(self, unit: _PythonUnit, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        package = unit.primary_module.split(".")[:-1]
        up = max(0, node.level - 1)
        if up:
            package = package[:-up] if up <= len(package) else []
        if node.module:
            package.extend(node.module.split("."))
        return ".".join(package)

    def _module_candidates(self, module: str, imported_name: str | None = None) -> list[str]:
        if imported_name:
            child_candidates = self.module_index.get(
                f"{module}.{imported_name}".strip("."), set()
            )
            if child_candidates:
                return sorted(child_candidates)
        exact = self.module_index.get(module, set())
        if exact:
            return sorted(exact)
        if "." not in module:
            return sorted(self.module_stem_index.get(module, set()))
        return []

    def _add_resolved_edges(
        self,
        source: str,
        candidates: list[str],
        relation: str,
        unit: _PythonUnit,
        line: int,
        *,
        raw_target: str,
    ) -> None:
        snippet = self._source_line(unit, line)
        if len(candidates) == 1:
            self.graph.add_relation(
                source,
                candidates[0],
                relation,
                Confidence.RESOLVED,
                path=unit.rel,
                line=line,
                snippet=snippet,
            )
            return
        if len(candidates) > 1:
            for candidate in candidates:
                self.graph.add_relation(
                    source,
                    candidate,
                    relation,
                    Confidence.AMBIGUOUS,
                    path=unit.rel,
                    line=line,
                    snippet=snippet,
                )
            paths = [self.graph.nodes[candidate].path or candidate for candidate in candidates]
            self.graph.add_diagnostic(
                "ambiguous_target",
                f"{raw_target!r} matches {', '.join(paths)}",
                path=unit.rel,
                line=line,
            )
            return
        external_id = f"module:{raw_target}"
        self.graph.add_node(CodeNode(external_id, "module", raw_target))
        self.graph.add_relation(
            source,
            external_id,
            relation,
            Confidence.EXTRACTED,
            path=unit.rel,
            line=line,
            snippet=snippet,
        )

    def _symbols_in_files(self, files: list[str], name: str) -> list[str]:
        symbols: list[str] = []
        for file_id in files:
            path = self.graph.nodes[file_id].path
            if not path or path not in self.units:
                continue
            symbols.extend(self.units[path].symbols_by_short.get(name, []))
        return sorted(set(symbols))

    def _extract_imports(self, unit: _PythonUnit) -> dict[str, _Binding]:
        bindings: dict[str, _Binding] = {}
        source_id = file_node_id(unit.rel)
        for node in ast.walk(unit.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    candidates = self._module_candidates(alias.name)
                    self._add_resolved_edges(
                        source_id,
                        candidates,
                        "imports",
                        unit,
                        node.lineno,
                        raw_target=alias.name,
                    )
                    local = alias.asname or alias.name.split(".")[0]
                    bindings[local] = _Binding(candidates, [])
            elif isinstance(node, ast.ImportFrom):
                module = self._absolute_import(unit, node)
                for alias in node.names:
                    if alias.name == "*":
                        candidates = self._module_candidates(module)
                        local = "*"
                    else:
                        candidates = self._module_candidates(module, alias.name)
                        local = alias.asname or alias.name
                    self._add_resolved_edges(
                        source_id,
                        candidates,
                        "imports",
                        unit,
                        node.lineno,
                        raw_target=f"{module}.{alias.name}".strip("."),
                    )
                    bindings[local] = _Binding(
                        candidates,
                        self._symbols_in_files(candidates, alias.name),
                    )
        return bindings

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = self._call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return None

    def _add_call_targets(
        self,
        unit: _PythonUnit,
        source_id: str,
        targets: list[str],
        line: int,
        raw_target: str,
    ) -> None:
        # Calls are useful only when they resolve to repository code. Recording
        # every builtin/library call as an external node would swamp xrefs and
        # reverse impact; imports retain that broader dependency inventory.
        if not targets:
            return
        confidence = Confidence.RESOLVED if len(targets) == 1 else Confidence.AMBIGUOUS
        for target in sorted(set(targets)):
            self.graph.add_relation(
                source_id,
                target,
                "calls",
                confidence,
                path=unit.rel,
                line=line,
                snippet=self._source_line(unit, line),
            )
        if confidence is Confidence.AMBIGUOUS:
            self.graph.add_diagnostic(
                "ambiguous_call",
                f"call {raw_target!r} has {len(set(targets))} candidate definitions",
                path=unit.rel,
                line=line,
            )

    def _extract_calls(self, unit: _PythonUnit, bindings: dict[str, _Binding]) -> None:
        def on_call(node: ast.Call, scope: str | None) -> None:
            source_id = (
                unit.symbols_by_qualname.get(scope or "")
                or file_node_id(unit.rel)
            )
            name = self._call_name(node.func)
            if name:
                targets: list[str] = []
                parts = name.split(".")
                binding = bindings.get(parts[0])
                if len(parts) == 1 and binding:
                    targets = binding.symbols or binding.files
                elif binding and len(parts) > 1:
                    final = parts[-1]
                    targets = self._symbols_in_files(binding.files, final) or binding.files
                elif len(parts) == 1:
                    targets = unit.symbols_by_short.get(name, [])
                elif parts[0] in {"self", "cls"} and scope and "." in scope:
                    class_name = scope.split(".")[0]
                    target = unit.symbols_by_qualname.get(f"{class_name}.{parts[-1]}")
                    targets = [target] if target else []
                self._add_call_targets(unit, source_id, targets, node.lineno, name)
                self._extract_dynamic_import(unit, source_id, node, name)
                self._extract_python_execution(unit, source_id, node, name)

        _CallVisitor(on_call).visit(unit.tree)

    def _string_values(self, node: ast.AST) -> Iterator[str]:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                yield child.value

    def _extract_dynamic_import(
        self, unit: _PythonUnit, source_id: str, node: ast.Call, name: str
    ) -> None:
        base = name.split(".")[-1]
        candidates: list[str] = []
        raw = ""
        if base in {"import_hyphenated", "import_module"} and node.args:
            values = list(self._string_values(node.args[0]))
            raw = values[0] if values else ""
            candidates = self._module_candidates(raw)
        elif base == "spec_from_file_location" and len(node.args) >= 2:
            values = [v for v in self._string_values(node.args[1]) if v.endswith(".py")]
            raw = values[-1] if values else ""
            candidates = self._path_candidates(raw) if raw else []
        if raw:
            self._add_resolved_edges(
                source_id,
                candidates,
                "imports",
                unit,
                node.lineno,
                raw_target=raw,
            )

    def _path_candidates(self, raw: str) -> list[str]:
        normalized = raw.replace("${REPO}/", "").replace("$REPO/", "")
        normalized = normalized.replace("\\", "/")
        absolute = Path(normalized).expanduser()
        if absolute.is_absolute():
            try:
                normalized = absolute.resolve().relative_to(self.root).as_posix()
            except ValueError:
                pass
        exact = file_node_id(normalized.lstrip("./"))
        if exact in self.graph.nodes:
            return [exact]
        if "/" in normalized:
            suffix_matches = [
                node.id
                for node in self.graph.nodes.values()
                if node.kind == "file"
                and node.path
                and node.path.endswith(normalized.lstrip("./"))
            ]
            if suffix_matches:
                return sorted(set(suffix_matches))
        return sorted(self.basename_index.get(Path(normalized).name, set()))

    def _extract_python_execution(
        self, unit: _PythonUnit, source_id: str, node: ast.Call, name: str
    ) -> None:
        base = name.split(".")[-1]
        if base not in EXEC_CALLS and not base.startswith("_run"):
            return
        raw_paths = {
            value
            for arg in [*node.args, *[kw.value for kw in node.keywords]]
            for value in self._string_values(arg)
            if Path(value).suffix in CODE_SUFFIXES
        }
        for raw in sorted(raw_paths):
            self._add_resolved_edges(
                source_id,
                self._path_candidates(raw),
                "executes",
                unit,
                node.lineno,
                raw_target=raw,
            )

    def _add_path_relation(
        self,
        source_id: str,
        raw: str,
        relation: str,
        *,
        path: str,
        line: int,
        snippet: str,
    ) -> None:
        candidates = self._path_candidates(raw)
        if not candidates:
            target_id = f"path:{raw}"
            self.graph.add_node(CodeNode(target_id, "path", raw))
            self.graph.add_relation(
                source_id,
                target_id,
                relation,
                Confidence.EXTRACTED,
                path=path,
                line=line,
                snippet=snippet,
            )
            return
        confidence = Confidence.RESOLVED if len(candidates) == 1 else Confidence.AMBIGUOUS
        for target in candidates:
            self.graph.add_relation(
                source_id,
                target,
                relation,
                confidence,
                path=path,
                line=line,
                snippet=snippet,
            )
        if confidence is Confidence.AMBIGUOUS:
            paths = [self.graph.nodes[c].path or c for c in candidates]
            self.graph.add_diagnostic(
                "ambiguous_target",
                f"{raw!r} matches {', '.join(paths)}",
                path=path,
                line=line,
            )

    def _extract_shell(self, operational_paths: set[Path]) -> None:
        target_re = re.compile(r"(?:[\w./${}~-]+/)?[\w.-]+\.(?:py|sh)")
        for shell in sorted(path for path in operational_paths if path.suffix == ".sh"):
            rel = _relpath(self.root, shell)
            try:
                lines = shell.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                self.graph.add_diagnostic("shell_read_error", str(exc), path=rel)
                continue
            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                relation = "sources" if re.match(r"^(?:source|\.)\s", stripped) else "executes"
                for raw in target_re.findall(stripped):
                    self._add_path_relation(
                        file_node_id(rel),
                        raw.strip('"\''),
                        relation,
                        path=rel,
                        line=lineno,
                        snippet=line,
                    )

    def _extract_justfile(self) -> None:
        justfile = self.root / "justfile"
        if not justfile.is_file():
            return
        rel = "justfile"
        try:
            lines = justfile.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            self.graph.add_diagnostic("justfile_read_error", str(exc), path=rel)
            return
        header_re = re.compile(r"^([A-Za-z_][\w-]*)(?:\s+[^:=]+)?\s*:\s*(?:#.*)?$")
        target_re = re.compile(r"(?:[\w./${}~-]+/)?[\w.-]+\.(?:py|sh)")
        recipe_lines: dict[str, int] = {}
        for lineno, line in enumerate(lines, 1):
            if line and not line[0].isspace() and not line.startswith(("#", "[", "set ")):
                match = header_re.match(line)
                if match:
                    name = match.group(1)
                    recipe_lines[name] = lineno
                    node_id = recipe_node_id(name)
                    self.graph.add_node(CodeNode(node_id, "recipe", name, rel, lineno, name))
                    self.graph.add_relation(
                        file_node_id(rel),
                        node_id,
                        "contains",
                        Confidence.EXTRACTED,
                        path=rel,
                        line=lineno,
                        snippet=line,
                    )

        current: str | None = None
        for lineno, line in enumerate(lines, 1):
            if line and not line[0].isspace() and not line.startswith(("#", "[", "set ")):
                match = header_re.match(line)
                current = match.group(1) if match else None
                continue
            if not current or not line[:1].isspace():
                continue
            for raw in target_re.findall(line):
                self._add_path_relation(
                    recipe_node_id(current),
                    raw,
                    "executes",
                    path=rel,
                    line=lineno,
                    snippet=line,
                )
            for invoked in re.findall(r"(?:^|[;&|]\s*)just\s+([\w-]+)", line.strip()):
                target = recipe_node_id(invoked)
                if target not in self.graph.nodes:
                    self.graph.add_node(CodeNode(target, "recipe", invoked, rel, None, invoked))
                self.graph.add_relation(
                    recipe_node_id(current),
                    target,
                    "invokes_recipe",
                    Confidence.RESOLVED if invoked in recipe_lines else Confidence.EXTRACTED,
                    path=rel,
                    line=lineno,
                    snippet=line,
                )

    def _extract_launchd(self) -> None:
        launchd_dir = self.root / "ops" / "launchd"
        if not launchd_dir.is_dir():
            return
        for plist_path in sorted(launchd_dir.glob("*.plist")):
            rel = _relpath(self.root, plist_path)
            try:
                raw_bytes = plist_path.read_bytes()
                payload = plistlib.loads(raw_bytes)
                lines = raw_bytes.decode("utf-8").splitlines()
            except (OSError, UnicodeDecodeError, plistlib.InvalidFileException) as exc:
                self.graph.add_diagnostic("plist_parse_error", str(exc), path=rel)
                continue
            label = str(payload.get("Label") or plist_path.stem)
            source_id = launchd_node_id(rel, label)
            label_line = next((i for i, line in enumerate(lines, 1) if label in line), 1)
            self.graph.add_node(CodeNode(source_id, "launchd", label, rel, label_line, label))
            self.graph.add_relation(
                file_node_id(rel),
                source_id,
                "contains",
                Confidence.EXTRACTED,
                path=rel,
                line=label_line,
                snippet=lines[label_line - 1],
            )
            for argument in payload.get("ProgramArguments", []):
                if not isinstance(argument, str) or Path(argument).suffix not in CODE_SUFFIXES:
                    continue
                lineno = next((i for i, line in enumerate(lines, 1) if argument in line), 1)
                self._add_path_relation(
                    source_id,
                    argument,
                    "launches",
                    path=rel,
                    line=lineno,
                    snippet=lines[lineno - 1],
                )


def _nodes_in_cycles(edges: dict[str, set[str]]) -> set[str]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    counter = 0
    in_cycle: set[str] = set()

    def strongconnect(node: str) -> None:
        nonlocal counter
        index[node] = low[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)
        for target in edges.get(node, set()):
            if target not in index:
                strongconnect(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], index[target])
        if low[node] != index[node]:
            return
        component: list[str] = []
        while True:
            target = stack.pop()
            on_stack.remove(target)
            component.append(target)
            if target == node:
                break
        if len(component) > 1 or component[0] in edges.get(component[0], set()):
            in_cycle.update(component)

    for node in edges:
        if node not in index:
            strongconnect(node)
    return in_cycle


def build_code_relations(
    root: Path,
    *,
    source_dirs: Iterable[Path | str] | None = None,
    python_files: Iterable[Path | str] | None = None,
    include_operational: bool = True,
) -> CodeRelationGraph:
    return CodeRelationBuilder(
        root,
        source_dirs=source_dirs,
        python_files=python_files,
        include_operational=include_operational,
    ).build()


def gather_python_files(path: Path) -> list[Path]:
    """Gather Python files using the substrate's canonical exclusion rules."""
    path = path.resolve()
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    return sorted(
        candidate.resolve()
        for candidate in path.rglob("*.py")
        if not any(part in SKIP_DIRS for part in candidate.parts)
    )


def _diagnostic_payload(diagnostic: Diagnostic) -> dict[str, object]:
    return asdict(diagnostic)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("impact", "validate"):
        sub = subparsers.add_parser(command)
        sub.add_argument("repo", type=Path)
        sub.add_argument("--source-dirs", help="comma-separated source directories")
        sub.add_argument("--json", action="store_true")
        if command == "impact":
            sub.add_argument("target")
            sub.add_argument("--depth", type=int, default=3)
    args = parser.parse_args(argv)
    source_dirs = args.source_dirs.split(",") if args.source_dirs else None
    graph = build_code_relations(args.repo, source_dirs=source_dirs)

    if args.command == "validate":
        diagnostics = graph.validate()
        if args.json:
            print(json.dumps([_diagnostic_payload(d) for d in diagnostics], indent=2))
        else:
            print(
                f"# code relations — {len(graph.nodes)} nodes, "
                f"{len(graph.relations)} relations, {len(diagnostics)} diagnostics"
            )
            for diagnostic in diagnostics:
                location = diagnostic.path or "<graph>"
                if diagnostic.line:
                    location += f":{diagnostic.line}"
                print(f"  [{diagnostic.severity}] {diagnostic.code} {location} — {diagnostic.message}")
        return 1 if any(d.severity == "error" for d in diagnostics) else 0

    try:
        hops = graph.impact(args.target, max_depth=args.depth)
    except AmbiguousTargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                [
                    {"depth": hop.depth, "relation": asdict(hop.relation)}
                    for hop in hops
                ],
                indent=2,
            )
        )
    else:
        print(f"# Reverse impact: {args.target} ({len(hops)} evidence edge(s))")
        for hop in hops:
            relation = hop.relation
            source = graph.nodes[relation.source]
            target = graph.nodes[relation.target]
            print(
                f"  D{hop.depth} {source.path or source.label}:{relation.evidence.line} "
                f"--{relation.relation}/{relation.confidence.value}--> "
                f"{target.path or target.label}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
