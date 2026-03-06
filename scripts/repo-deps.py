#!/usr/bin/env python3
"""Show project dependencies with descriptions.

Parses pyproject.toml and enriches each dependency with its PyPI summary.
Agents can quickly see what libraries are available without guessing.

Usage:
  repo-deps.py <project_dir>           # show deps with descriptions
  repo-deps.py <project_dir> --installed  # also show installed version
"""
import json
import sys
import re
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Cache PyPI lookups in memory (one session)
_pypi_cache: dict[str, str] = {}


def parse_pyproject(project_dir: Path) -> dict[str, list[str]]:
    """Parse pyproject.toml for dependencies. Returns {group: [dep_specs]}."""
    toml_path = project_dir / "pyproject.toml"
    if not toml_path.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    result = {}

    # Standard dependencies
    deps = data.get("project", {}).get("dependencies", [])
    if deps:
        result["main"] = deps

    # Optional dependency groups
    optional = data.get("project", {}).get("optional-dependencies", {})
    for group, group_deps in optional.items():
        result[group] = group_deps

    # uv-specific dev dependencies
    uv_dev = data.get("tool", {}).get("uv", {}).get("dev-dependencies", [])
    if uv_dev:
        result["dev"] = uv_dev

    return result


def normalize_pkg_name(spec: str) -> str:
    """Extract package name from a dependency spec like 'httpx>=0.25'."""
    # Remove extras like [all]
    name = re.split(r"[\[>=<~!;@\s]", spec)[0]
    return name.strip().lower().replace("-", "_").replace(".", "_")


def display_name(spec: str) -> str:
    """Package name as written in pyproject.toml."""
    return re.split(r"[\[>=<~!;@\s]", spec)[0].strip()


def version_constraint(spec: str) -> str:
    """Extract version constraint from spec."""
    name = display_name(spec)
    rest = spec[len(name):].strip()
    # Remove extras
    rest = re.sub(r"\[.*?\]", "", rest).strip()
    # Remove environment markers
    rest = re.sub(r";.*$", "", rest).strip()
    return rest or "*"


def fetch_pypi_summary(pkg_name: str) -> str:
    """Fetch one-line summary from PyPI JSON API."""
    normalized = pkg_name.lower().replace("_", "-")
    if normalized in _pypi_cache:
        return _pypi_cache[normalized]

    try:
        url = f"https://pypi.org/pypi/{normalized}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            summary = data.get("info", {}).get("summary", "")
            _pypi_cache[normalized] = summary
            return summary
    except Exception:
        _pypi_cache[normalized] = ""
        return ""


def get_installed_version(pkg_name: str) -> str | None:
    """Check installed version via importlib.metadata."""
    try:
        from importlib.metadata import version
        return version(pkg_name.replace("_", "-"))
    except Exception:
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir", type=Path, help="Project directory containing pyproject.toml")
    parser.add_argument("--installed", action="store_true", help="Show installed versions")
    parser.add_argument("--no-pypi", action="store_true", help="Skip PyPI lookups (offline mode)")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    dep_groups = parse_pyproject(project_dir)

    if not dep_groups:
        print(f"No dependencies found in {project_dir / 'pyproject.toml'}")
        sys.exit(1)

    # Collect all unique packages for batch PyPI lookup
    all_pkgs = set()
    for specs in dep_groups.values():
        for spec in specs:
            all_pkgs.add(display_name(spec))

    # Fetch PyPI summaries in parallel
    summaries = {}
    if not args.no_pypi:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch_pypi_summary, pkg): pkg for pkg in all_pkgs}
            for future in futures:
                pkg = futures[future]
                summaries[pkg] = future.result()

    print(f"# Dependencies: {project_dir.name}")
    print(f"# {len(all_pkgs)} packages\n")

    for group, specs in dep_groups.items():
        print(f"## {group}")
        for spec in sorted(specs, key=lambda s: display_name(s).lower()):
            name = display_name(spec)
            ver = version_constraint(spec)
            summary = summaries.get(name, "")
            parts = [f"  {name:<25} {ver:<12}"]

            if args.installed:
                installed = get_installed_version(name)
                parts.append(f"  [{installed or 'not installed'}]")

            if summary:
                parts.append(f"  {summary}")

            print("".join(parts))
        print()


if __name__ == "__main__":
    main()
