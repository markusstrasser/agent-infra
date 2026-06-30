# Sonnet 5 Dispatch Substitution Probe

PROBE IN PROGRESS

Investigating where claude-sonnet-5 could be substituted into agent-infra's model
dispatch logic (model-guide skill, llmx routing, justfile recipes, subagent types)
to save cost over claude-opus-4-8 without losing quality on non-Opus-tier tasks.

## Step 0: Pricing/model verification (via claude-api skill, cached 2026-06-24)

CONFIRMED:
- Model ID: `claude-sonnet-5` (exact string, no date suffix)
- Pricing: $3/$15 per MTok standard; **$2/$10 per MTok introductory through 2026-08-31** — matches user's claim exactly
- xhigh effort: CONFIRMED — "Claude Sonnet 5 supports the full low/medium/high/xhigh/max range — the first Sonnet-tier model with xhigh"
- vs claude-opus-4-8: $5/$25 per MTok — matches user's claim
- Adaptive thinking on by default (omitting `thinking` runs adaptive, unlike Sonnet 4.6 which ran thinking-off by default)
- New tokenizer: ~30% MORE tokens for same text vs Sonnet 4.6 (cost-relevant: nominal $/token drop is partially offset by more tokens per request)
- High-res vision (2576px long edge), same as Opus 4.7+
- Positioning per migration guide: "near-Opus quality on agentic and coding work at Sonnet cost"

User's pricing/capability claims in the prompt are verified accurate. Proceeding to repo investigation.

## Step 1: model-guide skill (canonical dispatch-economics source)

Files: `/Users/alien/Projects/skills/model-guide/SKILL.md` (symlinked into `~/.claude/skills/model-guide`).
Last updated line says **2026-06-20**. Today is 2026-06-30 (Sonnet 5 release day). **Stale — does not
mention `claude-sonnet-5` anywhere.**

Current stance is not merely "missing Sonnet 5" — it is actively anti-Sonnet:
> "Active stance: This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok, and Sonnet
> routes were removed from active guidance."
> "Architecture / design / high-reasoning critique | Opus 4.8 `max` + GPT-5.5 — **NEVER Sonnet**"

Yet the Dispatch Economics table (line 99) still has a live row recommending Sonnet:
> "Mechanical no-gate tasks (rename sweeps, boilerplate) | **Sonnet/haiku tier**"

This is an internal inconsistency in the skill itself (banner says Sonnet routing was removed; one table
row still routes to "Sonnet tier" with no model ID). Sonnet 5's positioning ("near-Opus on agentic/coding
at Sonnet cost," first Sonnet-tier model with `xhigh`) directly challenges the "NEVER Sonnet" line for
architecture/critique — that verdict was reached when the best Sonnet was 4.6. Re-evaluating it is now a
live question, not a settled one, but the skill gives the agent no current model to even consider.

