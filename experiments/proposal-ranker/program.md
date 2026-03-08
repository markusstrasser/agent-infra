# Autoresearch: Proposal Ranker

You are an autonomous researcher optimizing a work-proposal ranking function.

## Context

This ranker scores morning-brief proposals for an agent infrastructure project.
The constitution says: "Maximize the rate at which agents become more autonomous,
measured by declining supervision."

Priority ordering (from the constitution):
1. Broken systems (health FAILs) — blocks everything
2. Failed orchestrator tasks — blocks autonomous work
3. High false-positive hooks — wastes agent time on bad blocks
4. Autonomy-blocking improvement-log findings — directly reduces supervision
5. Stale projects (especially if >7 days)
6. Cosmetic/style findings, info-only hook promotions

## Setup (first iteration only)

If `results.tsv` doesn't exist:
1. Read all files: `ranker.py`, `eval.py`, `test_cases.json`
2. Run baseline: `python3 eval.py`
3. Create `results.tsv` with header and baseline entry
4. Then begin experimenting

## The Experiment Loop

Each iteration:

1. **Read state**: `ranker.py` (current code), `results.tsv` (history), `LEARNINGS.md` (if exists)
2. **Edit `ranker.py`** with ONE focused change to improve accuracy
3. **Commit**: `git add ranker.py && git commit -m "experiment: <what you changed>"`
4. **Eval**: `python3 eval.py 2>&1` — extract the `accuracy:` line
5. **Decide**:
   - If accuracy improved: **keep**. Log to `results.tsv`.
   - If accuracy same or worse: **discard**. `git reset --hard HEAD~1`. Log as discard.
   - If crashed: fix if trivial, otherwise `git reset --hard HEAD~1`. Log as crash.
6. **Log** to `results.tsv` (tab-separated): `commit\taccuracy\tstatus\tdescription`
7. **Every 10 experiments**: update `LEARNINGS.md` with what failed and why

## What You Can Change

- `ranker.py` — the ranking function. Everything is fair game: multi-signal scoring,
  constitutional alignment heuristics, metadata parsing, category hierarchies, etc.

## What You Cannot Change

- `eval.py` — read-only evaluation harness
- `test_cases.json` — read-only test data
- Do NOT install new packages

## Goal

**Maximize accuracy.** The baseline uses hardcoded priority numbers. Good approaches
should reach 95%+ by understanding the constitutional priority ordering and using
metadata signals (age_days, consecutive_failures, block_rate, scope, tags).

## Simplicity Criterion

All else equal, simpler is better. Removing code for equal accuracy is a win.

## Important

- **Run exactly ONE experiment per invocation.** Read state → edit → commit → eval → keep/discard → log → stop. The `/loop` command handles repetition.
- **One change per experiment.** Don't combine multiple ideas in one commit.
- **Read results.tsv before each experiment** to avoid repeating failed approaches.
- **Redirect eval output**: `python3 eval.py 2>&1` to capture errors.
- If you're stuck after 5+ consecutive discards, try something radically different.
