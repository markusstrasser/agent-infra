"""AST-based import-graph contract test — zero domain leaks in core.

Uses ast module to walk every .py file in claim_bench/src/ and assert:
- Zero imports from genomics.*, phenome.*, synthetic_finance.*
- Zero domain-specific literal strings in source code
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "claim_bench"

# Domain-specific terms that should NOT appear in core source
FORBIDDEN_LITERALS = {
    "genomics", "phenome", "clingen", "vcep", "self_report",
    "wearable", "synthetic_finance", "insider_report", "sec_filing",
}

# Forbidden import namespaces
FORBIDDEN_IMPORTS = {"genomics", "phenome", "synthetic_finance"}


def _collect_imports(tree: ast.Module) -> list[str]:
    """Extract all imported module names from an AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """Return the id() of AST nodes that are docstrings."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                ids.add(id(node.body[0].value))
    return ids


def _collect_string_literals(tree: ast.Module) -> list[str]:
    """Extract non-docstring string literals from an AST."""
    docstrings = _docstring_nodes(tree)
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                strings.append(node.value)
    return strings


class TestImportGraph:
    def test_no_domain_imports(self):
        """No imports from genomics/phenome/synthetic_finance namespaces."""
        violations = []
        for py_file in SRC_DIR.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for imp in _collect_imports(tree):
                root = imp.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    violations.append(f"{py_file.name}: imports {imp}")
        assert violations == [], f"Domain imports in core:\n" + "\n".join(violations)

    def test_no_domain_literals(self):
        """No domain-specific literal strings in core source code."""
        violations = []
        for py_file in SRC_DIR.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for s in _collect_string_literals(tree):
                # Check each forbidden term as a whole word in the string
                s_lower = s.lower()
                for term in FORBIDDEN_LITERALS:
                    if term in s_lower:
                        violations.append(f"{py_file.name}: literal contains '{term}': {s[:80]!r}")
        assert violations == [], f"Domain literals in core:\n" + "\n".join(violations)
