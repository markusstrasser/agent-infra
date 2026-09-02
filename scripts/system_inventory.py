#!/usr/bin/env python3
"""Unified system inventory — typed, derived from ground truth.

Machine tags (@system) live on plists and orchestrator-tool-names.md.
Live launchd state comes from launchctl; recipes from justfile + registry.

Usage:
    uv run python3 scripts/system_inventory.py
    uv run python3 scripts/system_inventory.py --json
    uv run python3 scripts/system_inventory.py --drift
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
LAUNCH_AGENTS = HOME / "Library" / "LaunchAgents"
SCRIPT_PATH_RE = re.compile(r"(/[^\s\"']+\.(?:sh|py))")
KINDS_PATH = REPO_ROOT / "config" / "system-kinds.json"
ORCHESTRATOR_REGISTRY = REPO_ROOT / ".claude/rules/orchestrator-tool-names.md"
SYSTEM_TAG = re.compile(
    r"@system\s+((?:[a-z_]+=[a-z0-9_-]+\s*)+)",
    re.IGNORECASE,
)
ORCHESTRATOR_ROW = re.compile(
    r"\| \*\*(none|optional|required)\*\* \| `([^`]+)` \| `?([^|`]+)`? \| `?([^|`]+)`? \|"
)


def _run(cmd: list[str], timeout: int = 8) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def parse_system_tags(text: str) -> dict[str, str]:
    m = SYSTEM_TAG.search(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for part in m.group(1).split():
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def plist_label(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
        for child in root.findall("dict/key"):
            if child.text == "Label" and child.tail is None:
                idx = list(root.find("dict")).index(child)
                val = list(root.find("dict"))[idx + 1]
                if val.tag == "string" and val.text:
                    return val.text
    except (ET.ParseError, OSError, ValueError, IndexError):
        pass
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<key>Label</key>\s*<string>([^<]+)</string>", raw)
    return m.group(1) if m else path.stem


def collect_plist_sources() -> list[Path]:
    """Repo manifest is source of truth; ~/Library/LaunchAgents is runtime only."""
    manifest_dir = REPO_ROOT / "ops" / "launchd"
    if not manifest_dir.exists():
        return []
    return sorted(manifest_dir.glob("com.agent-infra.*.plist"))


def collect_launchd_jobs() -> list[dict]:
    out = _run(["launchctl", "list"])
    if not out:
        return [{"unavailable": True}]
    jobs = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or "com.agent-infra" not in parts[2]:
            continue
        pid, status, label = parts
        short = label.replace("com.agent-infra.", "")
        try:
            exit_code = int(status)
        except ValueError:
            exit_code = None
        jobs.append(
            {
                "name": short,
                "label": label,
                "loaded": True,
                "running": pid not in ("-", "0") and pid.isdigit(),
                "last_exit": exit_code,
                "ok": exit_code == 0,
            }
        )
    return sorted(jobs, key=lambda j: j["name"])


def plist_program_paths(path: Path) -> list[str]:
    """Script/executable paths referenced in a runtime plist's ProgramArguments.

    Returns absolute *.sh/*.py paths only — interpreters (/bin/bash,
    /usr/bin/python3) end in bash/python3 and are correctly skipped, and
    StandardOut/ErrorPath (.out/.err) are never matched. Handles both the
    bare-wrapper form (["/bin/bash", "/…/foo.sh"]) and the compound form
    (["/bin/bash", "-lc", "cd … && uv run python3 /…/foo.py"])."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    # Isolate the ProgramArguments <array> so we don't match log paths.
    m = re.search(r"<key>ProgramArguments</key>\s*<array>(.*?)</array>", text, re.DOTALL)
    block = m.group(1) if m else text
    args = re.findall(r"<string>([^<]*)</string>", block)
    paths: list[str] = []
    for a in args:
        paths.extend(SCRIPT_PATH_RE.findall(a))
    return paths


def plist_schedule_seconds(path: Path) -> int | None:
    """The job's own declared period, in seconds, or None if it is not periodic.

    `StartInterval` is already seconds. `StartCalendarInterval` is a fire-time
    spec, not a period: a bare Hour/Minute means daily (86400); adding Weekday
    or Day makes it weekly/monthly. Read the plist as XML rather than regex —
    a nested dict under StartCalendarInterval is exactly where a regex would
    silently match the wrong key.
    """
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ET.ParseError):
        return None
    top = root.find("dict")
    if top is None:
        return None
    children = list(top)
    for index, node in enumerate(children):
        if node.tag != "key" or index + 1 >= len(children):
            continue
        value = children[index + 1]
        if node.text == "StartInterval" and value.tag == "integer" and value.text:
            try:
                return int(value.text)
            except ValueError:
                return None
        if node.text == "StartCalendarInterval":
            # One dict, or an array of dicts (multiple fire times per period).
            entries = [value] if value.tag == "dict" else list(value)
            keys = {
                key.text for entry in entries if entry.tag == "dict" for key in entry.findall("key")
            }
            if "Month" in keys:
                return 365 * 86400
            if "Day" in keys:
                return 31 * 86400
            if "Weekday" in keys:
                return 7 * 86400
            return 86400
    return None


def _last_run_epoch(path: Path) -> float | None:
    """Newest mtime across the job's stdout/stderr sinks.

    Contract: launchd does NOT touch a sink's mtime on open — only a WRITE does. So
    this dates the job's last run only if the job writes at least one line per run
    to stdout/stderr. A job that logs elsewhere and stays silent on its sinks reads
    as dead (spend-alarm: sinks frozen 2026-08-05, reported "not fired in 26d" on
    2026-09-01 while its own log showed a run every 30 min). Every periodic job owes
    a stdout heartbeat; the false alarm is the detector's, not the job's."""
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ET.ParseError):
        return None
    stamps: list[float] = []
    for node in root.iter("string"):
        text = (node.text or "").strip()
        if text.endswith((".out", ".err")) and text.startswith("/"):
            try:
                stamps.append(Path(text).stat().st_mtime)
            except OSError:
                continue
    return max(stamps) if stamps else None


def collect_stale_jobs(now: float | None = None) -> list[dict]:
    """Periodic jobs that have not FIRED within a tolerant multiple of their period.

    The third and decisive launchd failure mode, and the only one that is
    invisible to both existing checks. `check_launchd_script_integrity` catches
    a deleted script (leading); `check_launchd_spawn_health` catches a job
    launchd cannot exec (leading); a job that fails while running is caught by
    `last_exit`. NONE of them catch a loaded, intact, spawnable job that simply
    never fires — it reports no error because it produces no run at all.

    Measured 2026-08-18: `test-health` (daily) had not fired since 2026-08-04
    and `pulse-tick` (45 min) not since 2026-07-20 — 14 and 29 days of silence,
    while `launchctl list` showed only a stale `last_exit` from their final real
    run. The job whose entire purpose is catching broken tests was itself dead,
    which is why 22 test-collection errors accumulated unnoticed in genomics.

    Tolerance is 2.5x the declared period: a laptop asleep at the fire time
    legitimately delays one run, but not three.
    """
    reference = now if now is not None else datetime.now(timezone.utc).timestamp()
    live = {job["label"]: job for job in collect_launchd_jobs() if job.get("label")}
    stale: list[dict] = []
    for plist in collect_plist_sources():
        label = plist_label(plist)
        if label not in live:
            continue
        period = plist_schedule_seconds(plist)
        if period is None:
            continue  # on-demand / WatchPaths job — silence is not a signal
        last = _last_run_epoch(plist)
        if last is None:
            continue  # no log sink declared; nothing to date the run from
        age = reference - last
        if age <= period * 2.5:
            continue
        stale.append(
            {
                "name": label.replace("com.agent-infra.", ""),
                "label": label,
                "period_s": period,
                "age_s": int(age),
                "missed_runs": int(age // period),
                "last_run": datetime.fromtimestamp(last, timezone.utc).isoformat(),
                "last_exit": live[label].get("last_exit"),
            }
        )
    return sorted(stale, key=lambda job: -job["age_s"])


def collect_orphan_scripts() -> list[dict]:
    """Loaded agent-infra jobs whose ProgramArguments script no longer exists.

    The PRECISE dead-orphan signal — distinct from `loaded_no_manifest_in_repo`
    (manifest hygiene; over-broad — flags working-but-untracked jobs like
    gov-report). A deleted wrapper makes the job fail `exit 127` at every fire,
    silently, until a human happens to read `launchctl list`. This is the
    LEADING check: it fires the moment the script is gone, before the next
    scheduled fire. Caught 4 orphans from the d4c553a consolidation (2026-06-24)
    only after they'd leaked daily failures — this closes that gap."""
    orphans: list[dict] = []
    for job in collect_launchd_jobs():
        if job.get("unavailable") or not job.get("loaded"):
            continue
        plist = LAUNCH_AGENTS / f"{job['label']}.plist"
        if not plist.is_file():
            continue
        referenced = plist_program_paths(plist)
        missing = [p for p in referenced if not Path(p).exists()]
        if missing:
            orphans.append(
                {
                    "name": job["name"],
                    "label": job["label"],
                    "missing_paths": missing,
                    "last_exit": job.get("last_exit"),
                }
            )
    return orphans


def collect_plist_manifest() -> list[dict]:
    rows = []
    for path in collect_plist_sources():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        label = plist_label(path)
        slug = label.replace("com.agent-infra.", "")
        tags = parse_system_tags(text)
        state = tags.get("state", "active")
        rows.append(
            {
                "name": slug,
                "label": label,
                "source": str(
                    path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
                ),
                "layer": tags.get("layer", "watch"),
                "role": tags.get("role", "miner"),
                "llm": tags.get("llm", "none"),
                "state": state,
                "tags": tags,
                "tagged": bool(tags),
            }
        )
    return sorted(rows, key=lambda r: r["name"])


def collect_orchestrator_recipes() -> list[dict]:
    if not ORCHESTRATOR_REGISTRY.exists():
        return []
    rows: list[dict] = []
    seen: set[str] = set()
    for line in ORCHESTRATOR_REGISTRY.read_text().splitlines():
        m = ORCHESTRATOR_ROW.match(line.strip())
        if not m:
            continue
        llm, name, layer, role = m.group(1), m.group(2), m.group(3), m.group(4)
        if name in seen:
            continue
        seen.add(name)
        rows.append(
            {
                "recipe": name,
                "llm": llm,
                "layer": layer or "session",
                "role": role or "orchestrator-tool",
                "kind": "just-recipe",
            }
        )
    return rows


def collect_skills() -> list[dict]:
    skills_dir = HOME / "Projects" / "skills"
    if not skills_dir.exists():
        return []
    rows = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        name = skill_md.parent.name
        layer, role = "session", "skill"
        if m := re.search(r"^name:\s*(\S+)", text, re.M):
            name = m.group(1)
        if name == "orchestrate":
            layer, role = "session", "orchestrator-workflow"
        elif name == "debug":
            layer, role = "session", "scout-workflow"
        rows.append({"skill": name, "layer": layer, "role": role, "kind": "skill"})
    return rows


def merge_launchd(manifest: list[dict], live: list[dict]) -> list[dict]:
    live_by = {j["name"]: j for j in live if j.get("name")}
    man_by = {m["name"]: m for m in manifest}
    names = sorted(set(live_by) | set(man_by))
    rows = []
    for name in names:
        m = man_by.get(name, {})
        l = live_by.get(name, {})
        rows.append(
            {
                "name": name,
                "loaded": l.get("loaded", False),
                "running": l.get("running", False),
                "last_exit": l.get("last_exit"),
                "ok": l.get("ok"),
                "layer": m.get("layer", "watch"),
                "role": m.get("role", "miner"),
                "llm": m.get("llm", "none"),
                "source": m.get("source"),
                "tagged": m.get("tagged", False),
                "state": m.get("state", "active"),
                "kind": "launchd-job",
            }
        )
    return rows


def collect_launchd_inventory() -> list[dict]:
    live = collect_launchd_jobs()
    if live and live[0].get("unavailable"):
        return live
    return merge_launchd(collect_plist_manifest(), live)


def collect_inventory() -> dict:
    kinds = json.loads(KINDS_PATH.read_text()) if KINDS_PATH.exists() else {}
    live = collect_launchd_jobs()
    manifest = collect_plist_manifest()
    launchd = collect_launchd_inventory()
    orchestrator = collect_orchestrator_recipes()
    skills = collect_skills()
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "kinds": kinds,
        "launchd": launchd,
        "orchestrator_recipes": orchestrator,
        "skills": skills,
    }


def collect_drift() -> dict:
    inv = collect_inventory()
    launchd = inv["launchd"]
    untagged_loaded = [j["name"] for j in launchd if j.get("loaded") and not j.get("tagged")]
    manifest_not_loaded = [
        j["name"]
        for j in launchd
        if j.get("source") and not j.get("loaded") and j.get("state", "active") == "active"
    ]
    loaded_no_source = [j["name"] for j in launchd if j.get("loaded") and not j.get("source")]
    llm_jobs = [j["name"] for j in launchd if j.get("llm") == "required" and j.get("loaded")]
    untagged_ops = [
        m["name"]
        for m in collect_plist_manifest()
        if not m.get("tagged") and str(m.get("source", "")).startswith("ops/")
    ]
    orphan_scripts = collect_orphan_scripts()
    return {
        "untagged_loaded": untagged_loaded,
        "untagged_ops_manifest": untagged_ops,
        "manifest_not_loaded": manifest_not_loaded,
        "loaded_no_manifest_in_repo": loaded_no_source,
        "orphan_dead_script": orphan_scripts,
        "llm_launchd_jobs": llm_jobs,
        "has_drift": bool(
            untagged_loaded
            or untagged_ops
            or manifest_not_loaded
            or loaded_no_source
            or orphan_scripts
        ),
    }


def format_watch_summary(launchd: list[dict]) -> str:
    by_layer: dict[str, list[str]] = {}
    for j in launchd:
        if not j.get("loaded"):
            continue
        layer = j.get("layer", "watch")
        llm = j.get("llm", "none")
        tag = j["name"] if llm == "none" else f"{j['name']} (llm:{llm})"
        by_layer.setdefault(layer, []).append(tag)
    parts = []
    for layer in ("watch", "gov", "infra"):
        if layer in by_layer:
            parts.append(f"{layer}: " + " · ".join(by_layer[layer]))
    return "<br/>".join(parts) if parts else "no loaded jobs"


def format_orchestrator_summary(recipes: list[dict]) -> str:
    if not recipes:
        return "/orchestrate — see orchestrator-tool-names.md"
    core = [r["recipe"] for r in recipes if r["role"] != "operator-tool"]
    return (
        "/orchestrate · "
        + " · ".join(core)
        + "<br/>just -f agent-infra/justfile &lt;recipe&gt; &lt;repo&gt;"
    )


def render_architecture_mmd(inv: dict | None = None) -> str:
    inv = inv or collect_inventory()
    template_path = REPO_ROOT / "architecture.template.mmd"
    if not template_path.exists():
        raise FileNotFoundError(template_path)
    text = template_path.read_text()
    launchd = inv["launchd"]
    motor = next((j for j in launchd if j.get("name") == "pulse-tick" and j.get("loaded")), None)
    has_manifest = any(j.get("name") == "pulse-tick" for j in launchd)
    motor_line = (
        f"pulse-tick · rsi-motor · llm:none · {'loaded' if motor else 'NOT LOADED'}"
        if has_manifest
        else "pulse-tick · rsi-motor (manifest)"
    )
    replacements = {
        "{{GENERATED_AT}}": inv["generated_at"],
        "{{WATCH_INVENTORY}}": format_watch_summary(launchd),
        "{{RSI_MOTOR_STATUS}}": motor_line,
        "{{ORCHESTRATOR_SUMMARY}}": format_orchestrator_summary(inv["orchestrator_recipes"]),
        "{{LLM_LAUNCHD}}": ", ".join(inv.get("drift", {}).get("llm_launchd_jobs", []))
        if inv.get("drift")
        else ", ".join(
            j["name"] for j in launchd if j.get("llm") == "required" and j.get("loaded")
        ),
    }
    drift = collect_drift()
    replacements["{{LLM_LAUNCHD}}"] = ", ".join(drift["llm_launchd_jobs"]) or "none loaded"
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _normalize_generated_ts(text: str) -> str:
    return re.sub(r"derived [\d-]+ [\d:]+ UTC", "derived TIMESTAMP", text)


def _normalize_volatile_inventory(text: str) -> str:
    """Strip live launchctl-derived lines so --check ignores transient job churn."""
    text = _normalize_generated_ts(text)
    text = re.sub(r'L\["[^"]*"\]', 'L["STABLE_INVENTORY"]', text, count=1)
    text = re.sub(
        r'LLMJOBS\["LLM launchd: [^"]*"\]',
        'LLMJOBS["LLM launchd: STABLE"]',
        text,
        count=1,
    )
    text = re.sub(
        r"pulse-tick · rsi-motor · llm:none · (?:loaded|NOT LOADED)",
        "pulse-tick · rsi-motor · llm:none · STABLE",
        text,
    )
    return text


def write_architecture_mmd(check: bool = False) -> tuple[Path, bool]:
    out = REPO_ROOT / "architecture.mmd"
    rendered = render_architecture_mmd()
    changed = not out.exists() or _normalize_volatile_inventory(
        out.read_text()
    ) != _normalize_volatile_inventory(rendered)
    if check:
        return out, changed
    out.write_text(rendered)
    return out, changed


def main() -> int:
    args = set(sys.argv[1:])
    if "--drift" in args:
        drift = collect_drift()
        if "--json" in args:
            print(json.dumps(drift, indent=2))
        else:
            for o in drift.get("orphan_dead_script", []):
                exit_note = f" (exit {o['last_exit']})" if o.get("last_exit") else ""
                print(
                    f"✗ ORPHAN dead script{exit_note}: {o['name']} → {', '.join(o['missing_paths'])} "
                    f"(loaded but script deleted — `launchctl bootout` + rm the plist, or restore the script)"
                )
            if drift["loaded_no_manifest_in_repo"]:
                print(f"loaded but no ops plist: {', '.join(drift['loaded_no_manifest_in_repo'])}")
            if drift.get("untagged_ops_manifest"):
                print(
                    f"ops/launchd plists missing @system: {', '.join(drift['untagged_ops_manifest'])}"
                )
            if drift["untagged_loaded"]:
                print(f"loaded plists missing @system tags: {', '.join(drift['untagged_loaded'])}")
            if drift["manifest_not_loaded"]:
                print(f"manifest plists not loaded: {', '.join(drift['manifest_not_loaded'])}")
            if not drift["has_drift"]:
                print("OK: launchd inventory in sync with tagged manifests")
        return 1 if drift["has_drift"] else 0

    if "--render" in args or "--write" in args:
        path, changed = write_architecture_mmd(check="--check" in args)
        if "--check" in args:
            print("stale" if changed else "fresh", str(path))
            return 1 if changed else 0
        print(f"wrote {path}")
        return 0

    inv = collect_inventory()
    inv["drift"] = collect_drift()
    if "--json" in args:
        print(json.dumps(inv, indent=2, default=str))
        return 0

    print(f"System inventory ({inv['generated_at']})")
    print("\nLaunchd (loaded):")
    for j in inv["launchd"]:
        if not j.get("loaded"):
            continue
        st = "ok" if j.get("ok") else f"exit {j.get('last_exit')}"
        print(
            f"  {j['name']:<24} layer={j['layer']:<7} role={j['role']:<12} llm={j['llm']:<8} {st}"
        )
    not_loaded = [j["name"] for j in inv["launchd"] if j.get("source") and not j.get("loaded")]
    if not_loaded:
        print(f"\nManifest not loaded: {', '.join(not_loaded)}")
    print(f"\nOrchestrator recipes: {len(inv['orchestrator_recipes'])}")
    print(f"Skills: {len(inv['skills'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
