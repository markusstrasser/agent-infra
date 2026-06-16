---
id: 2026-06-15-llmx-refactor-dispatch-layer
concept: llmx-transport-routing
repo: agent-infra
decision_date: 2026-06-15
recorded_date: 2026-06-15
provenance: contemporaneous
status: accepted
initial_leaning: Refactor llmx CLI flags (effort aliases, --subscription) only — surface polish without moving llm_dispatch
relations:
  - type: branches_from
    target: 2026-05-31-gemini-cli-to-paid-api-migration
  - type: depends_on
    target: 2026-06-14-review-dispatch-consolidation
---

# 2026-06-15: llmx refactor — transport truth in llmx, intent profiles in skills

## Context

Week of 2026-06-08–15 usage audit across `~/Projects/*`:

- **~6,690 logged llmx calls** (`~/.claude/llmx-usage.jsonl`), dominated by phenome (4,195), intel (752), genomics (167), skills/critique (509 model-review invocations).
- **Two parallel dispatch stacks:** direct `llmx chat` subprocess (production scripts) and `skills/shared/llm_dispatch.py` → `llmx.api.chat` (critique, sweep, research-ops ticks).
- **13 llmx package commits** in 7 days (cursor transport, auto-retry, schema normalize, timeout/reasoning fixes) — high velocity, caught routing bug same-day via blind review (`a91f0f1` / `64f51ed`).
- **358/611 model-review invocations abort in <5s** — bootstrap/Python-version/auth failures, not model latency (`research/2026-06-15-critique-slow-and-unreliable.md`).
- **`llm_dispatch` exists because llmx lacks:** typed profiles, `api_only` vs subscription transport, structured `DispatchResult`, interpreter contract, unified failure taxonomy.

The question is not “prettier CLI flags” but **where dispatch intelligence should live** and how llmx integrates with critique, model-guide, and production scripts without a third wrapper layer.

## Alternatives considered

1. **CLI polish only** — effort aliases (`max`→backend mapping), `--subscription`, `--dry-run`; leave `llm_dispatch.py` as the thick harness API.
   - Pros: smallest blast radius; skills unchanged.
   - Cons: duplicates routing logic forever; 5k/week subprocess callers never get profiles or structured errors; critique bootstrap fixes stay in skills.

2. **llmx absorbs everything** — move `PROFILES`, critique axis orchestration, verify passes into llmx; skills become thin shells.
   - Pros: one binary, one mental model.
   - Cons: couples release cycles; llmx becomes a review framework; hutter/execute native agent loops don't fit; violates “architecture over instructions” at wrong layer.

3. **Retire llmx; skills call native CLIs only** (`claude -p`, `codex exec`, `cursor-agent`).
   - Pros: fewer translation layers; effort knobs match vendor CLIs.
   - Cons: loses cross-vendor schema normalize, retry, telemetry, batch API; intel/phenome/genomics already standardized on `llmx chat`; 6k calls/week migration cost.

4. **Split llmx-core (library) + thin CLI; skills keep intent profiles** *(chosen)*.
   - llmx owns: transport resolution, capability matrix, structured `DispatchResult`, effort normalization, subscription vs API policy, telemetry.
   - skills own: named profiles (`deep_review`, `composer_review`, …), critique orchestration (parallel axes, verify-before-fold, packet assembly).
   - model-guide owns: which model/effort tier for a *task class* (cosigner economics, Fable path).
   - Pros: matches actual usage; production scripts can adopt library without critique coupling; testable transport invariants in one repo.
   - Cons: two repos to coordinate; migration period with dual paths.

5. **Skill-native routing only** — delete central dispatch; each skill documents its own `llmx` incantations.
   - Pros: zero shared code.
   - Cons: already failed — footguns (`-p` misuse, `--lite` auth, multi-`-f` drops) recur; `llmx-guide` is 300+ lines of damage control.

## Counterevidence sought

Searched for evidence that **llm_dispatch should stay the permanent owner of transport logic**:

