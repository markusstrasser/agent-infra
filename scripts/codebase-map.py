#!/usr/bin/env python3
"""Generate a compact codebase map for agent context.

Joins repo-summary cache (one-liner descriptions) with repo-imports
internal graph (cross-file edges) to produce a file map that agents
auto-load from .claude/rules/codebase-map.md.

Usage:
  codebase-map.py /path/to/project [--source-dirs scripts,src]
"""
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Import from sibling script
sys.path.insert(0, str(Path(__file__).parent))
import importlib
_repo_imports = importlib.import_module("repo-imports")
gather_py_files = _repo_imports.gather_py_files
build_import_graph = _repo_imports.build_import_graph
module_name = _repo_imports.module_name

CACHE_DIR = Path.home() / ".cache" / "repo-summary"
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".tox",
             ".mypy_cache", "dist", "build", ".claude"}


def load_summaries(project_name: str) -> dict[str, str]:
    """Load {relative_path: summary} from repo-summary cache."""
    cache_path = CACHE_DIR / f"{project_name}.json"
    if not cache_path.exists():
        return {}
    data = json.loads(cache_path.read_text())
    return {k: v["summary"] for k, v in data.items() if v.get("summary")}


def build_edges(source_dirs: list[Path]) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Build import edges and hub counts across all source dirs.

    Returns:
        imports_from: {module: set of modules it imports from}
        imported_by_count: {module: number of files that import it}
    """
    imports_from: dict[str, set[str]] = defaultdict(set)
    imported_by_count: dict[str, int] = defaultdict(int)

    for src_dir in source_dirs:
        result = build_import_graph(src_dir)
        if not result:
            continue
        graph, internal_modules, files, base = result

        for mod, imps in graph.items():
            for imp in imps:
                if imp["kind"] == "internal":
                    target = imp["module"].split(".")[0]
                    if target != mod:
                        imports_from[mod].add(target)
                        imported_by_count[target] += 1

    return dict(imports_from), dict(imported_by_count)


def gather_all_files(source_dirs: list[Path]) -> list[tuple[Path, Path]]:
    """Gather (file, base_dir) pairs from all source dirs."""
    results = []
    for src_dir in source_dirs:
        for f in gather_py_files(src_dir):
            results.append((f, src_dir))
    return results


def generate_map(project_root: Path, source_dirs: list[Path]) -> str:
    """Generate the codebase map content."""
    project_name = project_root.name

    # Load summaries — try both directory-level and project-level cache keys
    summaries: dict[str, str] = {}
    for src_dir in source_dirs:
        dir_name = src_dir.name
        summaries.update(load_summaries(dir_name))
    summaries.update(load_summaries(project_name))

    # Build import graph
    imports_from, imported_by = build_edges(source_dirs)

    # Gather files and group by directory relative to project root
    groups: dict[str, list[tuple[str, str, Path]]] = defaultdict(list)
    all_files = gather_all_files(source_dirs)

    for filepath, base_dir in all_files:
        rel_to_project = filepath.relative_to(project_root)
        rel_to_base = filepath.relative_to(base_dir)
        mod = module_name(filepath, base_dir)

        # Directory group key (first component of relative path)
        parts = rel_to_project.parts
        group = str(Path(*parts[:-1])) if len(parts) > 1 else "."

        # Summary lookup — try multiple key patterns
        summary = ""
        for key in [str(rel_to_base), str(rel_to_project), filepath.name]:
            if key in summaries:
                summary = summaries[key]
                break

        groups[group].append((filepath.stem, summary, filepath))

    # Build edges annotation per file
    def edge_annotation(filepath: Path, base_dir: Path) -> str:
        mod = module_name(filepath, base_dir)
        parts = []
        targets = imports_from.get(mod, set())
        if targets:
            parts.append(f"→ {', '.join(sorted(targets))}")
        count = imported_by.get(mod, 0)
        if count >= 3:
            parts.append(f"← {count} files")
        return "  ".join(parts)

    # Format output
    total_files = sum(len(v) for v in groups.values())
    lines = [
        "---",
        "description: Auto-generated file map with cross-file relationships. Updated daily.",
        "paths:",
        '  - "scripts/**"',
        "---",
        "# Codebase Map",
        f"# {total_files} Python files — generated {date.today()}",
        "# Navigation: repo_callgraph(target=\"name\") finds callers across files",
        "",
    ]

    for group_name in sorted(groups):
        lines.append(f"## {group_name}/")
        lines.append("")

        entries = sorted(groups[group_name], key=lambda x: x[0])
        # Calculate column width
        max_name = max(len(e[0]) + 3 for e in entries)  # +3 for .py
        max_name = min(max_name, 35)

        for stem, summary, filepath in entries:
            fname = f"{stem}.py"
            # Find the base_dir for this file
            base = next(b for f, b in all_files if f == filepath)
            edges = edge_annotation(filepath, base)

            desc = summary[:55] if summary else ""
            edge_str = f"  {edges}" if edges else ""

            # Truncate description if line would be too long
            max_desc = 55 - len(edge_str) if edge_str else 55
            if len(desc) > max_desc and max_desc > 10:
                desc = desc[:max_desc - 1] + "…"

            line = f"  {fname:<{max_name}} {desc}{edge_str}"
            lines.append(line.rstrip())
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("project", type=Path, help="Project root directory")
    parser.add_argument("--source-dirs", type=str, default=None,
                        help="Comma-separated subdirectories to scan (default: whole project)")
    args = parser.parse_args()

    project_root = args.project.resolve()
    if not project_root.exists():
        print(f"Project not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    if args.source_dirs:
        source_dirs = [project_root / d.strip() for d in args.source_dirs.split(",")]
        missing = [d for d in source_dirs if not d.exists()]
        if missing:
            print(f"Source dirs not found: {', '.join(str(m) for m in missing)}", file=sys.stderr)
            sys.exit(1)
    else:
        source_dirs = [project_root]

    content = generate_map(project_root, source_dirs)

    # Write to .claude/rules/codebase-map.md
    output_dir = project_root / ".claude" / "rules"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "codebase-map.md"
    output_path.write_text(content)

    # Count files in output
    file_count = sum(1 for line in content.splitlines() if line.strip().endswith(".py") or ".py " in line)
    print(f"Wrote {output_path} ({file_count} files mapped)")


if __name__ == "__main__":
    main()
