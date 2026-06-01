#!/usr/bin/env python3
"""Critique-axis health — report-only quality monitor for the /critique skill.

Reads the audit trail the skill already writes (.model-review/*/findings.json,
coverage.json, verified-disposition.md) across all projects and reports, per
reviewer model: finding volume, severity skew, and — where the verify pass ran —
the confirmed / hallucinated / inconclusive split (verdicts joined to findings
by claim title). Also reports cross-model agreement (the "convergent" bucket the
skill treats as its strongest signal) and flags drift.

This exists because model routing drifts silently: when the Gemini cosigner
flipped 3.1-Pro -> 3.5-flash (2026-05-24) the whole hallucination ranking
inverted, and a 503-fallback was quietly degrading reviews to a 42%-hallucination
model — both invisible until an ad-hoc audit. This makes that audit a 10s check.

Report-only: no scoring gate, no blocking, no model calls. Always exits 0.

Usage:
    uv run python3 scripts/critique_health.py [--days N] [--project NAME]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common.console import con

PROJECTS = Path.home() / "Projects"
VERDICTS = ("CONFIRMED", "CORRECTED", "HALLUCINATED", "INCONCLUSIVE")
_ROW = re.compile(r"^\|\s*\d+\s*\|\s*(" + "|".join(VERDICTS) + r")\s*\|\s*(.+?)\s*\|", re.I)
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
# Hallucination rate above which an axis is "noisy" and worth attention.
NOISY_HALLUC = 0.35
# gemini-3-flash-preview is the cheap-classification slot, NOT a critique cosigner
# (measured ~42% hallucination). It should never appear as a review axis.
NON_COSIGNER = "gemini-3-flash-preview"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _family(model: str) -> str:
    m = model.lower()
    if "gemini" in m and "3.5" in m:
        return "gemini-3.5-flash"
    if "gemini" in m and "3.1-pro" in m:
        return "gemini-3.1-pro"
    if "gemini" in m and "flash" in m:
        return "gemini-3-flash"
    if "gemini" in m:
        return "gemini-other"
    if "gpt-5.5" in m:
        return "gpt-5.5"
    if "gpt" in m:
        return "gpt-5.4/other"
    return model


def _review_dirs():
    seen = set()
    for pat in ("*/.model-review", "*/*/.model-review"):
        for mr in PROJECTS.glob(pat):
            for d in mr.iterdir():
                if d.is_dir() and d not in seen:
                    seen.add(d)
                    yield d


def _review_date(d: Path) -> datetime:
    m = _DATE.match(d.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return datetime.fromtimestamp(d.stat().st_mtime)


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="Critique-axis health monitor (report-only).")
    ap.add_argument("--days", type=int, default=0, help="Only reviews from the last N days (0 = all time).")
    ap.add_argument("--project", type=str, default=None, help="Limit to one project (directory name under ~/Projects).")
    args = ap.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days) if args.days else None

    reviews = 0
    dates: list[datetime] = []
    findings_total = 0
    reviews_nonzero = 0
    vol = Counter()
    crit_high = Counter()
    conf = defaultdict(list)
    verdicts = defaultdict(Counter)          # family -> Counter(verdict)
    agree = 0
    agree_findings = 0
    noncosigner_recent = Counter()           # family appearances that shouldn't be axes

    for d in _review_dirs():
        if args.project and f"/{args.project}/" not in f"{d}/":
            continue
        if cutoff and _review_date(d) < cutoff:
            continue
        fj = d / "findings.json"
        if not fj.exists():
            continue
        try:
            data = json.loads(fj.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        F = data.get("findings", []) if isinstance(data, dict) else data
        if not isinstance(F, list):
            continue
        reviews += 1
        dates.append(_review_date(d))
        if F:
            reviews_nonzero += 1
        findings_total += len(F)

        title2fam: dict[str, str] = {}
        for f in F:
            if not isinstance(f, dict):
                continue
            fam = _family(str(f.get("source_model", "?")))
            vol[fam] += 1
            if str(f.get("severity", "")).lower() in ("critical", "high"):
                crit_high[fam] += 1
            c = f.get("confidence")
            if isinstance(c, (int, float)):
                conf[fam].append(c)
            if f.get("title"):
                title2fam[_norm(f["title"])] = fam
            if NON_COSIGNER in str(f.get("source_model", "")):
                noncosigner_recent[fam] += 1

        cov_path = d / "coverage.json"
        if cov_path.exists():
            try:
                ex = json.loads(cov_path.read_text()).get("extraction", {})
                if ex.get("findings_after_dedup"):
                    agree += ex.get("cross_model_agreements", 0)
                    agree_findings += ex["findings_after_dedup"]
            except (json.JSONDecodeError, OSError):
                pass

        vd = d / "verified-disposition.md"
        if vd.exists():
            for line in vd.read_text().splitlines():
                m = _ROW.match(line.strip())
                if not m:
                    continue
                fam = title2fam.get(_norm(m.group(2)))
                if fam:
                    verdicts[fam][m.group(1).upper()] += 1

    # ---- report ----
    window = f"last {args.days}d" if args.days else "all time"
    proj = f", project={args.project}" if args.project else ""
    con.header(f"Critique-axis health — {window}{proj}")
    if not reviews:
        con.warn("No model-review runs matched the filter.")
        return 0

    span = f"{min(dates).date()} → {max(dates).date()}" if dates else "—"
    con.kv("Reviews", str(reviews))
    con.kv("Date span", span)
    con.kv("Findings", str(findings_total))
    con.kv("Found ≥1 issue", f"{_pct(reviews_nonzero, reviews)} of reviews")
    con.kv("Convergent", f"{_pct(agree, agree_findings)} of findings flagged by BOTH models")

    con.header("Per-model axis quality")
    rows = []
    for fam, n in vol.most_common():
        v = verdicts[fam]
        vtot = sum(v.values())
        real = v["CONFIRMED"] + v["CORRECTED"]
        cs = conf[fam]
        med = sorted(cs)[len(cs) // 2] if cs else 0.0
        rows.append([
            fam,
            str(n),
            _pct(crit_high[fam], n),
            f"{med:.2f}",
            _pct(real, vtot),
            _pct(v["HALLUCINATED"], vtot),
            _pct(v["INCONCLUSIVE"], vtot),
            str(vtot) if vtot else "—",
        ])
    con.table(
        ["model", "found", "crit+hi", "conf", "real%", "halluc%", "inconc%", "verified-n"],
        rows,
    )
    con.kv("Note", "real%/halluc%/inconc% are over the verified-n subset only", width=6)

    # ---- drift flags ----
    con.header("Flags")
    flagged = False
    for fam, n in vol.most_common():
        v = verdicts[fam]
        vtot = sum(v.values())
        if vtot >= 30:
            h = v["HALLUCINATED"] / vtot
            if h > NOISY_HALLUC:
                con.warn(f"{fam}: {h*100:.0f}% hallucination over {vtot} verified findings — noisy axis.")
                flagged = True
    if noncosigner_recent:
        total_nc = sum(noncosigner_recent.values())
        con.warn(
            f"{NON_COSIGNER} produced {total_nc} findings as a review axis — it is the cheap "
            "classification model, not a cosigner. Check for a 503-fallback or a misrouted deep-axis."
        )
        flagged = True
    if agree_findings and (agree / agree_findings) < 0.02:
        con.warn(
            f"Convergent bucket is thin ({_pct(agree, agree_findings)}). The skill's strongest "
            "trust signal is rarely available — check the dedup threshold (CROSS_MODEL_JACCARD_THRESHOLD)."
        )
        flagged = True
    if not flagged:
        con.ok("No axis-quality drift detected.")

    # ---- one-line verdict ----
    verified_fams = {f: verdicts[f] for f in verdicts if sum(verdicts[f].values()) >= 30}
    if verified_fams:
        best = min(verified_fams, key=lambda f: verdicts[f]["HALLUCINATED"] / sum(verdicts[f].values()))
        bh = verdicts[best]["HALLUCINATED"] / sum(verdicts[best].values())
        con.header("Verdict")
        con.ok(f"Cleanest axis: {best} ({bh*100:.0f}% hallucination). Keep it as the primary cosigner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
