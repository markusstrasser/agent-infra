# Vendor Binary Skill Archaeology — what Anthropic's built-in skills do better (and worse) than ours

**Date:** 2026-06-12 · **Source grade:** A (primary — extracted verbatim from the shipped binary) ·
**Method:** string extraction from `~/.local/share/claude/versions/2.1.175` (214 MB bundled
executable; built-in skills/workflows are embedded as JS template literals, not plugin files).
Reproduce: `uv run python3` over the binary bytes, regex for `export const meta = {` /
distinctive prompt phrases, dump surrounding regions. Full dump: `.scratch/binary-skills-dump.txt`.

## Why this exists

Question from operator: are the vendor-shipped review skills (`code-review`, `review`, `simplify`,
`verify`, `security-review`) better than our `critique`, and what should we learn? Routing context:
this cluster is our main semantic-confusability risk (SkillRouter, arXiv:2603.22455 — overlap, not
count, degrades routing).

## Inventory of embedded assets (v2.1.175)

| Asset | Kind | What it is |
|---|---|---|
| `code-review` | skill + hidden workflow | Effort-parameterized multi-agent diff review (the serious one; details below). `ultra` = cloud workflow variant. |
| `deep-research` | workflow | Scope → search-angle pipeline → URL-dedup → fetch/extract falsifiable claims → 3-vote adversarial verify (≥2/3 refutations kill) → synthesize. "Ported from bughunter architecture." |
| `verify` | skill | Runtime-observation verification philosophy + per-surface examples (CLI/server). Strongest prose of the set. |
| `simplify` | skill | 4 parallel cleanup agents (reuse/simplification/efficiency/altitude) → apply fixes. Subset of code-review's cleanup angles, with `--fix` semantics. |
| `security-review` / `review` | skills | Thinner variants on the same finder/verifier machinery (PR-oriented). |
| `/stuck` | skill | Diagnose frozen/slow Claude Code sessions on the machine: ps state-letter triage (D/T/Z), child-process hangs, `sample <pid>` stack dumps, debug-log tails. We have no analog. |
| `update-config` | skill | Full settings.json + hooks schema embedded, with construct-and-VERIFY hook workflow ("Constructing a Hook (with verification)") and "When Hooks Are Required (Not Memory)" — same architecture-over-instructions position as our constitution. |
| skill-creator interview flow | skill | Analyze session → interview user → write SKILL.md → confirm/save. |
| `run-skill-generator` | skill | Generates per-repo `run-*`/`verifier-*` skills; `verify` treats those as the repo's evidence-capture protocol. |

## The code-review pipeline (extracted)

Effort cells: `low → 1 diff pass, no verify, ≤4 findings` · `medium → 3+4 angles × 6 candidates →
1-vote verify → ≤8 (precision)` · `high → same fan-out, recall-biased verify, ≤10` · `xhigh/max →
5+4 angles × 8 → verify → gap sweep → ≤15 (recall)`. Hidden workflow mirrors the same cells for
cloud execution (`LEVEL_PARAMS`, `MAX_VERIFY=25`, `SWEEP_MAX=8`).

Mechanics worth naming:
1. **Independent finder angles, no cross-suppression.** 5 correctness + 4 cleanup
   (reuse/simplification/efficiency/altitude) angles run as separate agents; "if two angles flag
   the same line for different reasons, record both."
2. **Mandatory `failure_scenario` per candidate** — "concrete inputs/state → wrong output/crash."
   Kills vague findings at the source.
3. **Anti-self-censorship instruction:** "Pass every candidate with a nameable failure scenario
   through — finders that silently drop half-believed candidates bypass the verify step and are
   the dominant cause of misses."
4. **3-state verdict ladder with a constructibility criterion:** CONFIRMED / PLAUSIBLE / REFUTED,
   where REFUTED is allowed "only when constructible from the code: factually wrong (quote the
   actual line); provably impossible (type/constant/invariant — show it); already handled in this
   diff (cite the guard); or pure style with no observable effect."
