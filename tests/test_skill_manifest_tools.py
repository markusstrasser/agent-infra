from pathlib import Path
import importlib.util
import json

from scripts.common.skill_objects import (
    SkillRoot,
    collect_skill_objects,
    extract_markdown_section,
    load_object_content,
    stored_skill_filename,
)
from scripts.skill_manifest import validate_rows


_ROUTING_SPEC = importlib.util.spec_from_file_location(
    "skill_routing_script",
    Path(__file__).resolve().parents[1] / "scripts" / "skill-routing.py",
)
assert _ROUTING_SPEC and _ROUTING_SPEC.loader
skill_routing_script = importlib.util.module_from_spec(_ROUTING_SPEC)
_ROUTING_SPEC.loader.exec_module(skill_routing_script)

_EXPORT_SPEC = importlib.util.spec_from_file_location(
    "export_public_skills_script",
    Path(__file__).resolve().parents[1] / "scripts" / "export_public_skills.py",
)
assert _EXPORT_SPEC and _EXPORT_SPEC.loader
export_public_skills_script = importlib.util.module_from_spec(_EXPORT_SPEC)
_EXPORT_SPEC.loader.exec_module(export_public_skills_script)


def test_collect_skill_object_from_temp_root(tmp_path: Path):
    skills_root = tmp_path / ".claude" / "skills"
    skill_dir = skills_root / "example-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: example-skill\n"
        "description: Example routing description.\n"
        "user-invocable: true\n"
        "---\n"
        "# Example\n",
        encoding="utf-8",
    )

    root = SkillRoot("example", skills_root, tmp_path)
    rows = [obj.to_json() for obj in collect_skill_objects([root], include_planned=False)]

    assert len(rows) == 1
    assert rows[0]["object_id"] == "example:skill.example-skill"
    assert rows[0]["stored_filename"] == "SKILL.md"
    assert rows[0]["description"] == "Example routing description."


def test_shared_skill_exportable_comes_from_frontmatter(tmp_path: Path):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "public-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: public-skill\n"
        "exportable: true\n"
        "---\n"
        "# Public\n",
        encoding="utf-8",
    )

    root = SkillRoot("skills", skills_root, tmp_path)
    rows = [obj.to_json() for obj in collect_skill_objects([root], include_planned=False)]

    assert rows[0]["private"] is False
    assert rows[0]["exportable"] is True


def test_intel_dataset_module_package_uses_object_prefix(tmp_path: Path):
    module_path = tmp_path / ".claude" / "skills" / "dataset" / "references" / "onboarding.md"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("# Dataset Onboarding\n", encoding="utf-8")

    root = SkillRoot("intel", tmp_path / ".claude" / "skills", tmp_path)
    rows = [obj.to_json() for obj in collect_skill_objects([root])]
    row = next(row for row in rows if row["object_id"] == "intel:dataset.module.onboarding")

    assert row["package"] == "dataset"
    assert row["status"] == "active"


def test_forbidden_intel_entrypoint_fails_collection(tmp_path: Path):
    skills_root = tmp_path / ".claude" / "skills"
    skill_dir = skills_root / "workup"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: workup\n---\n# Workup\n", encoding="utf-8")

    root = SkillRoot("intel", skills_root, tmp_path)

    try:
        collect_skill_objects([root], include_planned=False)
    except ValueError as exc:
        assert "forbidden Intel skill entrypoint" in str(exc)
    else:
        raise AssertionError("forbidden Intel skill entrypoint was accepted")


def test_stored_skill_filename_preserves_lowercase(tmp_path: Path):
    skill_dir = tmp_path / "lowercase-skill"
    skill_dir.mkdir()
    (skill_dir / "skill.md").write_text("---\nname: lowercase-skill\n---\n", encoding="utf-8")

    assert stored_skill_filename(skill_dir) == "skill.md"


def test_manifest_validation_rejects_private_exportable_row():
    result = validate_rows([
        {
            "object_id": "x:skill.bad",
            "object_type": "SkillEntrypoint",
            "project": "x",
            "package": "x",
            "name": "bad",
            "path": "SKILL.md",
            "repo_root": "/tmp/x",
            "primary_category": "workflow",
            "private": True,
            "exportable": True,
        }
    ])

    assert result["errors"]
    assert "exportable object cannot be private" in result["errors"][0]["errors"]


