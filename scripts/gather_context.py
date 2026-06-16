#!/usr/bin/env python3
"""Deterministic v0 context gather for `just gather` / `just critique`.

NO LLM. Given a target doc (a plan, ADR, or design memo), this:
  1. extracts referenced repo-relative paths from the doc text,
  2. existence-checks them (resolved → gathered; unresolved → missing),
  3. collects ambient provenance (git log for the target),
  4. delegates packet assembly to the EXISTING builder
     (skills/critique/scripts/build_plan_close_context.py),
  5. emits the brief-schema with an HONEST `missing:` field.

This is the "deterministic middle" of the dispatch unification plan
(.claude/plans/2026-06-16-just-cli-dispatch-unification.md, Phase 1.3).
It does NOT do LLM auto-discovery — referenced paths are pulled by literal
text extraction, and anything the doc does not name is reported as not
reached, never silently assumed covered. The honest `missing:` field is the
signal the middle layer is actually working: when it is routinely non-empty
for novel paths, the v0 has hit its ceiling and Phase 2 generalization is
warranted (per the plan's HALT/expand gate).

Brief-schema (every dispatch recipe emits this):
  gathered: <sources covered>
  missing:  <not reached + caveats>
  findings: <engine output, or "context-only" at the gather stage>
  drill:    just gather <path> --json
  next:     just critique <path>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BUILDER = Path(__file__).resolve().parent.parent.parent / "skills" / "critique" / "scripts" / "build_plan_close_context.py"

# Extensions we treat as real in-repo artifacts when path-extracting.
CODE_EXTS = {
    "py", "md", "sql", "ts", "tsx", "js", "jsx", "sh", "json", "toml",
    "yaml", "yml", "txt", "rs", "go", "html", "css", "plist",
}

# markdown link target:  [label](path)
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# inline-code or bare token that looks like a path (has a slash or known ext).
# Extensions are tried longest-first AND a trailing (?!\w) word-boundary guard so
# `.json` never truncates to `.js` (alternation-ordering bug) — that would
# misclassify real .json refs as missing.
_PATH_TOKEN = re.compile(
    r"`?([\w./~@-]+\.(?:" + "|".join(sorted(CODE_EXTS, key=len, reverse=True)) + r"))(?!\w)"
)


def extract_paths(text: str) -> list[str]:
    """Pull candidate file references from doc text. Order-preserving, deduped."""
    seen: dict[str, None] = {}
    for m in _MD_LINK.finditer(text):
        seen.setdefault(m.group(1).strip(), None)
    for m in _PATH_TOKEN.finditer(text):
        seen.setdefault(m.group(1).strip(), None)
    out = []
    for raw in seen:
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        # strip a trailing line/anchor suffix and surrounding punctuation
        cand = raw.split("#", 1)[0].rstrip(".,:;)").lstrip("(")
        if not cand or cand in {".", "..", "./", "../"}:
            continue
        # a real path segment never starts with '-' — this is a placeholder
        # fragment (e.g. `<slug>-context.md` → `-context.md`), not a ref.
        if cand.startswith("-"):
            continue
        out.append(cand)
    return out


def classify(paths: list[str], repo: Path) -> tuple[list[str], list[str], list[str]]:
    """Partition into (in_repo_existing, external_existing, missing).

    in_repo_existing → fed to the builder as --file.
    external_existing → noted as gathered context but NOT inlined (packet is repo-local).
    missing → noted honestly (broken ref, future file, or out-of-tree).
    """
    in_repo: list[str] = []
    external: list[str] = []
    missing: list[str] = []
    for p in paths:
        expanded = Path(p).expanduser()
        # in-repo resolution: relative to repo root
        rel = (repo / p)
        if not p.startswith(("/", "~")) and rel.is_file():
            in_repo.append(p)
        elif expanded.is_absolute() and expanded.is_file():
            external.append(str(expanded))
        elif p.startswith("~") and expanded.is_file():
            external.append(str(expanded))
        else:
            missing.append(p)
    return in_repo, external, missing


def git_provenance(repo: Path, target_rel: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "log", "--oneline", "--no-ext-diff",
             "-8", "--", target_rel],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    return out.splitlines() if out else []


def build_packet(repo: Path, target_rel: str, in_repo: list[str], output: Path,
                 max_files: int) -> int:
    cmd = [
        "uv", "run", "python3", str(BUILDER),
        "--repo", str(repo), "--output", str(output),
        "--file", target_rel, "--max-files", str(max_files),
    ]
    # cap referenced files so the packet stays within the builder's budget
    for ref in in_repo[: max_files - 1]:
        if ref != target_rel:
            cmd += ["--file", ref]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic v0 context gather (no LLM).")
    ap.add_argument("path", help="Target doc to gather context around (plan/ADR/memo)")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--output", type=Path, default=None,
                    help="Packet path (default .model-review/<slug>-context.md)")
    ap.add_argument("--max-files", type=int, default=12)
    ap.add_argument("--json", action="store_true", help="Emit coverage as JSON")
    ap.add_argument("--no-packet", action="store_true",
                    help="Only compute coverage; skip builder invocation")
    args = ap.parse_args()

    repo = args.repo.resolve()
    target = (repo / args.path) if not Path(args.path).is_absolute() else Path(args.path)
    if not target.is_file():
        print(f"target not found: {args.path}", file=sys.stderr)
        return 2
    try:
        target_rel = str(target.resolve().relative_to(repo))
    except ValueError:
        print(f"target must live inside --repo ({repo}): {args.path}", file=sys.stderr)
        return 2

    slug = Path(target_rel).stem
    output = args.output or (repo / ".model-review" / f"{slug}-context.md")
    output.parent.mkdir(parents=True, exist_ok=True)

    text = target.read_text(errors="replace")
    paths = extract_paths(text)
    in_repo, external, missing = classify(paths, repo)
    provenance = git_provenance(repo, target_rel)

    packet_rc = 0
    if not args.no_packet:
        packet_rc = build_packet(repo, target_rel, in_repo, output, args.max_files)

    coverage = {
        "target": target_rel,
        "packet": str(output) if not args.no_packet else None,
        "packet_ok": packet_rc == 0,
        "gathered": {
            "target": target_rel,
            "in_repo_refs": in_repo,
            "external_refs": external,
            "git_provenance": provenance,
        },
        "missing": {
            "unresolved_refs": missing,
            "caveat": "deterministic v0 — LLM auto-discovery NOT run; "
                      "ambient deps the doc does not name by path are not covered",
        },
    }
    cov_path = output.with_name(f"{slug}-coverage.json")
    cov_path.write_text(json.dumps(coverage, indent=2))

    if args.json:
        print(json.dumps(coverage, indent=2))
        return 0 if packet_rc == 0 else 1

    print(f"gathered: target + {len(in_repo)} in-repo refs, {len(external)} external refs, "
          f"{len(provenance)} provenance commits")
    if missing:
        print(f"missing:  {len(missing)} unresolved ref(s): {', '.join(missing[:6])}"
              + (" …" if len(missing) > 6 else ""))
    else:
        print("missing:  no unresolved refs (LLM auto-discovery NOT run — ambient deps uncovered)")
    print("findings: context-only at gather stage — run `just critique` to dispatch the engine")
    print(f"drill:    just gather {args.path} --json    (coverage → {cov_path.name})")
    print(f"next:     just critique {args.path}")
    return 0 if packet_rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
