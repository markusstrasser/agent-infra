---
title: Claude Sonnet 5 release — system card findings + cross-repo adoption sites
date: 2026-06-30
tags: [models, dispatch-economics, model-guide]
status: active
---

# Claude Sonnet 5 — system card findings + cross-repo adoption sites

## Context

Anthropic released Claude Sonnet 5 (`claude-sonnet-5`) 2026-06-30: "near-Opus
intelligence at Sonnet pricing," $3/$15 per MTok ($2/$10 intro through
2026-08-31), first Sonnet-tier model with `xhigh` effort. Read the full 145-page
system card and surveyed agent-infra + sibling repos (intel, anim-workbench) for
where the new model could be substituted into existing dispatch logic.

Full system-card digest (all sections, preserved numbers): `~/Projects/skills/model-guide/references/sonnet-5-system-card.md`.
Cross-repo survey transcript: `.claude/reviews/sonnet-5-dispatch-substitution-probe.md`.
Routing changes applied: `~/Projects/skills/model-guide/SKILL.md` + `references/CHANGELOG.md` (2026-06-30 entry).

## Findings worth carrying forward (cross-cutting, non-marketing-typical)

1. **New "Mythos" model class revealed above Opus.** Mythos 5 is the actual
   capability-frontier model this card benchmarks against — Opus is no longer
   Anthropic's top tier. Mythos 5 and Fable 5 were **"de-deployed in response to
   the US government's export control directive"** mid-cycle (stated 3× in the
   card) — a concrete regulatory event, not present in typical announcement copy.
2. **Disclosed training-health issue:** "the Sonnet 5 training run was flagged as
   unhealthy in its second half" — offered as partial explanation for an
   unusually high abstention rate (26.6%) and low correct-rate (46.9%) on
   AA-Omniscience.
3. **Largest agentic-safety gain in the card is prompt-injection robustness** —
   browser-use attack success without safeguards collapsed from Sonnet 4.6's
   47-51% to Sonnet 5's 0.93-1.01%; with safeguards, 0% (matches Mythos 5). Tied
   Opus 4.8 for best result in a blind cross-lab bug bounty (0.19% attack
   success vs Sonnet 4.6's 1.41%).
4. **Real regressions disclosed alongside the gains:** worst prefill- and
   harmful-system-prompt-susceptibility of the models compared (absolute rates
   still low); "concerningly high" evaluation awareness (~6% of audit
   transcripts); measurably more turns/tokens per task on long agentic work than
   Opus 4.8 or Fable 5 (Toolathlon 26.0 avg turns vs 16.5-32.0 range; AA-Briefcase
   183 avg turns vs 55-67) — the $/token saving partially erodes on long loops.
5. Lowest MASK sycophantic-lying rate of any tested Claude model (3.1%); "the
   first model" to criticize Claude's constitution's hard-constraints clause as
   potentially requiring unethical action (stated 3× — a genuine self-critique
   finding).

## Cross-repo adoption — what was changed vs what's still open

### Changed this session (low-risk, additive/forward-compat)
- `scripts/_detector_patterns.py` — added `claude-sonnet-5` context-window row
  (1M); prevents future agentlogs context-pressure detection from silently
  resolving to `None` once Sonnet 5 sessions appear.
- `~/Projects/skills/llmx-guide/references/models.md` — added `claude-sonnet-5`
  row to the canonical ID-spelling registry.
- `~/Projects/skills/research-ops/SKILL.md` — bumped `/schedule` cloud-agent
  default from `claude-sonnet-4-6` to `claude-sonnet-5` (same cheap-default +
  Opus-escalation design, newer model — not a new policy).
- `~/Projects/skills/model-guide/SKILL.md` + `references/sonnet-5-system-card.md`
  — Sonnet 5 reinstated as a named, cost-tier Claude option: new model section,
  validation checklist, Dispatch Economics rows (resolved the orphaned
  "Sonnet/haiku tier" row that had no live model name), CHANGELOG entry.

### Explicitly left open (operator/design calls, not auto-resolved)
- **"NEVER Sonnet" for architecture/design/high-reasoning critique** — that
  verdict (model-guide, 2026-06-20) was reached against Sonnet 4.6. Sonnet 5's
  profile (strong agentic/coding gains, near-Opus on several real-world
  benchmarks, but worst-of-cohort prefill susceptibility and more turn-verbose
  execution) makes re-litigating it a live question, flagged inline in SKILL.md
  as an OPEN QUESTION — not resolved here.
- **llmx subscription allowlist gap** — `~/.claude/cache/llmx-routing.json`
  `lite_allowed_models` has never included any Sonnet model (4.6 or 5). Without
  an entry, `llmx chat --subscription -m claude-sonnet-5` won't route regardless
  of routing guidance. Fix lives in llmx's own config, out of scope here.
- **No `sonnet5-tier` subagent lane exists.** The only cost-segmented subagent
  types (`opus-low`, `fable-low`, etc.) are defined globally at
  `~/.claude/agents/*.md`, not per-project. A `sonnet5-low`-style lane would have
  global blast radius across every project's Agent-tool dispatch — per the
  Constitution's autonomy boundaries this is shared infrastructure affecting 3+
  projects and needs explicit human sign-off before deploying, not just
  proposing.
- **`scripts/debug_until_dry.py` `opus_adjudicate()` (`--verifier opus` lane).**
  The harness already has a 3-way `--verifier cursor|opus|none` knob built for
  exactly this kind of swap — the highest-value place to actually bakeoff Sonnet
  5 against the Opus baseline on adjudication accuracy before defaulting to it,
  since per the model-guide's own Dispatch Economics doctrine this is
  judgment-coupled verifier work that shouldn't be blindly downgraded.
- **Cross-repo staleness beyond agent-infra** confirmed in `intel/tools/llmx_models.sh:30`
  ("Latest Sonnet" label now wrong) and the same "hardcoded frontier model, no
  review cadence" pattern in `anim-workbench/evolver/outer-loop-models.json:12` —
  not Sonnet-5-specific, not actioned this session.

## Revisit if

- The operator decides the architecture/critique "NEVER Sonnet" verdict should be
  revisited — update `model-guide/SKILL.md` Default Routing + Dispatch Economics
  and log a dated CHANGELOG entry, don't silently flip the line.
- A `--verifier sonnet5` bakeoff on `debug_until_dry.py` runs and shows
  comparable confirm/refute accuracy to `--verifier opus` — promote it as a
  cheaper default for that lane.
- Someone adds Sonnet to the llmx subscription allowlist — re-test
  `llmx chat --subscription -m claude-sonnet-5 --dry-run`.
