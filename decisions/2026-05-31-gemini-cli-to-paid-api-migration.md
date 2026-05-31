---
id: 2026-05-31-gemini-cli-to-paid-api-migration
concept: llmx-transport-routing
repo: llmx
decision_date: 2026-05-31
recorded_date: 2026-05-31
provenance: contemporaneous
status: accepted
initial_leaning: keep $0 by repointing llmx's free CLI transport gemini→agy
relations:
  - type: depends_on
    target: 2026-05-24-gemini-3.5-flash-default-cosigner
---

# 2026-05-31: Migrate llmx Gemini transport from free gemini-cli to paid API

## Context
Google announced (2026-05-19 blog) the retirement of Gemini CLI in favor of
Antigravity CLI (`agy`). Hard cutoff: **2026-06-18**, the free Gemini CLI
consumer tier (Google AI Pro/Ultra + free Code Assist) stops serving requests.
llmx's "$0 via CLI" transport shelled out to `gemini -p … -m …` on exactly that
consumer-OAuth tier (`cli_backends.py`), and the entire llmx-routing cost model
plus marker default leaned on it. The free path dies in 18 days.

## Alternatives considered
1. **agy free transport (hybrid)** — repoint llmx `gemini`→`agy`, keep $0 for the
   default-model workload, route model-pinned/schema to paid API. *Killed by probe:*
   `agy` headless print mode runs `model=""` locked to the account default; no `-m`
   flag, `CASCADE_DEFAULT_MODEL_OVERRIDE` had no effect, and the free tier exposes
   only Gemini 3.5 Flash + 3.1 Pro (not the cheap `gemini-3-flash-preview`). So
   it can't serve llmx's model-routed / cheap-classification / schema calls.
2. **Paid Gemini Developer API (chosen)** — drop CLI transport entirely; Google
   resolves to the existing `_google_chat` API path (`GEMINI_API_KEY`). Full
   model + schema + search control; `--flex` opt-in for 50% off. Cost: per-token
   (Gemini Flash is cheap), abandons the $0 principle.
3. **Defer — keep gemini-cli until 2026-06-18** — rejected: leaves the paid path
   untested until a deadline scramble; reintroduces the subprocess fragility the
   user wanted gone.

## Counterevidence sought
- *Does `agy` have any headless model selector?* Probed `--help`, the binary's
  env-var strings (`CASCADE_DEFAULT_MODEL_OVERRIDE`, `agy_allowed_models`),
  config files, and agy's own `model_config_manager` log line. All confirmed
  print mode is locked to the persisted default. No headless selector exists.
- *Is "Flex" a real synchronous Gemini Developer API tier, or just the Batch
  discount?* Initially mis-read the `google-genai` SDK (TrafficType "output only,
  not supported in Gemini API") as "no sync flex." Official docs
  (ai.google.dev/gemini-api/docs/flex-inference) + Google blog confirmed Flex IS
  synchronous, `config={"service_tier":"flex"}`, 50% off — my SDK read was wrong
  (the field exists in google-genai ≥2.7, not 1.66). Flip recorded.

## Decision
Drop the gemini-cli backend from llmx entirely (CLI_PROVIDERS, both alias maps,
the `cli_chat` gemini branch, PROVIDER_CONFIGS). Google always routes
`transport=google-api`. Added a `--flex` opt-in flag (default off — Flex is
best-effort/variable-latency, observed 503s under demand spikes) threaded through
`chat()` → `_google_chat` → `config.service_tier`. Bumped `google-genai` pin
1.66 → ≥2.7 (the typed config only gained `service_tier` there) and verified
llmx's google paths import/run clean on 2.7. `agy` installed as the interactive
terminal replacement, but is NOT an llmx transport.

## Evidence
- llmx@551e742 (cutover), llmx@3fc3553 (--flex). Verified via installed tool:
  `gemini-3.5-flash` and `gemini-3-flash-preview` both log `google-api` and
  return correctly; `--flex` returns correctly; a flex call 503'd under load
  (best-effort tier behaving as designed).
- agy 1.0.3 probe: 4/4 clean headless calls, ~3.4s latency, consumer free tier
  confirmed (`consumerOnboardingComplete:true`, no API key).

## Revisit if
- Google ships a headless model selector for `agy` (would reopen a $0 path).
- Gemini API spend becomes material → push more dispatch to `--flex`/Batch, or
  reconsider per-call model routing to cheaper tiers.
- Flex 503 rate makes background dispatch unreliable → default `--fallback`.

## Supersedes
The "$0 via CLI" Gemini rows of `~/.claude/rules/llmx-routing.md` (updated same day).
