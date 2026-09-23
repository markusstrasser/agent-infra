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
+ evidence. Scouts only RECOMMEND; the sweep itself never mutates the stores.

  --apply-verdicts MEMO   apply a sweep's MOOT/SUPERSEDED verdicts (llm: none):
              steward proposals move to steward-proposals/resolved/ with the
              verdict + evidence stamped at the top (append-only: mark, never
              delete); decisions-pending files are unlinked (their git history
              is the record — the standing convention for that dir); anything
              else is listed for a human. STILL-VALID items are never touched.
              The operator gates the sweep, not each item (2026-09-02 queue freeze).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
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
4. Judge the PROBLEM, not the proposed design. If a different mechanism now \
prevents the incident (check the files the incident involved, not only the \
proposal's design), that is SUPERSEDED. STILL-VALID means the incident can \
still happen today.

Return ONLY this block (no preamble):
VERDICT: STILL-VALID | MOOT | SUPERSEDED
EVIDENCE: <=3 lines — specific commits/files (path:line or sha) and what they show
RECOMMENDED: keep | resolve-moot | resolve-superseded — one clause why
"""


def _stale_items(repo: Path) -> list[questions_view.Question]:
    """Stale operator questions plus every DUE prediction verdict (agent work, any age)."""
    result = questions_view.collect_questions(repo)
    return [q for q in result.questions if questions_view.is_stale(q)] + result.agent_verdicts


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


_CLOSING_VERDICTS = frozenset({"MOOT", "SUPERSEDED"})


def parse_memo(text: str) -> list[dict]:
    """Sections of a drain memo → [{prompt, ref, verdict, evidence, recommended}]."""
    items: list[dict] = []
    for chunk in text.split("\n## ")[1:]:
        head, _, body = chunk.partition("\n")
        if head.strip().lower() in {"token cost", "dispositions applied"} or head.startswith("Dispositions applied"):
            continue
        item = {"prompt": head.strip(), "ref": "", "verdict": "", "evidence": "", "recommended": ""}
        for ln in body.splitlines():
            s = ln.strip()
            if s.startswith("- ref: `"):
                item["ref"] = s[len("- ref: `"):].split("`", 1)[0]
            elif s.upper().startswith("VERDICT:"):
                item["verdict"] = s.split(":", 1)[1].strip().upper()
            elif s.upper().startswith("EVIDENCE:") and not item["evidence"]:
                item["evidence"] = s.split(":", 1)[1].strip()
            elif s.upper().startswith("RECOMMENDED:"):
                item["recommended"] = s.split(":", 1)[1].strip()
        items.append(item)
    return items


def apply_verdicts(
    memo_path: Path, *, steward_dir: Path, pending_dir: Path, dry_run: bool = False,
) -> dict[str, list[dict]]:
    """Apply MOOT/SUPERSEDED verdicts from *memo_path*. Returns {resolved, deleted, kept, manual}."""
    out: dict[str, list[dict]] = {"resolved": [], "deleted": [], "kept": [], "manual": []}
    stamp_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resolved_dir = steward_dir / "resolved"
    memo_text = memo_path.read_text(encoding="utf-8")
    backend = re.search(r"\(backend: ([\w-]+)", memo_text)
    scout = f"{backend.group(1)} scout" if backend else "scout"
    for item in parse_memo(memo_text):
        ref = Path(item["ref"]).expanduser() if item["ref"] else None
        if item["verdict"] not in _CLOSING_VERDICTS:
            out["kept"].append(item)
            continue
        if ref is None or not ref.exists():
            out["manual"].append({**item, "why": "ref missing on disk"})
            continue
        if ref.parent == steward_dir:
            if not dry_run:
                resolved_dir.mkdir(exist_ok=True)
                stamp = (
                    f"> **{item['verdict']}** — resolved {stamp_day} by the stale-question drain "
                    f"({scout}; memo `{memo_path}`). Evidence: {item['evidence'] or '(none quoted)'}\n\n"
                )
                (resolved_dir / ref.name).write_text(
                    stamp + ref.read_text(encoding="utf-8"), encoding="utf-8",
                )
                ref.unlink()
            out["resolved"].append(item)
        elif ref.parent == pending_dir:
            if not dry_run:
                ref.unlink()
            out["deleted"].append(item)
        else:
            out["manual"].append({**item, "why": "ref outside the two drainable stores"})
    if not dry_run:
        lines = [f"\n## Dispositions applied {datetime.now(timezone.utc).isoformat(timespec='seconds')}", ""]
        for key in ("resolved", "deleted", "manual", "kept"):
            lines.append(f"- {key}: {len(out[key])}")
        for item in out["resolved"] + out["deleted"]:
            lines.append(f"  - {item['verdict']} → `{item['ref']}`")
        for item in out["manual"]:
            lines.append(f"  - MANUAL ({item['why']}) `{item['ref']}` — {item['prompt'][:80]}")
        with memo_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return out


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
    ap.add_argument("--apply-verdicts", metavar="MEMO",
                    help="apply MOOT/SUPERSEDED verdicts from a drain memo (llm: none; see docstring)")
    args = ap.parse_args()

    if args.apply_verdicts:
        print("llm: none", file=sys.stderr)
        res = apply_verdicts(
            Path(args.apply_verdicts),
            steward_dir=questions_view.STEWARD_DIR,
            pending_dir=Path(args.repo) / "decisions-pending",
            dry_run=args.dry_run,
        )
        verb = "would" if args.dry_run else "did"
        print(f"[apply] {verb} resolve {len(res['resolved'])} steward proposal(s), "
              f"delete {len(res['deleted'])} decisions-pending file(s); "
              f"{len(res['kept'])} kept (STILL-VALID / no verdict), {len(res['manual'])} manual")
        for item in res["manual"]:
            print(f"  MANUAL ({item['why']}): {item['ref']} — {item['prompt'][:80]}")
        for item in res["kept"]:
            print(f"  KEEP {item['verdict'] or '(no verdict)':<11} {item['prompt'][:90]}")
        return 0

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
