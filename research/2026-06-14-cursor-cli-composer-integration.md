---
title: Cursor CLI (cursor-agent) + Composer 2.5 — Headless Integration Verification
date: 2026-06-14
tags: [cursor, composer, llmx, critique, transport, vendor-pricing]
status: complete
---

# Cursor CLI (`cursor-agent`) + Composer 2.5 — Headless Integration Verification

**Date:** 2026-06-14
**Question:** Verify our `llmx` subscription-transport + `/critique` cosigner wiring of
`cursor-agent -p --output-format text --mode ask --trust --model composer-2.5` (stdin prompt, neutral empty cwd) against official Cursor docs.
**Sources:** all official (cursor.com / docs.cursor.com / cursor.com/blog), pulled 2026-06-14. Source-authority grades below.

---

## Verdict vs our integration

| # | Our choice | Verdict | Basis |
|---|---|---|---|
| 1 | `-p`/`--print` as headless flag; `--output-format text\|json\|stream-json`; `--mode ask` (read-only); `--trust` required headless; `--force`/`--yolo`/`--sandbox` | **CONFIRMED** | `docs/cli/reference/parameters` quotes every flag verbatim (see below) |
| 2 | App-login authorizes headless use; `--api-key`/`CURSOR_API_KEY` optional | **CONFIRMED (with caveat)** | `--api-key` documented as *"can also use `CURSOR_API_KEY`"* — i.e. **alternative**, not mandatory. No ToS restriction found; Cursor actively markets CI/GitHub-Actions use. Caveat: ToS legal page not directly inspected. |
| 3 | Composer 2.5 in standard subscription at ~$0-marginal; headless counts against usage | **PARTIALLY CONTRADICTED — IMPORTANT** | Composer 2.5 is **metered/usage-based** ($0.50/M in, $2.50/M out), NOT free. It draws from the **"Auto + Composer" included-usage pool** ("significantly more included usage"), so it is *effectively* near-zero-marginal *until the included pool is exhausted*, then it bills usage-based. CLI calls are "any model as part of your subscription" → **count against the same pool**. Not a flat-free transport. |
| 4 | `--mode ask` reads workspace; run from empty cwd to isolate | **CONFIRMED (mechanism), choice is SOUND** | Ask mode "searches the codebase and provides answers without modifying files" and reads rules/files for context. No official "ignore workspace" flag exists → **empty cwd is the correct isolation method.** |
| 5 | Automation gotchas | **SURFACED** — see Gotchas section (beta status, `--force`/`--yolo` write-access, `--approve-mcps`, auto-update, usage-pool exhaustion) |
| 6 | Composer 2.5 has NO reasoning-effort tiers (only `-fast` serving variant); effort for proxied frontier models set via model-name suffix | **CONFIRMED** | Composer 2.5 has only standard + `fast` variants (fast = default). Frontier models use name suffixes `-high`/`-low`/`-fast` (e.g. `gpt-5.3-codex-high`, `claude-opus-4-8-...`); **no separate effort flag exists.** |

**Bottom line:** flags, auth model, ask-isolation, and the reasoning-effort design are all confirmed correct. The **one correction** is choice #3's framing: Composer 2.5 is metered, consuming an included-usage pool — not unconditionally free at $0 marginal. Treat it as "near-free until the monthly Auto+Composer pool runs out, then usage-billed."

---

## Per-source findings

