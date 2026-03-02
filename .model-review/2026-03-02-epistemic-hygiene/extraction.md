# Extraction & Disposition — Epistemic Hygiene Brainstorm

## Extraction: gemini-brainstorm.md

G1. Zero-Trust Provenance — agent can't write directly; claims go to KG, "compiler" renders markdown
G2. Adversarial Shadow Agent — async shadow agent runs Exa falsification searches during research
G3. Epistemic Budgeting — finite confidence tokens per session, hedges cost less, sources refund
G4. ACH null hypothesis requirement — force agent to generate null hypothesis before starting
G5. Sterile Cockpit — constrained JSON extraction during tool use, disable CoT while extracting
G6. Double-Entry Bookkeeping — exact-string-match anchor for every claim to ingested file
G7. Defensive Honeypots — inject fake data into tool outputs, halt if agent accepts without questioning
G8. Drop SAFE-lite — academic benchmark, too much latency/cost for data you won't act on
G9. Drop calibration tracker — 5x sampling is massive token waste, violates generative principle
G10. Drop citation density — easily gamed, counting brackets doesn't measure truth
G11. String-Math exact-match hook — grep noun-phrases of claims against source docs, zero LLM
G12. Pushback Index — % of UserPromptSubmit events met with "No"/"However"/"Cannot" response
G13. Query Divergence Rate — embedding distance between user prompt and agent search queries
G14. Context Distance metric — token index ingested vs token index written, >40K = hallucination risk
G15. Devil's Advocate Injector — PreToolUse hook appends negative terms to search queries
G16. Sycophancy Brake — UserPromptSubmit hook prefixes system prompt for confirmation-bias triggers
G17. PreCompact Epistemic Anchoring — save source tags to "hard memory" before compaction
G18. Silent Fallback Trap — hard block same-model review for non-trivial decisions
G19. Self-critique: LLM-as-judge still unreliable even cross-model
G20. Self-critique: user can be the epistemic failure source
G21. Self-critique: non-textual domains need deterministic tests not text checks

## Extraction: gpt-brainstorm.md

