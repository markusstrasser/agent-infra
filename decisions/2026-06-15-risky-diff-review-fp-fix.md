---
date: 2026-06-15
concept: writer-reviewer-separation / risky-diff-review
decision: FP-fix the shadow detector; do NOT promote to an enforce-gate (iatrogenic + scope-wrong)
relations:
  resolves: improvement-log "[2026-06-07] SHADOW: risky-diff-review demand probe"
  supersedes: one-shot launchd com.agent-infra.risky-diff-review (2026-06-21 promote/cut scan)
  evidence: this session (item_analysis + llmx bugs caught by blind review)
provenance: operator "do 1-3" (session retro); ground-truth from the 30d scan data
blast_radius: local
---

# Risky-diff-review: FP-fix, not enforce-gate

## The promote call was made early, and the data redirected it

The operator promoted risky-diff-review (writer/reviewer separation) from SHADOW. The
pre-registered criterion was "promote to an auto-review trigger only if it fires often AND
unreviewed-risky commits correlate with later fixes." Pulling the actual 30-day data before
acting (probe-before-build) **falsified the naive promotion**:

- The detector flagged **49/140** commits as unreviewed-risky — but ~80% are FALSE POSITIVES:
  governance-PROSE edits (`CLAUDE.md`/`GOALS.md`/`.claude/rules/*.md`) and `[wip]`
  auto-checkpoints. Those are human-gated governance / mechanical commits, not code with a
  latent bug a blind review catches.
- Flipping that to an enforce-gate would nudge on nearly every doc edit = textbook iatrogenic
  noise, which the operator explicitly ruled out ("no iatrogenic harm").

## What changed belief

A blind code review (fresh-eyes / critique) catches LOGIC bugs in **code/enforcement** files;
governance **prose** has a different failure mode (is-this-rule-wise, already human-gated by the
constitution). Conflating the two is the FP. So the trigger must be code-scoped.

## Acted (strictly-better, non-iatrogenic)

`scripts/risky_diff_review_shadow.py`: the code-review trigger now fires ONLY on unreviewed
CODE/enforcement diffs (`hook`/`schema`/`settings`), drops PROSE → `PROSE_ONLY` and `[wip]` →
excluded. **49 noisy → 11 genuine.** `REVIEW_WORTHY`/`PROSE_ONLY` split, drift-test updated (4/4).

## Did NOT do, and why (the real next iteration — needs its own probe)

The enforce-gate is **deferred, not shipped.** The detector's scope (agent-infra governance
paths) MISSES the demand this session actually demonstrated: unreviewed new **CODE-LOGIC,
cross-repo**. The two real bugs this session — item_analysis stat logic (`3a239bc`) and llmx
routing (`a91f0f1`) — were committed unreviewed in `skills`/`llmx`, caught only because blind
review happened to run, and needed fix commits (`cca807e`, `64f51ed`). That correlation IS the
promote signal — but a gate that catches it must be **cross-repo + logic-aware + FP-controlled +
probed**. A rushed broad gate false-positives on every new function. Building it without a probe
is exactly the iatrogenic move the operator forbade. So: scoped as the next iteration, with a
probe-before-build requirement, not shipped today.

## Rejected
- **Flip the existing shadow to enforce** — 80% FP + scope-wrong (would not have caught this
  session's bugs). Theater that adds noise.
- **Ship a broad cross-repo new-logic gate now** — unbounded FP risk without a probe.
