#!/usr/bin/env python3
"""questions_view.py — the focused "Questions for you" VIEW (a VIEW, not a STORE).

ADR:  decisions/2026-06-16-agent-question-convergence.md  (accepted; 0 reversals)
Plan: .claude/plans/992ed156-agent-question-convergence.md

Aggregates the question-class items the human must answer — pending decisions
(`decisions-pending/`) and tool/hook steward proposals (`~/.claude/steward-proposals/`)
— into ONE focused section, separate from loop-funnel counts. It only READS + filters +
renders; it adds NO store (reversible by deletion — the spine of the ADR). The stores
keep their native markdown; the Question dataclass is just the VIEW's lingua franca.

Two lanes:
  - standalone:  `just questions`        → prints the section (inspectable/debuggable unit)
  - surfaced:    act_drain.py imports collect_questions()+render_section() → the digest

Robustness (the HOWs the cross-model critique confirmed):
  - parser-robust: a malformed item is SKIPPED + COUNTED, never crashes the section (#13/#16/#34)
  - fail-loud:     a feeder-LEVEL read error emits [DEGRADED: <feeder>] — not silence (#18, P8)
  - atomic write:  --output writes temp + os.replace (#53)
  - envelope:      the Question dataclass renders uniformly across feeders (#15)
  - dedup:         by stable id (source,ref) + cross-feeder prompt-normalized (#20)

The clash-feeder (category: governance, from `~/.claude/clash-shadow.jsonl`) is a THIRD
feeder GATED on shadow precision (ADR 2026-06-16-governance-clash-detection). The seam
exists (include_clash=, reads promoted=true rows ONLY) but is dormant+inert until the gate
opens — nothing is promoted yet, so include_clash=True is a verified no-op today.

Envelope placement: kept HERE, not lifted to scripts/common/, on purpose. The proven-common
bar is ≥2 *real* consumers; today there is 1 (this view) + 1 dormant seam (clash). Lift to
scripts/common/question_envelope.py the moment a 2nd independent consumer needs the contract
(no speculative extraction — .claude/rules/vetoed-decisions.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Module-level feeder paths — constants so tests can monkeypatch them hermetically.
STEWARD_DIR = Path.home() / ".claude" / "steward-proposals"
# A human-gated item unactioned past this many days is STALE: the loop must
# revalidate it (does the incident still recur?) or drop it. Flagged + floated
# to the top of its category — never auto-hidden (append-only; the genomics
# 2026-04-16 proposals had sat invisible for 2 months).
STALE_DAYS = 30
CLASH_LOG = Path.home() / ".claude" / "clash-shadow.jsonl"

# Envelope taxonomy — the four classes a human-gated question can be ABOUT.
CAT_ORDER = ("governance", "goal", "tool", "hook")
CAT_LABEL = {"governance": "Governance", "goal": "Goals", "tool": "Tools", "hook": "Hooks"}
SOURCE_LABEL = {"decisions-pending": "decision", "steward-proposals": "steward",
                "predictions": "prediction", "clash": "clash"}


# ── The envelope (the VIEW's lingua franca) ──────────────────────────────────
@dataclass(frozen=True)
class Question:
    id: str        # stable hash over (source, ref) — idempotent across runs (#20)
    source: str    # decisions-pending | steward-proposals | clash
    category: str  # goal | tool | hook | governance (#15)
    prompt: str    # the actual question to the human
    created: str   # ISO date (YYYY-MM-DD) from filename / field / mtime
    ref: str       # path to the source item (so the human can open it)
    detail: str = ""  # optional one-line context (boundary / recommendation / class)


@dataclass
class ViewResult:
    """Inspectable result: the questions, plus the two distinct notice streams."""
    questions: list[Question] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)  # feeder-LEVEL, LOUD (P8 fail-loud)
    skipped: list[str] = field(default_factory=list)    # item-level, quiet footnote count


# ── small pure helpers (testable in isolation) ───────────────────────────────
def make_id(source: str, ref: str) -> str:
    return hashlib.sha1(f"{source}\0{ref}".encode()).hexdigest()[:12]


def _age_days(created: str) -> int | None:
    """Days since an ISO `created` date; None if unparseable (treated as not-stale)."""
    if not created:
        return None
    try:
        d = datetime.fromisoformat(created[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - d).days


def _norm(text: str) -> str:
    """Whitespace-collapse + lowercase. An idiom (disjoint inputs from surface_gates'
    same-named helper), inlined to avoid pulling yaml into the SessionStart surface path."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _truncate(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def _field_value(text: str, label: str) -> str:
    """Read a `**Label:** value`, joining soft-wrapped continuation lines (hard-wrapped
    markdown splits a sentence across physical lines). Stops at a blank line, the next
    `**field:**`, a heading, or a list item. Case-insensitive."""
    lines = text.splitlines()
    pat = re.compile(rf"\*\*{re.escape(label)}:\*\*\s*(.*)", re.I)
    for i, line in enumerate(lines):
        m = pat.search(line)
        if not m:
            continue
        parts = [m.group(1).strip()]
        for cont in lines[i + 1:]:
            s = cont.strip()
            if not s or s.startswith(("**", "#", "- ", "* ")):
                break
            parts.append(s)
        return " ".join(p for p in parts if p).strip()
    return ""


