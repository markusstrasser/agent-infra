from pathlib import Path
import importlib.util
import json

from scripts.common.skill_objects import (
    SkillRoot,
    collect_skill_objects,
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
        "object_id": "intel:skill.workup",
        "name": "workup",
        "description": "Full workup battery",
        "primary_category": "alias",
    }

    assert skill_routing_script._score("work up VST", row) > 0


def test_public_export_rejects_symlink(tmp_path: Path):
    source = tmp_path / "skill"
    source.mkdir()
    private = tmp_path / "private.md"
    private.write_text("Markus private token", encoding="utf-8")
    (source / "linked.md").symlink_to(private)

    result = export_public_skills_script._contains_blocked_token(source)

    assert result
    assert "symlink exports are not allowed" in result


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
