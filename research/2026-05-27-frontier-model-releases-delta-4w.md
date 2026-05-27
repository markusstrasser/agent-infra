---
title: Frontier Model Releases — 4-Week Delta (2026-04-29 → 2026-05-27)
date: 2026-05-27
tags: [frontier-models, releases, benchmarks, pricing, gemini, deepseek, qwen, claude, meta, cohere, glm]
status: complete
prior_anchors:
  - frontier-delta-2026-05-08.md
  - gemini-3.5-flash-benchmarks.md
  - gemini-3.5-flash-vs-exa-vs-perplexity-probe.md
  - kimi-k2.6-release-2026-04-20.md
  - trending-scout-2026-05-19.md
window: 2026-04-29 → 2026-05-27
---

# Frontier Model Releases — 4-Week Delta

Filter: confirmed releases or material capability/pricing changes that landed in the window. Anything still in "leak / coming June" territory is in pertinent negatives, not the main table.

## What's new vs prior memos

The window is dominated by **two events**:

1. **Open-weight pricing war re-escalated.** DeepSeek made its 75% V4-Pro discount **permanent** on May 22 — output now at $1.74/MTok, claimed ≥34× cheaper than GPT-5.5 [SOURCE: the-decoder.com, Engadget, InfoWorld]. Cohere open-sourced **Command A+** (218B MoE, Apache 2.0) on May 21 [SOURCE: VentureBeat, the-decoder.com]. Both push the open-weight floor down hard.
2. **Google I/O shipped Gemini 3.5 Flash** (May 19) with Terminal-Bench 2.1 **76.2%** and the new MCP Atlas eval at **83.6%** — outperforming Gemini 3.1 Pro on coding/agent benchmarks at fraction-of-Flash cost [SOURCE: blog.google, llm-stats.com]. 3.5 Pro deferred to "next month."

Everything else: Qwen 3.7 Max (Alibaba, May 20–21), Meta Muse Spark (April 8 — barely in window; closed-weights pivot), Anthropic Mythos public-access expansion announcement (May 26, still restricted). xAI Grok 5 = still teased, not shipped.

## Confirmed releases — claims table

