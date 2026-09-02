"""`--apply-verdicts` moves MOOT/SUPERSEDED items out of the drainable stores, labeled.

Steward proposals are not git-tracked, so the stamp at the top of the moved file is the
only provenance; decisions-pending files are unlinked (git history is that dir's record).
STILL-VALID items and refs outside the two stores are never touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import questions_drain as qd  # noqa: E402


def _memo(steward: Path, pending: Path, other: Path) -> str:
    return f"""# Stale-question drain — 2026-09-02

_intro_

## Proposal already shipped
- ref: `{steward / 'a.md'}` · created 2026-06-15 (79d)
- scout: ok=True wall=92s tok(in/out/reason)=1/2/3

VERDICT: MOOT
EVIDENCE: 56c24f7 repointed the hook.
RECOMMENDED: resolve-moot — implemented.

## Pending decision overtaken
- ref: `{pending / 'b.md'}` · created 2026-07-15 (49d)
- scout: ok=True wall=100s tok(in/out/reason)=1/2/3

VERDICT: SUPERSEDED
EVIDENCE: b765a98 implemented B.
RECOMMENDED: resolve-superseded

## Still a live problem
- ref: `{steward / 'c.md'}` · created 2026-06-20 (74d)
- scout: ok=True wall=50s tok(in/out/reason)=1/2/3

VERDICT: STILL-VALID
EVIDENCE: nothing changed.
RECOMMENDED: keep

## Lives elsewhere
- ref: `{other / 'd.md'}` · created 2026-06-20 (74d)
- scout: ok=True wall=50s tok(in/out/reason)=1/2/3

VERDICT: MOOT
EVIDENCE: whatever.
RECOMMENDED: resolve-moot

## Token cost
- scouts: 4 · out_tok: 8 · reason_tok: 12 · wall_sum: 292s
"""


def test_apply_verdicts_moves_closed_items_and_keeps_the_rest(tmp_path) -> None:  # noqa: ANN001
    steward, pending, other = tmp_path / "steward", tmp_path / "pending", tmp_path / "other"
    for d in (steward, pending, other):
        d.mkdir()
    (steward / "a.md").write_text("# Steward proposal: shipped\n\nbody a\n")
    (steward / "c.md").write_text("# Steward proposal: live\n\nbody c\n")
    (pending / "b.md").write_text("# Pending\n\nbody b\n")
    (other / "d.md").write_text("# Elsewhere\n")
    memo = tmp_path / "memo.md"
    memo.write_text(_memo(steward, pending, other))

    preview = qd.apply_verdicts(memo, steward_dir=steward, pending_dir=pending, dry_run=True)
    assert [i["prompt"] for i in preview["resolved"]] == ["Proposal already shipped"]
    assert [i["prompt"] for i in preview["deleted"]] == ["Pending decision overtaken"]
    assert (steward / "a.md").exists() and (pending / "b.md").exists()  # dry run moved nothing
    assert "Dispositions applied" not in memo.read_text()

    res = qd.apply_verdicts(memo, steward_dir=steward, pending_dir=pending)
    assert len(res["resolved"]) == 1 and len(res["deleted"]) == 1
    assert [i["prompt"] for i in res["kept"]] == ["Still a live problem"]
    assert [i["why"] for i in res["manual"]] == ["ref outside the two drainable stores"]

    moved = steward / "resolved" / "a.md"
    assert not (steward / "a.md").exists() and moved.exists()
    text = moved.read_text()
    assert text.startswith("> **MOOT** — resolved ")
    assert "56c24f7 repointed the hook." in text and text.endswith("body a\n")
    assert not (pending / "b.md").exists()
    assert (steward / "c.md").exists() and (other / "d.md").exists()
    assert "## Dispositions applied" in memo.read_text()
    assert "- resolved: 1" in memo.read_text()
