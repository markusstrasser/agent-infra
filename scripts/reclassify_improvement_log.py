#!/usr/bin/env python3
"""Reclassify improvement-log open `[ ]` statuses into the two-stream model (F1+F2).

The `[ ]` glyph is overloaded: it tags actionable infra todos, behavioral
observations (an append-only calibration ledger that can never be `[x]`),
rejected decisions, monitoring notes, AND items whose subject was eradicated.
That inflates the "open" count into a false panic number.

This pass marks TERMINAL things with non-`[ ]` glyphs so `grep '[ ]'` returns
only genuinely-actionable-still-open work. It NEVER deletes — it only rewrites
the status glyph (the gov-id "mark state, never delete" operation).

Glyphs:
  [ ]   actionable, still open      (the only stream "drain the backlog" applies to)
  [obs] logged behavioral observation / monitoring / noted — calibration ledger, terminal
  [~]   retired/moot — subject no longer exists
  [-]   rejected — decided not to do
  [x] [>]  unchanged (implemented / superseded)

Conservative: when in doubt, KEEP `[ ]` (never hide actionable work). Dry-run by
default; pass --write to apply.
"""
import re
import sys
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "improvement-log.md"

# Behavioral finding categories — an append-only calibration ledger. Their consumer
# is recurrence->rule promotion (aggregate), never per-item implementation.
BEHAVIORAL = re.compile(
    r"TOKEN[ _]WASTE|SYCOPHANCY|MISSING PUSHBACK|REASONING-ACTION|OVER-ENGINEER|"
    r"CAPABILITY[ _]ABANDON|PREMATURE[ _]TERMINATION|PREMATURE TERMINATION|"
    r"INFORMATION[ _]WITHHOLD|BUILD-THEN-UNDO|WRONG.TOOL|PERFORMATIVE|"
    r"FIRST-ANSWER|LATENCY-INDUCED|RESOURCE EXHAUSTION|FIX-THEN-RESTART|"
    r"WRITE_STDIN|BUDGET AWARENESS|STALE_DATA_READ|CODEX BRUTE-FORCE|HEREDOC|"
    r"BLIND FIX|BLIND DESTRUCTIVE|SUPERFICIAL HEALTH|PARTIAL SYSTEMIC|SYMLINK-BLIND|"
    r"REASONING-ACTION MISMATCH|MISSING BEHAVIOR|GUARD_EVASION|RULE_VIOLATION|"
    r"RULE VIOLATION|TOOL TRUST|ENVIRONMENT|PROMPT DESIGN|ARCHITECTURAL SUNK|"
    r"Inverted pushback|sunk cost|HOOK OWNERSHIP GUARD",
    re.I,
)

# Subject eradicated 2026-06-07 (orchestrator + its launchd schedule + the exec-session /
# restart churn that only happened under the orchestrator restart loop). BEHAVIORAL is
# checked FIRST, so a behavioral finding that merely *mentions* the orchestrator stays a
# calibration-ledger [obs]; only findings genuinely ABOUT orchestrator infra land here.
MOOT = re.compile(
    r"ORCHESTRATOR|RESTART CHURN|control-plane thrash|journal mutation|"
    r"EXEC SESSION|Exec session leak|exec session",
    re.I,
)

# Explicit keep-open allowlist: genuinely-actionable infra, still valid. Matched on the
# header text. Everything NOT matched here that is behavioral/moot/rejected gets a
# terminal glyph; anything else unmatched keeps `[ ]` (conservative).
KEEP_OPEN = re.compile(
    r"DEAD_INFRA: runlogs\.db|"
    r"IATROGENIC: whole-tree linters|"
    r"GOALS_GAP: no objective|"
    r"RSI_LOOP: end-of-session|"
    r"function-body lazy import inside a MOUNTED|"
    r"serial entity-write gauntlet|"
    r"CONTRACT_BUG: 22 stages|"
    r"risky-diff-review demand probe|"
    r"BUILD-THEN-VALIDATE: Custom MCP server|"
    r"SYSTEM-DESIGN — SKIPPED\+force",
    re.I,
)

