# Autoresearch: Skill Routing

You are optimizing the deterministic skill-routing scorer in
`../../scripts/skill-routing.py`.

## Goal

Maximize `accuracy` on the stress and holdout case files. A case passes when
the expected visible skill is ranked first, and when any expected planned
module/lens/reference is ranked first.

The primary eval is the locked aggregate suite:

- canonical cross-project cases in `../../schemas/skill-routing-cases.json`
- stress cases in `stress_cases.json`
- holdout cases in `holdout_cases.json`

Any kept patch must also pass holdout and stress checks. Do not optimize one
split at the expense of another.

## Editable Surface

- `../../scripts/skill-routing.py`

Do not modify case files, manifest generation, or skill docs. The point is to
improve the routing scorer, not the labels.

## Useful Direction

The current scorer does well on common workflow names but can miss reference
skills whose names appear as exact technical terms, such as `llmx-guide`.
Good changes usually improve exact name matching, hyphenated-token matching,
and reference-skill handling without breaking workflow routing.

## Rules

- Make one focused scorer change per experiment.
- Prefer small scoring improvements over new architecture.
- Keep deterministic behavior.
- Do not install packages.
- Do not special-case only one fixture id; use prompt/object metadata signals
  that generalize.
