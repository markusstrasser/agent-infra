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

ALL outputs are advisory features. They are deliberately NOT folded into
compute_quality_score until calibrated on a backfill review cycle (the critique's
"no metric mutation before calibration" gate).
"""
from __future__ import annotations

import statistics

import _detector_patterns as dp


def detect_context_pressure(assistant_texts, occupancies, model, *, min_turns=6):
    """Context-pressure-induced quality degradation.

    `context_pressure_flag` fires ONLY when high context utilization AND
    tail-compression both hold (mandatory causal gate).
    """
    lengths = [len(t) for t in assistant_texts]
    ctx_limit = dp.resolve_context_limit(model)
    peak_occ = max(occupancies) if occupancies else 0

    # Model strings under-specify the tier: CC JSONL records "claude-opus-4-8"
    # even when the 1M-context [1m] variant is in use. If observed occupancy
    # exceeds the resolved limit, the DATA proves a larger context — escalate to
    # the smallest known tier that fits (prevents bogus utilization >1.0).
    if ctx_limit is not None and peak_occ > ctx_limit:
        tiers = sorted({lim for _, lim in dp.DEFAULT_CONTEXT_LIMITS})
        bigger = [t for t in tiers if t >= peak_occ]
        ctx_limit = bigger[0] if bigger else peak_occ

    result = {
        "peak_context_tokens": peak_occ,
        "peak_context_utilization": None,
        "output_decline_ratio": None,
        "wrapup_signal_count": 0,
        "quality_cliff": False,
        "tail_compression_flag": False,
        "context_pressure_flag": False,
        "missing_prerequisites": [],
    }

    if ctx_limit is None:
        result["missing_prerequisites"].append("unknown_model_ctx_limit")
    elif ctx_limit > 0:
        result["peak_context_utilization"] = round(peak_occ / ctx_limit, 3)

    if len(lengths) < min_turns:
        result["missing_prerequisites"].append("too_few_turns")
        return result

    # --- output_decline: last-third vs first-third mean turn length ---
    third = max(1, len(lengths) // 3)
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
    quality_cliff = False
    if len(lengths) >= 5:
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
    }
    if not final_text:
        return result

    claimed = any(rx.search(final_text) for rx, _ in dp.COMPLETION_CLAIM_COMPILED)
    result["completion_claimed"] = claimed
    if not claimed:
        return result

    # honest-partial acknowledgement suppresses the flag (agent isn't misjudging)
    if any(rx.search(final_text) for rx, _ in dp.HONEST_PARTIAL_COMPILED):
        return result

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

    # numeric ratio a<b: evidence-only, never sufficient alone (critique: "7/10
    # files touched" is not incompleteness).
    for rx, _ in dp.NUMERIC_RATIO_COMPILED:
        for m in rx.finditer(final_text):
            try:
                a, b = int(m.group(1)), int(m.group(2))
            except (ValueError, IndexError):
                continue
            if 0 < a < b:
                result["numeric_ratio_incomplete"] = True
                break

    result["completion_evidence"] = evidence
    # Flag requires a STRONG contradiction: an unresolved code marker
    # (TODO/FIXME), an external blocker, or an explicit failure admission.
    # planned_work ("I'll add tests later") and numeric ratios are benign-common
    # and stay evidence-only — critique: "done + next steps" is not premature.
    strong = {"incomplete_marker", "blocker", "explicit_failure"}
    result["premature_completion_flag"] = bool(strong.intersection(evidence))
    result["false_success_flag"] = bool(claimed and explicit_failure)
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
