#!/usr/bin/env python3
"""headless_pin_audit [PATH ...]: headless `claude -p` and `codex exec` launches that leave model or effort unnamed.

A launch without those flags runs at whatever an interactive session last saved: Claude Code writes `/effort` as the
default for new sessions, and the Codex app writes its model, effort and speed pickers to ~/.codex/config.toml. On
2026-11-04 a saved Ultrafast tier billed every headless Codex run at 6x. Exit 1 lists `file:line  missing <flags>`.

A launch is a `["claude", "-p", ...]` / `["codex", "exec", ...]` argv list, or the command itself in a shell
file. Its flags are looked for in the enclosing Python function, or, in a shell file, on the launch's own lines and in
the arrays it expands. A `claude -p --resume/--continue` keeps its session's model, so only its effort must be named:
a bare resume takes the saved default (measured 2026-11-11: a session run at low resumed at xhigh).
A line carrying `headless-pin: ok` (say why) is skipped. With no PATH, the harness roots are scanned, and with them
the agent definitions in AGENT_DIRS: one without `model:` and `effort:` runs at its parent session's.
"""
from __future__ import annotations

import ast
import os
import re
import shlex
import sys
from pathlib import Path

HOME = Path.home()
DEFAULT_ROOTS = [
    HOME / "Projects/agent-infra/scripts",
    HOME / "Projects/agent-infra/justfile",
    HOME / "Projects/skills/bin",
    HOME / "Projects/skills/hooks",
    HOME / "Projects/skills",  # */scripts only, see iter_files
    HOME / ".claude/hooks",
    HOME / "Projects/llmx/llmx",
]
AGENT_DIRS = [HOME / ".claude/agents", HOME / "Projects/agent-infra/.claude/agents"]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "tests", "archive", "worktrees", "fixtures"}
TEXT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ""}

LIST_LAUNCH = re.compile(
    r"""["'](?P<claude>claude)["']\s*,\s*["'](?:-p|--print)["']|(?:["']codex["']|\bbinary)\s*,\s*["']exec["']"""
)
# Nothing below can match a file without both a CLI name and one of its headless words; skips most parses.
CLI_NAME = re.compile(r"\b(?:claude|codex)\b")
HEADLESS_WORD = re.compile(r"""\bexec\b|--print|["'\s]-p["'\s]""")
ARRAY_REF = re.compile(r"\$\{(\w+)\[@\]\}")
WAIVER = "headless-pin: ok"
FLAGS = {
    "claude": {
        "model": re.compile(r"--model\b"),
        "effort": re.compile(r"--effort\b"),
    },
    "codex": {
        "model": re.compile(r"""(?:["'\s(]-m["'\s]|--model\b)"""),
        "effort": re.compile(r"model_reasoning_effort"),
    },
}
RESUMES = re.compile(r"""(?:["'\s]-r["'\s]|--resume\b|--continue\b)""")


def iter_files(roots: list[Path]):
    for root in roots:
        if root.is_file():
            yield root
            continue
        skills_root = root == HOME / "Projects/skills"
        for directory, subdirs, names in os.walk(root):
            subdirs[:] = sorted(name for name in subdirs if name not in SKIP_DIRS and not name.startswith("."))
            folder = Path(directory)
            if skills_root and "scripts" not in folder.relative_to(root).parts:
                continue
            for name in sorted(names):
                path = folder / name
                if path.suffix not in TEXT_SUFFIXES or name.startswith("test_") or path.is_symlink():
                    continue
                if path.resolve() != Path(__file__).resolve():
                    yield path


