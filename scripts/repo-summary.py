#!/usr/bin/env python3
"""Generate or update per-file one-line summaries using a fast LLM.

Caches by content hash — only re-summarizes changed files.
Output is a compact file map an agent can scan in seconds.

Usage:
  repo-summary.py <path>                    # summarize, cache results
  repo-summary.py <path> --refresh          # re-summarize changed files only
  repo-summary.py <path> --model haiku      # use specific model (default: haiku)
  repo-summary.py <path> --dry-run          # show what would be summarized
  repo-summary.py <path> --no-llm           # use first docstring/comment only (free)
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = Path.home() / ".cache" / "repo-summary"
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "flash": "gemini-3-flash-preview",
    "sonnet": "claude-sonnet-4-6",
}
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".sh", ".sql"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".tox", ".mypy_cache", "dist", "build"}


def gather_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files = sorted(path.rglob("*"))
    return [
        f for f in files
        if f.is_file()
        and f.suffix in EXTENSIONS
        and not any(p in SKIP_DIRS for p in f.parts)
    ]


def content_hash(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()[:16]


def get_cache_path(project_name: str) -> Path:
    return CACHE_DIR / f"{project_name}.json"


def load_cache(project_name: str) -> dict[str, dict]:
    """Load {relative_path: {hash, summary}} cache."""
    cache_path = get_cache_path(project_name)
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return {}


def save_cache(project_name: str, cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    get_cache_path(project_name).write_text(json.dumps(cache, indent=2))


def extract_docstring(filepath: Path) -> str | None:
    """Try to get module docstring without LLM."""
    if filepath.suffix == ".py":
        try:
            tree = ast.parse(filepath.read_text())
            ds = ast.get_docstring(tree)
            if ds:
                # First line only
                return ds.split("\n")[0].strip()
        except (SyntaxError, UnicodeDecodeError):
            pass
    elif filepath.suffix in (".sh", ".sql"):
        try:
            lines = filepath.read_text().splitlines()
            for line in lines[:10]:
                stripped = line.lstrip("# ").lstrip("-- ").strip()
                if stripped and not stripped.startswith("!") and not stripped.startswith("set "):
                    return stripped
        except Exception:
            pass
    return None


def llm_summarize(filepath: Path, model_id: str) -> str | None:
    """Get one-line summary from LLM."""
    try:
        content = filepath.read_text()[:4000]  # First 4K chars is enough
    except (UnicodeDecodeError, OSError):
        return None

    prompt = f"One sentence: what does this file do? Be specific (mention key functions/classes). No preamble.\n\n```{filepath.suffix}\n{content}\n```"

    try:
        result = subprocess.run(
            ["llmx", "-m", model_id, "-t", "0", prompt],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0][:200]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="File or directory to summarize")
    parser.add_argument("--model", default="haiku", choices=list(MODELS.keys()), help="Model for summaries")
    parser.add_argument("--refresh", action="store_true", help="Only re-summarize changed files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be summarized")
    parser.add_argument("--no-llm", action="store_true", help="Use docstrings only (free)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel LLM calls")
    args = parser.parse_args()

    path = args.path.resolve()
    if not path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    files = gather_files(path)
    if not files:
        print(f"No source files found in {path}")
        sys.exit(1)

    base = path if path.is_dir() else path.parent
    project_name = base.name
    cache = load_cache(project_name) if args.refresh else {}

    # Determine which files need summarizing
    needs_summary = []
    for f in files:
        rel = str(f.relative_to(base))
        h = content_hash(f)
        cached = cache.get(rel)
        if cached and cached.get("hash") == h:
            continue
        needs_summary.append((f, rel, h))

    if args.dry_run:
        print(f"# {len(files)} files, {len(needs_summary)} need summarizing")
        for _, rel, _ in needs_summary:
            print(f"  {rel}")
        return

    model_id = MODELS[args.model]

    # Summarize files that need it
    if needs_summary and not args.no_llm:
        print(f"# Summarizing {len(needs_summary)} files with {args.model}...", file=sys.stderr)

        def do_one(item):
            f, rel, h = item
            # Try docstring first (free)
            summary = extract_docstring(f)
            if not summary:
                summary = llm_summarize(f, model_id)
            return rel, h, summary

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(do_one, item) for item in needs_summary]
            for future in as_completed(futures):
                rel, h, summary = future.result()
                if summary:
                    cache[rel] = {"hash": h, "summary": summary}
    elif needs_summary and args.no_llm:
        for f, rel, h in needs_summary:
            summary = extract_docstring(f)
            if summary:
                cache[rel] = {"hash": h, "summary": summary}

    # Also add cached entries for unchanged files
    for f in files:
        rel = str(f.relative_to(base))
        if rel not in cache:
            h = content_hash(f)
            summary = extract_docstring(f)
            if summary:
                cache[rel] = {"hash": h, "summary": summary}

    save_cache(project_name, cache)

    # Output
    print(f"# File map: {project_name}")
    print(f"# {len(files)} files\n")

    for f in files:
        rel = str(f.relative_to(base))
        cached = cache.get(rel)
        summary = cached["summary"] if cached else ""
        marker = "" if summary else "  [no summary]"
        print(f"  {rel:<50} {summary}{marker}")


if __name__ == "__main__":
    main()