### `cursor.com/docs/cli/reference/parameters` — **GRADE A (official, exact flag quotes)**
The authoritative flag reference. Verbatim:
- **`-p, --print`** — *"Print responses to console (for scripts or non-interactive use). Has access to all tools, including write and shell."* → NOTE: print mode is **not** read-only by itself; tool access is gated by mode + `--force`.
- **`--output-format <format>`** — *"Output format (only works with `--print`): `text`, `json`, or `stream-json` (default: `text`)."* ✓ matches our `text`.
- **`--mode <mode>`** — *"Set agent mode: `plan` or `ask` (agent is the default when no mode is specified)."* ✓ `--mode ask` valid.
- **`--model <model>`** — specify model. ✓
- **`--api-key <key>`** — *"API key for authentication (can also use `CURSOR_API_KEY` env var)."* → alternative to login, not mandatory.
- **`--trust`** — *"Trust the workspace without prompting (headless mode only)."* ✓ required to avoid an interactive trust prompt in `-p`.
- **`-f, --force`** — *"Force allow commands unless explicitly denied."*
- **`--yolo`** — alias of `--force`.
- **`--sandbox <mode>`** — *"Set sandbox mode: `enabled` or `disabled`."*
- **`--approve-mcps`** — auto-approve all MCP servers without per-server confirmation.
- **`--resume [chatId]`** / **`--continue`** (alias `--resume=-1`) — session resume.
- **`--fast`** flag does **NOT** appear — "fast" is a model *variant* (`composer-2.5-fast`), not a CLI flag. (Consistent with choice #6.)

### `cursor.com/docs/cli` (modes overview) — **GRADE A**
Three modes via `/` command, shortcut, or `--mode`:
- **Agent** (default): *"Full access to all tools for complex coding tasks."*
- **Plan**: *"Design your approach before coding with clarifying questions."*
- **Ask**: *"Read-only exploration without making changes."* ✓ confirms ask = read-only.
- `-p` documented for headless; `--output-format text` "for scripting and CI pipelines."
- `--sandbox <mode>` accepts `enabled`/`disabled`; "Settings persist across sessions."

### `cursor.com/docs/cli/using` — **GRADE A**
- Ask mode (`/ask`, `--mode=ask`): *"Explores code without editing. The agent searches the codebase and provides answers without modifying files."* → confirms ask reads the workspace; hence empty-cwd isolation (choice #4) is the right lever — **no "no-context" flag is documented.**
- Plan mode poses clarifying questions before coding.

### `cursor.com/docs/cli/reference/output-format` — **GRADE B (official page, but field list is a summarizer extraction — verify against live `--help`)**
`--output-format json` success envelope reported as:
```json
{ "type": "result", "subtype": "success", "is_error": false,
  "duration_ms": 1234, "duration_api_ms": 1234,
  "result": "<assistant text>", "session_id": "<uuid>", "request_id": "<optional>" }
```
- Confirms the fields you named: **`result`, `is_error`, `session_id`** ✓ and adds `type`/`subtype`/`duration_ms`/`duration_api_ms`/`request_id`.
- **`usage` field NOT confirmed present** — the extracted envelope does not list a `usage` object. Treat token/usage-in-envelope as **unverified** (see Open questions).
- `stream-json` = newline-delimited events (`system`/`assistant`/`tool_call`/`result`), terminal event identical to above. "thinking" events suppressed in print mode. Consumers should ignore unknown fields (forward-compat).
- Since we use `--output-format text`, the text path returns the final assistant response only — robust for a cosigner. The JSON envelope detail matters only if we later parse `is_error`/`session_id`.

### `cursor.com/blog/cli` (CLI launch) — **GRADE A (announcement)**
- *"You can now use Cursor Agent from the CLI or headless in any environment."*
- *"The CLI works with any model as part of your Cursor subscription."* → CLI usage = subscription usage (consumes pools).
- **Beta warning (load-bearing):** *"This CLI is still in beta. Security safeguards are still evolving. It can read, modify, and delete files, and execute shell commands you approve. Use at your own risk and only in trusted environments."*
- Install: `curl https://cursor.com/install -fsSL | bash`.

### `cursor.com/cli` (landing) — **GRADE A (marketing, but ToS-relevant)**
- Explicitly markets *"Run Agents in Terminal, GitHub Actions"* and *"build custom coding agents."* → Cursor **endorses** programmatic/CI use of the subscription. No prohibition on scripted use in the CLI/Agent docs.

### `cursor.com/blog/composer-2-5` (Composer 2.5 announcement) — **GRADE A**
- Built on *"the same open-source checkpoint as Composer 2, Moonshot's Kimi K2.5."*
- **Good at (Cursor's words, marketing):** *"a substantial improvement in intelligence and behavior over Composer 2"*; *"better at sustained work on long-running tasks, follows complex instructions more reliably, and is more pleasant to collaborate with."*
- **Bad at / limitations:** **NO explicit weakness list.** Only a training anecdote about *"reward hacking"* (model found "increasingly sophisticated workarounds" during synthetic-task RL) — relevant flavor, not a stated runtime limitation.
- **Pricing:** *"$0.50/M input and $2.50/M output tokens."* Fast variant: *"$3.00/M input and $15.00/M output … fast is the default option."*
- *"Composer 2.5 includes double usage for the first week."*
- **Context window: NOT stated anywhere in the blog.** (Kimi K2.5 base implies large, but Cursor publishes no number — see Open questions.)

### `cursor.com/docs/models-and-pricing` — **GRADE A**
- **Two usage pools:** *"Auto + Composer: Significantly more included usage"* and *"API: Charged at the model's API price."* Both reset monthly.
- Composer 2.5 draws from the **Auto + Composer included pool** → near-zero marginal *within* the included allotment, usage-billed past it.
- **Reasoning-effort = model-name suffix (confirms choice #6):** frontier models carry `-high`/`-low`/`-fast` suffixes — e.g. `-high` on Claude 4.5/4.6 Sonnet, Claude 4.7 Opus, GPT-5/5.2, GPT-5.3 Codex; `-low` on GPT-5 Fast; `-fast` on Claude Opus 4.6/4.7/4.8 variants. *"No separate flag mechanism … reasoning effort is encoded directly in model names."*
- Composer 2.5 listed at Input $0.5 / Output $2.5 / Cache-read $0.2 per M. Model string shown as **"Composer 2.5"**; a separate `-fast` string was not enumerated in the pricing table extraction (the fast variant is described in the blog).

---

## Gotchas / risks

1. **Composer 2.5 is metered, not flat-free (CORRECTS choice #3).** It consumes the monthly "Auto + Composer" included pool; once exhausted it bills usage-based ($0.50/$2.50 per M, or fast $3/$15). Heavy `/critique` + transport fan-out **will draw down the shared editor pool** — budget/monitor it; it is not an unlimited subscription tap.
2. **`-p` is NOT read-only on its own.** Print mode "has access to all tools, including write and shell." Safety comes from **`--mode ask`** (read-only) — keep it. Do **not** add `--force`/`--yolo` to an ask cosigner; combined with agent mode they grant unconfirmed file writes + shell.
3. **Beta, "safeguards still evolving," "use at your own risk."** Official posture. The empty-cwd + `--mode ask` combo is the right blast-radius control; rely on mode, not goodwill.
4. **`--approve-mcps` auto-approves ALL MCP servers** without per-server confirmation — do not pass it in an automated cosigner; if any user/global MCP config is present it could be auto-trusted. We run from empty cwd, which should avoid project `.cursor/mcp.json`, but a global MCP config could still apply.
5. **Auto-update drift.** `cursor-agent` updates itself (install script + `cursor-agent update`); the CLI is beta with evolving flags. A flag/output-format change could silently break the transport. **Pin or smoke-test on a schedule**; the "ignore unknown fields" note implies the JSON envelope may gain fields.
6. **Empty/0-byte output conditions (inferred, not doc-stated):** auth expiry, pool exhaustion, or a rate-limit error could yield empty stdout in `text` mode. **For automation, prefer `--output-format json` and check `is_error`** rather than trusting non-empty text — text mode gives no error signal. (Our transport uses `text`; consider switching the cosigner to json-parse for robustness.)
7. **No published rate-limit numbers.** Neither CLI nor pricing docs state req/min throttles. Error shapes for throttling are undocumented → cannot pre-handle a specific rate-limit error code; design for generic non-zero exit / `is_error: true`.
8. **Auth precedence ambiguity.** `--api-key`/`CURSOR_API_KEY` is an *alternative* to app login. If both an env key and a logged-in session exist, precedence is undocumented — an unexpected `CURSOR_API_KEY` in the environment could route billing to a different account/pool. Run the transport with a known, intended auth source.

---

## Open questions / unverifiable

- **`usage` field in JSON envelope:** the extracted `--output-format json` envelope did **not** include a `usage` object (only `result`/`is_error`/`session_id`/`type`/`subtype`/`duration_*`/`request_id`). Whether token usage is returned is **unconfirmed** — verify with a live `cursor-agent -p --output-format json --mode ask --model composer-2.5 "ping"` and inspect the actual JSON. (The output-format field list is GRADE B: a fast-model summary of the doc page, not a quote cross-checked by a second source — confabulation risk.)
- **Composer 2.5 context window:** no official number published (blog + pricing both silent). Base is Kimi K2.5 (large) but do not assert a specific token count.
- **ToS legal text not directly read.** Cursor *markets* CI/GitHub-Actions/"custom coding agents" use of the subscription (strong implicit permission) and no docs page restricts scripted use, but the binding Terms of Service page itself was not fetched. If contractual certainty on "subscription used headlessly in automation" is required, read `cursor.com/terms` directly. **No evidence of a restriction found.**
- **Does `--mode ask` read GLOBAL/user rules even from an empty cwd?** Confirmed it reads *workspace* rules/files; whether global `~/.cursor` rules or a global MCP config still load from a neutral cwd is unverified. For a maximally clean model-query, also ensure no global `.cursor/rules` or MCP config leaks in.
- **Included-pool exact size / reset behavior per plan tier:** "significantly more included usage" is qualitative; the precise monthly Composer allotment for our plan is not quantified in the pulled pages.
- **Live `--help` not run.** All flag confirmations are from docs (GRADE A for parameters page). A 30-second `cursor-agent --help` + one `--output-format json` probe would upgrade the JSON-envelope and ask-context items from "doc-extracted" to "observed." Recommended before finalizing.

## Confidence note
Flag names (#1, #6), ask=read-only (#4), and the metered/pool billing model (#3) are GRADE-A doc-confirmed. The JSON envelope field list (#1 detail) and the precise "ask reads workspace rules" wording are summarizer-extracted (GRADE B) — high but not certain; one live probe resolves both. The reasoning-effort-via-suffix design (#6) is GRADE-A confirmed and matches our wiring exactly.

## Live-probe resolutions (OBSERVED 2026-06-14, supersede the GRADE-B / open items above)
These were run directly against the installed `cursor-agent` (v2026.06.12) during integration — observed evidence beats doc-summary:

- **`usage` field IS present in the JSON envelope (RESOLVED — open question above was doc-extraction miss).** Probe:
  ```
  $ cursor-agent -p "..." --model composer-2.5 --output-format json --mode ask --trust
  {"type":"result","subtype":"success","is_error":false,"duration_ms":7406,"duration_api_ms":7406,
   "result":"PONG.","session_id":"…","request_id":"…",
   "usage":{"inputTokens":10966,"outputTokens":36,"cacheReadTokens":1874,"cacheWriteTokens":0}}
  ```
  So token usage IS available for cost tracking via json mode (the GRADE-B doc extraction simply omitted it).
- **`--help` WAS run** — confirms `-p/--print`, `--output-format text|json|stream-json`, `--mode plan|ask`, `--model`, `--trust`, `--force/--yolo`, `--sandbox enabled|disabled`, `--api-key`/`CURSOR_API_KEY`, `--approve-mcps`, `--resume/--continue`, `worker`, `mcp`, `models`. Matches the docs.
- **Error path observed:** bad `--model` → **exit 1** + error on stderr, empty stdout (text mode). So `text` mode + returncode IS a reliable failure signal for our transport — llmx's `returncode != 0`/empty-output handling catches it. (Gotcha #6's "text gives no error signal" is too strong: the *exit code* does. json `is_error` is still cleaner if we ever parse it.)
- **Empty-cwd overhead:** trivial call from an empty dir showed `inputTokens:2` + `cacheWriteTokens:29678` (system prompt cached once) — confirms the neutral-cwd isolation works and per-call marginal context is tiny after the first.
- **Reasoning effort:** `composer-2.5` and `composer-2.5-fast` are the only composer entries in `--list-models` (no effort tiers) — confirms #6.

## Composer 2.5 — measured routing profile (2026-06-14)
Three benchmarks, all reusing existing multi-model baselines, Composer dispatched via the llmx cursor transport.

| Benchmark | Task | Composer result | vs frontier baselines |
|---|---|---|---|
| cross_lab_review | injected-defect code review | 11/11 clean catches | **= frontier** (Opus/GPT/Gemini all 11/12) — saturated |
| extraction_bakeoff **phenome** | biomedical, HARD byte-exact quote contract | 100% faithful, 100% quote-present, 52% recall, **9% spurious**, yield 11 | **solid/disciplined** — clean, mid recall |
| extraction_bakeoff **intel** | financial, SOFT paraphrase, no verbatim anchor | faith **1.74**/3 (4th of 5), **69 claims / 24 unsupported** | **weak** — over-extracts, gpt-5.3 wins at 2.47 |

**Thesis — Composer is CONTRACT-GATED.** Same model, opposite behavior: with a hard
checkable contract (byte-exact quotes, schema, tests, a grader) it's competitive and
clean (9% spurious on phenome); with paraphrase freedom it over-generates unsupported
claims (35% on intel). It's a **high-recall, high-volume generator that needs an
external verifier to stay precise** — gpt-5.3/gpt-5.5 self-restrain, Composer doesn't.
Matches its design (Kimi-K2.5 base, coding-throughput tuned, no reasoning-effort tier)
and the cross_lab_review enumerate-and-hedge tendency.

**ROUTE TO Composer:** verifier-bound work where its yield is an asset and a contract
catches over-generation — code review (as a $-cheap third lineage), byte-exact/schema
extraction, anything with tests or a grader downstream. **DON'T ROUTE:** open/paraphrase
generation with no anchor, hard reasoning/math/novel design (untested, but the
cheap-coding-model prior says skip), latency- or cost-sensitive high volume (slower than
every API arm; usage-metered). **It beats no incumbent on its own track** — situational
tool, not a new default. Hard-reasoning axis remains unmeasured (no baseline-bearing
reasoning benchmark in evals; critique_replay is the harder-review candidate but its
runner is a stub with no baselines).

## Applied to the integration
- llmx `cursor` transport uses `--output-format text` + exit-code detection (sufficient per the error-path probe). If we later want token telemetry through llmx, switch the cursor branch to `json` and parse `result`/`usage`.
- Docs corrected: every "$0 marginal" claim → "usage-metered (included pool → ~$0.50/$2.50 per M)" across llmx-guide, critique SKILL, llm_dispatch profile, model-review axis label, COMPOSER_ARM_RESULTS.
- Still genuinely open (not blocking): exact included-pool size per plan tier; whether global `~/.cursor` rules leak from a neutral cwd; ToS legal text (marketed for CI, no restriction found).
