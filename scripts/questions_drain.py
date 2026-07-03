#!/usr/bin/env python3
"""questions_drain.py — drain the stale human-gated question backlog.

Staleness is a defect to DRAIN, not a flag to display (MIDDLE_MANAGER harvest;
plan .claude/plans/17d2a35c-middle-manager-harvests.md). questions_view.py owns
the stale predicate (is_stale / STALE_DAYS — single source); this verb consumes it.

  bare        list stale items (the work-list)                      llm: none
  --dispatch  one read-only revalidation scout per stale item        llm: required
              (scout_backends; codex default — read-only sandbox may
              roam ALL repos, which cross-repo revalidation needs),
              consolidated memo → docs/audit/<date>-stale-question-drain.md

Each scout answers ONE question: does the problem/opportunity this item names
still exist TODAY in the repos it targets? Verdict STILL-VALID | MOOT | SUPERSEDED
+ evidence. Scouts only RECOMMEND — this script never mutates the stores;
disposition (resolve-moot status edits, drops) stays with the orchestrator model
/ operator per the item's human-gating.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import questions_view  # noqa: E402  (stale predicate + collection — single source)
from scout_backends import ScoutReply, parse_backend_spec, scout_ask  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

SCOUT_PROMPT = """\
You are a revalidation scout. A human-gated proposal/question has sat unactioned \
for {age} days. Your ONLY job: does the problem or opportunity it names still \
exist TODAY, or has it been fixed, implemented, or superseded since {created}?

Item:  {prompt}
File:  {ref}

1. Read the file. Identify the concrete problem/change it proposes and which \
repo(s)/paths under ~/Projects (or ~/.claude) it targets.
2. Check CURRENT state: `git -C <repo> log --oneline --since={created}` on the \
targeted paths; read the current implementation the proposal criticizes or wants.
3. A grep hit/miss only LOCATES — read the source before concluding.

Return ONLY this block (no preamble):
VERDICT: STILL-VALID | MOOT | SUPERSEDED
EVIDENCE: <=3 lines — specific commits/files (path:line or sha) and what they show
RECOMMENDED: keep | resolve-moot | resolve-superseded — one clause why
"""


def _stale_items(repo: Path) -> list[questions_view.Question]:
    result = questions_view.collect_questions(repo)
    return [q for q in result.questions if questions_view.is_stale(q)]


def _dispatch_one(
    q: questions_view.Question, *, backend: str, model: str, effort: str,
    timeout: int, dry_run: bool,
) -> tuple[questions_view.Question, ScoutReply, float]:
    prompt = SCOUT_PROMPT.format(
        age=questions_view._age_days(q.created) or "?",
        created=q.created or "its creation",
        prompt=q.prompt,
        ref=q.ref,
    )
    t0 = time.monotonic()
    reply = scout_ask(
        backend, REPO, prompt,
        timeout=timeout, model=model, effort=effort, dry_run=dry_run,
    )
    return q, reply, time.monotonic() - t0


def _memo(rows: list[tuple[questions_view.Question, ScoutReply, float]], backend: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Stale-question drain — {today}",
        "",
        f"_One revalidation scout per stale item (backend: {backend}; "
        "`just questions-drain --dispatch`). Scouts recommend; disposition is "
        "orchestrator/operator work — see plan 17d2a35c-middle-manager-harvests._",
        "",
    ]
    for q, reply, wall in rows:
        age = questions_view._age_days(q.created)
        lines += [
            f"## {q.prompt}",
            f"- ref: `{q.ref}` · created {q.created or '?'} ({age}d)",
            f"- scout: ok={reply.ok} wall={wall:.0f}s "
            f"tok(in/out/reason)={reply.in_tok}/{reply.out_tok}/{reply.reason_tok}",
            "",
            reply.body.strip() if reply.body.strip() else "(empty scout reply)",
            "",
        ]
    tot_out = sum(r.out_tok for _, r, _ in rows)
    tot_reason = sum(r.reason_tok for _, r, _ in rows)
    tot_wall = sum(w for _, _, w in rows)
    lines += [
        "## Token cost",
        f"- scouts: {len(rows)} · out_tok: {tot_out} · reason_tok: {tot_reason} "
        f"· wall_sum: {tot_wall:.0f}s",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Drain stale human-gated questions (revalidate-or-drop)")
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--dispatch", action="store_true",
                    help="fire one revalidation scout per stale item (llm: required)")
    ap.add_argument("--backend", default="codex",
                    help="scout backend: codex|cursor|claude (codex default — read-only sandbox roams all repos)")
    ap.add_argument("--model", default="")
    ap.add_argument("--effort", default="")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="cap items (0 = all)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"llm: {'required' if args.dispatch else 'none'}", file=sys.stderr)
    parse_backend_spec(args.backend)  # validate early, fail loud

    items = _stale_items(Path(args.repo))
    if args.limit:
        items = items[: args.limit]

    if not args.dispatch:
        if args.json:
            print(json.dumps({"stale": [questions_view.asdict(q) for q in items],
                              "count": len(items)}, indent=2))
        elif not items:
            print("No stale questions — nothing to drain.")
        else:
            print(f"{len(items)} stale item(s) (>{questions_view.STALE_DAYS}d) — "
                  "revalidate with --dispatch:")
            for q in items:
                print(f"  {questions_view._age_days(q.created):>4}d  {q.prompt}")
                print(f"        `{q.ref}`")
        return 0

    if not items:
        print("No stale questions — nothing to dispatch.")
        return 0

    print(f"[drain] dispatching {len(items)} {args.backend} scout(s), "
          f"workers={args.workers} timeout={args.timeout}s", file=sys.stderr)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(
            lambda q: _dispatch_one(
                q, backend=args.backend, model=args.model, effort=args.effort,
                timeout=args.timeout, dry_run=args.dry_run,
            ),
            items,
        ))

    out = REPO / "docs" / "audit" / (
        datetime.now(timezone.utc).strftime("%Y-%m-%d") + "-stale-question-drain.md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_memo(rows, args.backend), encoding="utf-8")

    failed = [q.prompt for q, r, _ in rows if not r.ok]
    if args.json:
        print(json.dumps({
            "memo": str(out),
            "dispatched": len(rows),
            "failed": failed,
            "verdicts": [
                {"prompt": q.prompt, "ok": r.ok,
                 "verdict": next((ln.split(":", 1)[1].strip()
                                  for ln in r.body.splitlines()
                                  if ln.upper().startswith("VERDICT:")), None)}
                for q, r, _ in rows
            ],
        }, indent=2))
    else:
        print(f"[drain] {len(rows)} scout(s) done → {out}")
        if failed:
            print(f"[drain] ✗ {len(failed)} failed/timed out: {', '.join(failed[:3])}")
    return 1 if failed and len(failed) == len(rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
