#!/usr/bin/env python3
"""Cross-project memory generalization scanner — the harvest source for project memories.

The per-project Claude memory stores (~/.claude/projects/*/memory/*.md) and the Codex
memory (~/.codex/memories/) accumulate `feedback`/`reference`/`project` lessons that are
learned in ONE project but are often generalizable to a shared rule/skill/tool. The
harvest/observe loop historically never read this surface — a generation-without-consumption
gap (the lessons sit siloed where they were learned).

This script is the DETERMINISTIC pre-filter: it clusters memories by theme and flags
clusters that look generalizable (span ≥2 projects, OR a single-project silo whose theme
maps to an existing shared home like the `modal` skill). It does NOT judge generalizability
or do the factoring — that semantic step stays with the agent in `/improve harvest` Phase 2g,
which dedups each candidate against the shared rules/skills before proposing.

Usage:  uv run python3 scripts/memory_harvest.py [--min-span 2] [--json]
"""
from __future__ import annotations
import argparse, json, re, collections
from pathlib import Path

# theme keyword -> (display, suggested generalization target). Keywords matched on stem+desc.
THEMES = {
    "modal":        ("Modal ops", "skills/modal"),
    "worktree":     ("worktree/subagent hygiene", "global CLAUDE.md <subagent_usage> (check: mostly covered)"),
    "subagent":     ("worktree/subagent hygiene", "global CLAUDE.md <subagent_usage> (check: mostly covered)"),
    "probe":        ("probe-before-commit / scaling extrapolation", "global CLAUDE.md rule #8 (Probe before build)"),
    "extrapolat":   ("probe-before-commit / scaling extrapolation", "global CLAUDE.md rule #8 (Probe before build)"),
    "fabricat":     ("search-tool fabrication", "skills/research references/tool-routing.md"),
    "hallucinat":   ("search-tool fabrication", "skills/research references/tool-routing.md"),
    "self_confirm": ("search-tool fabrication", "skills/research references/tool-routing.md"),
    "perplexity":   ("search-tool fabrication", "skills/research references/tool-routing.md"),
    "exa":          ("search-tool fabrication", "skills/research references/tool-routing.md"),
    "effort":       ("model-effort routing", "skills/model-guide"),
    "routing":      ("model-effort routing", "skills/model-guide"),
    "flash":        ("model-effort routing", "skills/model-guide"),
    "verify":       ("verify-before-claiming (P8)", "global CLAUDE.md <ai_text_policy> / constitution P8"),
    "cache":        ("cache invalidation / stale-output", "domain-local (genomics) — check if pattern generalizes"),
    "budget":       ("compute budget guard", "skills/modal"),
}

def _themes_for(text: str) -> list[str]:
    hay = text.lower()
    return sorted({THEMES[k][0] for k in THEMES if k in hay})


def _scan_codex() -> list[tuple[str, str, str, str]]:
    """Parse ~/.codex/memories/MEMORY.md into (project, type, stem, desc) rows.

    Codex memory has no per-project frontmatter — it's one global MEMORY.md with
    `# Task Group:` blocks (carrying `applies_to: cwd=<path>`), `## Task N: <title>`
    sections, and `### keywords` bullet lists. We attribute each task to the cwd's
    project so its lessons cluster WITH the matching Claude project memories.
    """
    rows: list[tuple[str, str, str, str]] = []
    cx = Path.home() / ".codex/memories/MEMORY.md"
    if not cx.exists():
        return rows
    proj, title, kw, in_kw = "codex", None, [], False

    def flush():
        if title:
            rows.append((proj, "codex-task", title[:80], " ".join(kw)[:200]))

    for line in cx.read_text(errors="replace").splitlines():
        m = re.search(r'cwd=([^\s;,]+)', line)
        if m:
            proj = Path(m.group(1).rstrip("/")).name or "codex"
        if line.startswith("## Task"):
            flush()
            title, kw, in_kw = line.lstrip("# ").strip(), [], False
        elif line.startswith("### keywords"):
            in_kw = True
        elif line.startswith("###"):
            in_kw = False
        elif in_kw and line.strip().startswith("-"):
            kw.append(line.strip().lstrip("- ").strip())
    flush()
    return rows


def scan(min_span: int = 2):
    root = Path.home() / ".claude/projects"
    mems = []  # (project, type, stem, desc, themes)
    for md in root.glob("-Users-alien-Projects-*/memory/*.md"):
        if md.name == "MEMORY.md":
            continue
        proj = md.parent.parent.name.replace("-Users-alien-Projects-", "")
        try:
            txt = md.read_text(errors="replace")
        except OSError:
            continue
        typ = (re.search(r'type:\s*(\w+)', txt) or [None, "?"])[1]
        dm = re.search(r'description:\s*(.+)', txt)
        desc = (dm.group(1).strip() if dm else "")[:160]
        mems.append((proj, typ, md.stem, desc, _themes_for(md.stem + " " + desc)))
    # Codex memory store (different structure; same theme-clustering).
    for proj, typ, stem, desc in _scan_codex():
        mems.append((proj, typ, stem, desc, _themes_for(stem + " " + desc)))
    # cluster by theme
    clusters = collections.defaultdict(list)
    target = {disp: tgt for disp, tgt in THEMES.values()}
    for proj, typ, stem, desc, themes in mems:
        for th in themes:
            clusters[th].append((proj, typ, stem, desc))
    # rank: candidates = theme spanning >=min_span projects OR single-project silo with >=5 members
    out = []
    for th, items in clusters.items():
        projects = sorted({p for p, *_ in items})
        flag = len(projects) >= min_span or len(items) >= 5
        out.append({
            "theme": th, "target": target.get(th, "?"), "count": len(items),
            "projects": projects, "candidate": flag,
            "samples": [f"[{p}] {s}" for p, _, s, _ in items[:6]],
        })
    out.sort(key=lambda c: (c["candidate"], len(c["projects"]), c["count"]), reverse=True)
    return {"total_memories": len(mems), "clusters": out}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-span", type=int, default=2, help="min projects for a cross-project candidate")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = scan(a.min_span)
    if a.json:
        print(json.dumps(r, indent=1)); return
    print(f"# Memory generalization scan — {r['total_memories']} memories\n")
    print("Deterministic pre-filter. CANDIDATE = generalize-worthy (spans ≥%d projects or ≥5-silo)." % a.min_span)
    print("The semantic factoring (dedup vs shared rules, propose) is the agent's job in harvest Phase 2g.\n")
    for c in r["clusters"]:
        mark = "★ CANDIDATE" if c["candidate"] else "  watch"
        print(f"{mark} · {c['theme']} ({c['count']} mems, {len(c['projects'])} projs: {','.join(c['projects'])})")
        print(f"        → factor toward: {c['target']}")
        print(f"        e.g. {'; '.join(c['samples'][:4])}")

if __name__ == "__main__":
    main()
