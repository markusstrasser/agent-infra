#!/usr/bin/env python3
"""Generate a compact, two-tier codebase map for agent context.

Tier 1 (auto-loaded, path-scoped) → .claude/rules/codebase-map.md
  A routing INDEX: per directory group, the file count + hub files
  (high import fan-in) + a pointer to the detail file. Flat ~1-2K tokens
  regardless of repo size — this is the only part injected into context.

Tier 2 (on-demand, NOT auto-loaded) → .claude/maps/codebase.<group>.md
  The full per-file listing (one-liner + import edges) for one group.
  Agents Read these only when they need an area's full inventory.

Rationale: auto-loading a per-file summary of the whole tree is the
"wiki summary" anti-pattern (.claude/rules/context-budget-principles.md;
Gloaguen et al. AGENTS.md study: -0.5-3% success, +20% cost). Indexes
route; detail is fetched on demand. The import-edge spine (← imported-by-N)
is the signal `ls`/`Glob` cannot give, so it stays in Tier 1; the per-file
prose — the part the study dings — moves to on-demand Tier 2.
See decisions/2026-06-14-codebase-map-two-tier.md.

Joins repo-summary cache (one-liner descriptions) with repo-imports
internal graph (cross-file edges).

Usage:
  codebase-map.py /path/to/project [--source-dirs scripts,src]
"""
import json
import re
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

# Tier-1 tunables
HUB_MIN = 3        # minimum imported-by count to surface a file as a hub
HUB_PER_GROUP = 6  # cap hub files listed per group in the index
DESC_WIDTH = 55    # detail-tier description column width
DETAIL_MAX_FILES = 80  # split oversized groups into subtree detail files


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
        graph = result[0]  # (graph, internal_modules, files, base)

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


def slugify_group(group_name: str) -> str:
    """Stable filename slug for a directory group ('scripts/common' -> 'scripts-common')."""
    if group_name == ".":
        return "root"
    slug = group_name.replace("/", "-").strip("-")
    slug = re.sub(r"[^\w-]", "", slug.replace("*", "")).rstrip("_")
    return slug or "root"


def bucket_key_for_stem(group_name: str, stem: str) -> str:
    """Assign a flat-dir file to a prefix/letter subtree bucket."""
    if "_" in stem:
        prefix = stem.split("_", 1)[0]
        if len(prefix) >= 2:
            return f"{group_name}/{prefix}_*"
    letter = stem[0].lower() if stem else "?"
    return f"{group_name}/{letter}-*"


def partition_by_letter(bucket_name: str, entries: list, max_files: int) -> dict[str, list]:
    """Split an oversized bucket by first letter (and fixed chunks as last resort)."""
    by_letter: dict[str, list] = defaultdict(list)
    for entry in entries:
        letter = entry[0][0].lower() if entry[0] else "?"
        by_letter[letter].append(entry)

    result: dict[str, list] = {}
    for letter, letter_entries in sorted(by_letter.items()):
        if len(letter_entries) <= max_files:
            result[f"{bucket_name}/{letter}"] = letter_entries
            continue
        for i in range(0, len(letter_entries), max_files):
            chunk = letter_entries[i : i + max_files]
            suffix = "" if i == 0 else f"-{i // max_files}"
            result[f"{bucket_name}/{letter}{suffix}"] = chunk
    return result


def partition_group(
    group_name: str,
    entries: list,
    max_files: int = DETAIL_MAX_FILES,
) -> dict[str, list]:
    """Split a large directory group into subtree buckets for on-demand detail."""
    if len(entries) <= max_files:
        return {group_name: entries}

    buckets: dict[str, list] = defaultdict(list)
    for entry in entries:
        buckets[bucket_key_for_stem(group_name, entry[0])].append(entry)

    result: dict[str, list] = {}
    for bucket_name, bucket_entries in sorted(buckets.items()):
        if len(bucket_entries) > max_files:
            result.update(partition_by_letter(bucket_name, bucket_entries, max_files))
        else:
            result[bucket_name] = bucket_entries
    return result


