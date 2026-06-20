# Our system (for integration mapping)

A SINGLE-OPERATOR LOCAL agent harness over Claude Code + Codex CLI + Cursor. NOT a hosted
multi-agent service. $0 subscription dispatch. The relevant surfaces a paper might integrate into:

- **act-drain / blindspot loop** — daily zero-LLM job mines session corrections the human had to
  make, classifies them (GROW_COVERAGE / RAISE_AUTONOMY / REDUCE_ERROR), and proposes rules/hooks.
  Measured failure mode: **accretion** (rules/hooks grow monotonically → "policy maze"). Measured
  blindspot: **over_caution=63 / over-ask** (agent asks when it should act).
- **session-trace / agentlogs.db** — cross-vendor SQLite of sessions/runs/tool_calls; we replay
  raw transcripts for forensics. emb-over-agentlogs gives semantic search (R@5 ≈ SOTA).
- **skills / rules / hooks** — skills (procedures), rules (.claude/rules, auto-loaded or path-scoped),
  hooks (deterministic pre/post-tool gates). Currently FLAT lists.
- **MEMORY** — append-only condensed lessons; we keep raw agentlogs but the LINK from condensed→raw
  is not first-class.
- **/eval + ~/Projects/evals** — our eval home; we believe "harness on a frozen model" is the lever
  (verifier-gated autonomy). We measure token cost as a first-class axis.
- **predict-then-falsify gate** (planned) — pre-register the metric a harness edit should move;
  accept only if the trace shows the intended mechanism fired; else revert.
- **Workflow tool / file-bus just recipes** — our two orchestration engines (fan-out, pipeline,
  loop-until-dry, journal resume). Single-writer-many-readers.
- **deferred tools / ToolSearch** — large tool surface loaded lazily by query.

Integration = a CONCRETE bolt-on to one of these surfaces. We do NOT adopt frameworks as deps; we
pattern-extract mechanisms. Reject anything that requires a hosted runtime / server / DB stand-up.
