"""sync_skill_symlinks honors the operator's `skillOverrides: off` (Codex parity).

2026-09-01: the ~/.agents/skills mirror carried 16 skills Claude had switched off,
pushing Codex's skill-description index to 9,362 chars against its 8,000 ceiling.
Parity means an off skill is off on both vendors; the mirror is the only place
that can be enforced because Codex has no per-skill disable.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.surface_gates import claude_disabled_skills, sync_skill_symlinks


def _skill(root: Path, name: str, *, explicit_only: bool = False) -> Path:
    d = root / name
    d.mkdir(parents=True)
    extra = "disable-model-invocation: true\n" if explicit_only else ""
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} does a thing\n{extra}---\n# {name}\n",
        encoding="utf-8",
    )
    return d


def _mirror(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "claude-skills"
    dst = tmp_path / "agents-skills"
    _skill(src, "alpha")
    _skill(src, "bravo")
    _skill(src, "charlie", explicit_only=True)
    dst.mkdir()
    # Pre-existing mirror state: alpha correct, bravo present although it is off.
    (dst / "alpha").symlink_to((src / "alpha").resolve())
    (dst / "bravo").symlink_to((src / "bravo").resolve())
    return src, dst


def test_off_skill_is_not_mirrored_and_its_stale_link_is_removed(tmp_path: Path) -> None:
    src, dst = _mirror(tmp_path)

    result = sync_skill_symlinks(src, dst, exclude=frozenset({"bravo"}))

    assert result["ok"] and not result["errors"]
    assert result["excluded"] == 1
    assert result["removed"] == 1 and result["created"] == 0 and result["updated"] == 0
    assert (dst / "alpha").is_symlink()
    assert not (dst / "bravo").exists()
    assert not (dst / "charlie").exists()  # explicit-only stays Claude-side


def test_check_mode_counts_the_removal_without_touching_the_mirror(tmp_path: Path) -> None:
    src, dst = _mirror(tmp_path)

    result = sync_skill_symlinks(src, dst, check=True, exclude=frozenset({"bravo"}))

    assert result["removed"] == 1 and result["excluded"] == 1
    assert (dst / "bravo").is_symlink()  # untouched in check mode


def test_without_exclude_the_off_skill_would_be_mirrored(tmp_path: Path) -> None:
    src, dst = _mirror(tmp_path)

    result = sync_skill_symlinks(src, dst)

    assert result["removed"] == 0 and result["excluded"] == 0
    assert (dst / "bravo").is_symlink()


def test_claude_disabled_skills_reads_only_off(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "skillOverrides": {
                    "x": "off",
                    "plugin:y": "off",
                    "z": "name-only",
                    "w": "user-invocable-only",
                }
            }
        ),
        encoding="utf-8",
    )

    assert claude_disabled_skills(settings) == frozenset({"x", "plugin:y"})
    assert claude_disabled_skills(tmp_path / "missing.json") == frozenset()
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert claude_disabled_skills(tmp_path / "bad.json") == frozenset()
