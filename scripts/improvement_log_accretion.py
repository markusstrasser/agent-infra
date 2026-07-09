#!/usr/bin/env python3
"""L1 slice — read-only improvement-log accretion report for act-drain.

Surfaces MODIFY (duplicate open items) and stale `[ ]` rows. Does not mutate the log
(F3/human gate still required before lifecycle edits land).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "improvement-log.md"

HDR = re.compile(r"^### \[(\d{4}-\d{2}-\d{2})\]\s*(.+)$")
STATUS_OPEN = re.compile(r"^(- )?\*\*Status:\*\* \[ \]")
TOKEN = re.compile(r"[a-z0-9]+", re.I)


@dataclass
class OpenItem:
    date: date
    title: str
    line: int


def _parse_open_items(text: str) -> list[OpenItem]:
    lines = text.splitlines()
    items: list[OpenItem] = []
    current: OpenItem | None = None
    for i, line in enumerate(lines, start=1):
        m = HDR.match(line)
        if m:
            current = OpenItem(
                date=datetime.strptime(m.group(1), "%Y-%m-%d").date(),
                title=m.group(2).strip(),
                line=i,
            )
            continue
        if current and STATUS_OPEN.match(line.strip()):
            items.append(current)
            current = None
    return items


def _tokens(title: str) -> set[str]:
    return {t.lower() for t in TOKEN.findall(title) if len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def duplicate_clusters(items: list[OpenItem], threshold: float = 0.55) -> list[list[OpenItem]]:
    clusters: list[list[OpenItem]] = []
    used: set[int] = set()
    tok = [_tokens(it.title) for it in items]
    for i, a in enumerate(items):
        if i in used:
            continue
        cluster = [a]
        used.add(i)
        for j in range(i + 1, len(items)):
            if j in used:
                continue
            if _jaccard(tok[i], tok[j]) >= threshold:
                cluster.append(items[j])
                used.add(j)
        if len(cluster) > 1:
            clusters.append(cluster)
    return clusters


def stale_items(items: list[OpenItem], *, today: date | None = None, days: int = 30) -> list[OpenItem]:
    today = today or date.today()
    return [it for it in items if (today - it.date).days >= days]


def build_report(*, log_path: Path = LOG, today: date | None = None) -> dict:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    open_items = _parse_open_items(text)
    dups = duplicate_clusters(open_items)
    stale = stale_items(open_items, today=today)
    return {
        "open_count": len(open_items),
        "duplicate_clusters": dups,
        "stale": stale,
    }


def render_report(report: dict | None = None) -> str:
    report = report if report is not None else build_report()
    lines = [
        "## L1 accretion (read-only)",
        f"- open `[ ]`: {report['open_count']}",
        f"- duplicate clusters (MODIFY candidates): {len(report['duplicate_clusters'])}",
        f"- stale ≥30d (review for [~]/[-]/[>]): {len(report['stale'])}",
    ]
    for cluster in report["duplicate_clusters"][:5]:
        titles = "; ".join(f"L{c.line} {c.title[:60]}" for c in cluster[:3])
        lines.append(f"  · MODIFY? {titles}")
    for it in report["stale"][:5]:
        lines.append(f"  · stale L{it.line} [{it.date}] {it.title[:70]}")
    return "\n".join(lines)


def main() -> int:
    print(render_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
