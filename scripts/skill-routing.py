#!/usr/bin/env python3
"""Analyze skill usage and run deterministic skill-routing fixtures.

Without ``--cases``, reads agentlogs.db. For each Skill tool_call, looks at the
most recent preceding user_message in the same run; if it starts with
/skillname (possibly after preamble/newlines), it's user-slash; otherwise
proactive.

Use to validate skillOverrides decisions: a skill with N>0 proactive
invocations should not be set to user-invocable-only.

With ``--cases``, ranks manifest skill objects against hand-authored routing
fixtures and fails when the expected visible skill/module/lens is not selected
or forbidden legacy entrypoints are present.

Usage:
    uv run python3 scripts/skill-routing.py [--days N] [--skill NAME]
    uv run python3 scripts/skill-routing.py --cases schemas/skill-routing-cases.json [--json] [--explain]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

try:
    from scripts.common.skill_objects import collect_skill_objects, iter_default_roots, load_object_content
except ModuleNotFoundError:  # script execution: python3 scripts/skill-routing.py
    from common.skill_objects import collect_skill_objects, iter_default_roots, load_object_content

DB = Path.home() / ".claude" / "agentlogs.db"

QUERY = """
WITH skill_calls AS (
  SELECT
    e.run_id,
    e.seq AS skill_seq,
    e.ts,
    json_extract(tc.args_json, '$.skill') AS skill
  FROM tool_calls tc
  JOIN events e ON e.tool_call_id = tc.tool_call_id AND e.kind='tool_call'
  WHERE tc.tool_name='Skill' AND e.ts > ?
),
classified AS (
  SELECT
    sc.skill,
    sc.run_id,
    sc.skill_seq,
    (SELECT e2.text FROM events e2
     WHERE e2.run_id = sc.run_id AND e2.seq < sc.skill_seq AND e2.kind = 'user_message'
     ORDER BY e2.seq DESC LIMIT 1) AS user_text
  FROM skill_calls sc
  WHERE sc.skill IS NOT NULL
)
SELECT
  skill,
  CASE
    WHEN user_text LIKE '/' || skill || '%'
      OR user_text LIKE '%' || char(10) || '/' || skill || '%'
    THEN 'user-slash'
    ELSE 'proactive'
  END AS trigger,
  COUNT(*) AS n
FROM classified
GROUP BY skill, trigger
ORDER BY skill, trigger;
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--skill", help="Filter to one skill name")
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--cases", type=Path, help="Run deterministic routing fixture cases")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--explain", action="store_true", help="Show score components for case rankings")
    ap.add_argument("--top", type=int, default=5, help="Number of ranked candidates to show for cases")
    args = ap.parse_args()

    if args.cases:
        return run_cases(args.cases, json_output=args.json, explain=args.explain, limit=args.top)

    cutoff = f"date('now', '-{args.days} days')"
    conn = sqlite3.connect(args.db)
    cur = conn.execute(f"SELECT {cutoff}").fetchone()[0]
    rows = conn.execute(QUERY, (cur,)).fetchall()

    by_skill: dict[str, dict[str, int]] = {}
    for skill, trigger, n in rows:
        if args.skill and skill != args.skill:
            continue
        by_skill.setdefault(skill, {})[trigger] = n

    if not by_skill:
        print("No skill invocations found in window.")
        return 0

    rows_out = []
    for skill, counts in by_skill.items():
        proactive = counts.get("proactive", 0)
        user = counts.get("user-slash", 0)
        total = proactive + user
        rows_out.append((skill, proactive, user, total))
    rows_out.sort(key=lambda r: -r[3])

    print(f"{'skill':<40} {'proactive':>10} {'user-/':>8} {'total':>8}  signal")
    print("-" * 80)
    for skill, p, u, t in rows_out:
        if t == 0:
            sig = ""
        elif p == 0:
            sig = "user-only — candidate user-invocable-only"
        elif u == 0:
            sig = "model-only — keep on"
        else:
            sig = f"mixed ({p}/{u})"
        print(f"{skill:<40} {p:>10} {u:>8} {t:>8}  {sig}")

    return 0


