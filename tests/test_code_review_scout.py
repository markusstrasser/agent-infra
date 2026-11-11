"""Fail-closed contracts for the continuous code-review dispatcher."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "code-review-scout.py"
SPEC = importlib.util.spec_from_file_location("code_review_scout", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
scout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scout)


PROVIDER = {
    "name": "test-provider",
    "model_flag": "-m test-model",
    "extra": "",
}


def test_gather_files_scopes_skipped_directories_to_repository_root(
    tmp_path: Path,
) -> None:
    repository = tmp_path / ".claude" / "worktrees" / "target-repository"
    included = repository / "src" / "included.py"
    included.parent.mkdir(parents=True)
    included.write_text("included = True\n" * 10)
    excluded = repository / ".claude" / "excluded.py"
    excluded.parent.mkdir()
    excluded.write_text("excluded = True\n" * 10)

    assert repository.is_absolute()
    assert ".claude" in repository.parts
    assert scout.gather_files(repository) == [included]


def test_gather_files_includes_component_framework_sources(tmp_path: Path) -> None:
    sources = tmp_path / "src"
    sources.mkdir()
    svelte = sources / "Page.svelte"
    svelte.write_text("<script>let count = 0;</script>\n" * 3)
    tsx = sources / "Panel.tsx"
    tsx.write_text("export const Panel = () => <section />;\n" * 3)

    assert scout.gather_files(tmp_path) == [svelte, tsx]


def test_gather_files_includes_swift_and_shebang_scripts(tmp_path: Path) -> None:
    swift = tmp_path / "Input.swift"
    swift.write_text("let keys = [String]()\n" * 4)
    script = tmp_path / "lane-cargo"
    script.write_text('#!/bin/sh\nexec cargo "$@"\n' * 3)
    (tmp_path / "LICENSE").write_text("Permission is hereby granted\n" * 3)
    (tmp_path / "README.md").write_text("# readme\n" * 10)

    assert scout.gather_files(tmp_path) == [swift, script]


def test_gather_files_includes_node_module_suffixes(tmp_path: Path) -> None:
    # 2026-10-26: .cjs lane files were "not a reviewable source file" in a diff review.
    cjs = tmp_path / "case.cjs"
    cjs.write_text("module.exports = {};\n" * 4)
    mjs = tmp_path / "view.mjs"
    mjs.write_text("export const x = 1;\n" * 4)

    assert scout.gather_files(tmp_path) == [cjs, mjs]


def test_dispatch_returns_nonempty_reviewer_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scout.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "NO_ISSUES\n", ""),
    )

    assert scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1") == "NO_ISSUES"


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "match"),
    [
        (1, "", "authentication failed", "exited 1"),
        (0, "", "", "without a verdict"),
    ],
)
def test_dispatch_failure_cannot_be_reported_as_zero_findings(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    stderr: str,
    match: str,
) -> None:
    monkeypatch.setattr(
        scout.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode, stdout, stderr
        ),
    )

    with pytest.raises(scout.DispatchError, match=match):
        scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1")


def test_dispatch_timeout_is_a_hard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], timeout=300)

    monkeypatch.setattr(scout.subprocess, "run", timeout)

    with pytest.raises(scout.DispatchError, match="timed out"):
        scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1")


def test_parse_accepts_only_exact_no_issues() -> None:
    assert scout.parse_findings("NO_ISSUES\n", "test", [], Path(".")) == []
    with pytest.raises(scout.DispatchError, match="output contract"):
        scout.parse_findings("preface\nNO_ISSUES", "test", [], Path("."))


def test_parse_rejects_async_session_receipt_as_a_verdict() -> None:
    with pytest.raises(scout.DispatchError, match="output contract"):
        scout.parse_findings("SESSION_ID=28860", "composer", [], Path("."))


def test_parse_accepts_a_structured_finding() -> None:
    parsed = scout.parse_findings(
        "scripts/example.py:7 HIGH patterns unchecked terminal state",
        "composer",
        [],
        Path("."),
    )
    assert parsed == [
        {
            "file": "scripts/example.py",
            "line": 7,
            "severity": "HIGH",
            "category": "patterns",
            "description": "unchecked terminal state",
            "source": "composer",
        }
    ]


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "alpha.py").write_text("alpha = True\n" * 10)
    (root / "pkg" / "beta.py").write_text("beta = True\n" * 10)
    (root / "notes.txt").write_text("not source\n" * 10)
    return root


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *argv: str) -> int:
    monkeypatch.setattr(scout, "ARTIFACTS_BASE", tmp_path / "artifacts")
    monkeypatch.setattr(scout.sys, "argv", ["code-review-scout.py", *argv])
    try:
        scout.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def test_repeated_file_flags_select_every_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    code = _run(
        monkeypatch,
        tmp_path,
        str(root),
        "--file",
        "pkg/alpha.py",
        "--file",
        "pkg/beta.py",
        "--file",
        "pkg/alpha.py",
        "--dry-run",
    )
    out = capsys.readouterr()
    assert code == 0
    assert "pkg/alpha.py" in out.out and "pkg/beta.py" in out.out
    assert out.out.count("pkg/alpha.py") == 1
    assert ": 2 files," in out.err


def test_missing_and_non_source_files_refuse_before_dispatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)

    def no_dispatch(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("dispatch must not run on an invalid selection")

    monkeypatch.setattr(scout, "dispatch_review", no_dispatch)
    code = _run(
        monkeypatch,
        tmp_path,
        str(root),
        "--file",
        "pkg/alpha.py",
        "--file",
        "pkg/gone.py",
        "--file",
        "notes.txt",
    )
    err = capsys.readouterr().err
    assert code != 0
    assert "pkg/gone.py: does not exist" in err
    assert "notes.txt: not source" in err


def test_each_named_file_keeps_the_full_batch_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    big = root / "pkg" / "big.py"
    big.write_text("x = 1\n" * ((scout.MAX_FILE_BYTES // 6) + 100))
    assert scout.MAX_FILE_BYTES < big.stat().st_size <= scout.MAX_BATCH_BYTES
    code = _run(monkeypatch, tmp_path, str(root), "--file", "pkg/big.py", "--dry-run")
    assert code == 0
    huge = root / "pkg" / "huge.py"
    huge.write_text("x = 1\n" * ((scout.MAX_BATCH_BYTES // 6) + 100))
    code = _run(
        monkeypatch, tmp_path, str(root), "--file", "pkg/big.py", "--file", "pkg/huge.py"
    )
    assert code != 0
    assert "pkg/huge.py:" in capsys.readouterr().err


def test_failed_batch_exits_nonzero_and_names_its_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    monkeypatch.setattr(scout, "MAX_BATCH_BYTES", 150)

    def flaky(code_context: str, _focus: str, _provider: dict, label: str) -> str:
        if "### pkg/beta.py" in code_context:
            raise scout.DispatchError(f"[{label}] reviewer timed out after 300s")
        return "NO_ISSUES"

    monkeypatch.setattr(scout, "dispatch_review", flaky)
    code = _run(
        monkeypatch, tmp_path, str(root), "--file", "pkg/alpha.py", "--file", "pkg/beta.py"
    )
    out = capsys.readouterr()
    assert code == 3
    assert "Coverage: reviewed 1 of 2 selected files" in out.out
    assert "pkg/beta.py" in out.out.split("Unreviewed")[1]
    assert "# No new findings for" not in out.err


def test_complete_module_run_prints_full_coverage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    monkeypatch.setattr(scout, "dispatch_review", lambda *_args: "NO_ISSUES")
    code = _run(monkeypatch, tmp_path, str(root), "--module", "pkg")
    assert code == 0
    assert "Coverage: reviewed 2 of 2 selected files" in capsys.readouterr().out
