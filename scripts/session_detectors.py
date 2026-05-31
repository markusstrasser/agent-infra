"""Deterministic session-quality detectors (pure, importable, testable).

Called by session-features.py. Regex banks live in _detector_patterns.py.

Design constraints baked in from the cross-model critique (2026-05-31,
.model-review/2026-05-31-integration-plans-cf3a77/):
  - context_pressure REQUIRES a high-utilization gate. Output decline / wrap-up
    language ALONE is causally non-specific (healthy sessions explore long then
    execute short), so without high utilization we emit only `tail_compression`
    as a raw observation — we do not claim "context pressure".
  - premature_completion is EVIDENCE-ONLY (regex can't know task scope; a final
    "done + optional next steps" is benign). numeric ratios ("7/10 files") are
    evidence-only and never sufficient alone.
  - Unknown model => `missing_prerequisites`, never a guessed utilization.

ALL outputs are advisory features. They are emitted raw and never reduced to a
composite quality score (the parked scorer was retired 2026-06-01, migration 003).
"""
from __future__ import annotations

import re
import statistics

import _detector_patterns as dp


# Negation cues that flip a completion verb ("didn't complete") from a claim
# into a failure — checked in the clause preceding a claim match (close-review L6).
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no longer|cannot|can'?t|could ?n'?t|did ?n'?t|do ?n'?t|"
    r"does ?n'?t|was ?n'?t|is ?n'?t|are ?n'?t|won'?t|would ?n'?t|"
    r"unable to|fail(?:ed|s|ing)? to|without)\b",
    re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(r"[.!?;\n]")


def _has_unnegated_completion_claim(text: str) -> bool:
    """True if a completion-claim pattern matches in a clause NOT preceded by a
    negation cue, so "I didn't complete." is not counted as a claim.
    """
    for rx, _ in dp.COMPLETION_CLAIM_COMPILED:
        for m in rx.finditer(text):
            boundary = 0
            for bm in _CLAUSE_BOUNDARY.finditer(text, 0, m.start()):
                boundary = bm.end()
            if not _NEGATION_RE.search(text[boundary:m.start()]):
                return True
    return False


def detect_context_pressure(assistant_texts, occupancies, model, *, min_turns=6):
    """Context-pressure-induced quality degradation.

    `context_pressure_flag` fires ONLY when high context utilization AND
    tail-compression both hold (mandatory causal gate).
    """
    lengths = [len(t) for t in assistant_texts]
    ctx_limit = dp.resolve_context_limit(model)
    peak_occ = max(occupancies) if occupancies else 0
    model_l = (model or "").lower()

    result = {
        "peak_context_tokens": peak_occ,
        "peak_context_utilization": None,
        "output_decline_ratio": None,
        "wrapup_signal_count": 0,
        "quality_cliff": False,
        "tail_compression_flag": False,
        "context_pressure_flag": False,
        "occupancy_anomaly": None,
        "missing_prerequisites": [],
    }

    # Observed occupancy can exceed the resolved tier when the model string
    # under-specifies it (CC JSONL records "claude-opus-4-8" even for the 1M
    # [1m] variant). Escalate ONLY to a larger tier of the SAME model string —
    # NEVER another model family (cross-family escalation, e.g. gpt-4 -> Claude
    # 200k, is wrong). If nothing fits, the data is anomalous: abstain rather
    # than fabricate a utilization value.
    if ctx_limit is not None and peak_occ > ctx_limit:
        same_model = sorted(
            lim for name, lim in dp.DEFAULT_CONTEXT_LIMITS
            if model_l.startswith(name.lower()) or name.lower().startswith(model_l)
        )
        fits = [t for t in same_model if t > ctx_limit and t >= peak_occ]
        if fits:
            ctx_limit = fits[0]
            result["occupancy_anomaly"] = "tier_inferred_from_observation"
        else:
            result["occupancy_anomaly"] = "observed_exceeds_known_context_limit"
            ctx_limit = None

    if ctx_limit is None:
        result["missing_prerequisites"].append(
            result["occupancy_anomaly"] or "unknown_model_ctx_limit"
        )
    elif ctx_limit > 0:
        result["peak_context_utilization"] = round(peak_occ / ctx_limit, 3)

    if len(lengths) < min_turns:
        result["missing_prerequisites"].append("too_few_turns")
        return result

    # --- output_decline: last-third vs first-third mean turn length ---
    # Require >=3 turns per bucket (n>=9): a 2-sample mean (n=6) gives a single
    # outlier 50% leverage, making the ratio unstable (close-review L4).
    third = len(lengths) // 3
    output_decline = False
    if third >= 3:
        first_mean = statistics.mean(lengths[:third])
        last_mean = statistics.mean(lengths[-third:])
        decline_ratio = (last_mean / first_mean) if first_mean else 1.0
        result["output_decline_ratio"] = round(decline_ratio, 3)
        output_decline = decline_ratio < 0.50

    # --- wrap-up language in the last 40% of turns ---
    tail_start = int(len(assistant_texts) * 0.60)
    wrapup_count = 0
    for t in assistant_texts[tail_start:]:
        if any(rx.search(t) for rx, _ in dp.WRAPUP_COMPILED):
            wrapup_count += 1
    result["wrapup_signal_count"] = wrapup_count
    wrapup_signal = wrapup_count > 0

    # --- quality_cliff: any tail-20% turn > 2σ below the session mean ---
    # Require n>=10: by Samuelson's inequality a value can't be strictly >2σ
    # from the mean until n>10, and for small n the tail-20% slice isn't 20%
    # (n=6 -> 33%). Below 10 turns this signal is unreliable (close-review).
    quality_cliff = False
    if len(lengths) >= 10:
        mean_len = statistics.mean(lengths)
        std_len = statistics.pstdev(lengths)
        if std_len > 0:
            tail20 = lengths[int(len(lengths) * 0.80):]
            quality_cliff = any(L < mean_len - 2 * std_len for L in tail20)
    result["quality_cliff"] = quality_cliff

    tail_compression = output_decline or wrapup_signal or quality_cliff
    result["tail_compression_flag"] = tail_compression

    # --- MANDATORY high-utilization gate ---
    util = result["peak_context_utilization"]
    high_util = util is not None and util > 0.85
    result["context_pressure_flag"] = bool(high_util and tail_compression)
    return result