def python_launches(text: str, lines: list[str]):
    """(kind, line, enclosing function source) for each argv list that starts a CLI; docstrings do not count."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return
    scopes = [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)) or len(node.elts) < 2:
            continue
        head, second = node.elts[0], node.elts[1]
        if not isinstance(second, ast.Constant):
            continue
        first_word = head.value if isinstance(head, ast.Constant) else getattr(head, "id", None)
        if first_word == "claude" and second.value in ("-p", "--print"):
            kind = "claude"
        elif first_word in ("codex", "binary") and second.value == "exec":
            kind = "codex"
        else:
            continue
        inside = [scope for scope in scopes if scope[0] <= node.lineno <= scope[1]]
        first, last = max(inside) if inside else (node.lineno, node.end_lineno or node.lineno)  # innermost
        yield kind, node.lineno, "\n".join(lines[first - 1:last])


def shell_launches(lines: list[str]):
    """(kind, first line, last line) for each command line that runs the CLI itself; quoted mentions do not count."""
    index = 0
    while index < len(lines):
        start = index
        logical = lines[index]
        while logical.rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            logical = logical.rstrip()[:-1] + " " + lines[index]
        index += 1
        if logical.lstrip().startswith("#"):
            continue
        try:
            tokens = shlex.split(logical, comments=True, posix=True)
        except ValueError:
            continue
        for position, token in enumerate(tokens):
            rest = tokens[position + 1:]
            if token == "codex" and rest[:1] == ["exec"]:
                yield "codex", start, index - 1
            elif token == "claude" and any(flag in rest for flag in ("-p", "--print")):
                yield "claude", start, index - 1


def audit_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    if not (CLI_NAME.search(text) and HEADLESS_WORD.search(text)):
        return []
    lines = text.splitlines()
    launches: list[tuple[str, int, str]] = []  # kind, 1-based line, text holding its flags

    if path.suffix == ".py":
        launches.extend(python_launches(text, lines))
    else:
        # Python embedded in a shell heredoc: the argv list and the dozen lines after it.
        for match in LIST_LAUNCH.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            scope = "\n".join(lines[line_no - 1:line_no + 12])
            launches.append(("claude" if match["claude"] else "codex", line_no, scope))
        for kind, first, last in shell_launches(lines):
            scope = "\n".join(lines[first:last + 1])
            for array in set(ARRAY_REF.findall(scope)):
                scope += "\n" + "\n".join(line for line in lines if re.search(rf"\b{array}\+?=\(", line))
            launches.append((kind, first + 1, scope))

    problems = []
    for kind, line_no, scope in launches:
        if WAIVER in scope:
            continue
        missing = [name for name, pattern in FLAGS[kind].items() if not pattern.search(scope)]
        if kind == "claude" and RESUMES.search(scope) and "model" in missing:
            missing.remove("model")
        if missing:
            problems.append(f"{path}:{line_no}  {kind} launch names no {' or '.join(missing)}")
    return problems


def audit_agent(path: Path) -> list[str]:
    """An agent definition's frontmatter names a model (not `inherit`) and an effort."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path}:1  agent definition has no frontmatter"]
    front = text[4:].split("\n---", 1)[0]
    fields = dict(re.findall(r"(?m)^(model|effort):\s*(\S+)", front))
    missing = [name for name in ("model", "effort") if fields.get(name) in (None, "inherit")]
    return [f"{path}:1  agent definition names no {' or '.join(missing)}"] if missing else []


def audit(roots: list[Path], agent_dirs: list[Path] = ()) -> tuple[int, list[str]]:
    files, problems = 0, []
    for path in iter_files(roots):
        files += 1
        problems.extend(audit_file(path))
    for directory in agent_dirs:
        for path in sorted(directory.glob("*.md")):
            files += 1
            problems.extend(audit_agent(path))
    return files, sorted(set(problems))


def main() -> int:
    given = [Path(arg).expanduser() for arg in sys.argv[1:]]
    files, problems = audit(given or DEFAULT_ROOTS, [] if given else AGENT_DIRS)
    if problems:
        print(f"headless-pin-audit: {len(problems)} launch(es) inherit a saved default ({files} files scanned):")
        print("\n".join(problems))
        return 1
    print(f"headless-pin-audit: {files} files scanned, every headless launch and agent definition names its model and effort")
    return 0


if __name__ == "__main__":
    sys.exit(main())
