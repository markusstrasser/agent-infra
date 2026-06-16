#!/usr/bin/env python3
"""act_drain.py — scheduled ACT half of the RSI loop (zero-LLM).

Runs reflect classify (cheap deterministic drain), then ranks the human
disposition queue. Writes ~/.claude/act-drain-digest.md when anything needs
attention; removes it when all green (same no-noise pattern as drift-sentinel).

Scheduled: com.agent-infra.act-drain (daily). Surfaces at SessionStart via
act-drain-surface.sh. Manual: just act-drain.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import loop_funnel as lf  # noqa: E402
import questions_view as qv  # noqa: E402

DIGEST = Path.home() / ".claude" / "act-drain-digest.md"
REFLECT = REPO / "scripts" / "reflect.py"


def run_classify() -> str:
    """Run reflect classify; return stdout summary (fail-open)."""
    try:
        r = subprocess.run(
            [sys.executable, str(REFLECT), "classify"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO),
        )
        lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
        # Keep header + quarantine lines; skip per-signal attach spam.
        keep = [ln for ln in lines if ln.startswith("[reflect") or ln.startswith("  ▸")
                or ln.startswith("  !") or ln.startswith("Review:")]
        return "\n".join(keep[:30]) or f"(classify exit {r.returncode})"
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"(classify error: {e})"


def build_digest(classify_summary: str) -> tuple[str | None, dict]:
    m = lf.metrics()
    # The focused "Questions for you" VIEW (ADR 2026-06-16-agent-question-convergence):
    # human-gated questions surface regardless of the funnel metrics — a lone pending
    # decision is not counted by needs_attention(), so we OR it in here.
    qsection = qv.render_section(qv.collect_questions(REPO))
    if not lf.needs_attention(m) and not qsection:
        return None, m
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"# ACT drain — {stamp}",
        "_Daily zero-LLM drain: classify + disposition queue. "
        "Triage in any session; auto-clears when green._",
        "",
    ]
    if qsection:  # FOCUS FIRST — the questions, before the funnel counts (ADR invariant #3)
        parts.extend([qsection, ""])
    parts.append(lf.render(m))
    if classify_summary:
        parts.extend(["## Last classify run", "```", classify_summary[:2000], "```", ""])
    parts.append("**Next:** `/rsi close` for pending digests · "
                 "`just reflect-review` for quarantine · "
                 "steward-proposals for cross-repo hooks.")
    return "\n".join(parts) + "\n", m


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="ACT drain — classify + disposition digest")
    ap.add_argument("--no-classify", action="store_true", help="Metrics only, skip classify")
    ap.add_argument("--digest-path", default=str(DIGEST))
    args = ap.parse_args()

    summary = "" if args.no_classify else run_classify()
    digest, m = build_digest(summary)
    path = Path(args.digest_path)
    if digest:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(digest, encoding="utf-8")
        print(f"[act-drain] wrote digest — disposition={m['disposition_queue']} "
              f"unclassified={m['unclassified']}")
        return 0
    path.unlink(missing_ok=True)
    print("[act-drain] all green — no digest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
