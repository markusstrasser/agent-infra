# Git Commands Before Reading Code

**Source:** Ally Piechowski, "The Git Commands I Run Before Reading Any Code" (2026-04-08)
**URL:** workwithme.dev blog
**Status:** Implemented — `just churn-hotspots`, `just bug-hotspots`, `just velocity`

## Five Diagnostic Commands

### 1. Churn Hotspots (most-changed files)

```bash
git log --format=format: --name-only --since="1 year ago" | sort | uniq -c | sort -nr | head -20
```

High churn + nobody wants to own it = codebase drag. Cross-reference with bug hotspots — files appearing on both lists are highest risk. A 2005 Microsoft Research study found churn-based metrics predicted defects more reliably than complexity metrics alone.

### 2. Bus Factor (contributor concentration)

```bash
git shortlog -sn --no-merges
```

One person at 60%+ = bus factor risk. Compare overall vs 6-month window — if the top contributor disappeared, flag immediately. Caveat: squash-merge workflows compress authorship (reflects merger, not author).

### 3. Bug Clustering by File

```bash
git log -i -E --grep="fix|bug|broken" --name-only --format='' | sort | uniq -c | sort -nr | head -20
```

Depends on commit message discipline. Files on both churn AND bug lists = keep breaking, keep getting patched, never properly fixed.

### 4. Velocity Shape (commits per month)

```bash
git log --format='%ad' --date=format:'%Y-%m' | sort | uniq -c
```

Steady = healthy. Half-drop in single month = someone left. Declining 6-12mo curve = losing momentum. Periodic spikes = batched releases. This is team data, not code data.

### 5. Crisis Patterns (reverts/hotfixes)

```bash
git log --oneline --since="1 year ago" | grep -iE 'revert|hotfix|emergency|rollback'
```

A handful/year is normal. Every couple weeks = team doesn't trust deploy process. Zero = either stable or bad commit messages.

## Key Insight

The churn-bug overlap is the most actionable signal: a file that changes constantly AND keeps showing up in fix commits is the single biggest risk in the codebase. Two minutes of git commands beats hours of reading code to find where to look first.

## Implementation

Three of five commands added as cross-repo `just` recipes (2026-04-08):
- `just churn-hotspots` — file-level churn across 5 repos
- `just bug-hotspots` — fix-commit file clustering across 5 repos
- `just velocity` — commits-per-month shape across 5 repos

Bus factor skipped (single operator + agents). Crisis patterns already covered by `agent_maintainability.py` revert tracking.

<!-- knowledge-index
generated: 2026-04-08T19:21:35Z
hash: e22261bd6367


end-knowledge-index -->