def test_manifest_strict_rejects_missing_active_path(tmp_path: Path):
    result = validate_rows([
        {
            "object_id": "x:skill.missing",
            "object_type": "SkillEntrypoint",
            "project": "x",
            "package": "x",
            "name": "missing",
            "path": "missing/SKILL.md",
            "repo_root": str(tmp_path),
            "primary_category": "workflow",
            "private": True,
            "exportable": False,
            "status": "active",
        }
    ], strict=True)

    assert result["errors"]
    assert "active path does not exist: missing/SKILL.md" in result["errors"][0]["errors"]


def test_manifest_validation_requires_alias_boundary_and_sunset(tmp_path: Path):
    skill_file = tmp_path / "old" / "SKILL.md"
    skill_file.parent.mkdir()
    skill_file.write_text("---\nname: old\n---\n", encoding="utf-8")
    target_file = tmp_path / "new" / "SKILL.md"
    target_file.parent.mkdir()
    target_file.write_text("---\nname: new\n---\n", encoding="utf-8")
    rows = [
        {
            "object_id": "x:skill.old",
            "object_type": "SkillEntrypoint",
            "project": "x",
            "package": "x",
            "name": "old",
            "path": "old/SKILL.md",
            "repo_root": str(tmp_path),
            "primary_category": "alias",
            "private": True,
            "exportable": False,
            "replaced_by": "x:skill.new",
        },
        {
            "object_id": "x:skill.new",
            "object_type": "SkillEntrypoint",
            "project": "x",
            "package": "x",
            "name": "new",
            "path": "new/SKILL.md",
            "repo_root": str(tmp_path),
            "primary_category": "workflow",
            "private": True,
            "exportable": False,
        },
    ]

    result = validate_rows(rows, strict=True)

    assert result["errors"]
    assert "alias/replaced row missing boundary" in result["errors"][0]["errors"]
    assert "alias/replaced row missing sunset_after" in result["errors"][0]["errors"]


def test_manifest_validation_requires_side_effect_invocation_policy(tmp_path: Path):
    skill_file = tmp_path / "writer" / "SKILL.md"
    skill_file.parent.mkdir()
    skill_file.write_text("---\nname: writer\n---\n# Writer\n", encoding="utf-8")
    rows = [
        {
            "object_id": "x:skill.writer",
            "object_type": "SkillEntrypoint",
            "project": "x",
            "package": "x",
            "name": "writer",
            "path": "writer/SKILL.md",
            "repo_root": str(tmp_path),
            "primary_category": "workflow",
            "private": True,
            "exportable": False,
            "side_effectful": True,
            "boundary": "side-effectful: direct invocation required",
        }
    ]

    result = validate_rows(rows, strict=True)

    assert result["errors"]
    assert "side-effectful row missing explicit invocation policy" in result["errors"][0]["errors"]


def test_manifest_strict_validation_accepts_existing_shared_shadow():
    result = validate_rows([
        {
            "object_id": "agent-infra:skill.analyze-shadow",
            "object_type": "SkillEntrypoint",
            "project": "agent-infra",
            "package": "agent-infra",
            "name": "analyze",
            "path": "AGENTS.md",
            "repo_root": "${PROJECTS_ROOT}/agent-infra",
            "primary_category": "workflow",
            "private": True,
            "shadows": ["skills:skill.analyze"],
        }
    ], strict=True)

    assert result["errors"] == []


def test_routing_score_matches_split_compound_phrase():
    row = {
        "object_id": "intel:skill.asset-decision",
        "name": "asset-decision",
        "description": "Full workup battery",
        "primary_category": "workflow",
    }

    assert skill_routing_script._score("work up VST", row) > 0


def test_routing_prefers_router_over_internal_object_without_direct_slash():
    internal = {
        "object_id": "intel:asset-decision.module.workup-battery",
        "name": "workup-battery",
        "description": "Full workup battery",
        "primary_category": "module",
    }
    router = {
        "object_id": "intel:skill.asset-decision",
        "name": "asset-decision",
        "description": "Triggers on work up TICKER and full workup",
        "primary_category": "workflow",
    }

    assert skill_routing_script._score("work up VST", router) > skill_routing_script._score("work up VST", internal)


def test_public_export_rejects_symlink(tmp_path: Path):
    source = tmp_path / "skill"
    source.mkdir()
    private = tmp_path / "private.md"
    private.write_text("Markus private token", encoding="utf-8")
    (source / "linked.md").symlink_to(private)

    result = export_public_skills_script._contains_blocked_token(source)

    assert result
    assert "symlink exports are not allowed" in result