def _path_globs(project_root: Path, source_dirs: list[Path]) -> list[str]:
    """Path-scope globs for the source dirs, relative to the project root."""
    globs: list[str] = []
    for src_dir in source_dirs:
        try:
            rel = src_dir.resolve().relative_to(project_root.resolve())
        except ValueError:
            continue
        glob = "**" if str(rel) == "." else f"{rel.as_posix()}/**"
        if glob not in globs:
            globs.append(glob)
    return globs or ["**"]


def generate_maps(project_root: Path, source_dirs: list[Path]) -> tuple[str, dict[str, str]]:
    """Build the Tier-1 index and the Tier-2 per-group detail bodies.

    Returns (index_markdown, {group_slug: detail_markdown}).
    """
    project_name = project_root.name

    # Load summaries — try both directory-level and project-level cache keys
    summaries: dict[str, str] = {}
    for src_dir in source_dirs:
        summaries.update(load_summaries(src_dir.name))
    summaries.update(load_summaries(project_name))

    imports_from, imported_by = build_edges(source_dirs)

    # Gather files and group by directory relative to project root
    groups: dict[str, list[tuple[str, str, Path]]] = defaultdict(list)
    all_files = gather_all_files(source_dirs)
    base_of: dict[Path, Path] = {}

    for filepath, base_dir in all_files:
        base_of[filepath] = base_dir
        rel_to_project = filepath.relative_to(project_root)
        rel_to_base = filepath.relative_to(base_dir)

        parts = rel_to_project.parts
        group = str(Path(*parts[:-1])) if len(parts) > 1 else "."

        summary = ""
        for key in [str(rel_to_base), str(rel_to_project), filepath.name]:
            if key in summaries:
                summary = summaries[key]
                break

        groups[group].append((filepath.stem, summary, filepath))

    def imported_by_count(filepath: Path) -> int:
        return imported_by.get(module_name(filepath, base_of[filepath]), 0)

    def edge_annotation(filepath: Path) -> str:
        mod = module_name(filepath, base_of[filepath])
        parts = []
        targets = imports_from.get(mod, set())
        if targets:
            parts.append(f"→ {', '.join(sorted(targets))}")
        count = imported_by.get(mod, 0)
        if count >= HUB_MIN:
            parts.append(f"← {count} files")
        return "  ".join(parts)

    total_files = sum(len(v) for v in groups.values())
    today = date.today()

    # Partition oversized groups into subtree detail buckets (genomics scripts/ etc.).
    detail_groups: dict[str, list[tuple[str, str, Path]]] = {}
    split_parents: dict[str, list[tuple[str, str, int]]] = {}
    for group_name in sorted(groups):
        entries = groups[group_name]
        parts = partition_group(group_name, entries)
        if len(parts) == 1 and group_name in parts:
            detail_groups[group_name] = entries
            continue
        children: list[tuple[str, str, int]] = []
        for sub_name, sub_entries in sorted(parts.items()):
            detail_groups[sub_name] = sub_entries
            children.append((sub_name, slugify_group(sub_name), len(sub_entries)))
        split_parents[group_name] = children

    # --- Tier 2: per-group/subtree detail (on-demand, not auto-loaded) ---
    details: dict[str, str] = {}
    for detail_name in sorted(detail_groups):
        slug = slugify_group(detail_name)
        entries = sorted(detail_groups[detail_name], key=lambda x: x[0])
        max_name = min(max(len(e[0]) + 3 for e in entries), 35)

        dlines = [
            f"# Codebase detail — {detail_name} ({len(entries)} files)",
            f"# generated {today} · on-demand (not auto-loaded) · index: .claude/rules/codebase-map.md",
            "# Edge annotations: → imports  ← imported-by-N-files",
            "",
        ]
        for stem, summary, filepath in entries:
            fname = f"{stem}.py"
            edges = edge_annotation(filepath)
            desc = summary[:DESC_WIDTH] if summary else ""
            edge_str = f"  {edges}" if edges else ""
            max_desc = DESC_WIDTH - len(edge_str) if edge_str else DESC_WIDTH
            if len(desc) > max_desc and max_desc > 10:
                desc = desc[: max_desc - 1] + "…"
            dlines.append(f"  {fname:<{max_name}} {desc}{edge_str}".rstrip())
        details[slug] = "\n".join(dlines) + "\n"

    # --- Tier 1: index (auto-loaded, path-scoped, flat ~1-2K tokens) ---
    path_globs = _path_globs(project_root, source_dirs)
    ilines = [
        "---",
        "description: Codebase index — directory groups, hub files (import fan-in), and "
        "pointers. Per-file detail is on-demand in .claude/maps/ (not auto-loaded).",
        "paths:",
        *[f'  - "{g}"' for g in path_globs],
        "---",
        "# Codebase Map",
        "",
        "<!-- Gov-ID: rule:codebase-map",
        "goal: compact code map for agent navigation (generated)",
        "verifier: null",
        "blast_radius: style",
        "-->",
        "",
        f"# {total_files} Python files — generated {today}",
        "# Index only (routing). Full per-file listing: .claude/maps/codebase.<group>.md — Read on demand.",
        "# Per group: file count · hubs (high import fan-in, ← imported-by-N) · detail pointer.",
        "",
    ]
    for group_name in sorted(groups):
        entries = groups[group_name]
        ilines.append(f"## {group_name}/ — {len(entries)} files")

        ranked = sorted(
            ((e[0], imported_by_count(e[2])) for e in entries),
            key=lambda x: (-x[1], x[0]),
        )
        hub_strs = [f"{stem}.py ←{n}" for stem, n in ranked if n >= HUB_MIN][:HUB_PER_GROUP]
        if hub_strs:
            ilines.append(f"  hubs: {', '.join(hub_strs)}")
        if group_name in split_parents:
            index_slug = f"{slugify_group(group_name)}-index"
            children = split_parents[group_name]
            ilines.append(
                f"  detail index: .claude/maps/codebase.{index_slug}.md "
                f"({len(children)} subtrees)"
            )
            idx_lines = [
                f"# Codebase subtree index — {group_name}/ ({len(entries)} files)",
                f"# generated {today} · on-demand · pick a subtree detail file below",
                "",
            ]
            for sub_name, slug, count in children:
                idx_lines.append(
                    f"- {sub_name} ({count}): .claude/maps/codebase.{slug}.md"
                )
            details[index_slug] = "\n".join(idx_lines) + "\n"
        else:
            slug = slugify_group(group_name)
            ilines.append(f"  detail: .claude/maps/codebase.{slug}.md")
        ilines.append("")

    return "\n".join(ilines), details