- `composer_review` required `api_only=False` hack in skills because llmx had no first-class “subscription transport” intent — fixed in skills Jun 14, not in llmx. Confirms duplication, not that skills should own transport forever.
- Direct CLI bypass (hutter grinder, execute tier, Fable Agent) is **intentional** for agent loops — does not argue against llmx for headless batch/extraction/critique axes.
- Usage log shows 99% `transport: api` — searched whether subscription paths are unused. Genomics `_transport_for_model`, execute skill, and critique fallback **do** use `--lite bare`; they’re under-logged, not absent.
- Searched whether phenome/intel would resist library migration — they already shell `llmx chat`; a stable `DispatchResult` + `llmx dispatch` subcommand is strictly easier than parsing stdout/exit codes.

No evidence found that a CLI-only polish path reduces the 358 sub-5s critique abort rate or eliminates `llm_dispatch` duplication.

## Decision

**Adopt option 4: llmx becomes the single owner of transport truth and structured dispatch; skills keep intent profiles and orchestration.**

### Layer contract (who owns what)

| Layer | Owns | Does NOT own |
|-------|------|----------------|
| **llmx** | Provider/transport resolution; capability matrix; `DispatchResult` (text, transport, model, effort_applied, warnings, usage, exit_class); effort alias normalization; `--subscription` / `subscription=True`; `--dry-run`; auto-retry; schema dialect normalize; telemetry (`llmx-usage.jsonl`) | Critique axes, parallel lanes, verify-before-fold, context packet assembly, model cosigner policy |
| **skills/llm_dispatch** | Named `DispatchProfile` registry; profile fingerprints; critique/sweep/research-ops entrypoints | Re-implementing transport fallbacks, API-key stripping, cursor prefix routing |
| **model-guide** | Task-class model selection (Opus-low vs codex-low vs Fable Agent); cosigner tier economics | CLI flag gotchas (delegate to `llmx chat --dry-run` / `llmx info`) |
| **critique** | Axis presets, depth rounds, repo-access vs packet-only routing, Composer scout | Raw `llmx chat` recipes in SKILL.md (route through `model-review.py`) |
| **llmx-guide** | Historical footguns during migration; shrinks as llmx self-documents | Duplicating model-selection tables from model-guide |
| **research skill** | `llmx research` provider matrix, grounding tools | Gemini/OpenAI transport defaults |
| **eval skill** | `llmx batch` as required judge arm transport | Per-eval profile definitions (may reference llmx profiles) |

### llmx refactor phases (ordered)

**P0 — Stop the bleeding (shipped 2026-06-15, llmx repo)**

- Effort aliases: `max` → per-backend map (`xhigh` GPT, `--effort max` Claude CLI); `-e max` valid.
- Wire `--effort` through to `claude -p` on claude-cli path.
- `--subscription` alias for `--lite bare` (+ document `--lite research`).
- `--dry-run`: print resolved dispatch plan JSON + stderr `[llmx] transport=…`.
- Always emit one stderr dispatch line: `[llmx] transport/model/effort/timeout`.
- `llmx info` (+ `--write-mirror` → `~/.claude/cache/llmx-routing.json`) — transport facts CLI; judgment stays in model-guide.
- `model-review.py --preflight` — CLI-first critique health check.
- Fix stale README (Gemini CLI claims).

**Claude routing policy (operator directive 2026-06-15):** Anthropic paused API credit migration; `claude -p` / Agent SDK stay on **subscription**. Never route Claude through paid API (`anthropic-direct`, API-key billing) unless explicitly requested. Default: `llmx chat --subscription -m claude-opus-4-8`. Smoke: `llmx chat --dry-run --subscription -m claude-opus-4-8`.

**P1 — Structured dispatch API (llmx repo + thin skills shim)**

- `DispatchResult` dataclass in `llmx.api` matching `llm_dispatch` status taxonomy (map exit 3/4/5/6 → classes).
- `llmx.api.dispatch(**kwargs)` superset: `prompt`, `context_paths`, `output_path`, `model`, `provider`, `subscription`, `effort`, `schema`, `timeout`, `dry_run`.
- Auto-concat `-f` with `# --- path ---` boundaries (or warn/error on multi-`-f` without `--concat`).
- `llmx run` or documented re-exec helper for Python-version mismatch (critique bootstrap).
- Tests: `cli_backends` lite cwd, subscription key-strip, cursor prefix routing (extend existing `test_cursor_routing.py`).