| Model | Date | Status | Context | Pricing in/out per MTok | Headline numbers | Source |
|---|---|---|---|---|---|---|
| **Gemini 3.5 Flash** | 2026-05-19 | GA | 1,048,576 | (free tier + paid; ~3× Flash baseline per llmx-routing) | Terminal-Bench 2.1 76.2%, MCP Atlas 83.6%, GDPval-AA 1656 Elo, CharXiv-Reasoning 84.2%, 4× faster TPS than peer flagships [SOURCE: blog.google 2026-05-19, llm-stats.com 2026-05-19] |
| **Gemini 3.5 Pro** | "coming June" | Internal | n/a | n/a | Announced but not shipped [SOURCE: blog.google 2026-05-19] |
| **DeepSeek V4-Pro** (price cut) | 2026-05-22 perma | GA, MIT | 1M | $0.145 / $1.74 | 75% discount made permanent; output ~34× cheaper than GPT-5.5 [SOURCE: Engadget 2026-05-23, the-decoder.com 2026-05-23, InfoWorld 2026-05-25, HN 48237663]. Model itself (1.6T MoE / 49B active, LCB 93.5%, SWE-Verified 80.6%, Codeforces 3,206) shipped 2026-04-24 — out of window, covered prior |
| **DeepSeek V4-Flash** | (with V4) | GA, MIT | 1M | $0.14 / $0.28 | 284B MoE / 13B active [SOURCE: NivaaLabs 2026-05-09] |
| **Qwen 3.7 Max** | 2026-05-20 | GA, closed-weights | 1M (up from 256K) | undisclosed (Qwen3.6 ref: $1.30/$7.80) | AA Intelligence Index 56.6 (#5 overall, #1 Chinese; ahead of Gemini 3.5 Flash 55.3, trails Opus 4.7 57.3 and GPT-5.5 60.2). HLE 38.1%, Terminal-Bench Hard 50.8%, GDPval-AA 1546, AA-Omniscience 30.1% with 22.9% hallucination [SOURCE: officechai.com 2026-05-21, aimodelsnavi 2026-05-22, felloai 2026-05-22]. Caveat from reviewer: lower halluc rate driven by **higher abstention**, not better recall |
| **Cohere Command A+** | 2026-05-21 | GA, Apache 2.0 | 128K | open (self-host) | 218B MoE / 25B active; runs on 2× H100 or 1× Blackwell; τ²-Bench Telecom 37→85, Terminal-Bench Hard 3→25; AA Index ~37 (Haiku-4.5 / Mistral Medium 3.5 tier). 48 languages, multimodal. VentureBeat tagline "lossless quantization + native citations" — main article doesn't quantify either claim [SOURCE: VentureBeat 2026-05-20, the-decoder.com 2026-05-21] |
| **Meta Muse Spark** | 2026-04-08 (in window edge) | private preview, closed-weights | 256K or 1M (unclear) | free in meta.ai consumer; API gated | First Meta frontier model **without open weights**. AA Index 52, HealthBench Hard 42.8% (#1), CharXiv 86.4 (#1), ARC-AGI-2 42.5 (33pt gap behind leaders). "Thought compression" — 58M tokens on AA suite vs 157M for Opus 4.6 [SOURCE: chatforest 2026-05-15, aicerts 2026-05-12]. Strategic signal: Llama no longer on frontier track |
| **Anthropic Mythos** (Preview, 2026-04-07) public-access expansion announcement | 2026-05-26 | Project Glasswing partners only (~50 vetted firms) | n/a published | n/a | Glasswing partners collectively found "10,000+ high/critical vulns." Mythos: SWE-Verified 93.9%, SWE-Pro 77.8%, Terminal-Bench 2.0 82.0%, GPQA-Diamond 94.6%, BrowseComp 86.9% (5× fewer tokens than Opus 4.6) [SOURCE: tensoria.fr 2026-05-16, bankinfosecurity 2026-05-26]. Anthropic: "Mythos-level models widely available in 6-12 months." Not consumable in window. |
| **GLM-5.1** (Z.ai) | (pre-window release; reported in May coverage) | GA, MIT | 200K (output 128K) | self-host | 754B MoE / 40B active; Chatbot Arena Elo 1467; SWE-Pro 58.4% (94.6% of Opus 4.6 per Z.ai docs). FP8: 8× H200 ~$36/hr; INT4: 4× H200 ~$18/hr [SOURCE: Spheron 2026-05-18] |

## Agent-relevant implications

1. **Output-cost floor collapsed.** DeepSeek V4-Pro at $1.74/MTok output (perma) plus V4-Flash at $0.28/MTok output means any long-horizon agent that doesn't *require* Opus-class judgment should re-cost against V4-Flash. Output-token cost for verbose Opus 4.7 work (tokenizer inflation 1.0–1.35× per `frontier-delta-2026-05-08`) gets worse by comparison — re-cost any multi-day Modal job. Implicator.ai's framing: "Western labs cannot match." [SOURCE: implicator.ai 2026-05-24]
2. **MCP Atlas is a new agent-routing benchmark to watch.** Google ships it alongside Gemini 3.5 Flash (83.6%). Not yet referenced in prior frontier-delta memos — suggests `tool-attention` workstream should ingest the eval next sweep.
3. **Qwen 3.7 Max's "lower hallucination via higher abstention" mechanism** is a worked example of the calibration-vs-recall tradeoff. Useful for any LLM-as-classifier scoring exercise — abstention-driven metrics can look like quality gains without delivering them. Pattern transfers to our `/critique` flows. [SOURCE: felloai 2026-05-22]
4. **Mythos-class capability is now publicly announced even if not consumable.** Cyber autonomy from Mythos (write functional exploits, chain weaknesses) raises the realism of the `invariants.md` irreversible-state limits. Worth a cross-reference in any future hook design that handles network-touching tools. [SOURCE: EA Forum 2026-05-23, bankinfosecurity 2026-05-26]
5. **No update yet on Opus 4.7's MRCR collapse** (prior memo: 78→32% at 1M). Anthropic neither patched nor responded in this window. KG-augmented vs naked 1M comparison still unstudied. The open research gap from epoch 2 of frontier-delta-2026-05-08 remains open.

## Pertinent negatives — what was searched for but did not ship in window

- **GPT-5.6 / GPT-5.5 successor** — only leaks (Polymarket >80% odds for June, "1.5M-token context" claim accidentally exposed). Not shipped. [SOURCE: perplexityaimagazine 2026-05-23, news.aibase 2026-05-26]
- **xAI Grok 5** — explicitly NOT shipped. Internal engineering rebuild ongoing under new leaders from Cursor/SpaceX/DeepMind; internal memo describes compute performance as "embarrassingly low." Grok V9-Medium training complete, public release imminent but not in window. [SOURCE: Tesorb 2026-05-19, Techloy 2026-05-25] The "6 trillion parameters" figure for Grok 5 explicitly debunked as "not a technical spec" by TechFastForward.
- **Claude Sonnet 4.8 / Opus 4.8** — leaks only ("512,000-line leak"). Not shipped. [SOURCE: TokenMix 2026-05-25, geeky-gadgets 2026-05-26]
- **Claude Mythos as consumable model** — restricted to Glasswing partners; no public API in window.
- **Mistral frontier release** — Mistral Medium 3.5 mentioned only as Cohere Command A+ tier comparator. No new frontier-tier Mistral release in window.
- **Kimi K2.7** — no release; K2.6 (2026-04-20) remains current per `kimi-k2.6-release-2026-04-20.md`.
- **Llama 5 / Meta open-weight frontier** — Meta Muse Spark closes the open-weights frontier era for Meta. Llama remains available but off the frontier track.
- **Frontier successor to BioAgent Bench, ClawMark, RHB** — no new frontier-agent benchmarks shipped in window. Existing benchmarks from prior memo remain canonical.
- **Anthropic public engineering disclosures** — none in window comparable to the 2026-04-23 postmortem.

## Source grades

| Grade | Source | Notes |
|---|---|---|
| A | blog.google/innovation-and-ai/.../gemini-3-5/ | Vendor primary, 2026-05-19 |
| A | api-docs.deepseek.com pricing page | Vendor primary, current |
| A | Engadget DeepSeek V4 75% perma cut | 2026-05-23 |
| A | the-decoder.com DeepSeek pricing analysis | 2026-05-23 |
| A | the-decoder.com Cohere Command A+ open source | 2026-05-21 |
| A | VentureBeat Cohere Command A+ | 2026-05-20 |
| A | bankinfosecurity.com Mythos public access expansion | 2026-05-26 |
| B | llm-stats.com Gemini 3.5 Flash specs | 2026-05-19 |
| B | NivaaLabs DeepSeek V4 review | 2026-05-09 (covers V4 itself; V4 ships Apr 24, out of window) |
| B | officechai.com Qwen 3.7 Max benchmarks | 2026-05-21 (independent aggregator) |
| B | felloai.com Qwen 3.7 Max review (abstention caveat) | 2026-05-22 |
| B | aimodelsnavi.com Qwen 3.7 max vs plus | 2026-05-22 |
| B | chatforest.com Meta Muse Spark | 2026-05-15 |
| B | tensoria.fr Claude Mythos preview benchmarks | 2026-05-16 |
| B | Spheron open-weight showdown (GLM-5.1 details) | 2026-05-18 |
| C | technosports.co.in GPT-5.6 + flood roundup | 2026-05-24 (aggregator, used for negative claims) |
| C | thewincentral.com GPT-5.6 / Claude leak roundups | 2026-05-24, 2026-05-25 (rumor-tier) |

## Cross-check verifications run

- DeepSeek V4-Pro permanent 75% price reduction → `verify_claim` returns "supported" with confidence 1.0, 8 corroborating sources (Engadget, the-decoder, InfoWorld, HN, TokenMix, Implicator, official deepseek pricing page).
- All single-source claims (Mythos benchmarks, Muse Spark thought-compression numbers, Qwen 3.7 Max AA Index) marked with single [SOURCE] tag, not asserted as cross-confirmed. Mythos numbers should not be cited as benchmarked-by-Anthropic until system card releases.

## Net summary

A honest read: the 4-week window is dense on the **price-war + open-weights** axis (DeepSeek perma cut, Cohere Apache 2.0 218B, GLM-5.1 MIT 754B all live) and on **Google's catch-up** (Gemini 3.5 Flash GA), but **light on capability frontier shifts** — Opus 4.7 still tops SWE-Pro; GPT-5.5 still tops AA Intelligence Index at 60.2; Mythos is the only credibly higher capability point and it's gated. The frontier-delta-2026-05-08 memo's core conclusions (Opus 4.7 long-context regression, test-cheating disclosures, cross-model review pattern convergence) all hold — nothing in this window invalidates them. The notable *new* signals are (a) the open-weight cost structure that makes Opus 4.7 verbose-output economics noticeably worse, (b) Meta's strategic exit from open-weight frontier, and (c) the MCP Atlas eval as a new routing-quality benchmark to ingest.

<!-- knowledge-index
generated: 2026-05-27T09:18:06Z
hash: aeb9424bfee7

index:title: Frontier Model Releases — 4-Week Delta (2026-04-29 → 2026-05-27)
index:status: complete
index:tags: frontier-models, releases, benchmarks, pricing, gemini, deepseek, qwen, claude, meta, cohere, glm
table_claims: 3

end-knowledge-index -->
