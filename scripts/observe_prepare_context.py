#!/usr/bin/env python3
"""Build size-safe observe dispatch context (wc -c gate before llm-dispatch).

Default mix: primary project full Claude transcript + trimmed Codex + coverage + ops.
Drops Codex first, then reduces --sessions, to stay under --max-bytes (default 580000).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SKILL = Path.home() / ".claude/skills/observe"
DEFAULT_MAX = 580_000
SEP = "\n\n---\n\n"
SIGPIPE = 141


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _run_shell_to_file(script: Path, out: Path) -> None:
    """Run a shell script with stdout to *out*; tolerate benign SIGPIPE (141)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        proc = subprocess.run(
            ["bash", str(script)],
            stdout=fh,
            stderr=subprocess.PIPE,
            text=True,
        )
    if proc.returncode == 0:
        return
    if proc.returncode == SIGPIPE and out.stat().st_size > 0:
        return
    err = (proc.stderr or "").strip()
    raise subprocess.CalledProcessError(
        proc.returncode,
        ["bash", str(script)],
        output=err or None,
    )


def extract(project: str, sessions: int, full: bool, out: Path, codex: bool) -> None:
    args = [
        sys.executable,
        str(SKILL / "scripts/extract_transcript.py"),
        project,
        "--sessions",
        str(sessions),
        "--output",
        str(out),
    ]
    if full:
        args.insert(-2, "--full")
    _run(args)
    if codex:
        codex_out = out.parent / (out.stem.replace("input", "codex") + ".md")
        if out.name == "input.md":
            codex_out = out.parent / "codex.md"
        try:
            _run([
                sys.executable,
                str(SKILL / "scripts/extract_codex_transcript.py"),
                project,
                "--sessions",
                str(sessions),
                "--output",
                str(codex_out),
            ])
        except subprocess.CalledProcessError:
            codex_out.write_text("")
    else:
        (out.parent / "codex.md").write_text("")


def build_context(
    artifact_dir: Path,
    max_bytes: int,
    include_codex: bool,
) -> tuple[Path, int, list[str]]:
    notes: list[str] = []
    root = artifact_dir
    input_md = root / "input.md"
    codex_md = root / "codex.md"
    ops = root / "operational-context.txt"
    cov = root / "coverage-digest.txt"

    if not cov.is_file():
        digest = Path(__file__).resolve().parents[1] / "scripts/coverage-digest.sh"
        _run_shell_to_file(digest, cov)

    parts: list[Path] = [input_md]
    if include_codex and codex_md.stat().st_size > 0:
        parts.append(codex_md)
    if ops.is_file() and ops.stat().st_size > 0:
        parts.append(ops)
    parts.append(cov)

    def size(parts_list: list[Path]) -> int:
        total = 0
        for i, p in enumerate(parts_list):
            if p.is_file():
                total += p.stat().st_size
            if i:
                total += len(SEP)
        return total

    # Trim codex if over budget
    while include_codex and codex_md in parts and size(parts) > max_bytes:
        parts.remove(codex_md)
        notes.append("dropped codex.md (size cap)")

    out = root / "observe-context.md"
    while size(parts) > max_bytes and input_md in parts:
        if include_codex and codex_md in parts:
            parts.remove(codex_md)
            notes.append("dropped codex.md (size cap)")
            continue
        text = input_md.read_text(errors="replace")
        keep = int(len(text) * 0.75)
        if keep < 10_000:
            break
        input_md.write_text(text[:keep] + "\n\n[TRUNCATED for dispatch size cap]\n")
        notes.append(f"truncated input.md to {keep} chars")

    with out.open("w") as f:
        for i, p in enumerate(parts):
            if i:
                f.write(SEP)
            if p.is_file():
                f.write(p.read_text(errors="replace"))
    n = out.stat().st_size
    return out, n, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare observe context under byte cap")
    ap.add_argument("--project", default="agent-infra")
    ap.add_argument("--sessions", type=int, default=5)
    ap.add_argument("--artifact-dir", type=Path, default=Path("artifacts/observe"))
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_MAX)
    ap.add_argument("--no-codex", action="store_true")
    ap.add_argument("--full", action="store_true", default=True)
    ap.add_argument("--extract-only", action="store_true")
    args = ap.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    extract(args.project, args.sessions, args.full, args.artifact_dir / "input.md", not args.no_codex)

    if args.extract_only:
        print(args.artifact_dir / "input.md")
        return 0

    out, nbytes, notes = build_context(args.artifact_dir, args.max_bytes, not args.no_codex)
    print(f"context={out} bytes={nbytes} max={args.max_bytes}")
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    if nbytes > args.max_bytes:
        print(f"ERROR: still over cap ({nbytes} > {args.max_bytes})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
