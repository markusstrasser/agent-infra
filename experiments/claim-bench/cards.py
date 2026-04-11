"""Cards: independence + adequacy reports derived from inspect_ai EvalLog.

The plan deferred the joint_success metric out of the Scorer surface
because inspect_ai's Scorer API doesn't expose peer scorer outputs
in-band. cards.py is where the joint metric IS computed — by reading the
EvalLog after the run and rolling up per-scorer values into a single
per-sample boolean using `joint_success_per_sample` from process_metrics.

Two cards per run:

- **independence_card**: trustworthiness signals informed by BenchBrowser
  (arXiv:2603.18019) and Platinum Benchmarks (arXiv:2502.03461). Surfaces
  label leakage risk, single-author corpus risk, post-cutoff coverage,
  and domain concentration. Used by post-run readers to decide whether
  to trust the headline numbers.

- **adequacy_card**: statistical adequacy signals — n_cases, n_epochs,
  per-scorer 95% CI from epoch variance, verdict consistency across
  epochs, and a `decision_grade` (exploratory / bounded / promotion_grade)
  based on sample size and consistency.

Both cards attach to a benchmark RUN, not the benchmark itself. Different
runs (different SUTs, different epochs, different corpora) get different
cards.

Run as CLI:
    cd ~/Projects/agent-infra
    uv run python experiments/claim-bench/cards.py
    uv run python experiments/claim-bench/cards.py logs/2026-04-11T....eval --format json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Make sibling imports resolve the same way inspect_ai's task loader does.
THIS_DIR = str(Path(__file__).resolve().parent)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from process_metrics import joint_success_per_sample  # noqa: E402

# Decision grade thresholds. These are deliberately conservative —
# bench-grade conclusions need ≥30 cases per gold class with consistent
# verdicts; promotion-grade needs cross-SUT runs and n≥100. Anything
# smaller is exploratory by definition.
EXPLORATORY_MAX_N = 30
PROMOTION_MIN_N = 100
PROMOTION_MIN_CONSISTENCY = 0.80


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _samples(log: Any) -> list[Any]:
    return list(log.samples or [])


def _samples_by_case(samples: list[Any]) -> dict[str, list[Any]]:
    """Group samples by case id (across epochs)."""
    out: dict[str, list[Any]] = defaultdict(list)
    for s in samples:
        out[s.id].append(s)
    return out


def _safe_value(score: Any) -> float | None:
    """Extract a float Score.value, or None if non-numeric."""
    if score is None:
        return None
    v = getattr(score, "value", None)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _ci95_from_values(values: list[float]) -> tuple[float, float, float]:
    """Return (mean, ci95_low, ci95_high) using normal approximation.

    Wilson intervals would be tighter for binary outcomes, but the scorers
    return continuous [0, 1] values (currency uses 0/0.5/1, calibration uses
    0/0.5/1, atomic_claim uses F1 ∈ [0, 1]) — normal approximation is
    appropriate. Clamps to [0, 1].
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean_v = sum(values) / n
    if n < 2:
        return mean_v, mean_v, mean_v
    variance = sum((x - mean_v) ** 2 for x in values) / (n - 1)
    sd = math.sqrt(variance)
    se = sd / math.sqrt(n)
    ci_half = 1.96 * se
    return mean_v, max(0.0, mean_v - ci_half), min(1.0, mean_v + ci_half)


# ─── Independence card ───────────────────────────────────────────────────────