5. **Explicit recall/precision dial by effort tier** (medium: "every finding one a maintainer
   would act on"; high+: "a missed bug ships — err on the side of surfacing").
6. **Gap sweep (xhigh/max):** one fresh finder given the verified list, hunting ONLY gaps, with a
   curated miss-list: "moved/extracted code that dropped a guard or anchor; dataclass default
   evaluated once; `hash()` non-determinism; lock-scope shrink; predicate methods with side
   effects; setup/teardown asymmetry in tests; config defaults flipped."
7. **Streaming pipeline, no barrier** between find and verify; dedup by file + line bucketed to
   5-line windows; verify budget (25) with explicit `budgetDropped` accounting (no silent caps).
8. **Rank + salvage:** correctness > cleanup, CONFIRMED > PLAUSIBLE; if synthesis agent fails,
   return verified findings unmerged rather than discarding the run.

## The verify skill (extracted highlights)

- **"Verification is runtime observation."** Explicitly bans running tests/typecheck as
  verification ("proves you can run CI — not that the change works") and bans import-and-call
  ("a unit test you wrote; the app never ran").
- **Surface table:** change reaches CLI/server/GUI/library/agent-config/CI → observe at that
  surface; "internal function? Not a surface — follow the caller." Tests in the diff are "the
  author's evidence, not a surface."
- **Push-on-it probes:** after the claim checks out, probe around it at the same surface (flag
  passed twice, malformed body, Ctrl-C mid-op, stale state, two sessions at once). Report marks
  probes 🔍 distinct from ✅; "a Steps list that's all ✅ and no 🔍 is a happy-path replay."
  Held probes still get reported ("🔍 empty `--from` → clean error").
- **Verdict ladder PASS/FAIL/BLOCKED/SKIP, no partial pass** ("3 of 4 passed is FAIL until 4
  passes or is explained away"); "when in doubt, FAIL."
- **"The verdict is table stakes. Your observations are the signal."**

## Comparative verdict vs our `critique`

**They win on diff review mechanics.** Our critique has no diff-specialized multi-angle
finder/verifier pipeline; `critique close` Phase 2 dispatches packet reviews. Their pipeline is
better engineered for the diff layer (items 1–8 above).

**We win on epistemics and non-diff objects:**
- **Cross-MODEL diversity.** Their entire pipeline is same-model multi-agent — by our own opening
  argument in critique (same-model review is a martingale, arXiv:2508.17536), 9 Claude finders
  share Claude's blind spots. Different *contexts/angles* buy partial independence, not a
  different training family.
- **Premise falsification for plans.** Diffs carry their own ground truth; plans don't. Our
  2026-06-10 two-for-two evidence (packet-only reviewers 0-for-5 on repo-grounded findings; the
  repo-access Fable axis caught dead dispatch targets, phantom joins, existing helpers) has no
  vendor counterpart.
- **Calibration data.** Distrust-the-confidence-field (median 0.89 self-confidence, ~40%
  anchor-verify rate), three anchor-inflation fixes (extension-swap, sibling-roots,
  symbol-grep), HALLUCINATED-rate forensics.
- **Scope declaration + context anti-patterns + divergent-bucket escalation to the user.**

**Conclusion: partition, don't compete.** Vendor `code-review` owns diffs; our `critique` owns
plans/designs/findings/closeouts and the cross-model layer. Steal their mechanics where they're
ahead. Integration plan: `.claude/plans/2026-06-12-vendor-skill-integration.md`.

## Tool-surface note (last ~2 months of harness additions)

The same binary ships harness tools we hold but underuse: `Workflow` (deterministic multi-agent
orchestration with resume journal + budget API — our /improve and /upgrade fan-outs hand-roll
what `pipeline()` gives for free), `Monitor` (zero-token waiting, already in dreamer practice),
teams (`TeamCreate`/`SendMessage` — persistent addressable agents vs fire-and-forget),
`EnterWorktree`/`ExitWorktree`, `LSP`. The deep-research workflow's 3-vote adversarial verify is
the vendor's own implementation of our cross-check pattern — same convergence, different tier.
Binary archaeology is repeatable on each release: the diff of embedded prompts between versions
is a changelog Anthropic doesn't publish.

## Revisions
<!-- append-only -->