**P2 — Skills integration (skills repo)**

- `llm_dispatch.dispatch()` becomes thin wrapper over `llmx.api.dispatch`; profiles stay in skills.
- `model-review.py` CLI fallback (`llmx chat --subscription`) → `dispatch(subscription=True)`.
- Add `scout_review` profile for code-review-scout (cursor/composer-2.5) — scout stops hand-building argv.
- critique SKILL: remove duplicated transport recipes; point to `llmx info` + model-guide cosigner table.

**P3 — Production script adoption (opportunistic, per-repo)**

- phenome/intel/genomics: optional migration to `llmx.api` or `llmx dispatch --json` for cache keys and cost guards; **not blocking** — legacy `llmx chat` remains supported via stable CLI.
- Deprecation warnings for bare `llmx -p` (autoresearch, repo-summary) → `llmx chat`.

### Explicit non-goals

- llmx does **not** implement agent loops (multi-turn tools) — hutter/execute keep `claude -p` / `codex exec`.
- llmx does **not** subsume Fable routing — Agent subagent + key-stripped `claude -p` stay in model-guide/critique.
- llmx does **not** own critique packet assembly or verify-before-fold.
- No merge of model-guide into llmx-guide (economics vs mechanics split preserved).

### Integration with adjacent skills

| Skill | Integration action |
|-------|-------------------|
| **critique** | Single entry: `model-review.py`; axes reference profile names; preflight `model-review.py --preflight` (internally: `llmx chat --dry-run --subscription -m claude-opus-4-8`) replaces manual smoke strings |
| **model-guide** | Add “probe before dispatch” pointer to `llmx info` / `llmx chat --dry-run`; keep cosigner defaults |
| **code-review** | Scout uses `scout_review` profile; Composer transport locked by test (`test_call_llmx_honors_cli_transport_for_composer`) |
| **eval** | Document `DispatchResult` for judge arms; batch unchanged |
| **execute** | Tier table: agent loop = native CLI; cheap cosign = `subscription=True` via llmx |
| **research / research-ops** | `llmx research` stays; rate-limit tick uses `cheap_tick` profile via unified API |
| **brainstorm** | Keep ban on raw `llmx chat`; no change |

## Evidence

- Usage audit 2026-06-08–15: subagent reports + `llmx-usage.jsonl` volume by project.
- `skills/shared/llm_dispatch.py`: `DispatchProfile`, `api_only`, `composer_review` cursor fix comments.
- `research/2026-06-15-critique-slow-and-unreliable.md`: 358/611 sub-5s aborts; llmx mean 12.2s/call.
- llmx git: 13 commits/7d; cursor routing bug `64f51ed`; test gap on `cli_backends`/lite.
- `decisions/2026-06-15-risky-diff-review-fp-fix.md`: cross-repo llmx changes need review gates.
- `~/.claude/cache/llmx-routing.json` (from `llmx info --write-mirror`) + `~/.claude/rules/llmx-routing.md`: transport-only split; this ADR extends to API ownership.

## Revisit if

- After P1: `llm_dispatch.py` still >500 LOC of transport logic (failed absorption).
- Sub-5s critique abort rate not down ≥50% within 30 days of P0+P2.
- phenome/intel maintain >3 distinct subprocess argv builders for the same transport (profile adoption failed).
- llmx adds a stable agent-loop transport that matches hutter/execute needs (reopen native-CLI bypass policy).

## Supersedes

None. Extends transport-routing doctrine from `2026-05-31-gemini-cli-to-paid-api-migration` with **dispatch API ownership** and skill boundary.

<!-- knowledge-index
generated: 2026-06-15T00:00:00Z
hash: pending

status: accepted

end-knowledge-index -->