def derive_independence_card(log: Any) -> dict[str, Any]:
    """Derive trustworthiness signals from an EvalLog.

    Surfaces structural threats to the run's interpretability. Does NOT
    compute scorer means — that's adequacy_card's job. The independence
    card answers "should you trust this benchmark's structure" before
    you read the numbers.
    """
    samples = _samples(log)
    by_case = _samples_by_case(samples)
    n_cases = len(by_case)

    case_meta_by_id: dict[str, dict[str, Any]] = {}
    for sid, runs in by_case.items():
        case_meta_by_id[sid] = (runs[0].metadata or {}) if runs else {}

    threats: list[dict[str, Any]] = []

    # Threat 1: Memorizable cases (label leakage risk via easy difficulty)
    easy_cases = [
        sid
        for sid, m in case_meta_by_id.items()
        if (m.get("difficulty") or "").lower() == "easy"
    ]
    if easy_cases:
        severity = "medium" if len(easy_cases) >= n_cases / 2 else "low"
        threats.append(
            {
                "name": "memorizable_cases",
                "severity": severity,
                "description": (
                    f"{len(easy_cases)}/{n_cases} cases marked difficulty=easy. "
                    "Verdict-match on these may reflect training-data recall "
                    "rather than retrieval competence."
                ),
                "affected_cases": easy_cases,
            }
        )

    # Threat 2: Post-cutoff coverage. Cases citing only pre-2025 evidence
    # cannot distinguish retrieval from memorization for current SUTs.
    post_cutoff_cases: list[str] = []
    for sid, m in case_meta_by_id.items():
        sources = (m.get("gold_sources") or []) + (
            m.get("gold_contradict_sources") or []
        )
        for s in sources:
            if not isinstance(s, dict):
                continue
            d = (s.get("published_date") or "")
            if d.startswith("2025") or d.startswith("2026"):
                post_cutoff_cases.append(sid)
                break

    if n_cases > 0 and len(post_cutoff_cases) < n_cases / 4:
        threats.append(
            {
                "name": "low_post_cutoff_coverage",
                "severity": "medium",
                "description": (
                    f"Only {len(post_cutoff_cases)}/{n_cases} cases cite post-2025 "
                    "evidence. Bench may overestimate retrieval value when SUTs can "
                    "recall most claims from training data."
                ),
            }
        )

    # Threat 3: Single-author corpus (always present in this experimental
    # setup — call it out so headline numbers aren't treated as ranking-grade)
    threats.append(
        {
            "name": "single_author_corpus",
            "severity": "high",
            "description": (
                "All cases authored by one source. Selection bias is unmeasured. "
                "Use independent labeling (ResearchRubrics-style) before treating "
                "headline numbers as ranking-grade across SUTs."
            ),
        }
    )

    # Threat 4: Domain concentration
    domains = Counter(
        (m.get("domain") or "unknown") for m in case_meta_by_id.values()
    )
    if domains and max(domains.values()) > n_cases / 2:
        threats.append(
            {
                "name": "domain_concentration",
                "severity": "low",
                "description": (
                    f"Single domain dominates: {dict(domains.most_common(3))}. "
                    "Cross-domain generalization claims are not supported."
                ),
            }
        )

    return {
        "card_type": "independence",
        "schema_version": 1,
        "eval_id": getattr(log.eval, "run_id", None),
        "task": getattr(log.eval, "task", None),
        "model": getattr(log.eval, "model", None),
        "created": getattr(log.eval, "created", None),
        "n_cases": n_cases,
        "case_difficulty_distribution": dict(
            Counter(
                (m.get("difficulty") or "unspecified")
                for m in case_meta_by_id.values()
            )
        ),
        "case_domain_distribution": dict(domains),
        "post_cutoff_case_count": len(set(post_cutoff_cases)),
        "major_threats": threats,
        "allowed_claims": [
            f"This run produced per-sample evidence on {n_cases} cases.",
            "Headline metrics are descriptive of THIS run only, not promotion-grade.",
            "Cross-SUT comparisons require running the same corpus on each SUT.",
            "Verdict-match means agreed-with-author-labels, not agreed-with-truth.",
        ],
    }


# ─── Adequacy card ───────────────────────────────────────────────────────────