def test_public_export_uses_manifest_path_not_name(tmp_path: Path):
    skill_dir = tmp_path / "actual-dir"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: display-name\n---\n# Public\n", encoding="utf-8")
    row = {
        "repo_root": str(tmp_path),
        "path": "actual-dir/SKILL.md",
        "name": "display-name",
        "private": False,
        "exportable": True,
        "is_symlink": False,
    }

    source_file = export_public_skills_script.resolve_object_path(row)

    assert source_file.parent == skill_dir


def test_public_export_requires_manifest_exportable_flag():
    row = {"private": False, "exportable": False, "is_symlink": False}

    assert export_public_skills_script._export_block_reason(row) == "row is not marked exportable"


def test_markdown_section_extraction_returns_bounded_section():
    text = "# Doc\n\nIntro\n\n## Phase 1\none\n\n### Detail\nchild\n\n## Phase 2\ntwo\n"

    assert extract_markdown_section(text, "Phase 1") == "## Phase 1\none\n\n### Detail\nchild\n"


def test_markdown_section_extraction_ignores_code_fence_hash_comments():
    text = "# Doc\n\n## Target\nwanted\n```bash\n# not a heading\n```\nstill wanted\n\n## Other\nnoise\n"

    section = extract_markdown_section(text, "Target")

    assert section is not None
    assert "still wanted" in section
    assert "## Other" not in section


def test_load_object_content_uses_anchor(tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text("# Doc\n\nintro\n\n## Target\nwanted\n\n## Other\nnoise\n", encoding="utf-8")
    row = {
        "repo_root": str(tmp_path),
        "path": "doc.md",
        "content_anchor": "Target",
    }

    content = load_object_content(row, max_chars=100)

    assert content["available"] is True
    assert "wanted" in content["text"]
    assert "noise" not in content["text"]


def test_source_chain_rejects_verified_claim_without_primary_source():
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/schemas/source-chain.schema.json").read_text())
    instance = {
        "schema_version": "source-chain.v1",
        "origin_type": "article",
        "source_id": "s1",
        "source_identity": "Example",
        "admission_state": "admitted",
        "quarantine_state": "none",
        "primary_source_links": [],
        "entity_routes": ["ABC"],
        "claims": [{"claim_id": "c1", "text": "claim", "status": "verified"}],
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(instance))


def test_source_chain_rejects_admitted_failed_primary_check():
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/schemas/source-chain.schema.json").read_text())
    instance = {
        "schema_version": "source-chain.v1",
        "origin_type": "article",
        "source_id": "s1",
        "source_identity": "Example",
        "admission_state": "admitted",
        "quarantine_state": "failed_primary_check",
        "primary_source_links": [],
        "entity_routes": ["ABC"],
        "claims": [],
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(instance))


def test_source_chain_rejects_admitted_without_primary_links():
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/schemas/source-chain.schema.json").read_text())
    instance = {
        "schema_version": "source-chain.v1",
        "origin_type": "article",
        "source_id": "s1",
        "source_identity": "Example",
        "admission_state": "admitted",
        "quarantine_state": "none",
        "primary_source_links": [],
        "entity_routes": ["ABC"],
        "claims": [],
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(instance))


def test_source_chain_rejects_empty_primary_link_url():
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/schemas/source-chain.schema.json").read_text())
    instance = {
        "schema_version": "source-chain.v1",
        "origin_type": "article",
        "source_id": "s1",
        "source_identity": "Example",
        "admission_state": "admitted",
        "quarantine_state": "none",
        "primary_source_links": [{"url": "", "source_type": "filing"}],
        "entity_routes": ["ABC"],
        "claims": [
            {
                "claim_id": "c1",
                "text": "Claim",
                "status": "verified",
                "primary_source_urls": [""],
            }
        ],
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(instance))


def test_subagent_contract_requires_validation_for_durable_writes():
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/schemas/subagent-contract.schema.json").read_text())
    instance = {
        "schema_version": "subagent-contract.v1",
        "agent_role": "entity-filler",
        "task_id": "t1",
        "status": "complete",
        "summary": "done",
        "files_read": [],
        "files_written": ["docs/entities/genes/DPYD.md"],
        "claims": [],
        "open_questions": [],
        "cosign_status": "not_applicable",
    }

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(instance))