def detect_premature_completion(final_text):
    """Completion claim contradicted by incomplete/blocker/failure markers in
    the SAME final message. EVIDENCE-ONLY (never a score penalty).
    """
    result = {
        "completion_claimed": False,
        "premature_completion_flag": False,
        "false_success_flag": False,
        "completion_evidence": [],
        "numeric_ratio_incomplete": False,
        "suppressed_by": [],
    }
    if not final_text:
        return result

    # Negation-aware: "I didn't complete." must NOT count as a claim, else it
    # manufactures a bogus completion-claim + false-success (close-review L6).
    claimed = _has_unnegated_completion_claim(final_text)
    result["completion_claimed"] = claimed
    if not claimed:
        return result

    # Compute ALL evidence FIRST. honest-partial must not erase explicit-failure
    # facts (close-review L7) — suppression applies only to the final judgment.
    evidence = []
    if any(rx.search(final_text) for rx, _ in dp.INCOMPLETE_COMPILED):
        evidence.append("incomplete_marker")
    if any(rx.search(final_text) for rx, _ in dp.PLANNED_WORK_COMPILED):
        evidence.append("planned_work")
    if any(rx.search(final_text) for rx, _ in dp.BLOCKER_COMPILED):
        evidence.append("blocker")
    explicit_failure = any(rx.search(final_text) for rx, _ in dp.EXPLICIT_FAILURE_COMPILED)
    if explicit_failure:
        evidence.append("explicit_failure")

    # numeric ratio a<b: evidence-only, never sufficient alone ("7/10 files
    # touched" is not incompleteness).
    for rx, _ in dp.NUMERIC_RATIO_COMPILED:
        hit = False
        for m in rx.finditer(final_text):
            try:
                a, b = int(m.group(1)), int(m.group(2))
            except (ValueError, IndexError):
                continue
            if 0 < a < b:
                result["numeric_ratio_incomplete"] = True
                hit = True
                break
        if hit:
            break

    result["completion_evidence"] = evidence
    # An explicit failure alongside a real completion claim is a false-success
    # claim regardless of honest-partial language (evidence is preserved).
    result["false_success_flag"] = explicit_failure

    # Flag requires a STRONG contradiction (TODO/FIXME marker, blocker, or
    # explicit failure). planned_work + numeric ratios are benign-common and
    # stay evidence-only ("done + next steps" is not premature).
    strong = {"incomplete_marker", "blocker", "explicit_failure"}
    flag = bool(strong.intersection(evidence))
    # honest-partial suppresses ONLY the premature-completion judgment.
    if flag and any(rx.search(final_text) for rx, _ in dp.HONEST_PARTIAL_COMPILED):
        result["suppressed_by"] = ["honest_partial"]
        flag = False
    result["premature_completion_flag"] = flag
    return result


def result_has_rate_limit(result) -> bool:
    """True if a tool-result's text mentions a 429 / rate-limit."""
    if not isinstance(result, dict):
        return bool(dp.RATE_LIMIT_RE.search(str(result)[:2000]))
    parts = []
    for key in ("stderr", "stdout", "error"):
        v = result.get(key)
        if isinstance(v, str):
            parts.append(v)
    content = result.get("content", "")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for b in content[:3]:
            if isinstance(b, dict):
                parts.append(b.get("text", ""))
    return bool(dp.RATE_LIMIT_RE.search(" ".join(parts)[:2000]))


def count_rate_limit_cascade(tool_results, threshold=3):
    hits = sum(1 for r in tool_results if result_has_rate_limit(r))
    return {"rate_limit_hit_count": hits, "rate_limit_cascade_flag": hits >= threshold}
