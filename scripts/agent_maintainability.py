#!/usr/bin/env python3
"""Maintainability metrics for conservatively agent-attributed commits.

The goal is not perfect authorship attribution. The goal is a stable, explicit
baseline for "agent-touched changes": commits with enough provenance to support
maintenance comparisons over 7d / 30d windows.

Metrics:
- revert rate
- follow-up fix/revert density on touched files
- substantial rework rate on touched files
- untouched rate (supporting context only)

Usage:
    uv run python3 scripts/agent_maintainability.py
    uv run python3 scripts/agent_maintainability.py --repo meta --repo skills
    uv run python3 scripts/agent_maintainability.py --format json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable


RS = "\x1e"
US = "\x1f"
GS = "\x1d"
FIX_RE = re.compile(r"\b(fix|repair|correct|patch|resolve|handle)\b", re.I)
REVERT_RE = re.compile(r"\b(revert|undo|drop|remove|retire)\b", re.I)
SESSION_ID_RE = re.compile(r"^Session-ID:\s*(.+)$", re.M)
REVERT_TARGET_RE = re.compile(r"This reverts commit ([0-9a-f]{7,40})", re.I)
AGENT_NAME_RE = re.compile(r"\b(claude|codex|anthropic|openai|gpt|gemini)\b", re.I)
AGENT_TRAILER_RE = re.compile(
    r"^(Agent-Authored:\s*true|Co-authored-by: .*?(Claude|Codex|Anthropic|OpenAI|Gemini))",
    re.I | re.M,
)
DEFAULT_REPOS = {
    "meta": Path.home() / "Projects" / "meta",
}


@dataclass
class FileStat:
    path: str
    insertions: int
    deletions: int

    @property
    def churn(self) -> int:
        return self.insertions + self.deletions


@dataclass
class CommitRecord:
    repo: str
    hash: str
    authored_at: datetime
    author: str
    email: str
    subject: str
    body: str
    files: list[FileStat]
    session_id: str | None
    confidence: float
    cohort: str
    signals: list[str]
    reverted_hashes: list[str]

    @property
    def total_churn(self) -> int:
        return sum(item.churn for item in self.files)

    @property
    def paths(self) -> set[str]:
        return {item.path for item in self.files}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", help="Repo name or absolute path (default: meta)")
    parser.add_argument("--days", type=int, default=120, help="Lookback window for source commits")
    parser.add_argument(
        "--windows",
        default="7,30",
        help="Comma-separated maintenance windows in days (default: 7,30)",
    )
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--write", help="Optional output file")
    return parser.parse_args(argv)


def resolve_repos(values: list[str] | None) -> list[tuple[str, Path]]:
    if not values:
        return list(DEFAULT_REPOS.items())
    repos: list[tuple[str, Path]] = []
    for value in values:
        candidate = Path(value).expanduser()
        if candidate.exists():
            repos.append((candidate.name, candidate.resolve()))
            continue
        named = DEFAULT_REPOS.get(value)
        if named is not None:
            repos.append((value, named.resolve()))
            continue
        repos.append((value, (Path.home() / "Projects" / value).resolve()))
    return repos


def parse_dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)


def split_numstats(text: str) -> list[FileStat]:
    stats: list[FileStat] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        add_raw, del_raw, path = parts
        try:
            insertions = 0 if add_raw == "-" else int(add_raw)
            deletions = 0 if del_raw == "-" else int(del_raw)
        except ValueError:
            continue
        stats.append(FileStat(path=path.strip(), insertions=insertions, deletions=deletions))
    return stats


def classify_commit(author: str, email: str, body: str) -> tuple[float, str, list[str]]:
    score = 0.0
    signals: list[str] = []
    session_id = SESSION_ID_RE.search(body)
    if session_id:
        score += 0.70
        signals.append("session-id")
    if AGENT_TRAILER_RE.search(body):
        score += 0.25
        signals.append("agent-trailer")
    if AGENT_NAME_RE.search(author) or AGENT_NAME_RE.search(email):
        score += 0.25
        signals.append("agent-identity")
    body_lower = body.lower()
    if "claude code" in body_lower or "codex" in body_lower:
        score += 0.10
        signals.append("agent-text")
    score = min(score, 1.0)
    if score >= 0.70:
        cohort = "agent_high"
    elif score >= 0.35:
        cohort = "mixed"
    else:
        cohort = "other"
    return score, cohort, signals


def load_git_history(repo_name: str, repo_path: Path, days: int) -> list[CommitRecord]:
    fmt = f"{RS}%H{US}%aI{US}%an{US}%ae{US}%s{US}%B{GS}"
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "log",
            f"--since={days} days ago",
            "--date=iso-strict",
            "--format=" + fmt,
            "--numstat",
            "--no-renames",
            "--reverse",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git log failed for {repo_path}")

    commits: list[CommitRecord] = []
    for record in result.stdout.split(RS):
        record = record.lstrip("\n")
        if not record.strip():
            continue
        meta_text, _, numstat_text = record.partition(GS)
        parts = meta_text.split(US, 5)
        if len(parts) != 6:
            continue
        commit_hash, authored_at, author, email, subject, body = parts
        body = body.rstrip()
        session_match = SESSION_ID_RE.search(body)
        confidence, cohort, signals = classify_commit(author, email, body)
        commits.append(
            CommitRecord(
                repo=repo_name,
                hash=commit_hash,
                authored_at=parse_dt(authored_at),
                author=author,
                email=email,
                subject=subject.strip(),
                body=body,
                files=split_numstats(numstat_text),
                session_id=session_match.group(1).strip() if session_match else None,
                confidence=confidence,
                cohort=cohort,
                signals=signals,
                reverted_hashes=REVERT_TARGET_RE.findall(body),
            )
        )
    return commits


def summarize_repo(commits: list[CommitRecord], windows: list[int]) -> dict:
    commits = [commit for commit in commits if commit.files]
    if not commits:
        return {"summary": [], "top_followup": []}
    path_index: dict[str, list[int]] = {}
    for idx, commit in enumerate(commits):
        for path in commit.paths:
            path_index.setdefault(path, []).append(idx)
    revert_index: dict[str, list[CommitRecord]] = {}
    for commit in commits:
        for target in commit.reverted_hashes:
            revert_index.setdefault(target, []).append(commit)

    now = datetime.now(UTC)
    cohorts = ("agent_high", "mixed", "other")
    summary_rows: list[dict] = []
    followup_rows: list[dict] = []

    for cohort in cohorts:
        cohort_commits = [commit for commit in commits if commit.cohort == cohort]
        avg_confidence = (
            sum(commit.confidence for commit in cohort_commits) / len(cohort_commits)
            if cohort_commits
            else 0.0
        )
        for window in windows:
            eligible = [
                (idx, commit)
                for idx, commit in enumerate(commits)
                if commit.cohort == cohort and commit.authored_at <= now - timedelta(days=window)
            ]
            reverted = 0
            fix_followup = 0
            substantial_rework = 0
            untouched = 0
            for idx, commit in eligible:
                later_commits = overlapping_later_commits(commits, path_index, idx, window)
                if not later_commits:
                    untouched += 1
                if commit.hash in revert_index and any(
                    (reverter.authored_at - commit.authored_at).days <= window
                    and reverter.authored_at > commit.authored_at
                    for reverter in revert_index[commit.hash]
                ):
                    reverted += 1
                if any(is_fix_like(other.subject) for other in later_commits):
                    fix_followup += 1
                rework_churn = overlap_churn(commit, later_commits)
                threshold = max(25, math_floor_half(commit.total_churn))
                if rework_churn >= threshold:
                    substantial_rework += 1
                followup_rows.append(
                    {
                        "repo": commit.repo,
                        "hash": commit.hash[:12],
                        "cohort": cohort,
                        "window_days": window,
                        "confidence": round(commit.confidence, 2),
                        "followup_commits": len(later_commits),
                        "followup_fix_like": sum(1 for other in later_commits if is_fix_like(other.subject)),
                        "rework_churn": rework_churn,
                        "original_churn": commit.total_churn,
                        "subject": commit.subject,
                    }
                )
            total = len(eligible)
            summary_rows.append(
                {
                    "cohort": cohort,
                    "window_days": window,
                    "eligible_commits": total,
                    "avg_confidence": round(avg_confidence, 2),
                    "revert_rate": ratio(reverted, total),
                    "followup_fix_rate": ratio(fix_followup, total),
                    "substantial_rework_rate": ratio(substantial_rework, total),
                    "untouched_rate": ratio(untouched, total),
                }
            )

    top_followup = sorted(
        followup_rows,
        key=lambda row: (row["followup_fix_like"], row["rework_churn"], row["followup_commits"]),
        reverse=True,
    )[:10]
    return {"summary": summary_rows, "top_followup": top_followup}


def overlapping_later_commits(
    commits: list[CommitRecord],
    path_index: dict[str, list[int]],
    idx: int,
    window_days: int,
) -> list[CommitRecord]:
    commit = commits[idx]
    cutoff = commit.authored_at + timedelta(days=window_days)
    later_indices: set[int] = set()
    for path in commit.paths:
        for later_idx in path_index.get(path, []):
            if later_idx <= idx:
                continue
            later_commit = commits[later_idx]
            if later_commit.authored_at > cutoff:
                break
            later_indices.add(later_idx)
    return [commits[i] for i in sorted(later_indices)]


def overlap_churn(commit: CommitRecord, later_commits: Iterable[CommitRecord]) -> int:
    target_paths = commit.paths
    total = 0
    for later_commit in later_commits:
        for file_stat in later_commit.files:
            if file_stat.path in target_paths:
                total += file_stat.churn
    return total


def ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(num / den, 3)


def is_fix_like(subject: str) -> bool:
    return bool(FIX_RE.search(subject) or REVERT_RE.search(subject))


def math_floor_half(value: int) -> int:
    return max(1, value // 2)


def build_report(repos: list[tuple[str, Path]], days: int, windows: list[int]) -> dict:
    repo_reports: list[dict] = []
    for repo_name, repo_path in repos:
        commits = load_git_history(repo_name, repo_path, days)
        stats = summarize_repo(commits, windows)
        repo_reports.append(
            {
                "repo": repo_name,
                "path": str(repo_path),
                "commit_count": len(commits),
                "summary": stats["summary"],
                "top_followup": stats["top_followup"],
            }
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lookback_days": days,
        "windows": windows,
        "repos": repo_reports,
    }


def format_table(report: dict) -> str:
    lines = [
        "Agent Maintainability Report",
        f"Generated: {report['generated_at']}",
        f"Lookback: {report['lookback_days']} days",
        "",
    ]
    for repo in report["repos"]:
        lines.append(f"Repo: {repo['repo']} ({repo['commit_count']} commits)")
        for row in repo["summary"]:
            lines.append(
                "  "
                f"{row['cohort']:<10} "
                f"{row['window_days']:>2}d "
                f"n={row['eligible_commits']:<3} "
                f"avg_conf={row['avg_confidence']:<4} "
                f"revert={fmt_pct(row['revert_rate']):<6} "
                f"fix={fmt_pct(row['followup_fix_rate']):<6} "
                f"rework={fmt_pct(row['substantial_rework_rate']):<6} "
                f"untouched={fmt_pct(row['untouched_rate']):<6}"
            )
        if repo["top_followup"]:
            lines.append("  Top follow-up pressure")
            for item in repo["top_followup"][:5]:
                lines.append(
                    "    "
                    f"{item['cohort']:<10} {item['window_days']:>2}d "
                    f"{item['hash']} fixes={item['followup_fix_like']} "
                    f"rework={item['rework_churn']}/{item['original_churn']} "
                    f"{item['subject'][:70]}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    windows = [int(part.strip()) for part in args.windows.split(",") if part.strip()]
    report = build_report(resolve_repos(args.repo), args.days, windows)
    output = json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else format_table(report)
    if args.write:
        target = Path(args.write)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
    print(output, end="" if output.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