def derive_adequacy_card(log: Any) -> dict[str, Any]:
    """Derive statistical adequacy signals from an EvalLog.

    Computes per-scorer means with 95% CIs, verdict consistency across
    epochs, joint success rate (the headline), and a decision_grade
    (exploratory / bounded / promotion_grade) based on n_cases × epochs
    and consistency.
    """
    samples = _samples(log)
    by_case = _samples_by_case(samples)
    n_cases = len(by_case)
    n_total_runs = len(samples)
    epochs_per_case = max((len(runs) for runs in by_case.values()), default=0)

    # ─── Verdict distribution by gold ───
    gold_dist: Counter[str] = Counter()
    for sid, runs in by_case.items():
        if not runs:
            continue
        first = runs[0]
        gold = None
        if first.target:
            gold = str(first.target).strip()
        elif first.metadata:
            gold = first.metadata.get("gold_verdict")
        if gold:
            gold_dist[str(gold)] += 1

    # ─── Per-scorer means + 95% CIs ───
    scorer_names: set[str] = set()
    for s in samples:
        scores_dict = getattr(s, "scores", None) or {}
        for sn in scores_dict.keys():
            scorer_names.add(sn)

    per_scorer: dict[str, dict[str, Any]] = {}
    for sn in sorted(scorer_names):
        values: list[float] = []
        excluded_not_applicable = 0
        for s in samples:
            scores_dict = getattr(s, "scores", None) or {}
            score_obj = scores_dict.get(sn)
            v = _safe_value(score_obj)
            if v is None:
                continue
            # Bug fix (plan-close F1): atomic_claim_scorer returns value=1.0
            # with answer='not_applicable' for samples lacking gold claims
            # (e.g. not_verifiable cases). inspect_ai's raw mean() includes
            # these in the denominator, inflating the atomic_claim mean.
            # cards.py is the headline path — exclude not_applicable here.
            # Other scorers (currency, calibration) have similar semantics
            # but lower mean-inflation risk; exclude for atomic_claim only
            # to keep the fix narrow and avoid changing currency/calibration
            # semantics.
            if sn == "atomic_claim_scorer" and score_obj is not None:
                meta = score_obj.metadata or {}
                if meta.get("atomic_status") == "not_applicable":
                    excluded_not_applicable += 1
                    continue
            values.append(v)
        if not values:
            continue
        mean_v, ci_lo, ci_hi = _ci95_from_values(values)
        scorer_entry: dict[str, Any] = {
            "n": len(values),
            "mean": round(mean_v, 4),
            "ci95_low": round(ci_lo, 4),
            "ci95_high": round(ci_hi, 4),
            "ci95_width": round(ci_hi - ci_lo, 4),
        }
        if excluded_not_applicable > 0:
            scorer_entry["excluded_not_applicable"] = excluded_not_applicable
        per_scorer[sn] = scorer_entry

    # ─── Consistency per case (across epochs) ───
    consistency_per_case: dict[str, float | None] = {}
    for sid, runs in by_case.items():
        if len(runs) < 2:
            consistency_per_case[sid] = 1.0
            continue
        verdicts: list[str] = []
        for s in runs:
            scores_dict = getattr(s, "scores", None) or {}
            ves = scores_dict.get("verdict_enum_scorer")
            if ves and ves.metadata:
                v = ves.metadata.get("predicted")
                if v:
                    verdicts.append(str(v))
        if not verdicts:
            consistency_per_case[sid] = None
            continue
        most_common_count = Counter(verdicts).most_common(1)[0][1]
        consistency_per_case[sid] = round(most_common_count / len(verdicts), 4)

    consistency_values = [v for v in consistency_per_case.values() if v is not None]
    mean_consistency = (
        round(sum(consistency_values) / len(consistency_values), 4)
        if consistency_values
        else None
    )

    # ─── Joint success rollup (the headline) ───
    joint_passes = 0
    joint_total = 0
    for s in samples:
        scores_dict = getattr(s, "scores", None) or {}
        v_score = scores_dict.get("verdict_enum_scorer")
        g_score = scores_dict.get("groundedness_scorer")
        c_score = scores_dict.get("currency_scorer")
        if v_score is None or g_score is None:
            continue
        v_value = _safe_value(v_score)
        g_value = _safe_value(g_score)
        if v_value is None or g_value is None:
            continue
        joint_total += 1
        c_value = _safe_value(c_score) if c_score else None
        c_label = (c_score.metadata or {}).get("currency_status") if c_score else None
        if joint_success_per_sample(
            verdict_match=v_value,
            groundedness_value=g_value,
            currency_value=c_value,
            currency_label=c_label,
        ):
            joint_passes += 1
    joint_rate = round(joint_passes / joint_total, 4) if joint_total else None

    # ─── Decision grade ───
    if n_cases >= PROMOTION_MIN_N and (mean_consistency or 0) >= PROMOTION_MIN_CONSISTENCY:
        decision_grade = "promotion_grade"
    elif n_cases >= EXPLORATORY_MAX_N:
        decision_grade = "bounded"
    else:
        decision_grade = "exploratory"

    return {
        "card_type": "adequacy",
        "schema_version": 1,
        "eval_id": getattr(log.eval, "run_id", None),
        "task": getattr(log.eval, "task", None),
        "model": getattr(log.eval, "model", None),
        "created": getattr(log.eval, "created", None),
        "n_cases": n_cases,
        "n_total_sample_runs": n_total_runs,
        "epochs_per_case": epochs_per_case,
        "gold_distribution": dict(gold_dist),
        "per_scorer": per_scorer,
        "consistency_per_case": consistency_per_case,
        "mean_consistency": mean_consistency,
        "joint_success": {
            "n_passes": joint_passes,
            "n_total": joint_total,
            "rate": joint_rate,
        },
        "decision_grade": decision_grade,
        "decision_grade_thresholds": {
            "exploratory_max_n": EXPLORATORY_MAX_N,
            "promotion_min_n": PROMOTION_MIN_N,
            "promotion_min_consistency": PROMOTION_MIN_CONSISTENCY,
        },
    }


# ─── Markdown rendering ──────────────────────────────────────────────────────