def _terms(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", text.lower())
    terms = {t for t in raw if len(t) >= 3}
    terms.update(f"{a}{b}" for a, b in zip(raw, raw[1:]) if len(a) + len(b) >= 3)
    return terms


def _direct_slash(prompt: str, name: str) -> bool:
    return bool(re.search(rf"(^|\n)\s*/{re.escape(name)}(\s|$)", prompt, re.I))


GENERIC_NAME_TOKENS = {
    "agent",
    "agents",
    "docs",
    "guide",
    "model",
    "research",
    "skill",
    "style",
    "tool",
    "tools",
    "workflow",
}


def _name_atoms(name: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", name.lower())
        if len(token) >= 4 and token not in GENERIC_NAME_TOKENS
    }


def _name_variants(name: str) -> set[str]:
    normalized = name.lower().strip()
    if not normalized:
        return set()
    spaced = re.sub(r"[-_]+", " ", normalized)
    compact = re.sub(r"[-_\s]+", "", normalized)
    return {variant for variant in {normalized, spaced, compact} if len(variant) >= 3}


def _score_details(prompt: str, row: dict) -> dict:
    prompt_terms = _terms(prompt)
    raw_name = str(row.get("name") or "")
    name_terms = _terms(raw_name.replace("-", " "))
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("object_id", "name", "description", "primary_category", "notes")
    )
    row_terms = _terms(haystack)
    score = 0
    reasons: list[dict] = []

    term_hits = sorted(prompt_terms & row_terms)
    if term_hits:
        delta = len(term_hits)
        score += delta
        reasons.append({"reason": "term_overlap", "delta": delta, "terms": term_hits})

    name_term_hits = sorted(prompt_terms & name_terms)
    if name_term_hits:
        delta = 3 * len(name_term_hits)
        score += delta
        reasons.append({"reason": "name_term_overlap", "delta": delta, "terms": name_term_hits})

    name = str(row.get("name") or "").replace("-", " ").lower()
    if name and name in prompt.lower():
        score += 5
        reasons.append({"reason": "spaced_name_match", "delta": 5, "name": name})

    prompt_l = prompt.lower()
    prompt_compact = re.sub(r"[-_\s]+", "", prompt_l)
    exact_name_match = any(
        variant in prompt_l or variant in prompt_compact
        for variant in _name_variants(raw_name)
    )
    distinctive_name_hits = sorted(prompt_terms & _name_atoms(raw_name))
    object_type = row.get("object_type")
    can_boost_name = (
        object_type == "SkillEntrypoint"
        or (object_type is None and row.get("primary_category") not in {"artifact", "lens", "module"})
    )
    if can_boost_name and exact_name_match:
        score += 10
        reasons.append({"reason": "exact_name_variant", "delta": 10, "name": raw_name})
    if can_boost_name and distinctive_name_hits:
        delta = 8 * len(distinctive_name_hits)
        score += delta
        reasons.append({"reason": "distinctive_name_tokens", "delta": delta, "terms": distinctive_name_hits})
        if row.get("primary_category") == "reference":
            score += 6
            reasons.append({"reason": "reference_name_token", "delta": 6})

    if raw_name and _direct_slash(prompt, raw_name):
        score += 20
        reasons.append({"reason": "direct_slash", "delta": 20, "name": raw_name})
    elif row.get("replaced_by"):
        score -= 4
        reasons.append({"reason": "replaced_by_penalty", "delta": -4})

    if row.get("primary_category") in {"module", "lens", "reference", "artifact"} and not _direct_slash(prompt, raw_name):
        score -= 3
        reasons.append({"reason": "internal_object_penalty", "delta": -3})

    object_id_l = str(row.get("object_id", "")).lower()
    if "thread" in prompt_l and row.get("name") == "source-ingest":
        score += 8
        reasons.append({"reason": "source_thread_router", "delta": 8})
    if "thread" in prompt_l and "social-ingest" in object_id_l:
        score += 8
        reasons.append({"reason": "social_thread_module", "delta": 8})
    if any(term in prompt_l for term in ("workup", "work up", "battery")):
        if row.get("name") == "asset-decision":
            score += 8
            reasons.append({"reason": "asset_workup_router", "delta": 8})
        if "workup-battery" in object_id_l:
            score += 8
            reasons.append({"reason": "workup_battery_object", "delta": 8})
    if any(term in prompt_l for term in ("drawdown", "dip", "systemic", "trim")):
        if row.get("name") == "asset-decision":
            score += 8
            reasons.append({"reason": "asset_drawdown_router", "delta": 8})
        if "drawdown-context" in object_id_l:
            score += 8
            reasons.append({"reason": "drawdown_context_object", "delta": 8})
    if any(term in prompt_l for term in ("standalone", "fresh look", "portfolio context")):
        if row.get("name") == "asset-decision":
            score += 8
            reasons.append({"reason": "asset_standalone_router", "delta": 8})
        if "standalone-suppression" in object_id_l:
            score += 8
            reasons.append({"reason": "standalone_suppression_object", "delta": 8})
    if any(term in prompt_l for term in ("dataset", "duckdb", "views", "onboard")):
        if row.get("name") == "dataset":
            score += 8
            reasons.append({"reason": "dataset_router", "delta": 8})
        if "dataset.module.onboarding" in object_id_l:
            score += 8
            reasons.append({"reason": "dataset_onboarding_object", "delta": 8})
    life_science_terms = prompt_terms & {
        "biomedical",
        "biorxiv",
        "clinvar",
        "disease",
        "drug",
        "gene",
        "gnomad",
        "pharmacogenomics",
        "pubmed",
        "variant",
    }
    if life_science_terms:
        if row.get("name") == "life-science-research":
            score += 8
            reasons.append({
                "reason": "life_science_source_router",
                "delta": 8,
                "terms": sorted(life_science_terms),
            })
    if any(term in prompt_l for term in ("hardcoded", "constant", "constants", "coordinate", "coords")):
        if row.get("name") == "bio-verify":
            score += 8
            reasons.append({"reason": "bio_verify_constants_router", "delta": 8})
    if any(term in prompt_l for term in ("running", "status", "live")) and "modal-live-state-truth" in object_id_l:
        score += 8
        reasons.append({"reason": "modal_live_state_truth", "delta": 8})

    return {
        "object_id": row["object_id"],
        "name": raw_name,
        "score": score,
        "reasons": reasons,
    }


