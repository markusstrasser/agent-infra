"""Shared skill-object inventory and manifest helpers.

The manifest is intentionally filesystem-first: it records what agent loaders
can discover today, plus planned module/lens objects that routers can load
through MCP or a read-only filesystem fallback. Keep this module side-effect
free so validators, MCP tools, and migration scripts share one object model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECTS_ROOT = Path.home() / "Projects"
META_ROOT = PROJECTS_ROOT / "agent-infra"
PROJECTS_ROOT_TOKEN = "${PROJECTS_ROOT}"


@dataclass(frozen=True)
class SkillRoot:
    project: str
    root: Path
    repo_root: Path
    shared: bool = False


DEFAULT_ROOTS = {
    "skills": SkillRoot("skills", PROJECTS_ROOT / "skills", PROJECTS_ROOT / "skills", True),
    "agent-infra": SkillRoot(
        "agent-infra",
        PROJECTS_ROOT / "agent-infra" / ".claude" / "skills",
        PROJECTS_ROOT / "agent-infra",
    ),
    "genomics": SkillRoot(
        "genomics",
        PROJECTS_ROOT / "genomics" / ".claude" / "skills",
        PROJECTS_ROOT / "genomics",
    ),
    "phenome": SkillRoot(
        "phenome",
        PROJECTS_ROOT / "phenome" / ".claude" / "skills",
        PROJECTS_ROOT / "phenome",
    ),
    "intel": SkillRoot(
        "intel",
        PROJECTS_ROOT / "intel" / ".claude" / "skills",
        PROJECTS_ROOT / "intel",
    ),
}


SKIP_DIRS = {
    ".DS_Store",
    ".claude",
    ".git",
    "__pycache__",
    "archive",
    "hooks",
}


ARTIFACT_BUILDERS = {
    "3-statement-model",
    "audit-xls",
    "comps-analysis",
    "dcf-model",
    "model-update",
    "xlsx-author",
}

REFERENCE_SKILLS = {
    "annotsv",
    "clinpgx-database",
    "commands",
    "data-transform",
    "embedding-models",
    "gget",
    "llmx-guide",
    "markitdown",
    "vcfexpress",
    "x-api",
}

MODULE_SKILLS = {
    "confirm",
    "disqualify",
    "extract-generators",
    "propose-rule",
    "resolve-predictions",
    "talent-dossier",
    "thesis-check",
    "trace-influence",
}

LENS_SKILLS = {
    "drawdown-context",
    "standalone-asset",
}

ALIAS_SKILLS = {
    "workup",
    "genomics-status",
}

SIDE_EFFECTFUL_SKILLS = {
    "new-dataset",
    "propose-rule",
    "x-api",
}

INTEL_DISPOSITIONS = {
    "3-statement-model": "retain artifact builder under modeling",
    "asset-decision": "retain and compact as main decision router",
    "audit-xls": "retain artifact/checker under modeling",
    "commands": "retain disabled CLI reference",
    "comps-analysis": "retain artifact builder under modeling",
    "confirm": "retain safety-critical direct-invocable module",
    "dcf-model": "retain artifact builder under modeling",
    "disqualify": "retain safety-critical direct-invocable kill-switch module",
    "divergence-update": "move to asset-decision entity-update template/module",
    "drawdown-context": "move to asset-decision lens",
    "earnings-preview": "retain event-prep workflow",
    "entity-management": "shared symlink; record as shared-shadow entry",
    "extract-generators": "move to governance module",
    "forecast": "retain evidence-packet workflow, not decision router",
    "idea-generation": "retain sourcing/screening workflow",
    "ingest-article": "migrate into source-ingest/doc-ingest",
    "llm-check": "retain or deprecate after usage data",
    "model-update": "retain artifact builder under modeling",
    "new-dataset": "move/alias to dataset workflow",
    "propose-rule": "move to governance module",
    "resolve-predictions": "move to asset-decision/governance module",
    "social-thread": "migrate into source-ingest/social-ingest",
    "standalone-asset": "move to asset-decision framing-suppression lens",
    "talent-dossier": "retain asset-decision module",
    "thesis-check": "retain adversarial-stress direct-invocable module",
    "trace-influence": "move to governance/research module",
    "workup": "retain thin alias to asset-decision",
    "x-api": "shared symlink/tool skill",
    "xlsx-author": "retain artifact builder under modeling",
}

INTEL_MODULES = {
    "asset-decision.module.disqualify": ("disqualify", "disqualify/SKILL.md"),
    "asset-decision.module.confirm": ("confirm", "confirm/SKILL.md"),
    "asset-decision.module.talent-dossier": ("talent-dossier", "talent-dossier/SKILL.md"),
    "asset-decision.module.thesis-check": ("thesis-check", "thesis-check/SKILL.md"),
    "asset-decision.module.resolve-predictions": (
        "resolve-predictions",
        "resolve-predictions/SKILL.md",
    ),
    "source-ingest.engine.social-ingest": ("social-ingest", "social-thread/SKILL.md"),
    "source-ingest.engine.doc-ingest": ("doc-ingest", "ingest-article/SKILL.md"),
    "governance.module.extract-generators": (
        "extract-generators",
        "extract-generators/SKILL.md",
    ),
    "governance.module.propose-rule": ("propose-rule", "propose-rule/SKILL.md"),
}

INTEL_LENSES = {
    "asset-decision.lens.drawdown-context": (
        "drawdown-context",
        ".claude/skills/drawdown-context/SKILL.md",
    ),
    "asset-decision.lens.standalone-suppression": (
        "standalone-suppression",
        ".claude/skills/standalone-asset/SKILL.md",
    ),
    "asset-decision.lens.thesis-pivot": ("thesis-pivot", "docs/workflows/asset_decision.md"),
    "asset-decision.lens.conviction-divergence": (
        "conviction-divergence",
        ".claude/skills/divergence-update/SKILL.md",
    ),
    "asset-decision.lens.pillar-extraction": (
        "pillar-extraction",
        "docs/workflows/asset_decision.md",
    ),
    "asset-decision.lens.steelman-moat-erosion": (
        "steelman-moat-erosion",
        "docs/workflows/asset_decision.md",
    ),
    "asset-decision.lens.buyer-capex-first": (
        "buyer-capex-first",
        "docs/workflows/asset_decision.md",
    ),
    "asset-decision.lens.taxonomy-axis-verification": (
        "taxonomy-axis-verification",
        "docs/workflows/asset_decision.md",
    ),
    "asset-decision.lens.source-chain-admission": (
        "source-chain-admission",
        "docs/workflows/asset_decision.md",
    ),
    "asset-decision.lens.generator-extraction-routing": (
        "generator-extraction-routing",
        "memory/generator_library.md",
    ),
    "asset-decision.lens.position-action-translation": (
        "position-action-translation",
        "docs/workflows/asset_decision.md",
    ),
}

GENOMICS_LENSES = {
    "genomics-pipeline.lens.stage-truth-check": (
        "stage-truth-check",
        ".claude/skills/genomics-pipeline/SKILL.md",
    ),
    "genomics-pipeline.lens.raw-input-preflight": (
        "raw-input-preflight",
        ".claude/skills/genomics-pipeline/SKILL.md",
    ),
    "genomics-pipeline.lens.sample-readiness": (
        "sample-readiness",
        ".claude/skills/genomics-pipeline/SKILL.md",
    ),
    "genomics-pipeline.lens.publish-contract-verification": (
        "publish-contract-verification",
        ".claude/skills/genomics-pipeline/SKILL.md",
    ),
    "genomics-pipeline.lens.modal-live-state-truth": (
        "modal-live-state-truth",
        ".claude/skills/genomics-status/SKILL.md",
    ),
    "genomics-pipeline.lens.primary-vcf-interval-query-proof": (
        "primary-vcf-interval-query-proof",
        ".claude/skills/genomics-pipeline/SKILL.md",
    ),
}

PHENOME_ROLE_AGENTS = {
    "role-agent.claim-verifier": ("claim-verifier", ".claude/agents/claim-verifier.md"),
    "role-agent.entity-filler": ("entity-filler", ".claude/agents/entity-filler.md"),
}

ANALYZE_LENSES = {
    "analyze.lens.null-base-rate": ("null-base-rate", "analyze/lenses/null-base-rate.md"),
    "analyze.lens.causal-attribution": ("causal-attribution", "analyze/lenses/causal-attribution.md"),
    "analyze.lens.dag-adjustment": ("dag-adjustment", "analyze/lenses/dag-adjustment.md"),
    "analyze.lens.hypotheses-ach": ("hypotheses-ach", "analyze/lenses/hypotheses-ach.md"),
    "analyze.lens.weakest-link-audit": (
        "weakest-link-audit",
        "analyze/lenses/weakest-link-audit.md",
    ),
    "analyze.lens.decision-impact-stop": (
        "decision-impact-stop",
        "analyze/lenses/decision-impact-stop.md",
    ),
}


@dataclass
class SkillObject:
    object_id: str
    object_type: str
    project: str
    package: str
    name: str
    path: str
    repo_root: str
    resolved_path: str | None = None
    is_symlink: bool = False
    symlink_target: str | None = None
    stored_filename: str | None = None
    description: str | None = None
    primary_category: str = "workflow"
    secondary_roles: list[str] = field(default_factory=list)
    user_invocable: bool | None = None
    disable_model_invocation: bool | None = None
    side_effectful: bool = False
    artifact_builder: bool = False
    private: bool = True
    exportable: bool = False
    aliases: list[str] = field(default_factory=list)
    replaces: list[str] = field(default_factory=list)
    replaced_by: str | None = None
    boundary: str | None = None
    last_seen: str | None = None
    sunset_after: str | None = None
    shadows: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    workflow_docs: list[str] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    routing_cases: list[str] = field(default_factory=list)
    status: str = "active"
    notes: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, [], {})}


def parse_frontmatter_text(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    loaded = yaml.safe_load(text[4:end])
    return loaded if isinstance(loaded, dict) else {}


def read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        return parse_frontmatter_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}


def stored_skill_filename(skill_dir: Path) -> str | None:
    try:
        names = set(os.listdir(skill_dir))
    except OSError:
        return None
    for candidate in ("SKILL.md", "skill.md"):
        if candidate in names:
            return candidate
    for name in names:
        if name.lower() == "skill.md":
            return name
    return None


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def portable_path(path: Path) -> str:
    try:
        return f"{PROJECTS_ROOT_TOKEN}/{path.resolve().relative_to(PROJECTS_ROOT.resolve())}"
    except ValueError:
        return str(path)


def resolve_portable_path(path_text: str) -> Path:
    if path_text.startswith(f"{PROJECTS_ROOT_TOKEN}/"):
        return PROJECTS_ROOT / path_text.split("/", 1)[1]
    return Path(path_text)


def infer_category(name: str) -> str:
    if name in ARTIFACT_BUILDERS:
        return "artifact"
    if name in REFERENCE_SKILLS:
        return "reference"
    if name in MODULE_SKILLS:
        return "module"
    if name in LENS_SKILLS:
        return "lens"
    if name in ALIAS_SKILLS:
        return "alias"
    return "workflow"


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _entry_from_skill_dir(root: SkillRoot, skill_dir: Path, shared_names: set[str]) -> SkillObject | None:
    if skill_dir.name in SKIP_DIRS or not skill_dir.is_dir():
        return None

    stored = stored_skill_filename(skill_dir)
    if stored is None:
        return None

    skill_file = skill_dir / stored
    fm = read_frontmatter(skill_file)
    name = str(fm.get("name") or skill_dir.name)
    category = infer_category(skill_dir.name)
    resolved = skill_dir.resolve()
    is_symlink = skill_dir.is_symlink()
    target = os.readlink(skill_dir) if is_symlink else None
    shared_shadow = []
    if root.project != "skills" and (is_symlink or skill_dir.name in shared_names):
        shared_shadow.append(f"skills:skill.{skill_dir.name}")

    secondary_roles: list[str] = []
    if skill_dir.name in ARTIFACT_BUILDERS:
        secondary_roles.append("artifact_builder")
    if is_symlink:
        secondary_roles.append("shared_shadow")

    private = root.project != "skills"
    exportable = False

    entry = SkillObject(
        object_id=f"{root.project}:skill.{skill_dir.name}",
        object_type="SkillEntrypoint",
        project=root.project,
        package=root.project,
        name=name,
        path=repo_relative(skill_file, root.repo_root),
        repo_root=portable_path(root.repo_root),
        resolved_path=None,
        is_symlink=is_symlink,
        symlink_target=portable_path((skill_dir.parent / target).resolve()) if target and not Path(target).is_absolute() else portable_path(Path(target)) if target else None,
        stored_filename=stored,
        description=fm.get("description"),
        primary_category=category,
        secondary_roles=secondary_roles,
        user_invocable=_bool_or_none(fm.get("user-invocable")),
        disable_model_invocation=_bool_or_none(fm.get("disable-model-invocation")),
        side_effectful=skill_dir.name in SIDE_EFFECTFUL_SKILLS,
        artifact_builder=skill_dir.name in ARTIFACT_BUILDERS,
        private=private,
        exportable=exportable,
        shadows=shared_shadow,
        notes=INTEL_DISPOSITIONS.get(skill_dir.name) if root.project == "intel" else None,
    )

    if root.project == "intel":
        if skill_dir.name == "workup":
            entry.replaced_by = "intel:skill.asset-decision"
            entry.boundary = "live human prompt alias"
        elif skill_dir.name in {"social-thread", "ingest-article"}:
            entry.replaced_by = "intel:skill.source-ingest"
            entry.boundary = "live human prompt alias"
        elif skill_dir.name == "new-dataset":
            entry.replaced_by = "intel:skill.dataset"
            entry.boundary = "live human prompt alias"

    return entry


def _virtual_object(
    root: SkillRoot,
    object_id_suffix: str,
    object_type: str,
    name: str,
    rel_path: str,
    category: str,
    package: str,
    notes: str | None = None,
) -> SkillObject:
    path = root.repo_root / rel_path
    status = "planned" if not path.exists() else "active"
    return SkillObject(
        object_id=f"{root.project}:{object_id_suffix}",
        object_type=object_type,
        project=root.project,
        package=package,
        name=name,
        path=rel_path,
        repo_root=portable_path(root.repo_root),
        resolved_path=None,
        primary_category=category,
        private=True,
        exportable=False,
        status=status,
        notes=notes,
    )


def planned_objects_for(root: SkillRoot) -> list[SkillObject]:
    objects: list[SkillObject] = []
    if root.project == "skills":
        for suffix, (name, path) in ANALYZE_LENSES.items():
            objects.append(_virtual_object(root, suffix, "LensDoc", name, path, "lens", "analyze"))
    elif root.project == "intel":
        for suffix, (name, path) in INTEL_MODULES.items():
            package = (
                "source-ingest"
                if ".engine." in suffix
                else "governance"
                if suffix.startswith("governance.")
                else "asset-decision"
            )
            objects.append(
                _virtual_object(root, suffix, "ModuleDoc", name, f".claude/skills/{path}", "module", package)
            )
        for suffix, (name, path) in INTEL_LENSES.items():
            objects.append(_virtual_object(root, suffix, "LensDoc", name, path, "lens", "asset-decision"))
    elif root.project == "genomics":
        for suffix, (name, path) in GENOMICS_LENSES.items():
            objects.append(_virtual_object(root, suffix, "LensDoc", name, path, "lens", "genomics-pipeline"))
    elif root.project == "phenome":
        for suffix, (name, path) in PHENOME_ROLE_AGENTS.items():
            objects.append(_virtual_object(root, suffix, "RoleAgentContract", name, path, "role-agent", "phenome"))
    return objects


def collect_skill_objects(
    roots: Iterable[SkillRoot],
    include_planned: bool = True,
) -> list[SkillObject]:
    roots_list = list(roots)
    shared_root = next((r for r in roots_list if r.project == "skills"), None)
    shared_names: set[str] = set()
    if shared_root and shared_root.root.exists():
        shared_names = {
            p.name
            for p in shared_root.root.iterdir()
            if p.is_dir() and p.name not in SKIP_DIRS and stored_skill_filename(p)
        }

    objects: list[SkillObject] = []
    for root in roots_list:
        if not root.root.exists():
            continue
        for skill_dir in sorted(root.root.iterdir(), key=lambda p: p.name):
            entry = _entry_from_skill_dir(root, skill_dir, shared_names)
            if entry:
                objects.append(entry)
        if include_planned:
            objects.extend(planned_objects_for(root))

    return objects


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_manifest(path: Path, objects: Iterable[SkillObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(obj.to_json(), sort_keys=True) for obj in objects]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def root_for_name(name: str) -> SkillRoot:
    try:
        return DEFAULT_ROOTS[name]
    except KeyError as exc:
        raise SystemExit(f"unknown repo '{name}', expected one of: {', '.join(DEFAULT_ROOTS)}") from exc


def iter_default_roots(names: Iterable[str] | None = None) -> list[SkillRoot]:
    if names is None:
        return list(DEFAULT_ROOTS.values())
    return [root_for_name(name) for name in names]
