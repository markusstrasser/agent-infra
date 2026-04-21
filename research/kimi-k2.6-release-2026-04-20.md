---
title: "Kimi K2.6 Release — 2026-04-20"
date: 2026-04-21
tags: [kimi, moonshot, model-release, benchmarks]
status: complete
---

# Kimi K2.6 — Research Memo

**Date:** 2026-04-21 | **Status:** Released 2026-04-20 (GA)

## Config verification

Our `~/.kimi/config.toml` already has:

```toml
default_model = "moonshot-ai/kimi-k2.6"

[models."moonshot-ai/kimi-k2.6"]
provider = "managed:moonshot-ai"
model = "kimi-k2.6"             # bare canonical name sent to Moonshot API
max_context_size = 262144
capabilities = ["image_in", "video_in", "thinking"]
```

The `moonshot-ai/kimi-k2.6` key is Kimi CLI's internal namespacing convention (the hyphenated prefix is how Kimi CLI names managed-provider models in its config). The actual API call uses `model = "kimi-k2.6"`. This is correct — no change needed. The initial research concern about the prefix was a false alarm caused by confusing Kimi CLI's config key format with direct API / OpenRouter routing strings.

## (a) Canonical Model Name

- **Moonshot native API:** `kimi-k2.6` (no date suffix, no `moonshot-v1-` prefix). Confirmed by `platform.kimi.ai/docs/guide/kimi-k2-6-quickstart` and `platform.moonshot.ai`.
- **OpenRouter:** `moonshotai/kimi-k2.6` and dated form `moonshotai/kimi-k2.6-20260420` both resolve.
- **HuggingFace weights:** `moonshotai/Kimi-K2.6`.
- **Our config** (`default_model = "moonshot-ai/kimi-k2.6"`) uses an OpenRouter-style prefix with a hyphen variant (`moonshot-ai/` vs OpenRouter's canonical `moonshotai/`). If llmx routes via OpenRouter, verify the prefix — the canonical spelling is `moonshotai/` (no hyphen). If llmx hits Moonshot directly, the correct string is bare `kimi-k2.6`.

## (b) Capabilities Summary

K2.6 is a 1T-param MoE (32B active, 384 experts / 8 routed + 1 shared) natively multimodal (text, image, video) with 262,144-token context, released open-weight under Modified MIT. Headline gains vs K2.5: long-horizon coding (12–13 hr autonomous sessions, 4,000+ tool calls), 300 parallel sub-agents (agent swarm primitive), ships natively in INT4 quantization, ~20% lift on Moonshot's internal Kimi Code Bench. Trained on 15.5T tokens (vs K2.5's 15T). API shifted from `enable_thinking` to `chat_template_kwargs.thinking`; returns `reasoning` (not `reasoning_content`). Four consumer variants via kimi.com picker: **Instant**, **Thinking**, **Agent**, **Agent Swarm** — these are modes, not separate API model IDs.

**Benchmarks:** SWE-Bench Verified 80.2% (beats GPT-5.4, ~even with Claude Opus 4.7), SWE-Bench Pro 58.6 (vs Opus 4.7 at 59.1), Humanity's Last Exam 54.0% (#1), BrowseComp 83.2%, Terminal-Bench 2.0 66.7%, DeepSearchQA 92.5% (leads field). Artificial Analysis Intelligence Index: 54. GPQA/MMLU/HumanEval not headline-reported.

## (c) Pricing (Moonshot Platform, per MTok)

| Tier | Input | Cached | Output |
|---|---|---|---|
| **K2.6 (long context)** | $0.95 | $0.16 | $4.00 |
| **K2.6 (short context, some resellers)** | $0.60 | $0.20 | $2.50–$2.80 |
| K2.5 | $0.60 | $0.10 | $3.00 |
| K2 0905 | $0.60 | $0.15 | $2.50 |
| Claude Opus 4.7 (ref) | $5.00 | — | $25.00 |
| GPT-5.4 (ref) | ~$2.50 | — | ~$10.00 |

Moonshot's own console lists K2.6 at **$0.95 / $4.00** (long-context tier). OpenRouter / Kilo / devpik list **$0.60 / $2.80** — likely short-context or promotional. Automatic prompt caching gives 75–83% savings. Roughly 5–10× cheaper than Opus 4.7 on output.

## (d) Config Recommendation

**`default_model = "moonshot-ai/kimi-k2.6"` is likely wrong as written.** Two concerns:

1. **Prefix spelling:** Upstream canonical is `moonshotai/kimi-k2.6` (no hyphen) on OpenRouter, bare `kimi-k2.6` on native Moonshot API. The `moonshot-ai/` form with hyphen is not a canonical routing prefix — confirm whether llmx's provider adapter normalizes this, or switch to the correct spelling.
2. **Context window:** Our config says 262,144. That matches OpenRouter / HuggingFace / Puter / artificialanalysis.ai listings. Moonshot's own docs page says "256K" — likely a rounding label, the raw number is 262,144. Our value is fine.
3. **Capabilities flag `video_in`:** Correct — K2.6 adds native video input (new vs K2.5 which was vision+text only).

**Suggested fixes:**
- If llmx uses OpenRouter: change to `moonshotai/kimi-k2.6` (or `moonshotai/kimi-k2.6-20260420` for pinning).
- If llmx uses Moonshot direct: change to `kimi-k2.6`.
- K2.6-family models in our config: only `kimi-k2.6` itself. The others (`kimi-k2-0905-preview`, `kimi-k2-thinking`, `kimi-k2-turbo-preview`, `kimi-k2-thinking-turbo`, `kimi-k2-0711-preview`) are all **pre-K2.6** (K2 / K2 Thinking era, July 2025–Jan 2026). No `kimi-k2.6-turbo` or `kimi-k2.6-thinking` separate API IDs exist — thinking is a runtime flag on `kimi-k2.6`.

## Known Gotchas

- Verbose output (160M tokens on one eval vs 41M median). Budget max_tokens generously.
- Thinking API changed: `chat_template_kwargs.thinking` replaces `enable_thinking`; disable via `{"thinking": {"type": "disabled"}}`.
- Modified MIT: attribution required for products >100M MAU or >$20M/mo revenue. Irrelevant for our usage.
- Slightly behind Opus 4.7 on SWE-Bench multi-language and behind GPT-5.4 on Toolathlon.

## Sources

- platform.kimi.ai/docs/guide/kimi-k2-6-quickstart (Moonshot official)
- platform.moonshot.ai (pricing console, K2.6 $0.95/$4.00)
- huggingface.co/moonshotai/Kimi-K2.6 (weights)
- artificialanalysis.ai/models/kimi-k2-6
- openrouter.ai/moonshotai/kimi-k2.6-20260420
- developers.cloudflare.com/changelog/post/2026-04-20-kimi-k2-6-workers-ai/
- kimi-k2.org/blog (2026-04-21 release post)
- remio.ai/post/kimi-k2-6-landed-four-days-after-claude-opus-4-7 (pricing comparison)
- devpik.com/blog/kimi-k2-6-moonshot-ai-complete-guide (variant breakdown)

<!-- knowledge-index
generated: 2026-04-21T17:04:05Z
hash: 8300adbc31d9

title: Kimi K2.6 Release — 2026-04-20
status: complete
tags: kimi, moonshot, model-release, benchmarks

end-knowledge-index -->