**Most consequential adjacent finding (not Sonnet-5-specific, but load-bearing for any Sonnet routing
decision):** SKILL.md line 114 documents that the Agent-tool's default subagent model is
`CLAUDE_CODE_SUBAGENT_MODEL`, **observed = `claude-sonnet-4-6`** — i.e. every bare `Agent(...)` dispatch
with no explicit `model:` in this codebase ALREADY silently runs on Sonnet (4.6), not Opus. Grepped for
where this env var is actually set (`CLAUDE_CODE_SUBAGENT_MODEL`) — no setting found anywhere in
agent-infra, `~/.claude/`, or shell rc files; it only appears in `TODOS.md` (an open, unactioned item: "Use
Haiku for search-heavy subagents") and two research memos cataloging the env var's existence. **So the
4.6→5 default-subagent-model upgrade is NOT something agent-infra controls via a setting it owns — it's
whatever Claude Code's harness ships as the default, and the skill doc itself is the only place this
fact is recorded.** Action: re-verify the observed default after Sonnet 5's release (one `Agent()` call +
grep the transcript JSONL for `"model"`, per the skill's own verification recipe) and update this line.

## Step 2: hardcoded Sonnet model-ID references (`claude-sonnet-4-6` / `sonnet-4-6`)

agent-infra:
| File | Line | Context | Verdict |
|---|---|---|---|
| `scripts/repo-summary.py` | 26 | `MODELS["sonnet"] = "claude-sonnet-4-6"` (default model is `haiku`; sonnet is an opt-in `--model sonnet` flag) | Low-stakes — bump string to `claude-sonnet-5`, but this script already defaults to Haiku for cost, so the win is marginal |
| `scripts/_detector_patterns.py` | 136 | `("claude-sonnet-4-6", 1_000_000)` — context-window lookup table for parsing AGENTLOGS session JSONL, not a dispatch site | **Forward-compat gap, not a substitution candidate.** No `claude-sonnet-5` entry exists — once Sonnet 5 sessions start appearing in agentlogs, context-pressure detection will silently fail to resolve (falls through to `None` → flagged `missing_prerequisites`, per the file's own commented invariant). Needs an added row, not a swap. |
| `claim_bench/HANDOFF.md` | 147, 174 | judge/grader model recommendation: "`anthropic/claude-sonnet-4-6` or `google/gemini-3-flash-preview`. Never same-family [as solver]." | Candidate for bump to `claude-sonnet-5` if claim_bench is still active — same reasoning (cheap, different-family judge) applies, just a newer ID |
| `CYCLE.md` | 59 | historical changelog entry, frontmatter override removed 2026-03-25 | Dead history, not actionable |
| `research/*.md` (3 files) | — | citations of the Sonnet 4.6 announcement / pricing tables in archived research memos | Archival, not actionable (append-only per epistemic discipline) |

Skills repo (`~/Projects/skills/`):
| File | Line | Context | Verdict |
|---|---|---|---|
| `research-ops/SKILL.md` | 55 | `/schedule` cloud-agent default: "Default cloud model is `claude-sonnet-4-6`; request Opus if the generation warrants it." | **Clean substitution candidate** — this is a live dispatch default for GitHub-cloud-agent runs, explicitly chosen as the cheap/default tier with Opus as the escalation. Bumping to `claude-sonnet-5` is in-spirit with the existing design (cheap default, Opus on demand) and gets a stronger model at lower-than-Opus cost. |
| `llmx-guide/references/models.md` | 20 | Model-ID registry: `Claude Sonnet 4.6 \| claude-sonnet-4-6 \| Hyphens, not dots` | **Add a `claude-sonnet-5` row** — this is the canonical ID-spelling reference llmx dispatch code consults; missing it risks an agent guessing the wrong hyphenation. |

Sibling repos (intel, anim-workbench, hutter) — confirmed the staleness is NOT agent-infra-specific:
- `intel/tools/llmx_models.sh:30` — `claude-sonnet-4-6  "Latest Sonnet."` (label is now wrong — no longer latest)
- `anim-workbench/evolver/outer-loop-models.json:12` — `"model": "claude-opus-4-8"` (single hardcoded model for the outer loop; not a Sonnet ref, but shows the same "frontier model hardcoded, no review cadence" pattern)
- `phenome`, `genomics`, `research-mcp`: no live dispatch-config hits — only research/audit archive files (out of scope for substitution)

## Step 3: claude-opus-4-8 references that are candidates for downgrade

Surveyed every `claude-opus-4-8` / `opus-4-8` hit in agent-infra outside `research/`/`decisions/` archives
(grep above, ~25 hits). Classification:

**NOT candidates (Opus-tier reasoning genuinely matters, or it's a fixed eval baseline):**
- `scripts/fable_throttle_probe.py:47`, `scripts/behavioral_harness_replay.py:35` — `REFERENCE`/`MODEL` = Opus 4.8 as the **fixed control/reference model for behavioral evals**. Changing this changes what's being measured, not a cost optimization.
- `tests/agentlogs/test_provenance.py`, `tests/test_session_detectors.py` — hardcoded Opus strings are **test fixtures** asserting parser behavior, not dispatch.
- `.claude/skills/skill-authoring/SKILL.md:43` — `model: claude-opus-4-8` is a **documentation example** of skill frontmatter syntax, not an actual dispatch.
- `CLAUDE.md:180` (and the `analysis/agent-entities/claude-code.md` mirror) — `llmx chat --subscription -m claude-opus-4-8` as the **default headless dispatch** for Claude routing policy. This is intentionally Opus per the 2026-06-15 policy decision; not flagged as mechanical/cheap work.

**Genuine candidate found:**
- `scripts/debug_until_dry.py` — `opus_adjudicate()` (the `--verifier opus` lane) calls `claude-opus-4-8` at `effort high` as the **between-wave adjudicator** that confirms/refutes findings surfaced by cheap cursor scouts. The docstring already treats this as optional/swappable (`--verifier cursor|opus|none`). Per the model-guide's OWN Dispatch Economics doctrine ("Partial/noisy verifier... Don't downgrade — frontier model, normal effort"), this is judgment-coupled adjudication work, so a blind swap to Sonnet 5 is NOT a clean win by the skill's existing logic — but Sonnet 5's claimed "near-Opus on agentic/coding" positioning makes it a legitimate **eval candidate**: run a small bakeoff (`--verifier opus` vs a new `--verifier sonnet5` lane) on a shared audit memo and compare confirmed/refuted accuracy before defaulting to it. This is the single highest-value place in agent-infra to actually test Sonnet 5 against the existing Opus baseline, because the harness already has a 3-way `--verifier` knob built for exactly this kind of swap.

**Subagent definitions (`.claude/agents/*.md`):** only 3 files exist in agent-infra. `commit-hygiene.md` and `researcher.md` pin `model: opus` (deliberate — escalation-on-feisty-state and deep-research respectively); `session-analyst.md` pins `model: sonnet` (a **generic alias**, not a hardcoded ID — Claude Code presumably resolves "sonnet" to whatever the current Sonnet release is, so this file may auto-upgrade to Sonnet 5 with no edit needed; worth confirming empirically rather than assuming). No `opus-low`/`sonnet5-tier`-style cost-segmented subagent_type exists in agent-infra; the two named cost-tier subagents found system-wide are `opus-low` and `fable-low` (defined in the harness's built-in agent roster per the Agent tool's available-types list, not in this repo) — there is currently **no equivalent `sonnet5-low` or `sonnet5-tier` lane**, which is the gap the user's question 5 was asking about.

## Step 4: llmx routing allowlist gap

`~/.claude/cache/llmx-routing.json` → `lite_allowed_models: ["claude-opus-4-8", "gemini-3-flash-preview", "gpt-5.5"]`.
**No Sonnet model — 4.6 or 5 — is in the subscription-routable lite-allowlist at all.** This isn't a
Sonnet-5-specific gap; Sonnet has never been in this list. If the intent is to make Sonnet 5 a cheap
subscription-routed lane (the user's stated goal), this allowlist is the actual gate that needs an entry —
without it, `llmx chat --subscription -m claude-sonnet-5` / `--lite bare` will not route, regardless of
what model-guide recommends. (This file is machine-generated by `llmx info --write-mirror`, not hand-edited
— the fix lives in llmx's own allowlist config, not this JSON mirror.)

## Step 5: subagent_type tier gap (user's question 5)

Confirmed: the model-guide skill and llmx routing currently define cost tiers only as Opus-effort levels
(`opus-low`, generic `opus`) plus GPT-5.5/codex lanes — there is no Sonnet-tier-as-a-named-lane anywhere in
agent-infra's dispatch vocabulary. Given Sonnet 5 is the first Sonnet-tier model with `xhigh` effort and is
explicitly positioned as near-Opus-quality-at-Sonnet-cost, the natural new lane is a `sonnet5-tier` (or
similar) entry analogous to `opus-low`/`fable-low`, for work that's currently defaulting to Opus mainly
because no better-than-Opus-cost option existed. This doesn't exist yet and would need to be authored. Confirmed location:
`opus-low`/`fable-low` (and `fable-high`, `benchmark-rater`, `design-review`, `fresh-eyes-review`,
`supervision-audit`) are defined globally at `~/.claude/agents/opus-low.md` /
`~/.claude/agents/fable-low.md` etc. — NOT per-project. A new `sonnet5-low` (or similar) lane would be
authored there, following the same `model:`/`effort:`/lane-description pattern as `opus-low.md`, and would
become available to every project's Agent tool dispatch simultaneously (global blast radius — per the
Constitution's autonomy boundaries, this is "shared infrastructure affecting 3+ projects" and needs
human sign-off before deploying, not just proposing).
