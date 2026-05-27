---
title: continueOnBlock probe — measurement anchor
date: 2026-05-27
status: probe live (commits bcafcc6 + settings edits)
parent: research/2026-05-27-continueonblock-probe.md
---

# continueOnBlock Probe — Measurement Anchor

## What's live

| Hook | Settings change | Hook change | Effective |
|---|---|---|---|
| `posttool-bash-failure-loop.sh` | `continueOnBlock: true` added to `~/.claude/settings.json:289` | exit 2 + stderr (skills `bcafcc6`) | 2026-05-27 |
| `posttool-dup-read.sh` | `continueOnBlock: true` added to `~/.claude/settings.json:330` | no change — already exit 2 + stderr | 2026-05-27 |

Both PostToolUse hooks. With `continueOnBlock:true`, the stderr from exit-2 is fed back into the model's same turn instead of ending the turn.

## Why two targets

Original proposal picked `bash-failure-loop` as the conversion target. Baseline check (`~/.claude/hook-triggers.jsonl`, 96,370 entries spanning 3+ months) revealed it has fired **1 time total** — near-zero observability. Pivoted by also enabling continueOnBlock on `dup-read`, which has **9,168 lifetime fires** and is already architected for exit-2+stderr.

`bash-failure-loop` change stays: it's harmless (no-op until threshold), and the code path is now correct if/when 5+ consecutive Bash failures recur.

## Baseline (last 30 days, from `~/.claude/hook-triggers.jsonl`)

| Hook | 30d fires | per-day |
|---|---|---|
| `bash-failure-loop` | 0 | 0.0 |
| `dup-read` | (high — pull below) | ~10s/day |

Re-derive any time with:

```bash
python3 -c "
import json, time
from datetime import datetime
cutoff = time.time() - 30*86400
hooks = {'bash-failure-loop': 0, 'dup-read': 0}
with open('/Users/alien/.claude/hook-triggers.jsonl', 'rb') as f:
    for raw in f:
        try:
            e = json.loads(raw.decode('utf-8', errors='replace'))
            h = e.get('hook')
            if h not in hooks: continue
            ts = e.get('ts', 0)
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z','+00:00')).timestamp()
            if ts >= cutoff: hooks[h] += 1
        except: pass
for h, n in hooks.items():
    print(f'{h}: {n} fires/30d ({n/30:.1f}/day)')
"
```

## What to measure

The continueOnBlock hypothesis is: agent receives corrective stderr in-turn → fewer wasted turns recovering from blocked operations. Concretely, after a dup-read block, does the agent:

- (a) immediately switch to Grep / different offset (good — corrective signal landed), OR
- (b) retry the same Read with same args next turn (bad — block didn't change behavior, just delayed it), OR
- (c) abandon the read goal entirely (neutral — but possibly losing info)

The trigger log records `action="block"` per fire. Pair with `~/.claude/session-receipts.jsonl` (turn counts) and the JSONL session transcripts (`~/.claude/projects/<project>/<session>.jsonl`) to detect what the agent did in the turn immediately after a block.

## Re-measure after 14 days (suggested: 2026-06-10)

```bash
# Same query as baseline, plus: examine session transcripts for next-tool-after-block
# Concrete check: for each bash-failure-loop or dup-read block fire after 2026-05-27,
# what tool did the agent call next? Same file/cmd or different?
```

If `dup-read` blocks are followed by Grep calls more often after the flip than before → continueOnBlock improved in-turn recovery. If no difference → revert by removing `continueOnBlock: true` from the two settings entries; hook scripts can stay (still correct).

## Revert recipe

Remove the two `"continueOnBlock": true` lines from `~/.claude/settings.json` (search for "continueOnBlock"). For the bash-failure-loop hook script, revert skills `bcafcc6` if desired:

```bash
git -C ~/Projects/skills revert bcafcc6
```

## Decision criteria

- **Adopt** if dup-read post-block next-tool changes to Grep/offset/different-file in ≥70% of cases (vs current baseline behavior).
- **Revert** if next-tool is unchanged from pre-flip behavior OR if the in-turn rejection causes new loop pathologies.
- **Iterate** if mixed — try lowering dup-read BLOCK_THRESHOLD from 6 to 4 (earlier intervention).

<!-- knowledge-index
generated: 2026-05-27T11:08:54Z
hash: a4eac6b7a84b

index:title: continueOnBlock probe — measurement anchor
index:status: probe live (commits bcafcc6 + settings edits)
cross_refs: research/2026-05-27-continueonblock-probe.md

end-knowledge-index -->
