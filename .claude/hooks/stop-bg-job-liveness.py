#!/usr/bin/env python3
"""stop-bg-job-liveness.py — don't end a turn waiting on a job that is already gone.

Stop hook. The failure it catches, in the agent's own words:

    "I'll stop polling and end my turn here. The background monitor b7refde6z will
     surface the motif activity tables when the scan finishes..."

...except nothing ever showed up to wake it. In the benchmarks.bio Opus 5 biology
evaluation (4,674 trajectories, 2026-07-25) *all three* hard six-hour timeouts ended
exactly there — parked on an await for a harness-backgrounded job whose completion
notification never arrived. A fourth run burned 17 minutes blocked on a stray helper
because it read its instructions as forbidding it to end a turn while any job was
still running. Locally the same class is well documented: reaps at ~57 min AND at
~2-4 min, a Monitor that died silently at its undocumented 60-minute cap, teammate
Monitor notifications that batch-queue and never resume the teammate, and a parent
that declared a live 23-minute episode dead from log staleness.

Why a hook, not an instruction: ~/.claude/rules/wakeup-cadence.md already carries
SEVEN rules on this class, including the exact predicate ("a staleness signal
LOCATES, exact-PID DECIDES"). They keep not holding, which is Constitution
Principle 1's definition of a checkable predicate that belongs in architecture.

THE MECHANISM (validated empirically 2026-07-25, live and dead job side by side):
every harness-backgrounded Bash call writes to a deterministic artifact,
    <tmp>/claude-<uid>/<project-slug>/<session-id>/tasks/<bash_id>.output
and `lsof -t` on that file is authoritative about liveness:
    live job -> the whole process tree holds it open (shell wrapper, uv, python3)
    dead job -> zero holders, whether it completed or was reaped
So we need no PID ledger and no substring pgrep (banned: `*forkDC*` once matched
`forkDCH` and killed a healthy train client). `lsof` IS the principal check.

Contract (Claude Code 2.1.x):
  - Stop envelope on stdin: `.session_id`, `.transcript_path`, `.stop_hook_active`.
  - Advisory ONLY — emits reason text, never `{"decision":"block"}`.
  - Fails OPEN: any error -> exit 0, silent.
  - Honors `stop_hook_active` (infinite-loop guard, per the hook design principles).

ANTI-RATCHET, and the reason this hook says two different things:
the Stop fleet on this machine is 15 gates deep and several of them push "don't
stop yet" (stop-progress-check, stop-goal-wrapup, stop_loop_ended_on_question, plus
the TRIAGE-DISPATCH prompt injection). A liveness gate that could only ever say
*keep going* would deepen the exact ratchet that cost that run 17 minutes. So when
every awaited job is gone this hook states plainly that **ending the turn is
correct** — and when a job is genuinely still running it stays silent rather than
nagging, because that wait is legitimate.

Scope: this is the AGENT-INFRA-LOCAL build, wired only in this repo's
.claude/settings.json. Registering it in the global ~/.claude/settings.json is a
shared-tier action across 3+ projects and needs operator sign-off (hard limit #4).
"""
# Gov-ID: hook:stop-bg-job-liveness
# goal: stop the agent ending (or refusing to end) a turn on an await for a
#       background job that is already gone — the 3/3 hard-timeout signature in
#       the benchmarks.bio Opus 5 evaluation, and a repeat local failure class
# verifier: lsof holder count on the job's .output artifact (deterministic)
# blast_radius: local  # agent-infra-only registration; global = operator-gated
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time

MAX_JOBS = 8  # newest N output artifacts; lsof is ~10-30ms each
DEDUPE_SECONDS = 900  # one nudge per job per 15 min
TAIL_CHARS = 400
TAIL_LINES = 6

# A harness bash id as it appears in the tool result: "background with ID: bi4f9yfdw"
BASH_ID = re.compile(r"\b(b[a-z0-9]{7,10})\b")

# The agent is *awaiting* something, as opposed to merely mentioning a job it
# already read. Tight on purpose: a turn that finished and mentions "background"
# in passing must not fire this.
AWAITING = re.compile(
    r"(?:"
    r"wait(?:ing)?\s+(?:for|on)\b|"
    r"will\s+(?:notify|surface|report|appear|wake|come\s+back)|"
    r"when\s+(?:it|the\s+\w+)\s+(?:completes?|finishes|lands)|"
    r"(?:still\s+)?(?:running|in\s+flight|in\s+progress)\b|"
    r"(?:keep|continue|resume)\s+polling|"
    r"poll(?:ing)?\s+(?:again|until)|"
    r"once\s+(?:it|the\s+\w+)\s+(?:completes?|finishes)|"
    r"end(?:ing)?\s+my\s+turn\s+here"
    r")",
    re.IGNORECASE,
)