def _date_from_name(name: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


def _mtime_date(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _short(path: str) -> str:
    return str(path).replace(str(Path.home()), "~")


def _category(*, boundary: str = "", klass: str = "", title: str = "", body: str = "") -> str:
    """Heuristic grouping (NOT a decision — the human always sees prompt + ref and can open
    the file). Specific signals win over the blast-radius boundary."""
    hay = _norm(" ".join([klass, title, body]))
    if any(k in hay for k in ("constitution", "goals.md", "principle", "veto", "generative")):
        return "governance"
    if any(k in hay for k in ("hook", "guard", "gate")):
        return "hook"
    if any(k in hay for k in ("skill", "transport", "mcp", "/improve", "/critique", "/observe", " cli")):
        return "tool"
    if any(k in hay for k in ("optimize for", "telos", "what to optimize", "direction")):
        return "goal"
    if boundary.strip().lower() in ("shared", "irreversible"):
        return "governance"  # human-gated blast radius, no clearer content signal
    return "governance"


# ── per-feeder parsers (raise → item is skipped + counted) ───────────────────
def _parse_decision(path: Path) -> Question:
    text = path.read_text(encoding="utf-8", errors="replace")
    title = _title(text)
    if not title:
        raise ValueError("no title")
    boundary = _field_value(text, "Boundary")
    openq = _field_value(text, "Open question for you")
    rec = _field_value(text, "Recommendation")
    detail_bits = []
    if boundary:
        detail_bits.append(f"boundary={boundary}")
    if rec:
        detail_bits.append(f"rec: {_truncate(rec, 80)}")
    return Question(
        id=make_id("decisions-pending", path.name),
        source="decisions-pending",
        category=_category(boundary=boundary, title=title, body=text),
        prompt=_truncate(openq or title, 200),
        created=_date_from_name(path.name) or _mtime_date(path),
        ref=str(path),
        detail=" · ".join(detail_bits),
    )


def _parse_steward(path: Path) -> Question:
    text = path.read_text(encoding="utf-8", errors="replace")
    title = re.sub(r"^Steward proposal:\s*", "", _title(text), flags=re.I)
    if not title:
        raise ValueError("no title")
    klass = _field_value(text, "Class")
    found = _field_value(text, "Found")
    created = (
        _date_from_name(path.name)
        or (found[:10] if re.match(r"\d{4}-\d{2}-\d{2}", found) else "")
        or _mtime_date(path)
    )
    return Question(
        id=make_id("steward-proposals", path.name),
        source="steward-proposals",
        category=_category(klass=klass, title=title, body=text),
        prompt=_truncate(title, 200),
        created=created,
        ref=str(path),
        detail=f"class={klass}" if klass else "",
    )


# ── collection (parser-robust + fail-loud) ───────────────────────────────────
def _list_md(d: Path) -> list[Path]:
    """Indirection so the feeder-level DEGRADED path is unit-testable (monkeypatch to raise)."""
    return sorted(d.glob("*.md"))


def _collect_dir(d: Path, parser, *, skip: set[str], feeder: str, result: ViewResult) -> None:
    if not d.exists():
        return  # an absent feeder = nothing pending, NOT an error (stay silent)
    try:
        files = _list_md(d)
    except OSError as e:  # feeder-LEVEL failure → fail loud (P8), do not pretend green
        result.degraded.append(f"[DEGRADED: {feeder} unreadable — {type(e).__name__}]")
        return
    for f in files:
        if f.name in skip or not f.is_file():
            continue
        try:
            result.questions.append(parser(f))
        except Exception as e:  # one bad ITEM → skip + count, never crash the section
            result.skipped.append(f"{feeder}/{f.name} ({type(e).__name__})")


def _collect_predictions(result: ViewResult) -> None:
    """DUE pre-registered predictions (predictions.py) — each is a verdict the human owes
    (confirmed/refuted/partial). Imported, NOT re-derived: predictions.due_predictions()
    owns the DUE rule (single-source). The surfacing moved here from drift-sentinel so all
    human-gated verdicts converge in this one VIEW."""
    try:
        import predictions  # scripts/ is on path (conftest / uv run / act_drain insert)
        due = predictions.due_predictions()
    except Exception as e:  # feeder-LEVEL failure → fail loud (P8)
        result.degraded.append(f"[DEGRADED: predictions unreadable — {type(e).__name__}]")
        return
    for p in due:
        pid = p.get("id", "")
        if not pid:
            continue
        change = p.get("change") or _truncate(p.get("prediction", ""), 80) or pid
        result.questions.append(Question(
            id=make_id("predictions", pid),
            source="predictions",
            category="governance",
            prompt=_truncate(f"Resolve prediction: {change} — confirmed or refuted?", 200),
            created=p.get("check_date", ""),
            ref=f"predictions.jsonl#{pid}",
            detail=_truncate(f"predict: {p.get('prediction', '')}", 130),
        ))


def _collect_clash(result: ViewResult) -> None:
    """GATED feeder — promoted clash-shadow rows become governance questions. Dormant:
    reads ONLY rows with promoted=true, and nothing is promoted until `just clash-detect
    --summary` shows precision holds (ADR 2026-06-16-governance-clash-detection). Inert today."""
    if not CLASH_LOG.exists():
        return
    try:
        lines = CLASH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        result.degraded.append(f"[DEGRADED: clash-shadow unreadable — {type(e).__name__}]")
        return
    for ln in lines:
        try:
            row = json.loads(ln)
        except (json.JSONDecodeError, ValueError):
            continue
        if not row.get("promoted"):
            continue  # THE GATE — only human-promoted clashes surface as questions
        item = row.get("item") or row.get("clash_with") or "a governance principle"
        ts = str(row.get("ts", ""))
        result.questions.append(Question(
            id=make_id("clash", ts + str(row.get("message", ""))[:40]),
            source="clash",
            category="governance",
            prompt=_truncate(f"Your request clashes with: {item} — override (retire it) or reconsider?", 200),
            created=ts[:10],
            ref=_short(str(CLASH_LOG)),
            detail=f"msg: {_truncate(str(row.get('message', '')), 90)}",
        ))


def _dedup(questions: list[Question]) -> list[Question]:
    """Dedup by stable id, then by normalized prompt across feeders. More-structured
    sources win (decisions-pending > steward > clash)."""
    rank = {"decisions-pending": 0, "steward-proposals": 1, "predictions": 2, "clash": 3}
    seen_id: set[str] = set()
    seen_prompt: set[str] = set()
    out: list[Question] = []
    for q in sorted(questions, key=lambda x: rank.get(x.source, 9)):
        if q.id in seen_id:
            continue
        pk = _norm(q.prompt)
        if pk and pk in seen_prompt:
            continue
        seen_id.add(q.id)
        if pk:
            seen_prompt.add(pk)
        out.append(q)
    return out


def collect_questions(repo: str | Path = REPO, *, include_clash: bool = False) -> ViewResult:
    result = ViewResult()
    _collect_dir(
        Path(repo) / "decisions-pending", _parse_decision,
        skip={"README.md"}, feeder="decisions-pending", result=result,
    )
    _collect_dir(
        STEWARD_DIR, _parse_steward,
        skip=set(), feeder="steward-proposals", result=result,
    )
    _collect_predictions(result)
    if include_clash:
        _collect_clash(result)
    result.questions = _dedup(result.questions)
    return result


# ── rendering ────────────────────────────────────────────────────────────────
def render_section(result: ViewResult) -> str | None:
    """The focused 'Questions for you' markdown, or None when there is nothing to show."""
    if not result.questions and not result.degraded:
        return None
    lines = [
        "## Questions for you",
        "_Human-gated items aggregated from pending decisions + steward proposals "
        "(a VIEW, not a store — ADR 2026-06-16-agent-question-convergence)._",
        "",
    ]
    for d in result.degraded:  # LOUD first — a dead feeder must not read as "all clear"
        lines.append(f"> ⚠ {d}")
    if result.degraded:
        lines.append("")

    by_cat: dict[str, list[Question]] = {}
    for q in result.questions:
        by_cat.setdefault(q.category, []).append(q)
    for cat in list(CAT_ORDER) + [c for c in by_cat if c not in CAT_ORDER]:
        items = by_cat.get(cat)
        if not items:
            continue
        lines.append(f"### {CAT_LABEL.get(cat, cat.title())} ({len(items)})")
        # STALE items float to the top of their category (revalidate-or-drop),
        # then most-recent first. Flagged, never hidden.
        def _sort_key(x: Question) -> tuple[bool, str]:
            return ((_age_days(x.created) or -1) > STALE_DAYS, x.created)

        for q in sorted(items, key=_sort_key, reverse=True):
            age = _age_days(q.created)
            src = SOURCE_LABEL.get(q.source, q.source)
            stale = f"⚠ STALE {age}d — revalidate or drop · " if (age is not None and age > STALE_DAYS) else ""
            lines.append(f"- {stale}**{q.prompt}**")
            sub = f"  ↳ {src} · {q.created or '?'} · `{_short(q.ref)}`"
            if q.detail:
                sub += f" · {q.detail}"
            lines.append(sub)
        lines.append("")
    if result.skipped:
        shown = ", ".join(result.skipped[:5])
        more = f" (+{len(result.skipped) - 5} more)" if len(result.skipped) > 5 else ""
        lines.append(f"_({len(result.skipped)} item(s) skipped — unparseable: {shown}{more})_")
    return "\n".join(lines).rstrip() + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Focused 'Questions for you' VIEW over human-gated stores")
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--json", action="store_true", help="structured form (the machine lane)")
    ap.add_argument("--output", help="write section to file (atomic temp+rename)")
    ap.add_argument("--include-clash", action="store_true",
                    help="GATED: include promoted clash-shadow rows (dormant until shadow precision proven)")
    args = ap.parse_args()

    result = collect_questions(args.repo, include_clash=args.include_clash)
    if args.json:
        print(json.dumps({
            "questions": [asdict(q) for q in result.questions],
            "degraded": result.degraded,
            "skipped": result.skipped,
            "count": len(result.questions),
        }, indent=2))
        return 0

    section = render_section(result)
    if not section:
        print("No open questions — all clear.")
        return 0
    if args.output:
        _atomic_write(Path(args.output), section)
        print(f"[questions] wrote {len(result.questions)} question(s) → {args.output}")
    else:
        sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
