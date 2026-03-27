#!/usr/bin/env python3
"""Check latest versions of AI vendor tools and SDKs.

Checks npm, PyPI, and GitHub for latest releases.
Compares with locally installed versions where available.
Outputs markdown table + JSON cache for diff detection.

Usage:
    uv run python3 scripts/vendor-versions.py              # markdown to stdout
    uv run python3 scripts/vendor-versions.py --json        # json to stdout
    uv run python3 scripts/vendor-versions.py --output DIR  # write .md + .json to DIR
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def npm_latest(package: str) -> dict:
    """Get latest version from npm registry."""
    try:
        url = f"https://registry.npmjs.org/{package}/latest"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {"version": data.get("version", "?"), "source": "npm"}
    except Exception as e:
        return {"version": "error", "error": str(e), "source": "npm"}


def pypi_latest(package: str) -> dict:
    """Get latest version from PyPI."""
    try:
        url = f"https://pypi.org/pypi/{package}/json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {"version": data["info"]["version"], "source": "pypi"}
    except Exception as e:
        return {"version": "error", "error": str(e), "source": "pypi"}


def github_latest_release(owner: str, repo: str) -> dict:
    """Get latest release from GitHub API."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "vendor-versions/1.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                "version": data.get("tag_name", "?"),
                "published": data.get("published_at", "")[:10],
                "source": "github",
            }
    except Exception as e:
        return {"version": "error", "error": str(e), "source": "github"}


def local_version(cmd: list[str]) -> str | None:
    """Run a version command locally."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Take first line, strip common suffixes
            line = result.stdout.strip().split("\n")[0]
            return line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


# ── Registry of checks ──────────────────────────────────────────────
# (label, vendor, check_fn, args)
CHECKS = [
    # Anthropic
    ("Claude Code", "anthropic", npm_latest, ("@anthropic-ai/claude-code",)),
    ("Anthropic Python SDK", "anthropic", pypi_latest, ("anthropic",)),
    ("Anthropic TS SDK", "anthropic", npm_latest, ("@anthropic-ai/sdk",)),
    ("Claude Agent SDK", "anthropic", pypi_latest, ("claude-agent-sdk",)),
    ("MCP Python SDK", "anthropic", pypi_latest, ("mcp",)),
    ("MCP TS SDK", "anthropic", npm_latest, ("@modelcontextprotocol/sdk",)),
    # OpenAI
    ("Codex CLI", "openai", npm_latest, ("@openai/codex",)),
    ("OpenAI Python SDK", "openai", pypi_latest, ("openai",)),
    ("OpenAI TS SDK", "openai", npm_latest, ("openai",)),
    ("OpenAI Agents SDK", "openai", pypi_latest, ("openai-agents",)),
    # Google
    ("Gemini CLI", "google", npm_latest, ("@google/gemini-cli",)),
    ("Google GenAI SDK", "google", pypi_latest, ("google-genai",)),
    ("Google ADK", "google", pypi_latest, ("google-adk",)),
    # Kimi
    ("Kimi CLI", "kimi", pypi_latest, ("kimi-cli",)),
    # Modal
    ("Modal", "modal", pypi_latest, ("modal",)),
]

LOCAL_CHECKS = [
    ("Claude Code (local)", "anthropic", ["claude", "--version"]),
    ("Codex CLI (local)", "openai", ["codex", "--version"]),
    ("Gemini CLI (local)", "google", ["gemini", "--version"]),
    ("Kimi CLI (local)", "kimi", ["kimi", "--version"]),
    ("Modal (local)", "modal", ["modal", "--version"]),
]


def run_checks() -> list[dict]:
    """Run all checks in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for label, vendor, fn, args in CHECKS:
            fut = pool.submit(fn, *args)
            futures[fut] = (label, vendor)

        for fut in as_completed(futures):
            label, vendor = futures[fut]
            try:
                info = fut.result()
            except Exception as e:
                info = {"version": "error", "error": str(e)}
            info["label"] = label
            info["vendor"] = vendor
            results.append(info)

    # Local checks (sequential, fast)
    for label, vendor, cmd in LOCAL_CHECKS:
        ver = local_version(cmd)
        if ver:
            results.append({
                "label": label,
                "vendor": vendor,
                "version": ver,
                "source": "local",
            })

    results.sort(key=lambda r: (r.get("vendor", ""), r.get("label", "")))
    return results


def format_markdown(results: list[dict], prev: dict | None = None) -> str:
    """Format results as markdown table with delta indicators."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Vendor Versions — {now}",
        "",
        "| Tool | Version | Source | Delta |",
        "|------|---------|--------|-------|",
    ]

    current_vendor = None
    for r in results:
        vendor = r.get("vendor", "")
        if vendor != current_vendor and vendor != "local":
            current_vendor = vendor
            lines.append(f"| **{vendor.title()}** | | | |")

        label = r["label"]
        ver = r["version"]
        src = r.get("source", "?")

        delta = ""
        if prev and label in prev:
            old = prev[label]
            if old != ver and ver != "error":
                delta = f"**{old} -> {ver}**"
        elif prev is not None and label not in prev:
            delta = "NEW"

        err = ""
        if "error" in r and r["version"] == "error":
            err = f" ({r['error'][:60]})"

        lines.append(f"| {label} | `{ver}`{err} | {src} | {delta} |")

    return "\n".join(lines) + "\n"


def load_previous(path: Path) -> dict | None:
    """Load previous version JSON for delta detection."""
    try:
        data = json.loads(path.read_text())
        return {item["label"]: item["version"] for item in data.get("results", [])}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Check AI vendor tool versions")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--output", type=Path, help="Write .md + .json to directory")
    args = parser.parse_args()

    results = run_checks()
    now = datetime.now(timezone.utc).isoformat()

    prev = None
    if args.output:
        prev = load_previous(args.output / "vendor-versions.json")

    if args.json:
        print(json.dumps({"checked_at": now, "results": results}, indent=2))
    elif args.output:
        args.output.mkdir(parents=True, exist_ok=True)

        md = format_markdown(results, prev)
        (args.output / "vendor-versions.md").write_text(md)

        json_data = {"checked_at": now, "results": results}
        (args.output / "vendor-versions.json").write_text(
            json.dumps(json_data, indent=2) + "\n"
        )

        # Summary to stdout
        changes = [
            r for r in results
            if prev and r["label"] in prev
            and prev[r["label"]] != r["version"]
            and r["version"] != "error"
        ]
        if changes:
            print(f"{len(changes)} version change(s) detected:")
            for c in changes:
                old = prev.get(c["label"], "?") if prev else "?"
                print(f"  {c['label']}: {old} -> {c['version']}")
        else:
            print(f"{len(results)} packages checked, no changes")
    else:
        print(format_markdown(results, prev))


if __name__ == "__main__":
    main()
