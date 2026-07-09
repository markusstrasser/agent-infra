#!/usr/bin/env python3
"""act_drain.py — reflect classify + funnel metrics for the RSI loop.

Zero-LLM drain step inside `pulse tick drain`. Surfacing is owned by
`pulse status --write-inbox` — this module does NOT write digests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import loop_funnel as lf  # noqa: E402

REFLECT = REPO / "scripts" / "reflect.py"


def accretion_summary() -> str:
    """L1 read-only accretion hints for the drain digest."""
    try:
        import improvement_log_accretion as ila  # noqa: E402

        return ila.render_report()
    except OSError as e:
        return f"(accretion report error: {e})"


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
        keep = [ln for ln in lines if ln.startswith("[reflect") or ln.startswith("  ▸")
                or ln.startswith("  !") or ln.startswith("Review:")]
        return "\n".join(keep[:30]) or f"(classify exit {r.returncode})"
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"(classify error: {e})"


def drain(*, classify: bool = True) -> tuple[dict, str]:
    """Classify (optional) + funnel metrics."""
    summary = "" if not classify else run_classify()
    return lf.metrics(), summary


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="ACT drain — classify + funnel metrics")
    ap.add_argument("--no-classify", action="store_true", help="Metrics only, skip classify")
    args = ap.parse_args()

    metrics, summary = drain(classify=not args.no_classify)
    print(lf.render(metrics), end="")
    print(accretion_summary())
    if summary:
        print("\n## Last classify run\n```\n" + summary[:2000] + "\n```\n")
    print(f"[act-drain] disposition={metrics['disposition_queue']} unclassified={metrics['unclassified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
