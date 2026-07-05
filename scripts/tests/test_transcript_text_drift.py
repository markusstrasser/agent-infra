"""Drift-test: skills' vendored transcript reader == canonical common.transcript_text.

skills/improve/scripts/extract_user_tags.py can't import agent-infra's
scripts/common (different repo), so it vendors the same semantics. Epistemic
principle #9: a vendored copy of a correctness invariant is allowed ONLY
behind a drift-test asserting equality. If this fails, fix BOTH to match —
divergence here means two miners disagree on what counts as user text.
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.transcript_text import user_texts

SKILLS_COPY = (
    Path.home() / "Projects" / "skills" / "improve" / "scripts" / "extract_user_tags.py"
)


def _load_skills_module():
    spec = importlib.util.spec_from_file_location("extract_user_tags", SKILLS_COPY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FIXTURES = [
    # (label, transcript line obj)
    ("envelope-str", {"type": "user", "message": {"role": "user", "content": "plain #f text"}}),
    (
        "envelope-blocks",
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "real feedback"},
                    {"type": "tool_result", "content": "not user text"},
                ],
            },
        },
    ),
    ("legacy-flat", {"role": "user", "content": "flat form"}),
    ("assistant", {"type": "assistant", "message": {"role": "assistant", "content": "no"}}),
    (
        "compact-summary",
        {
            "type": "user",
            "isCompactSummary": True,
            "message": {"role": "user", "content": "This session is being continued ... #f"},
        },
    ),
    (
        "meta-injected",
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "skill body #g"}},
    ),
    ("empty", {"type": "user", "message": {"role": "user", "content": ""}}),
    ("weird-content", {"type": "user", "message": {"role": "user", "content": 42}}),
]


def test_vendored_reader_matches_canonical():
    assert SKILLS_COPY.exists(), f"skills copy moved? {SKILLS_COPY}"
    skills = _load_skills_module()
    for label, obj in FIXTURES:
        assert skills._message_texts(obj) == user_texts(obj), (
            f"drift on fixture {label!r}: skills._message_texts != common.transcript_text.user_texts"
        )
