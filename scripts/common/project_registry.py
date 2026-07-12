"""Shared project registries for cross-repo agent-infra checks."""

from __future__ import annotations


MIRRORED_REPOS = (
    "agent-infra", "intel", "genomics", "phenome", "publishing",
    "personal", "substrate", "imagegen", "ext", "arc-agi",
)
SKILL_REPOS = ("skills", *MIRRORED_REPOS)
