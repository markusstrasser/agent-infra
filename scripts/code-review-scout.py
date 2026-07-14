#!/usr/bin/env python3
"""Continuous code review scout — dispatches code chunks to local CLI reviewers.

Groups files by directory, keeps each batch under CLI context limits (~40KB),
dispatches to cursor-agent (Composer 2.5, default), gemini, or codex via llmx,
writes structured findings to artifacts/code-review/{project}/{date}.jsonl.

Transport probe (no LLM call): `llmx chat --dry-run -m composer-2.5 -p cursor`.
See `decisions/2026-06-15-llmx-refactor-dispatch-layer.md` for subscription/API policy.

Usage:
  code-review-scout.py <project_path> [--focus refactoring]
  code-review-scout.py <project_path> --focus dead-code --provider cursor
  code-review-scout.py <project_path> --focus optimization --dry-run
  code-review-scout.py <project_path> --list-modules
  code-review-scout.py <project_path> --module tools/downloaders
  code-review-scout.py <project_path> --file scripts/large_runner.py
  code-review-scout.py <project_path> --all-providers

Focus areas (rotate these):
  refactoring    — simplification, duplication, clarity
  dead-code      — unused functions/imports/variables, unreachable code
  optimization   — performance, unnecessary allocations, O(n²) patterns
  patterns       — inconsistent conventions, anti-patterns, error handling
  security       — injection, path traversal, unsafe deserialization
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# CLI context budget: tested up to 100KB via gemini-cli/codex-cli (stdin piping).
# Model context is 1M tokens but CLI calls are free — keep batches moderate for
# focused review quality (not a hard transport limit).
MAX_BATCH_BYTES = 80_000  # ~80KB of code per batch
MAX_FILE_BYTES = 75_000  # fail loud above this until line-aware chunking exists
EXTENSIONS = {".py", ".js", ".ts", ".sh", ".sql", ".rs", ".go"}
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".tox",
    ".mypy_cache",
    "dist",
    "build",
    ".context",
    ".model-review",
    "data",
    "databases",
    "artifacts",
    ".claude",
}

ARTIFACTS_BASE = Path(__file__).parent.parent / "artifacts" / "code-review"


class CoverageError(RuntimeError):
    """The scout cannot prove complete coverage of the selected source set."""


class DispatchError(RuntimeError):
    """A selected review batch did not produce a reviewer verdict."""


def checked_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise CoverageError(f"cannot stat selected source file {path}: {exc}") from exc


FOCUS_PROMPTS = {
    "refactoring": (
        "Review for refactoring opportunities: duplicated logic, overly complex functions, "
        "functions doing too many things, unclear naming, code that could be simplified. "
        "Ignore style-only issues (formatting, docstrings). Focus on structural improvements."
    ),
    "dead-code": (
        "Find dead code: functions never called (check imports and call sites within the batch), "
        "unused imports, unreachable branches, commented-out code blocks, variables assigned but "
        "never read. Be conservative — if a function might be called externally (CLI entry point, "
        "MCP handler, test fixture), don't flag it."
    ),
    "optimization": (
        "Find performance issues: O(n²) or worse patterns in loops, repeated file/DB reads that "
        "could be cached, unnecessary copies of large data, blocking I/O in async contexts, "
        "repeated subprocess calls that could be batched. Ignore micro-optimizations."
    ),
    "patterns": (
        "Find inconsistent patterns: same problem solved differently across files, error handling "
        "gaps (bare except, swallowed errors), inconsistent return types, mixed conventions "
        "(some files use X, others use Y for the same thing). Reference the specific inconsistency."
    ),
    "security": (
        "Find security issues: command injection (unsanitized input in subprocess/os.system), "
        "path traversal, SQL injection, unsafe deserialization (pickle/yaml.load), hardcoded "
        "secrets, overly permissive file permissions. Only flag real risks, not theoretical."
    ),
}

PROVIDERS = {
    "cursor": {
        "model_flag": "-p cursor -m composer-2.5",
        # Local cursor-agent via llmx cursor transport (usage-metered Composer pool).
        "extra": "--timeout 300",
        "name": "composer",
    },
    "google": {
        "model_flag": "-p google -m gemini-3.1-pro-preview",
        # Gemini routes to the paid API since 2026-05-31 (free gemini-cli retired).
        "extra": "--timeout 180",
        "name": "gemini",
    },
    "openai": {
        "model_flag": "-p openai -m gpt-5.6-sol",
        "extra": "--reasoning-effort medium --timeout 180",
        "name": "gpt",
    },
}


def gather_files(root: Path) -> list[Path]:
    """Collect reviewable source files."""
    files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix not in EXTENSIONS:
            continue
        if any(p in SKIP_DIRS for p in f.parts):
            continue
        size = checked_size(f)
        if size < 50:  # skip trivially small files
            continue
        files.append(f)
    return files


def group_by_module(files: list[Path], root: Path) -> dict[str, list[Path]]:
    """Group files by their parent directory (1 level deep from root)."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        rel = f.relative_to(root)
        # Use first directory component as module, or "root" for top-level files
        parts = rel.parts
        if len(parts) == 1:
            module = "."
        elif len(parts) == 2:
            module = parts[0]
        else:
            # Group by first two levels for deeper nesting
            module = str(Path(parts[0]) / parts[1])
        groups[module].append(f)
    return dict(sorted(groups.items()))


