"""Portable URIs for cross-repo references.

Two URI schemes:

  corpus://<source_id>/<sub-path>         → ~/Projects/corpus/<source_id>/<sub-path>
  project-root://<project>/<sub-path>     → ~/Projects/<project>/<sub-path>

Per-repo verdict shorthand:
  genomics://verdicts/<verdict_id>        → equivalent to project-root://genomics/...

Goals: outputs referenced by annotation records SHOULD use these schemes (not
absolute filesystem paths) so a corpus dump moves between machines without
rewriting paths. The resolver expands schemes to local Path objects.
"""
from __future__ import annotations

import os
from pathlib import Path

KNOWN_PROJECT_SCHEMES = {
    "genomics", "phenome", "intel", "agent-infra", "research-mcp",
}


def _projects_root() -> Path:
    return Path(os.environ.get("PROJECTS_ROOT", str(Path.home() / "Projects")))


def _corpus_root() -> Path:
    return Path(
        os.environ.get("CORPUS_ROOT", str(_projects_root() / "corpus"))
    )


def _split(uri: str) -> tuple[str, str]:
    if "://" not in uri:
        raise ValueError(f"not a URI: {uri!r}")
    scheme, rest = uri.split("://", 1)
    return scheme, rest


def resolve(uri: str) -> Path:
    """Expand a corpus:// / project-root:// / repo:// URI to a local Path.

    No filesystem check — caller decides whether existence matters.
    """
    scheme, rest = _split(uri)
    if scheme == "corpus":
        return _corpus_root() / rest
    if scheme == "project-root":
        return _projects_root() / rest
    if scheme in KNOWN_PROJECT_SCHEMES:
        return _projects_root() / scheme / rest
    raise ValueError(
        f"unknown URI scheme {scheme!r} (expected corpus, project-root, or one of {sorted(KNOWN_PROJECT_SCHEMES)})"
    )


def make_corpus_uri(source_id: str, *parts: str) -> str:
    if not source_id:
        raise ValueError("source_id required")
    suffix = "/".join(parts).lstrip("/")
    return f"corpus://{source_id}" + (f"/{suffix}" if suffix else "")


def make_project_uri(project: str, *parts: str) -> str:
    if not project:
        raise ValueError("project required")
    suffix = "/".join(parts).lstrip("/")
    return f"project-root://{project}" + (f"/{suffix}" if suffix else "")


def make_repo_uri(repo: str, *parts: str) -> str:
    """Compact `<repo>://<sub-path>` form (used in annotation output_uri).

    Equivalent to project-root://<repo>/<sub-path> after resolution.
    """
    if repo not in KNOWN_PROJECT_SCHEMES:
        raise ValueError(f"unknown repo {repo!r}")
    suffix = "/".join(parts).lstrip("/")
    return f"{repo}://" + suffix