HDR = re.compile(r"^### (.*)")
STATUS = re.compile(r"^(- )?\*\*Status:\*\* \[ \](.*)$")


def classify(header: str, status_tail: str) -> tuple[str, str]:
    """Return (new_glyph, note) or ('[ ]', '') to keep open."""
    tail = status_tail.strip()
    if "rejected" in tail.lower():
        return "[-]", ""  # already a decided-no; just re-glyph
    if KEEP_OPEN.search(header):
        return "[ ]", ""  # explicit actionable
    if BEHAVIORAL.search(header):
        return "[obs]", ""  # behavioral calibration ledger, terminal (wins over MOOT)
    if MOOT.search(header):
        return "[~]", " retired — orchestrator + its churn eradicated 2026-06-07 (agent-infra@df9afe0); subject no longer exists"
    if tail.startswith("monitoring") or tail.startswith("noted"):
        return "[obs]", ""  # monitoring/noted = logged, not a todo
    return "[ ]", ""  # unknown -> conservative, keep open


CONVENTION = """
> **Status glyphs (two-stream model, F1 2026-06-08).** `[ ]` is reserved for genuinely
> **actionable, still-open** infra/tooling/architecture work — the only stream "drain the
> backlog" applies to. Terminal dispositions use non-`[ ]` glyphs so a `[ ]` count reflects
> real work, not a panic number:
> - `[x]` implemented · `[>]` superseded-by `<id>` · `[~]` retired/moot (subject gone)
> - `[obs]` **behavioral observation** — an append-only calibration-ledger entry (TOKEN WASTE,
>   SYCOPHANCY, MISSING PUSHBACK, REASONING-ACTION MISMATCH, OVER-ENGINEERING…). Its consumer is
>   recurrence→rule promotion (aggregate signal), NOT per-item implementation — it can never be
>   `[x]`. When a rule ships covering a class, bulk-mark contributors `[>]` superseded-by rule:X.
> - `[-]` rejected — decided not to do.
>
> Session-analyst / `/observe` retro write behavioral findings as `[obs]`, never `[ ]`.
> Backfill of the pre-2026-06-08 log: `scripts/reclassify_improvement_log.py`.
"""


def inject_convention(lines: list[str]) -> list[str]:
    if any("Status glyphs (two-stream model" in l for l in lines):
        return lines  # idempotent
    for i, l in enumerate(lines):
        if l.strip() == "## Findings":
            return lines[: i + 1] + CONVENTION.split("\n") + lines[i + 1 :]
    return lines


def main() -> None:
    write = "--write" in sys.argv
    lines = LOG.read_text().split("\n")
    if write:
        lines = inject_convention(lines)
    cur_header = ""
    changes = []  # (lineno, old, new, glyph, header)
    for i, line in enumerate(lines):
        m = HDR.match(line)
        if m:
            cur_header = m.group(1)
            continue
        s = STATUS.match(line)
        if not s:
            continue
        glyph, note = classify(cur_header, s.group(2))
        if glyph == "[ ]":
            continue  # kept open
        prefix = s.group(1) or ""
        old_tail = s.group(2)
        # preserve the existing descriptive tail; append the moot note if any
        new_line = f"{prefix}**Status:** {glyph}{old_tail}{note}"
        changes.append((i, line, new_line, glyph, cur_header))
        if write:
            lines[i] = new_line

    by_glyph: dict[str, int] = {}
    for _, _, _, g, _ in changes:
        by_glyph[g] = by_glyph.get(g, 0) + 1
    print(f"{'WROTE' if write else 'DRY-RUN'}: {len(changes)} status lines reclassified")
    for g, n in sorted(by_glyph.items()):
        print(f"  {g}: {n}")
    # show residual open count
    remaining = sum(1 for l in lines if STATUS.match(l)) if write else \
        sum(1 for l in lines if STATUS.match(l)) - len(changes)
    print(f"  residual [ ] actionable-open: {remaining}")
    print("\n--- reclassified (header | new glyph) ---")
    for _, _, _, g, h in changes:
        print(f"  {g:6} {h[:95]}")

    if write:
        LOG.write_text("\n".join(lines))
        print(f"\nwrote {LOG}")


if __name__ == "__main__":
    main()