def make_batches(files: list[Path], root: Path) -> list[list[Path]]:
    """Split files into batches that fit within CLI context limit."""
    batches = []
    current_batch = []
    current_size = 0

    for f in files:
        size = checked_size(f)
        if current_size + size > MAX_BATCH_BYTES and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(f)
        current_size += size

    if current_batch:
        batches.append(current_batch)
    return batches


def build_code_context(files: list[Path], root: Path) -> str:
    """Concatenate files into a single context string."""
    parts = []
    for f in files:
        rel = f.relative_to(root)
        try:
            content = f.read_text(errors="replace")
        except OSError as exc:
            raise CoverageError(f"cannot read selected source file {f}: {exc}") from exc
        parts.append(f"### {rel}\n```{f.suffix.lstrip('.')}\n{content}\n```\n")
    return "\n".join(parts)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def load_previous_findings(project_name: str) -> set[str]:
    """Load hashes of previously reported findings to deduplicate."""
    project_dir = ARTIFACTS_BASE / project_name
    if not project_dir.exists():
        return set()
    hashes = set()
    for f in sorted(project_dir.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            try:
                entry = json.loads(line)
                # Hash on file + category + description core
                key = f"{entry.get('file', '')}:{entry.get('category', '')}:{entry.get('description', '')[:80]}"
                hashes.add(hashlib.sha256(key.encode()).hexdigest()[:12])
            except (json.JSONDecodeError, KeyError, AttributeError):
                continue
    return hashes


# Track which provider hit a hard rate limit so we skip remaining batches for it
_rate_limited_providers: set[str] = set()


def dispatch_review(
    code_context: str, focus: str, provider_cfg: dict, batch_label: str
) -> str:
    """Send code to LLM CLI for review. Returns raw output.

    On rate limit: retries once after 30s. If still limited, marks the provider
    as exhausted for the rest of this run (no point waiting hours).
    """
    import time as _time

    provider_name = provider_cfg["name"]
    if provider_name in _rate_limited_providers:
        raise DispatchError(
            f"[{batch_label}] not reviewed because {provider_name} is rate limited"
        )

    focus_prompt = FOCUS_PROMPTS[focus]

    prompt = f"""<system>
You are a code reviewer. Be concrete and specific. Use the exact file paths shown in ### headers.
Output ONLY findings, one per line, in this exact format:
FILEPATH:LINE SEVERITY CATEGORY description

Where FILEPATH is the exact relative path from the ### header (e.g., scripts/foo.py).
SEVERITY: HIGH, MEDIUM, or LOW
CATEGORY: {focus}

If no issues found, output exactly: NO_ISSUES

Do not output explanations, headers, or markdown formatting. Just the findings, one per line.
</system>

Review the following code files. Focus: {focus_prompt}

{code_context}"""

    # Build command — omit -s to stay on CLI transport
    model_parts = provider_cfg["model_flag"].split()
    extra_parts = provider_cfg["extra"].split()
    cmd = ["llmx", "chat"] + model_parts + extra_parts + [prompt]

    for attempt in range(2):  # try once, retry once on rate limit
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min max
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            if result.returncode == 3:  # rate limit
                if attempt == 0:
                    print(
                        f"  [{batch_label}] rate limited, retrying in 30s...",
                        file=sys.stderr,
                    )
                    _time.sleep(30)
                    continue
                else:
                    # Still limited after retry — give up on this provider
                    print(
                        f"  [{batch_label}] {provider_name} rate limited twice, "
                        f"skipping remaining batches for this provider",
                        file=sys.stderr,
                    )
                    _rate_limited_providers.add(provider_name)
                    raise DispatchError(
                        f"[{batch_label}] reviewer rate limited twice: {provider_name}"
                    )
            if result.returncode != 0:
                detail = (
                    result.stderr.strip() or result.stdout.strip() or "no diagnostic"
                )
                raise DispatchError(
                    f"[{batch_label}] reviewer exited {result.returncode}: {detail[:1000]}"
                )
            raise DispatchError(
                f"[{batch_label}] reviewer exited successfully without a verdict"
            )
        except subprocess.TimeoutExpired:
            raise DispatchError(f"[{batch_label}] reviewer timed out after 300s")
        except FileNotFoundError:
            raise DispatchError("llmx not found — install it first")
    raise AssertionError("review dispatch retry loop exhausted without a verdict")


def parse_findings(
    raw: str, provider_name: str, _batch_files: list[Path], _root: Path
) -> list[dict]:
    """Parse raw LLM output into structured findings."""
    if not raw or "NO_ISSUES" in raw:
        return []

    findings = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue

        # Try to parse FILE:LINE SEVERITY CATEGORY description
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue

        file_line = parts[0]
        severity = parts[1].upper().rstrip(":")
        category = parts[2].lower().rstrip(":")
        description = parts[3]

        if severity not in ("HIGH", "MEDIUM", "LOW"):
            continue

        # Split file:line
        if ":" in file_line:
            file_part, line_part = file_line.rsplit(":", 1)
            try:
                line_num = int(line_part)
            except ValueError:
                file_part = file_line
                line_num = 0
        else:
            file_part = file_line
            line_num = 0

        findings.append(
            {
                "file": file_part,
                "line": line_num,
                "severity": severity,
                "category": category,
                "description": description,
                "source": provider_name,
            }
        )

    return findings


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path)
    parser.add_argument(
        "--focus", default="refactoring", choices=list(FOCUS_PROMPTS.keys())
    )
    parser.add_argument(
        "--provider",
        default="cursor",
        choices=list(PROVIDERS.keys()),
        help="LLM provider (cursor=composer-2.5, google=gemini, openai=codex)",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Dispatch to google+openai in parallel (legacy)",
    )
    parser.add_argument(
        "--all-providers",
        action="store_true",
        help="Dispatch to cursor+google+openai in parallel",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--module", type=str, default=None, help="Review only this module/directory"
    )
    selection.add_argument(
        "--file",
        type=str,
        default=None,
        help=(
            "Review one exact repo-relative file; permits a file up to the full "
            "batch budget instead of the multi-file safety limit"
        ),
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="List modules and their sizes, then exit",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show batches without dispatching"
    )
    parser.add_argument(
        "--workers", type=int, default=2, help="Parallel dispatch workers"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Seconds to wait between batch dispatches (rate limit throttle)",
    )
    args = parser.parse_args()

    root = args.project_path.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    project_name = root.name
    files = gather_files(root)
    if not files:
        print(f"No source files found in {root}")
        sys.exit(1)

    modules = group_by_module(files, root)

    if args.list_modules:
        print(f"# {project_name}: {len(files)} files in {len(modules)} modules\n")
        for mod, mod_files in modules.items():
            total_kb = sum(checked_size(f) for f in mod_files) / 1024
            oversized = sum(checked_size(f) > MAX_FILE_BYTES for f in mod_files)
            reviewable = [f for f in mod_files if checked_size(f) <= MAX_FILE_BYTES]
            batches = make_batches(reviewable, root)
            print(
                f"  {mod:<40} {len(mod_files):>4} files  {total_kb:>7.1f}KB  "
                f"{len(batches)} batches  oversized={oversized}"
            )
        return

    # Filter to one exact file or a specific module if requested.
    if args.file:
        candidate = (root / args.file).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            print("--file must stay inside the project root.", file=sys.stderr)
            sys.exit(1)
        if candidate not in files:
            print(
                f"File '{args.file}' is not a reviewable source file.",
                file=sys.stderr,
            )
            sys.exit(1)
        target_files = [candidate]
    elif args.module:
        if args.module not in modules:
            # Try prefix match
            matches = [m for m in modules if m.startswith(args.module)]
            if not matches:
                print(
                    f"Module '{args.module}' not found. Use --list-modules.",
                    file=sys.stderr,
                )
                sys.exit(1)
            target_files = []
            for m in matches:
                target_files.extend(modules[m])
        else:
            target_files = modules[args.module]
    else:
        target_files = files

    selected_file_limit = MAX_BATCH_BYTES if args.file else MAX_FILE_BYTES
    oversized = [f for f in target_files if checked_size(f) > selected_file_limit]
    if oversized:
        print(
            f"Coverage error: {len(oversized)} selected source file(s) exceed "
            f"the selected limit={selected_file_limit}; no review was dispatched.",
            file=sys.stderr,
        )
        for path in oversized:
            print(
                f"  {path.relative_to(root)}: {checked_size(path)} bytes",
                file=sys.stderr,
            )
        print("Implement line-aware chunking or narrow the selection.", file=sys.stderr)
        sys.exit(2)

    batches = make_batches(target_files, root)
    total_kb = sum(checked_size(f) for f in target_files) / 1024

    print(
        f"# {project_name}: {len(target_files)} files, {total_kb:.0f}KB, "
        f"{len(batches)} batches, focus={args.focus}",
        file=sys.stderr,
    )

    if args.dry_run:
        for i, batch in enumerate(batches):
            batch_kb = sum(checked_size(f) for f in batch) / 1024
            print(f"\n  Batch {i + 1} ({batch_kb:.1f}KB, {len(batch)} files):")
            for f in batch:
                print(f"    {f.relative_to(root)}")
        return

    # Determine providers to use
    if args.all_providers:
        providers = list(PROVIDERS.values())
    elif args.both:
        providers = [PROVIDERS["google"], PROVIDERS["openai"]]
    else:
        providers = [PROVIDERS[args.provider]]

    # Load previous findings for dedup
    prev_hashes = load_previous_findings(project_name)

    # Dispatch reviews
    all_findings = []

    def review_batch(batch_idx: int, batch: list[Path], provider: dict):
        import time as _time

        # Throttle: wait before dispatching (helps with Gemini rate limits on large runs)
        if args.delay > 0 and batch_idx > 0:
            _time.sleep(args.delay)
        label = f"{provider['name']}:batch-{batch_idx + 1}"
        code_ctx = build_code_context(batch, root)
        print(
            f"  Dispatching {label} ({len(batch)} files, {len(code_ctx) // 1024}KB)...",
            file=sys.stderr,
        )
        raw = dispatch_review(code_ctx, args.focus, provider, label)
        if raw:
            findings = parse_findings(raw, provider["name"], batch, root)
            print(f"  {label}: {len(findings)} findings", file=sys.stderr)
            return findings
        return []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = []
        for i, batch in enumerate(batches):
            for provider in providers:
                futures.append(pool.submit(review_batch, i, batch, provider))

        for future in as_completed(futures):
            findings = future.result()
            all_findings.extend(findings)

    # Deduplicate against previous findings
    new_findings = []
    for f in all_findings:
        key = f"{f['file']}:{f['category']}:{f['description'][:80]}"
        h = hashlib.sha256(key.encode()).hexdigest()[:12]
        if h not in prev_hashes:
            f["hash"] = h
            f["date"] = str(date.today())
            f["project"] = project_name
            f["focus"] = args.focus
            new_findings.append(f)

    # Write output
    if new_findings:
        out_dir = ARTIFACTS_BASE / project_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{date.today()}.jsonl"

        with open(out_file, "a") as fh:
            for f in new_findings:
                fh.write(json.dumps(f) + "\n")

        print(f"\n# {len(new_findings)} new findings → {out_file}", file=sys.stderr)

        # Also print summary to stdout for orchestrator capture
        by_severity = defaultdict(list)
        for f in new_findings:
            by_severity[f["severity"]].append(f)

        print(f"\n## Code Review: {project_name} ({args.focus})")
        print(f"**Date:** {date.today()}")
        print(f"**Files reviewed:** {len(target_files)}")
        print(
            f"**New findings:** {len(new_findings)} "
            f"(HIGH: {len(by_severity.get('HIGH', []))}, "
            f"MEDIUM: {len(by_severity.get('MEDIUM', []))}, "
            f"LOW: {len(by_severity.get('LOW', []))})\n"
        )

        for sev in ("HIGH", "MEDIUM", "LOW"):
            for f in by_severity.get(sev, []):
                print(
                    f"- **{sev}** `{f['file']}:{f['line']}` [{f['category']}] "
                    f"{f['description']} ({f['source']})"
                )
    else:
        print(f"\n# No new findings for {project_name}/{args.focus}", file=sys.stderr)

    # Report rate-limited providers
    if _rate_limited_providers:
        skipped = ", ".join(sorted(_rate_limited_providers))
        print(
            f"\n**Rate limited:** {skipped} — re-run later or use the other provider.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
