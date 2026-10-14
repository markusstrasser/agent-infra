"""doctor check: editable uv tool envs must carry their source's declared dependencies."""

from doctor import missing_declared_deps


def test_reports_dependency_added_after_install(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\ndependencies = [\n'
        '  "fastmcp>=3.4.2,<4.0", "exa-py>=2.6", "modal>=1.6.1", "pkg[extra]; python_version>\'3\'",\n]\n'
    )
    installed = {"FastMCP", "exa_py", "pkg"}
    assert missing_declared_deps(pyproject, installed) == ["modal"]


def test_no_dependencies_table(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n')
    assert missing_declared_deps(pyproject, set()) == []
