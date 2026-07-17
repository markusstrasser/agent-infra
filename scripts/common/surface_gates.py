"""Composable surface primitives — failure envelopes, skill budgets, governance dedup.

Convention anchor: decisions/2026-06-08-failure-envelope-convention.md
Research: research/2026-06-16-session-surface-errors-verified.md

No cross-repo package — agent-infra local only. Other repos copy the 3-line
envelope format inline (per ADR), not import this module.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECTS_ROOT = Path.home() / "Projects"
CODEX_SKILLS_BUDGET_CHARS = 8000
SKIP_SKILL_DIR_NAMES = frozenset(
    {"hooks", "archive", "_archive", "__pycache__", "node_modules", ".git", ".system"}
)

GOVERNANCE_GLOBS = (
    "CLAUDE.md",
    "AGENTS.md",
    "GOALS.md",
    "improvement-log.md",
    ".claude/rules/**/*.md",
    "decisions/**/*.md",
    ".claude/skills/**/SKILL.md",
    "skills/**/SKILL.md",
)


@dataclass(frozen=True)
class FailureEnvelope:
    """Greppable block contract for agent-facing gates."""

    check: str
    reason: str
    fix: str
    detail: str = ""

    def format(self) -> str:
        lines = [f"[{self.check}] BLOCKED — {self.reason}"]
        if self.detail:
            lines.append(self.detail)
        lines.append(f"fix: {self.fix}")
        return "\n".join(lines)

    def to_payload(self, **extra: Any) -> dict[str, Any]:
        out: dict[str, Any] = {
            "error": True,
            "envelope": self.format(),
            "check": self.check,
            "reason": self.reason,
            "fix": self.fix,
            "recoverable": True,
        }
        if self.detail:
            out["detail"] = self.detail
        out.update(extra)
        return out


@dataclass
class SkillMount:
    label: str
    path: str
    skill_count: int
    description_chars: int
    # description_chars minus disable-model-invocation skills — the ambient
    # model-facing index. Raw sum stays the conservative Codex number
    # (Codex honoring of the flag is unverified; fa0ce09).
    effective_description_chars: int = 0
    skills: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SkillsBudgetReport:
    codex_budget_chars: int
    mounts: list[SkillMount]
    violations: list[str]

    @property
    def over_budget(self) -> bool:
        return bool(self.violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "codex_budget_chars": self.codex_budget_chars,
            "over_budget": self.over_budget,
            "violations": self.violations,
            "mounts": [asdict(m) for m in self.mounts],
        }


def parse_skill_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str]:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm if isinstance(fm, dict) else {}, text[end + 5 :]


def skill_description_line(skill_md: Path) -> str:
    fm, _ = parse_skill_frontmatter(skill_md)
    desc = fm.get("description")
    if isinstance(desc, str) and desc.strip():
        return f"description: {desc.strip()}"
    for line in skill_md.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("description:"):
            return line
    return ""


def iter_skill_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP_SKILL_DIR_NAMES or child.name.startswith("."):
            continue
        skill_md = child / "SKILL.md"
        if skill_md.is_file() or skill_md.is_symlink():
            out.append(child)
    return out


def measure_skill_mount(label: str, root: Path) -> SkillMount:
    skills: list[dict[str, Any]] = []
    desc_chars = 0
    effective_chars = 0
    for skill_dir in iter_skill_dirs(root):
        skill_md = skill_dir / "SKILL.md"
        line = skill_description_line(skill_md)
        n = len(line)
        desc_chars += n
        fm, _ = parse_skill_frontmatter(skill_md)
        model_invocable = not bool(fm.get("disable-model-invocation"))
        if model_invocable:
            effective_chars += n
        skills.append(
            {
                "name": str(fm.get("name") or skill_dir.name),
                "path": str(skill_md),
                "description_chars": n,
                "model_invocable": model_invocable,
            }
        )
    return SkillMount(
        label=label,
        path=str(root),
        skill_count=len(skills),
        description_chars=desc_chars,
        effective_description_chars=effective_chars,
        skills=skills,
    )


def _resolve_project(project: str | Path | None) -> Path | None:
    if project is None:
        return None
    p = Path(project).expanduser().resolve()
    return p if p.is_dir() else None


def build_skills_budget(project: str | Path | None = None) -> SkillsBudgetReport:
    """Measure description-char totals for vendor-loaded skill index populations."""
    mounts: list[SkillMount] = []
    home = Path.home()
    mounts.append(measure_skill_mount("claude_global", home / ".claude" / "skills"))
    mounts.append(measure_skill_mount("codex_global", home / ".agents" / "skills"))

    proj = _resolve_project(project)
    if proj:
        repo_skills = proj / ".agents" / "skills"
        if not repo_skills.is_dir() and (proj / ".claude" / "skills").is_dir():
            repo_skills = proj / ".claude" / "skills"
        mounts.append(measure_skill_mount(f"repo:{proj.name}", repo_skills))

    violations: list[str] = []
    by_label = {m.label: m for m in mounts}

    # claude_global gates on the EFFECTIVE (ambient model-facing) index: Claude
    # honors disable-model-invocation, and doesn't hard-clip at 8000 anyway.
    if by_label["claude_global"].effective_description_chars > CODEX_SKILLS_BUDGET_CHARS:
        violations.append(
            f"claude_global {by_label['claude_global'].effective_description_chars} "
            f"effective chars > {CODEX_SKILLS_BUDGET_CHARS}"
        )
    if by_label["codex_global"].description_chars > CODEX_SKILLS_BUDGET_CHARS:
        violations.append(
            f"codex_global {by_label['codex_global'].description_chars} chars "
            f"> {CODEX_SKILLS_BUDGET_CHARS}"
        )

    repo_mount = next((m for m in mounts if m.label.startswith("repo:")), None)
    if repo_mount and repo_mount.description_chars > CODEX_SKILLS_BUDGET_CHARS:
        violations.append(
            f"{repo_mount.label} {repo_mount.description_chars} chars "
            f"> {CODEX_SKILLS_BUDGET_CHARS}"
        )
    if repo_mount:
        combined = by_label["codex_global"].description_chars + repo_mount.description_chars
        if combined > CODEX_SKILLS_BUDGET_CHARS:
            violations.append(
                f"codex_global+{repo_mount.label} {combined} chars > {CODEX_SKILLS_BUDGET_CHARS}"
            )

    return SkillsBudgetReport(
        codex_budget_chars=CODEX_SKILLS_BUDGET_CHARS,
        mounts=mounts,
        violations=violations,
    )


def governance_roots(project: Path | None) -> list[Path]:
    roots: list[Path] = []
    if project:
        roots.append(project)
    global_claude = Path.home() / ".claude" / "CLAUDE.md"
    if global_claude.is_file():
        roots.append(global_claude.parent)
    return roots


def _rg_files(root: Path, glob: str) -> list[Path]:
    if "*" in glob:
        return sorted(root.glob(glob))
    p = root / glob
    return [p] if p.is_file() else []


def governance_files(project: Path | None) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for root in governance_roots(project):
        for pattern in GOVERNANCE_GLOBS:
            for path in _rg_files(root, pattern):
                try:
                    key = path.resolve()
                except OSError:
                    key = path
                if key in seen or not path.is_file():
                    continue
                seen.add(key)
                files.append(path)
    skills_canonical = PROJECTS_ROOT / "skills"
    if skills_canonical.is_dir():
        for path in skills_canonical.glob("*/SKILL.md"):
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                files.append(path)
    return files


def normalize_for_dedup(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def search_governance(
    needle: str,
    project: Path | None = None,
    *,
    max_hits: int = 20,
    min_needle_len: int = 24,
) -> list[dict[str, Any]]:
    """Return files/lines that may already cover a proposed governance snippet."""
    needle_norm = normalize_for_dedup(needle)
    if len(needle_norm) < min_needle_len:
        return []

    # Tokenize: long words from needle for grep
    tokens = [t for t in re.findall(r"[a-z0-9]{5,}", needle_norm) if len(t) >= 5]
    if not tokens:
        return []
    pattern = tokens[0] if len(tokens) == 1 else "|".join(tokens[:4])

    hits: list[dict[str, Any]] = []
    for path in governance_files(project):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle_norm in normalize_for_dedup(text):
            hits.append({"path": str(path), "match": "full_substring", "line": None})
            continue
        for i, line in enumerate(text.splitlines(), 1):
            line_norm = normalize_for_dedup(line)
            if any(tok in line_norm for tok in tokens[:3]):
                hits.append({"path": str(path), "match": "token", "line": i, "text": line[:200]})
                if len(hits) >= max_hits:
                    return hits
    return hits[:max_hits]


def validate_closeout_dispatch(data: dict[str, Any]) -> list[str]:
    """Partition invariants for .model-review/dispatch.json (closeout path)."""
    errors: list[str] = []
    layers = data.get("layers") or {}
    diff = layers.get("diff") or {}
    design = layers.get("design") or {}

    if diff.get("owner") != "code-review":
        errors.append("layers.diff.owner must be code-review")
    if design.get("owner") != "critique":
        errors.append("layers.design.owner must be critique")

    axes = str(design.get("axes") or "")
    if "composer" in axes.replace(" ", "").split(","):
        errors.append("layers.design.axes must not include composer on closeout (use /code-review)")

    artifact = data.get("artifact")
    if artifact == "closeout" and diff.get("run") and design.get("run"):
        if data.get("blockers"):
            errors.append(f"dispatch has blockers: {data['blockers'][:2]}")
    return errors


def sync_skill_symlinks(
    src: Path,
    dst: Path,
    *,
    check: bool = False,
) -> dict[str, Any]:
    """Mirror skill directory symlinks from src → dst (Codex/Claude parity)."""
    result = {"created": 0, "updated": 0, "removed": 0, "ok": True, "errors": []}
    if not src.is_dir():
        result["ok"] = False
        result["errors"].append(f"missing source: {src}")
        return result

    dst.mkdir(parents=True, exist_ok=True)
    expected: dict[str, Path] = {}
    for skill_dir in iter_skill_dirs(src):
        # Codex has no verified disable-model-invocation support, so every
        # mirrored skill lands in its AMBIENT auto-fire index. Explicit-only
        # skills (fa0ce09: execute/leverage/…) therefore stay Claude-side;
        # mirroring them would grant Codex exactly the ambient auto-fire the
        # flag exists to prevent — and they burn its 8K description budget.
        fm, _ = parse_skill_frontmatter(skill_dir / "SKILL.md")
        if fm.get("disable-model-invocation"):
            continue
        target = skill_dir.resolve()
        expected[skill_dir.name] = target

    for name, target in expected.items():
        link = dst / name
        if link.is_symlink():
            try:
                have = link.resolve()
            except OSError:
                have = None
            if have == target:
                continue
            if check:
                result["updated"] += 1
            else:
                link.unlink(missing_ok=True)
                link.symlink_to(target)
                result["updated"] += 1
        elif link.exists():
            result["errors"].append(f"{link} exists and is not a symlink")
            result["ok"] = False
        else:
            if not check:
                link.symlink_to(target)
            result["created"] += 1

    for child in list(dst.iterdir()):
        if child.name in SKIP_SKILL_DIR_NAMES or child.name.startswith("."):
            continue
        if child.name not in expected and child.is_symlink():
            if not check:
                child.unlink()
            result["removed"] += 1

    return result


def run_rg_count(pattern: str, path: Path) -> int:
    try:
        proc = subprocess.run(
            ["rg", "-l", pattern, str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode not in (0, 1):
            return 0
        return len([ln for ln in proc.stdout.splitlines() if ln.strip()])
    except OSError:
        return 0