def render_independence_md(card: dict[str, Any]) -> str:
    lines = []
    lines.append("# Independence Card")
    lines.append("")
    lines.append(f"**Eval ID:** `{card.get('eval_id')}`")
    lines.append(f"**Task:** {card.get('task')}")
    lines.append(f"**Model:** {card.get('model')}")
    lines.append(f"**Created:** {card.get('created')}")
    lines.append("")
    lines.append(f"**Cases:** {card.get('n_cases')}")
    lines.append(f"**Post-cutoff cases:** {card.get('post_cutoff_case_count')}")
    lines.append("")
    lines.append("## Difficulty distribution")
    for k, v in (card.get("case_difficulty_distribution") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Domain distribution")
    for k, v in (card.get("case_domain_distribution") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Major threats")
    for t in card.get("major_threats", []):
        sev = t.get("severity", "?").upper()
        lines.append(f"### [{sev}] {t.get('name')}")
        lines.append(t.get("description", ""))
        if t.get("affected_cases"):
            lines.append(f"Affected: {', '.join(t['affected_cases'])}")
        lines.append("")
    lines.append("## Allowed claims")
    for c in card.get("allowed_claims", []):
        lines.append(f"- {c}")
    return "\n".join(lines)


def render_adequacy_md(card: dict[str, Any]) -> str:
    lines = []
    lines.append("# Adequacy Card")
    lines.append("")
    lines.append(f"**Eval ID:** `{card.get('eval_id')}`")
    lines.append(f"**Task:** {card.get('task')}")
    lines.append(f"**Model:** {card.get('model')}")
    lines.append(
        f"**Decision grade:** **{(card.get('decision_grade') or 'unknown').upper()}**"
    )
    lines.append("")
    lines.append(
        f"**Cases:** {card.get('n_cases')}  |  "
        f"**Epochs/case:** {card.get('epochs_per_case')}  |  "
        f"**Total sample-runs:** {card.get('n_total_sample_runs')}"
    )
    lines.append("")
    lines.append("## Joint success (headline)")
    js = card.get("joint_success") or {}
    lines.append(
        f"**{js.get('n_passes')}/{js.get('n_total')} sample-runs joint-pass "
        f"= {js.get('rate')}**"
    )
    lines.append("")
    lines.append(
        "Joint success = verdict_match AND groundedness ≥ 0.5 AND "
        "(currency_pass OR currency_NA)."
    )
    lines.append("")
    lines.append("## Per-scorer means + 95% CI")
    lines.append("")
    lines.append("| Scorer | n | mean | 95% CI | width |")
    lines.append("|---|---|---|---|---|")
    for sn, ps in (card.get("per_scorer") or {}).items():
        lines.append(
            f"| {sn} | {ps['n']} | {ps['mean']} | "
            f"[{ps['ci95_low']}, {ps['ci95_high']}] | {ps['ci95_width']} |"
        )
    lines.append("")
    lines.append("## Verdict consistency across epochs")
    lines.append(f"**Mean consistency:** {card.get('mean_consistency')}")
    lines.append("")
    for sid, c in (card.get("consistency_per_case") or {}).items():
        lines.append(f"- {sid}: {c}")
    lines.append("")
    lines.append("## Gold distribution")
    for k, v in (card.get("gold_distribution") or {}).items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _latest_eval_log() -> Path | None:
    candidates = sorted(
        Path("logs").glob("*.eval"), key=lambda p: p.stat().st_mtime
    )
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive independence + adequacy cards from an inspect_ai EvalLog"
    )
    parser.add_argument(
        "log_path",
        nargs="?",
        help="Path to .eval log file. If omitted, uses the latest in ./logs/",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--card",
        choices=["independence", "adequacy", "both"],
        default="both",
        help="Which card(s) to emit (default: both)",
    )
    args = parser.parse_args()

    from inspect_ai.log import read_eval_log

    if args.log_path:
        path = Path(args.log_path)
    else:
        path = _latest_eval_log()
        if path is None:
            print("ERROR: no .eval log files found in ./logs/", file=sys.stderr)
            sys.exit(1)

    log = read_eval_log(str(path))

    cards: dict[str, Any] = {}
    if args.card in ("independence", "both"):
        cards["independence"] = derive_independence_card(log)
    if args.card in ("adequacy", "both"):
        cards["adequacy"] = derive_adequacy_card(log)

    if args.format == "json":
        print(json.dumps(cards, indent=2, default=str))
        return

    if "independence" in cards:
        print(render_independence_md(cards["independence"]))
        print()
    if "adequacy" in cards:
        print(render_adequacy_md(cards["adequacy"]))


if __name__ == "__main__":
    main()