def _score(prompt: str, row: dict) -> int:
    return _score_details(prompt, row)["score"]


def _rank_with_scores(prompt: str, rows: list[dict], limit: int = 5) -> list[dict]:
    ranked = sorted(
        (_score_details(prompt, row) for row in rows),
        key=lambda item: item["score"],
        reverse=True,
    )
    return [item for item in ranked[:limit] if item["score"] > 0]


def _rank(prompt: str, rows: list[dict], limit: int = 5) -> list[str]:
    return [item["object_id"] for item in _rank_with_scores(prompt, rows, limit=limit)]


def _case_expectation(case: dict, key: str) -> set[str]:
    if key in case:
        return set(case[key])
    if key == "expected_visible":
        return set(case.get("expected", []))
    return set()


def _format_reasons(item: dict) -> str:
    parts = []
    for reason in item.get("reasons", []):
        label = reason["reason"]
        detail = ""
        if reason.get("terms"):
            detail = ":" + ",".join(reason["terms"])
        elif reason.get("name"):
            detail = ":" + str(reason["name"])
        parts.append(f"{label}{detail}={reason['delta']:+d}")
    return "; ".join(parts)


def run_cases(cases_path: Path, *, json_output: bool = False, explain: bool = False, limit: int = 5) -> int:
    cases = json.loads(cases_path.read_text())
    rows = [obj.to_json() for obj in collect_skill_objects(iter_default_roots(None))]
    by_id = {row["object_id"]: row for row in rows}
    results = []
    for case in cases:
        project = case.get("project")
        project_rows = [row for row in rows if row.get("project") == project]
        visible_rows = [
            row for row in project_rows
            if row.get("object_type") == "SkillEntrypoint"
            and row.get("status", "active") == "active"
        ]
        planned_rows = [
            row for row in project_rows
            if row.get("object_type") != "SkillEntrypoint"
            and row.get("status", "active") in {"active", "planned"}
        ]
        visible_ranked = _rank_with_scores(case["prompt"], visible_rows, limit=limit)
        planned_ranked = _rank_with_scores(case["prompt"], planned_rows, limit=limit)
        visible_top = [item["object_id"] for item in visible_ranked]
        planned_top = [item["object_id"] for item in planned_ranked]
        expected_visible = _case_expectation(case, "expected_visible")
        expected_planned = _case_expectation(case, "expected_planned")
        forbidden_visible = set(case.get("forbidden_visible_absent", []))
        forbidden_planned = set(case.get("forbidden_planned_absent", []))
        visible_passed = bool(visible_top and visible_top[0] in expected_visible) if expected_visible else True
        planned_passed = bool(planned_top and planned_top[0] in expected_planned) if expected_planned else True
        visible_ids = {row["object_id"] for row in visible_rows}
        planned_ids = {row["object_id"] for row in planned_rows}
        forbidden_visible_present = sorted(forbidden_visible & visible_ids)
        forbidden_planned_present = sorted(forbidden_planned & planned_ids)
        expected_planned_content_errors = []
        for object_id in expected_planned:
            row = by_id.get(object_id)
            if row is None:
                expected_planned_content_errors.append(f"{object_id}: missing row")
                continue
            content = load_object_content(row, max_chars=1)
            if not content.get("available"):
                expected_planned_content_errors.append(
                    f"{object_id}: {content.get('error') or 'content unavailable'}"
                )
        forbidden_passed = not forbidden_visible_present and not forbidden_planned_present
        content_passed = not expected_planned_content_errors
        passed = visible_passed and planned_passed and forbidden_passed and content_passed
        result = {
            "id": case["id"],
            "prompt": case["prompt"],
            "expected_visible": sorted(expected_visible),
            "expected_planned": sorted(expected_planned),
            "forbidden_visible_present": forbidden_visible_present,
            "forbidden_planned_present": forbidden_planned_present,
            "expected_planned_content_errors": expected_planned_content_errors,
            "visible_top": visible_top,
            "planned_top": planned_top,
            "visible_passed": visible_passed,
            "planned_passed": planned_passed,
            "forbidden_passed": forbidden_passed,
            "content_passed": content_passed,
            "passed": passed,
        }
        if explain:
            result["visible_explain"] = visible_ranked
            result["planned_explain"] = planned_ranked
        results.append(result)

    if json_output:
        print(json.dumps({"cases": results}, indent=2))
    else:
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            print(
                f"{status} {result['id']}: "
                f"visible={result['visible_top']} expected_visible={result['expected_visible']} "
                f"planned={result['planned_top']} expected_planned={result['expected_planned']} "
                f"forbidden_visible={result['forbidden_visible_present']} "
                f"content_errors={result['expected_planned_content_errors']}"
            )
            if explain:
                for item in result.get("visible_explain", []):
                    print(f"  visible {item['score']:>3} {item['object_id']}: {_format_reasons(item)}")
                for item in result.get("planned_explain", []):
                    print(f"  planned {item['score']:>3} {item['object_id']}: {_format_reasons(item)}")
    return 1 if any(not result["passed"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