def _norm(s: str) -> str:
    """Normalize the date stamp so a daily refresh doesn't churn unchanged content."""
    return re.sub(r"generated \d{4}-\d{2}-\d{2}", "generated DATE", s)


def _write_idempotent(path: Path, content: str) -> str:
    """Write only on a real (non-date) content change; else touch mtime. Returns status."""
    if path.exists() and _norm(path.read_text()) == _norm(content):
        path.touch()
        return "unchanged"
    path.write_text(content)
    return "wrote"


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

    index, details = generate_maps(project_root, source_dirs)

    rules_dir = project_root / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    maps_dir = project_root / ".claude" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    idx_path = rules_dir / "codebase-map.md"
    status = _write_idempotent(idx_path, index)
    print(f"[index]  {idx_path} — {status} ({len(index)} chars)")

    current: set[str] = set()
    for slug, content in sorted(details.items()):
        p = maps_dir / f"codebase.{slug}.md"
        current.add(p.name)
        status = _write_idempotent(p, content)
        print(f"[detail] {p.name} — {status} ({len(content)} chars)")

    # Prune detail files for groups that no longer exist (only our own prefix).
    for old in maps_dir.glob("codebase.*.md"):
        if old.name not in current:
            old.unlink()
            print(f"[prune]  removed stale {old.name}")


if __name__ == "__main__":
    main()
