#!/usr/bin/env python3
"""Sensor integration ranking — daily RSI priority memo.

llm: optional (--synthesis). Default: deterministic (launchd-safe).

Usage:
  sensor_integration_ranking.py
  sensor_integration_ranking.py --synthesis
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from tool_contract import LlmClass, llm_denied, print_llm_header

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _excerpt(path: Path, lines: int = 40) -> str:
    if not path.is_file():
        return f"(missing: {path.relative_to(REPO)})"
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:lines])


def gather_context(days: int) -> str:
    from loop_funnel import metrics

    m = metrics()
    parts = [
        f"# Integration rank inputs — {date.today().isoformat()}",
        f"_window: blindspot {days}d digest excerpt; funnel live_",
        "",
        "## Blindspot digest",
        _excerpt(REPO / ".claude/blindspot-digest.md", 45),
        "",
        "## Loop funnel",
        f"- captured: **{m['captured']}** → classified: **{m['classified']}** "
        f"(unclassified: **{m['unclassified']}**)",
        f"- disposition queue: **{m['disposition_queue']}** · RSI close pending: **{m['rsi_close_pending']}**",
        f"- sessions (7d): **{(m.get('session_split_7d') or {}).get('total', '?')}** · "
        f"automation **{(m.get('session_split_7d') or {}).get('automation_pct', '?')}%**",
        "",
    ]
    cand_path = REPO / "config/maintain-candidates.json"
    if cand_path.is_file():
        data = json.loads(cand_path.read_text(encoding="utf-8"))
        open_c = [c for c in data.get("candidates", []) if not c.get("done")]
        parts.append("## Maintain candidates (open)")
        if open_c:
            for c in open_c:
                parts.append(f"- **{c['id']}** ({c.get('blast_radius', '?')}) — {c.get('title', '')}")
        else:
            parts.append("- (none — motor queue empty)")
        parts.append("")
    log_tail = REPO / "maintenance-actions.jsonl"
    if log_tail.is_file():
        tail = log_tail.read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
        parts.extend(["## maintenance-actions (tail)", ""] + [f"- `{ln}`" for ln in tail if ln.strip()] + [""])
    return "\n".join(parts)


def _blindspot_buckets(ctx: str) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for kind in ("rediscovery", "over_caution", "error_correction"):
        m = re.search(rf"\({kind}=(\d+)\)", ctx)
        if m:
            buckets[kind] = int(m.group(1))
    return buckets


def deterministic_rank(ctx: str) -> str:
    day = date.today().isoformat()
    buckets = _blindspot_buckets(ctx)
    lines = [
        f"# Sensor integration ranking — {day} (deterministic)",
        "",
        "## Top 3",
    ]
    rank = 1

    cand_path = REPO / "config/maintain-candidates.json"
    if cand_path.is_file():
        for c in json.loads(cand_path.read_text(encoding="utf-8")).get("candidates", []):
            if c.get("done"):
                continue
            tier = "tier-0" if c.get("blast_radius") == "agent-infra" else "human-gate (shared)"
            lines.append(
                f"{rank}. **{c['id']}** — {c.get('title', '')} | autonomy: {tier} | "
                f"gate: {c.get('build_kind', 'build')}"
            )
            rank += 1
            if rank > 3:
                break

    if buckets.get("rediscovery", 0) >= buckets.get("over_caution", 0):
        lines.append(
            f"{rank}. **prior-context v2 / existing_infra** — "
            f"rediscovery={buckets.get('rediscovery', 0)} dominates blindspot | "
            "autonomy: tier-0 | gate: prior_context_triage ship slice"
        )
    else:
        lines.append(
            f"{rank}. **over_caution instrumentation** — "
            f"over_caution={buckets.get('over_caution', 0)} | "
            "autonomy: eval-gated | gate: behavioral smoke"
        )

    lines.extend(
        [
            "",
            "## Deferred",
            "- Full RSI rebuild (field converged on our arch)",
            "- integrate-rank LLM path (deterministic default; use `--synthesis` to opt in)",
            "",
            "## Noise dropped",
            "- Retired maintain candidates (`done: true`)",
            "",
            "_Sensors excerpt:_",
            "```",
            ctx[:3500] + ("…" if len(ctx) > 3500 else ""),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def llm_rank(ctx_path: Path, out_path: Path) -> bool:
    """Optional deep_review synthesis — returns False on failure."""
    try:
        import subprocess

        prompt = (
            "Rank top 3 integration/build priorities for the RSI loop from the sensor excerpt. "
            "Format: numbered list with autonomy tier + verifier gate. One paragraph deferred/noise."
        )
        subprocess.run(
            [
                "uv", "run", "python3",
                str(Path.home() / "Projects/skills/scripts/llm-dispatch.py"),
                "--profile", "deep_review",
                "--context", str(ctx_path),
                "--prompt", prompt,
                "--output", str(out_path),
            ],
            check=True,
            cwd=REPO,
            capture_output=True,
            timeout=180,
        )
        return out_path.is_file() and out_path.stat().st_size > 50
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthesis", action="store_true", help="LLM rank via deep_review")
    ap.add_argument("--no-llm", action="store_true", help="Force deterministic")
    ap.add_argument("--days", type=int, default=7, help="blindspot digest window label")
    args = ap.parse_args()

    use_llm = args.synthesis and not args.no_llm and not llm_denied()
    print_llm_header(LlmClass.OPTIONAL if use_llm else LlmClass.NONE,
                     "synthesis" if use_llm else "deterministic")

    day = date.today().isoformat()
    art = REPO / "artifacts" / "sensor-integration-ranking"
    art.mkdir(parents=True, exist_ok=True)
    ctx_path = art / f"{day}-context.md"
    ctx = gather_context(args.days)
    ctx_path.write_text(ctx, encoding="utf-8")

    out_research = REPO / "research" / f"{day}-sensor-integration-ranking.md"
    tmp_out = art / f"{day}-rank.md"

    if use_llm and llm_rank(ctx_path, tmp_out):
        body = tmp_out.read_text(encoding="utf-8")
    else:
        if args.synthesis and not args.no_llm:
            print("synthesis failed — deterministic fallback", file=sys.stderr)
        body = deterministic_rank(ctx)

    out_research.write_text(body, encoding="utf-8")
    print(out_research)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
