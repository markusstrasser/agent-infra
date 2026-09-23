#!/usr/bin/env python3
"""Replay the ctx-wrapup Stop hook's threshold against real fill cycles.

skills/hooks/stop-context-wrapup.py nudges a session to commit and checkpoint
before native auto-compact. It can fire only at a turn end, so the useful
question is how much room is left when it fires. For every auto
compact_boundary in recent transcripts this collects preTokens (the real
trigger) and the context at each turn end in that fill cycle, then replays
the hook's current threshold plus a few alternatives.

Usage: ctx_wrapup_replay.py [days]   (default 21)
"""
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

HOOK = Path.home() / "Projects/skills/hooks/stop-context-wrapup.py"
UNCONFIGURED_WINDOW = 500_000  # the hook's resolved window for unconfigured 1M sessions


def load_hook():
    spec = importlib.util.spec_from_file_location("ctx_wrapup", HOOK)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def turn_end_ctx(line: str) -> int | None:
    if '"stop_reason":"end_turn"' not in line and '"stop_reason":"stop_sequence"' not in line:
        return None
    try:
        usage = json.loads(line)["message"]["usage"]
    except (ValueError, KeyError, TypeError):
        return None
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def fill_cycles(days: float) -> list[tuple[str, int, list[int]]]:
    """(session prefix, preTokens, turn-end contexts) per auto-compaction."""
    cutoff = time.time() - days * 86_400
    cycles = []
    for path in Path.home().glob(".claude/projects/*/*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        ends: list[int] = []
        for line in path.read_text(errors="replace").splitlines():
            if '"compact_boundary"' in line:
                try:
                    meta = json.loads(line).get("compactMetadata") or {}
                except ValueError:
                    continue
                if meta.get("trigger") == "auto" and meta.get("preTokens"):
                    cycles.append((path.stem[:8], meta["preTokens"], ends))
                ends = []
                continue
            ctx = turn_end_ctx(line)
            if ctx is not None:
                ends.append(ctx)
    return cycles


def main() -> int:
    days = float(sys.argv[1]) if len(sys.argv) > 1 else 21
    hook = load_hook()
    cycles = [c for c in fill_cycles(days) if c[1] > 250_000]  # 1M-window sessions
    if not cycles:
        print(f"no 1M-window auto-compactions in {days:.0f}d")
        return 0
    pres = [pre for _, pre, _ in cycles]
    trigger, current = hook.thresholds(UNCONFIGURED_WINDOW)
    print(f"{len(cycles)} auto-compactions in {days:.0f}d; preTokens median {statistics.median(pres):,.0f}"
          f" (min {min(pres):,}, max {max(pres):,}); hook assumes trigger {trigger:,}")
    print(f"{'threshold':>10} {'fires':>9} {'median lead':>12} {'lead>=25K':>10}")
    for threshold in sorted({current, 455_000, 425_000, 400_000, 375_000}, reverse=True):
        leads = [pre - hit for _, pre, ends in cycles
                 if (hit := next((c for c in ends if threshold <= c < pre), None)) is not None]
        roomy = sum(1 for lead in leads if lead >= 25_000)
        mark = "  <- hook" if threshold == current else ""
        median = f"{statistics.median(leads):,.0f}" if leads else "-"
        print(f"{threshold:>10,} {len(leads):>4}/{len(cycles):<4} {median:>12} {roomy / len(cycles):>10.0%}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