def _final_assistant_text(transcript_path: str) -> str:
    """Last assistant message's text blocks, concatenated."""
    try:
        with open(transcript_path, errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            text = "\n".join(p for p in parts if p)
            if text.strip():
                return text
    return ""


def _task_outputs(session_id: str) -> list[str]:
    """Background-job output artifacts for THIS session.

    The session id is unique, so globbing on it avoids having to re-derive the
    project-slug encoding (which is a harness implementation detail).
    """
    if not session_id:
        return []
    hits: list[str] = []
    for base in ("/private/tmp", "/tmp", os.environ.get("TMPDIR", "") or "/tmp"):
        pat = os.path.join(base, "claude-*", "*", session_id, "tasks", "*.output")
        hits.extend(glob.glob(pat))
    uniq = {os.path.realpath(h) for h in hits}
    return sorted(uniq, key=lambda p: os.path.getmtime(p), reverse=True)[:MAX_JOBS]


def _holders(path: str) -> list[str]:
    """PIDs holding the artifact open. Empty == the job is no longer running.

    This is the principal check, not a proxy: a reaped job and a completed job
    both release the file, and either way there is nothing left to wait for.
    """
    try:
        out = subprocess.run(
            ["lsof", "-t", "--", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ["unknown"]  # lsof unavailable -> assume live, stay silent
    return [p for p in out.stdout.split() if p.strip()]


def _tail(path: str, n: int = TAIL_CHARS) -> str:
    """Last few lines, capped by both line count and chars.

    Line-capped as well as char-capped because a chatty progress log (tick 0,
    tick 1, ...) fills a char budget with nothing informative.
    """
    try:
        with open(path, errors="ignore") as fh:
            data = fh.read()
    except OSError:
        return ""
    lines = [ln for ln in data.strip().splitlines() if ln.strip()][-TAIL_LINES:]
    out = "\n".join(lines)
    return out[-n:] if len(out) > n else out


def _deduped(session_id: str, job_ids: list[str]) -> bool:
    """True if we already nudged about this exact job set recently."""
    key = "-".join(sorted(job_ids))[:80]
    marker = f"/tmp/claude-bgliveness-{session_id[:12]}-{abs(hash(key)) % 10**8}"
    now = time.time()
    try:
        if os.path.exists(marker) and now - os.path.getmtime(marker) < DEDUPE_SECONDS:
            return True
        with open(marker, "w") as fh:
            fh.write(str(int(now)))
    except OSError:
        pass
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    if data.get("stop_hook_active", False):
        return 0

    session_id = data.get("session_id", "") or os.environ.get("CLAUDE_SESSION_ID", "")
    outputs = _task_outputs(session_id)
    if not outputs:
        return 0  # nothing was backgrounded this session

    text = _final_assistant_text(data.get("transcript_path", ""))
    if not text or not AWAITING.search(text):
        return 0  # not awaiting anything -> not this failure mode

    jobs = [(os.path.basename(p).rsplit(".", 1)[0], p) for p in outputs]

    # Scope BEFORE deciding liveness. A session routinely has several background
    # jobs; if the turn names the one it is awaiting, an unrelated job that
    # happens to still be running must not vouch for it. Getting this backwards
    # made the gate silent on a real dead-job envelope even though every mocked
    # single-job test passed — found only by an unmocked live-fire control.
    named = set(BASH_ID.findall(text))
    scoped = [(j, p) for j, p in jobs if j in named]
    candidates = scoped or jobs

    live, gone = [], []
    for job_id, path in candidates:
        (live if _holders(path) else gone).append((job_id, path))

    if live:
        # Something it is actually awaiting is running. A real wait is legitimate.
        return 0
    if not gone:
        return 0

    relevant = gone
    if _deduped(session_id, [j for j, _ in relevant]):
        return 0

    lines = [
        "[bg-job-liveness] This turn is waiting on background work, and every job "
        "it launched has already exited — `lsof` shows nothing holding its output "
        "open. No completion notification is coming.",
        "",
    ]
    for job_id, path in relevant:
        age = int(time.time() - os.path.getmtime(path))
        tail = _tail(path)
        lines.append(f"  {job_id}: NOT RUNNING (0 holders, last write {age}s ago)")
        lines.append(f"    output: {path}")
        if tail:
            snippet = tail.replace("\n", "\n      ")
            lines.append(f"    tail: {snippet}")
    lines += [
        "",
        "Read those files now and finish the work with what they contain. If the "
        "output is complete, or the job contributed nothing you need, then ENDING "
        "THE TURN IS CORRECT — a dead background job is not a reason to stay in the "
        "turn or to keep polling.",
    ]
    print("\n".join(lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open