P1. Universal Provenance Gate — cross-project, typed tags: [src:URL], [quote], [calc], [spec]
P2. Subagent Output Gate — SubagentStop with claim ledger requirement
P3. Cross-model Review Circuit Breaker — fail closed for non-trivial, log reviewer status
P4. Epistemic Lint — static check flagging numbers/dates/entities without nearby source tags
P5. Citation Density + Claim-Type Ratio Monitor — verifiable_claims/sources, %speculation, trend
P6. SAFE-lite Sampling Harness — weekly, atomize claims, verify with Exa, JSONL log
P7. Irreversible-Action Stop Hook — require decision.md artifact with alternatives + rollback
P8. Consensus-Search Detector — warn/block "best/top/most" queries unless paired with systematic screen
P9. Context-Rot Watchdog — force structured summary + risks when context exceeds threshold
P10. Disagreement Sampling — re-run with perturbations, log dispersion
P11. Tag spamming risk — agent adds [src] but source doesn't support claim (performative compliance)
P12. Outage deadlocks risk — Gemini/GPT down = constant blocking; need override path
P13. Evaluator drift risk — LLM judge can hallucinate support; need snippet quoting in logs
P14. Verifiable-claim coverage metric — fraction of numbers/dates/entities with nearby source tag
P15. Source-to-claim alignment metric — % of cited claims where snippet actually contains claim
P16. Quote ratio metric — how often agent includes direct quotes for key claims
P17. Correction load per session — count user corrections, reverts, "undo" sequences
P18. Hook trigger rates over time — gates trigger less AND SAFE precision rises = honest autonomy
P19. Genomics-specific: ClinVar ID validation, HGVS format check, allele frequency range
P20. Contradiction detection for selve — scan for conflicting claims across notes
P21. Priority ranking: circuit breaker > subagent gate > provenance gate > monitor > SAFE-lite
P22. Self-critique: bias toward enforcement over workflow design
P23. Self-critique: proxy metrics can be gamed or miss real failures
P24. Self-critique: annoyance costs / friction budget is real for single operator
P25. Self-critique: needs differ across projects (genomics vs intel vs selve)

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1 | Zero-Trust KG provenance | REJECT | Massive scope change; requires rebuilding entire write pipeline. Not 30-min buildable |
| G2 | Adversarial Shadow Agent | DEFER | Cool but complex. Needs async agent infrastructure that doesn't exist. Revisit post-orchestrator |
| G3 | Epistemic Budgeting (tokens) | REJECT | Clever but unhookable — no way to track "confidence tokens" across tool calls deterministically |
| G4 | ACH null hypothesis | MERGE WITH P1 | Good principle, but subsumes into typed provenance: `[spec]` tag forces hypothesis visibility |
| G5 | Sterile Cockpit extraction | DEFER | Interesting — constrain output during tool reads. Would need PreToolUse prompt hook (broken per MEMORY.md). Revisit when prompt hooks verified |
| G6 | Double-Entry exact-match | MERGE WITH G11 | Same idea: structural verification of claims against sources |
| G7 | Defensive Honeypots | REJECT | High effort, adversarial to own system, hard to calibrate false positive rate |
| G8 | Drop SAFE-lite | REJECT (disagree) | GPT's framing is better: measurement comes after enforcement. SAFE-lite is the lagging indicator |
| G9 | Drop calibration tracker | INCLUDE | Agree — sampling-based calibration is too expensive for regular use. Market feedback (intel) is the only practical calibration signal |
| G10 | Drop citation density standalone | MERGE WITH P5 | Citation density alone is gameable. Upgraded to claim-type ratio (P5) which catches tag-spam |
| G11 | String-match noun-phrase check | DEFER | Interesting but brittle — real claims paraphrase. Consider as component of SAFE-lite verification |
| G12 | Pushback Index | INCLUDE — Tier 1 | Cheapest possible sycophancy metric. Can extract from session transcripts retroactively. Zero-cost |
| G13 | Query Divergence Rate | DEFER | Requires embedding pipeline per search query. Good idea, expensive to implement |
| G14 | Context Distance metric | DEFER | Would need token-level tracking infrastructure that doesn't exist. PreCompact hook can't see token indices |
| G15 | Devil's Advocate search injection | INCLUDE — Tier 2 | Simple PreToolUse hook. Append disconfirmation terms to searches. Directly attacks consensus-search pattern |
| G16 | Sycophancy Brake | INCLUDE — Tier 2 | UserPromptSubmit prompt hook. Injects adversarial system prompt on trigger words. Needs careful calibration |
| G17 | PreCompact Epistemic Anchoring | DEFER | Interesting but PreCompact has no decision control (can't modify context). Would need MCP or file-based workaround |
| G18 | Silent Fallback Trap | MERGE WITH P3 | Same as circuit breaker — both models agree on fail-closed for review |
| G19 | LLM-as-judge unreliable | NOTE | Valid. All LLM-based checks are approximate. Architecture (string matching, structural checks) > LLM judgment |
| G20 | User as epistemic failure source | NOTE | Valid but out of scope for this system. UserPromptSubmit hook (G16) partially addresses |
| G21 | Non-textual domains need tests | NOTE | Valid. Genomics needs deterministic validation (P19), not text epistemics |
| P1 | Universal Provenance Gate | INCLUDE — Tier 1 | Both models converge. Generalize intel's hooks cross-project. Add typed tags. Highest leverage |
| P2 | Subagent Output Gate | INCLUDE — Tier 1 | Both models agree. SubagentStop hook. Stops unchecked sludge |
| P3 | Cross-model Review Circuit Breaker | INCLUDE — Tier 1 | Both models agree. Fail closed, log status. Simplest fix for known failure |
| P4 | Epistemic Lint (static) | INCLUDE — Tier 2 | Simple grep for unsourced numbers/dates. Can run as pre-commit or periodic check |
| P5 | Citation Density + Claim-Type Ratio | INCLUDE — Tier 2 | Upgrade of citation density with type awareness. Leading indicator for SAFE-lite |
| P6 | SAFE-lite Sampling Harness | INCLUDE — Tier 3 | Build after provenance gate exists. Lagging indicator. Weekly/biweekly |
| P7 | Irreversible-Action Stop Hook | DEFER | Already partially covered by existing PreToolUse hooks (data-guard, bash-rm-guard). Not epistemic-specific |
| P8 | Consensus-Search Detector | INCLUDE — Tier 2 | Simple regex on search queries. Directly addresses observed failure pattern |
| P9 | Context-Rot Watchdog | INCLUDE — Tier 2 | Force structured summary at context threshold. Cheap, high leverage for long sessions |
| P10 | Disagreement Sampling | DEFER | Expensive. Do manually when suspicion arises. Not worth automating |
| P11 | Tag spamming risk | NOTE | Valid. P5 (claim-type ratio) partially addresses. SAFE-lite (P6) is the definitive check |
| P12 | Outage deadlocks risk | NOTE | Valid. Circuit breaker needs explicit override path with logged rationale |
| P13 | Evaluator drift risk | NOTE | Valid. SAFE-lite must log snippets, not just verdicts |
| P14 | Verifiable-claim coverage | MERGE WITH P5 | Component of claim-type ratio monitor |
| P15 | Source-to-claim alignment | MERGE WITH P6 | This IS SAFE-lite |
| P16 | Quote ratio | MERGE WITH P5 | Component of claim-type ratio |
| P17 | Correction load per session | INCLUDE — metric | Already partially measured by session-analyst. Formalize as first-class metric |
| P18 | Hook trigger rates over time | INCLUDE — metric | Already logged by tool-tracker. Need dashboard/trend extraction |
| P19 | Genomics: ClinVar/HGVS validation | DEFER | Domain-specific. Implement in genomics project, not meta |
| P20 | Contradiction detection for selve | DEFER | Interesting but needs NLP infrastructure. Revisit with embedding pipeline |
| P21 | Priority ranking | NOTE | Agree with ranking: circuit breaker > subagent gate > provenance gate |
| P22-P25 | Self-critiques | NOTE | All valid. Friction budget is the key constraint |

## Coverage Check

- Total extracted: 46 items (21 Gemini + 25 GPT)
- INCLUDE: 14 (3 Tier 1, 6 Tier 2, 1 Tier 3, 2 metrics, 2 from merges)
- DEFER: 10
- REJECT: 4
- MERGE: 6 (into other INCLUDE items)
- NOTE: 10
- Total dispositioned: 46/46 ✓
