# Dispatch Brief-Schema (tool-protocol contract)

The shared output contract for the `just`-fronted dispatch verbs (`gather`,
`critique`, and the verbs that follow). Every dispatch recipe ends by emitting
these five lines so an orchestrator (or a headless subagent) can act on the
result without re-reading the whole packet.

```
gathered: <sources actually covered>
missing:  <what was NOT reached + honest caveats>
findings: <engine output, or "context-only" before the engine runs>
drill:    just <verb> <path> --json     (the machine-readable form)
next:     just <verb> <path>            (the next verb in the lane)
```

## Why these five fields

| Field | Answers | Failure it prevents |
|---|---|---|
| `gathered` | what context the verb assembled | silent under-coverage read as "complete" |
| `missing` | what it could NOT reach | premise-blindness (the packet-only 0-for-5) |
| `findings` | the engine's verdict | burying the result in prose |
| `drill` | how to get the structured form | forcing a re-run to get JSON |
| `next` | the next lane step | orchestrator guessing the pipeline |

`missing` is load-bearing: an honest non-empty `missing` is the signal the
deterministic gather has hit its ceiling (per the plan's expand gate). A verb
that never reports `missing` is lying about coverage, not achieving it.

## Lanes (where outputs go)

```
gather  → .model-review/<slug>-context.md   + <slug>-coverage.json   (read-only assembly)
critique→ .model-review/findings.json       + per-axis files          (engine dispatch)
write   → worktree → diff → `just code-review` on the diff → merge     (mutation path)
```

`--json` is the machine lane on every verb; bare invocation prints the
human/agent-readable brief. Flags after the path are `*args`-forwarded to the
engine's argparse — `just` itself does not parse them.

## Status

Phase 1 of `.claude/plans/2026-06-16-just-cli-dispatch-unification.md`.
`gather`/`critique` implement this; `code-review`/`rsi` adopt it when they
graduate from skill to recipe (Phase 3, gated on Phase-2 measurement).
