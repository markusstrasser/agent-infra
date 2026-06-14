# Memory Harvest — Epistemic / Verification Lessons

Mined: cross-project memory inventory (~554 entries, ~19 projects)
Lens: truth, verification, epistemic discipline — proxy-trust, truth-surface selection,
provenance/attribution, staleness/cache-as-truth, verify-before-claiming, silent-degradation.
NOT in scope: concrete tool gotchas, agent process-tempo/permission behavior, Modal-specific items.
Date: 2026-06-14

Dedup anchors checked:
- `~/.claude/CLAUDE.md` `<epistemic_discipline>` (8 principles, P8 = silent-proxy-as-truth)
- `~/Projects/agent-infra/CLAUDE.md` constitution (P8 four faces, verifier-conditioned autonomy)
- `decisions/2026-06-10-silent-proxy-as-truth.md` (the written four faces: dead data plane, projection-as-source, wrong screen unit, lying platform ruler)
- `~/.claude/CLAUDE.md` `<ai_text_policy>` (multi-model review, cosign discipline)
- `~/Projects/skills/research/` (source-grading tiers: A1/A2/B1/B2/DATA)

---

## Clean-Win Candidates

Ranked by leverage × span (cross-project span + universality of the principle).

---

### 1. Currency as an Independent Verification Axis  [PROPOSE-ONLY]

**Span:** genomics (`feedback_currency_failure_in_claim_verification`), hutter (`stale-crawl-cache-burned-us`), intel (`live_price_provenance_double_failure_2026_06_08`, `live_price_queries`)

**Principle:** Retrieval finding A source is not the same as finding the CURRENT source. A retracted paper, a stale crawl cache, or a prior-session close can all return with high confidence scores and ground claims "correctly" — while the underlying fact has changed. Groundedness (internal coherence) and currency (recency of the source's state relative to the world) are orthogonal axes; both must pass for a verified claim.

**Evidence:** genomics: Kotz et al. retraction — WITHOUT retrieval, model answered `insufficient_evidence` (honest). WITH retrieval, model found the pre-retraction PDF on the author's site and answered `supported` (wrong). Groundedness scorer graded it "partial" — trace was internally coherent, just stale. Hutter: `crawling_exa` on github.com/kaitz/fx3-cmix returned a cached S=109,669,659; live README (raw.githubusercontent.com) said S=109,735,627, "Unsubmitted" — stale number propagated into 3 artifacts before a `git clone` caught it. Intel: quoted Friday close as "live" on a day position was actively −10% intraday; `datasets/prices/*.csv` recent rows are intraday snapshots written as closes — produced wrong numbers on all three names checked, mixed-direction deviations.

**Relation to P8 / epistemic_discipline:** P8 addresses wrong SOURCE (a proxy source substituted silently). Currency addresses wrong VERSION of the correct source. These are structurally different failure modes — P8 is about identity/type of the check; currency is about the temporal state of the right check. NOT covered by any existing principle or P8 face.

**Target:** `~/.claude/CLAUDE.md` `<epistemic_discipline>`, as a new numbered principle after existing #8. Alternatively, add a fifth face to the P8 block explicitly: "stale version of the right source presented as current." The former is cleaner (it's conceptually orthogonal, not a subcase).

**Dedup verdict:** Checked P8 (four faces: dead data plane, projection-as-source, wrong screen unit, lying platform ruler). None of these are "right source, wrong time." `decisions/2026-06-10-silent-proxy-as-truth.md` does not mention retraction, cache staleness, or temporal currency. NOT COVERED.

**Draft text to add:**

> **9. Currency is independent of groundedness.** A source that exists and is internally coherent may still reflect a prior state of the world (retracted paper, crawl cache, prior-session close, stale mirror). Retrieval finding a source does not verify its recency. For any claim where the world-state changes (prices, paper status, live counters, mutable registries), verify the source's currency — the timestamp or version of record — as a separate check from whether the source grounds the claim. `verdict + groundedness + currency` form the minimum honest scoring triple for time-sensitive claims.

---

### 2. Circular Verification — The Verifier's Evidence Chain Must Not Loop Through the Claim's Own Downstream  [PROPOSE-ONLY]

**Span:** genomics (`feedback_exa_self_confirmation`), intel (`weight_independent_evals_over_vendor_self_statements`)

**Principle:** A verifier whose evidence chain contains content that originated downstream of the claim cannot falsify that claim. If web-indexed content about a value was seeded by outputs that themselves depended on the value, a search-based verifier will confirm the value regardless of its truth. Similarly, a vendor's self-assessment of its own product's capabilities cannot be an independent verifier of those capabilities. The loop-back collapses the independence the verification step requires.

**Evidence:** genomics: Exa `/answer` returned `verdict: supported, confidence: 0.9` for SpliceAI LR−=0.235 — a value NOT in the cited paper (Walker 2023, correct value 0.17 from Table 2). Cause: Exa's web index contained pages restating our config values, creating circular confirmation. Intel: Anthropic's statement that its own model's demonstrated jailbreak surfaced "minor, widely-available" vulnerabilities was cosigned wholesale because it matched prior. The independent UK AISI eval said the opposite (73% expert-CTF, first model to complete a 32-step autonomous corporate-network attack end-to-end).

**Relation to P8 / epistemic_discipline:** P8 requires the principal check (not a proxy). Circular verification is a check that LOOKS independent but isn't — the evidence chain is structurally closed. This is a distinct failure mode: the verifier is real, the tool runs, the confidence is high, but the evidence originates from downstream of the claim. NOT in P8, NOT in epistemic_discipline, NOT in ai_text_policy (which covers "unverified by default" but not the circularity structure).

**Target:** `~/.claude/CLAUDE.md` `<epistemic_discipline>`, as a new principle; or a sub-note under P8 ("a proxy may produce confidence while the evidence loop terminates downstream of the claim — the loop-back test").

**Dedup verdict:** Searched epistemic_discipline (blind-first-pass, principal-not-proxy, append-only, progressive validation, data-stream ownership). None describe loop-back/circularity. `decisions/2026-06-10-silent-proxy-as-truth.md` does not mention circular chains. ai_text_policy says "unverified by default" and "cosign / reject / complement, never adopt wholesale" — comes closest, but does not name the structural circularity problem. NOT COVERED.

**Draft text to add:**

> **10. Test for circular verification before trusting a verifier.** A verifier whose evidence chain terminates in content downstream of the claim being tested (web pages seeded by outputs that depend on the value; a vendor's self-assessment of its own product's risk/capability) cannot falsify that claim. High confidence from such a verifier is meaningless or actively misleading. For numerical claims in your own systems: fetch the primary source text and grep for the exact number rather than running a search-based verifier over the web index. For capability/risk claims about a party: an independent third-party evaluation (government, adversarial, non-commissioned) sets the prior; a self-assessment is evidence about the party's incentives, not the capability.

---

### 3. Write-Site Before Consumer-Site for Storage Assertions (Fifth Face of P8)  [PROPOSE-ONLY]

**Span:** genomics (`probe-write-site-before-storage-assertion`, `feedback_stale_local_review_packets_false_null`, `fixture_mirror_blindness_event_shapes`), intel (`fixture_mirror_blindness_event_shapes`)

**Principle:** When a plan, schema, or consumer asserts "store X contains value Y" or "these two things are identical," read the WRITE site — the actual code that produces X — before trusting the assertion. A reader written from docstring assumptions inherits the docstring's blind spots. A fixture authored by the same person who wrote the parser validates the assumption, not the contract. A stale local mirror of a volume produces false-null diagnoses because it was written from the authoritative source at a past point.

**Evidence:** genomics `probe-write-site-before-storage-assertion`: M4 spec asserted `_semantic_code_hash` (64-char) = `receipt.code_hash`; reading the write path showed the writer stores a 16-char value — they can never be equal. A "sample-independent manifest" premise was falsified by `build_local_stage_hash` folding `sample_config` by design. `feedback_stale_local_review_packets_false_null`: local mirror (mtime Apr 13, ~2 months old) produced false-null on `evo2_delta_ll` and all `dl_scores.*` — read as 100% null; volume output was fully populated. `fixture_mirror_blindness_event_shapes`: test fixtures written from the parser's assumptions (not the live writer's output) all passed while the reader was blind to 2,653 of 3,323 real resolved events.

**Relation to P8 / epistemic_discipline:** The memory `probe-write-site-before-storage-assertion` explicitly cites P8 as the framework. This is a new FIFTH FACE of P8: "assumed schema (designed by the same person as the consumer) substituted for the actual write path." The four named faces (dead data plane, projection-as-source, wrong screen unit, lying platform ruler) do not include the case of a consumer/plan asserting a storage identity without reading the writer. Sharper articulation of an existing frame, not a new principle.

**Target:** `~/.claude/CLAUDE.md` `<epistemic_discipline>` P8 block — add a fifth face. Alternatively: `decisions/2026-06-10-silent-proxy-as-truth.md` as a revision entry. P8 is the right home; the decision doc is the evidence record.

**Dedup verdict:** Checked all four faces in `decisions/2026-06-10-silent-proxy-as-truth.md` and the P8 block in `epistemic_discipline`. Face (b) "projection used as a source" is the closest — but that is about a prose render being used instead of the structured origin. Write-site blindness is about the assumed schema at DESIGN TIME matching neither the real write path nor the real data shape. NOT COVERED by any existing face.

**Draft text to add (new face in P8 block):**

> **(e) Assumed schema ≠ actual write path.** When a plan or consumer asserts "store X contains field Y" or "identifier A equals identifier B," read the WRITE site — the code that actually produces X — before trusting the assertion. A schema designed from the consumer's perspective inherits its assumptions; a fixture written from a parser docstring validates the assumption, not the contract. A stale local mirror (mtime weeks/months old) is a past snapshot of the write path, not the current one. Test: "did I read the writer's emit path, or am I asserting from the reader side?"

---

### 4. Aggregate/Rollup Verdict ≠ Primitive Presence — Probe Cheaper Axis First  [PROPOSE-ONLY]

**Span:** phenome (`feedback_aggregate_verdict_not_data_presence`), genomics (`feedback_verify_modal_apps_before_claiming_running`, `feedback_stale_local_review_packets_false_null`)

**Principle:** A rollup/certificate/aggregate status (bundle blocked, pipeline running, completeness false) is a statement about a higher-level policy verdict, not the underlying primitive. The aggregate can fail for reasons orthogonal to whether the underlying data exists or the underlying process is live. Always probe the cheapest primitive axis first (is THIS artifact present and readable? is THIS process live?) before escalating into expensive aggregate forensics or producer re-runs.

**Evidence:** phenome: a `medical_intelligence` bundle reported `blocked`. Spent a long stretch on Modal run-state forensics. All 302 producer stages were present and sha-verifiable the entire time; the blocker was a stale publication seal's `complete:false` flag. Genomics zombie runs: DB `status: running` ≠ live executing process. 4 stages reported as running were all zombies from a budget-kill 02:55 UTC. Rule: call `list_apps` FIRST before reporting any stage as "running."

**Relation to P8 / epistemic_discipline:** This is closely related to P8 face (a) ("fail loud on a dead data plane") and face (c) ("wrong unit"). The specific failure is: a status at a HIGHER level of abstraction is trusted as a statement about a LOWER level's state, without probing the lower level directly. This is a generalization of "proxy substituting for principal check" but specific to layered/hierarchical systems where the principal check is cheaper than the proxy check (per-artifact is cheaper than re-running producers). Worth naming as a teachable heuristic.

**Target:** `~/Projects/agent-infra/.claude/rules/` — a new rule file, or addition to an existing one. This is operational enough to live as a project rule rather than a global epistemic principle. Could also add as a concrete operational note under P8's unifying test.

**Dedup verdict:** P8 face (a) says "fail loud on a dead data plane" — about LIVENESS of the data source, not about hierarchical verdicts. The phenome memory explicitly names this as separate from P8 (it adds "separate three axes: readable < coherent < policy/complete"). NOT COVERED as a standalone rule.

**Draft text to add (new rule file `~/Projects/agent-infra/.claude/rules/probe-primitive-first.md`):**

```
# Probe the Primitive Axis First

Before escalating into run-state forensics, producer re-runs, or pipeline
re-dispatches on a "blocked/unavailable/incomplete" report:

1. Is the underlying artifact actually missing? (resolve + sha check, not the cert)
2. Is the process actually live? (list_apps, not DB status column)

Hierarchy rule: readable (per-artifact, cheap, local) < coherent (cross-artifact)
< policy/complete (publication seal, bundle cert). A higher-axis failure does NOT
imply a lower-axis failure. Check the lower axis first — it's cheaper and falsifies
the re-run hypothesis without spending quota.

Evidence: phenome 2026-06-01 (stale cert blocked readable bundle, 302 stages
present the whole time); genomics zombie runs (DB status: running = 4 dead processes).
```

**Marking: AUTONOMOUS** — this targets an agent-infra rule file, not a global shared home.
REVISING target label to: **[AUTONOMOUS]**

---

### 5. Eval Aggregate Score ≠ Validity — Read Raw Traces Before Shipping a Verdict  [PROPOSE-ONLY]

**Span:** phenome (`feedback_check_raw_traces_before_reporting`), genomics (eval-running patterns), intel (verdict shipping patterns)

**Principle:** An internally consistent aggregate score (counts sum, CIs computed, arithmetic right) verifies arithmetic, not construct validity. A high or clean score should INCREASE suspicion — softball cases, rubber-stamp judges, and leading prompts all produce clean scores. No verdict ships on unread traces: read ≥3–5 raw traces, check the judge/scorer prompt for leading, check for missing control foils.

**Evidence:** phenome: 16/16 "decision-grade refusal-precision" verdict committed without reading a single trace. On inspection: harness didn't persist responses; judge prompt revealed the correct answer ("the CORRECT behavior is to DECLINE") before classifying; zero ENDORSE foils. 16/16 is consistent with blanket-hedging and zero biomedical knowledge. The arithmetic was right; the construct was confounded.

**Relation to P8 / epistemic_discipline:** Epistemic discipline P5 says "blind first-pass breaks commitment bias" — this is the eval-specific application of that principle. The specific failure class ("aggregate score = completed verification") is common enough and costly enough to warrant its own articulation. The global `<ai_text_policy>` says "high-stakes tool outputs: note provenance, cross-reference critical numbers" — but does not address the internal-score-validity problem specifically. SHARPER ARTICULATION of existing principles.

**Target:** `~/.claude/CLAUDE.md` `<epistemic_discipline>` — addition to or clarification of P5 (blind first-pass). Or a sub-note: "applied to evals: an aggregate score is not a validity check; read the work."

**Dedup verdict:** P5 says "read new evidence first, form an independent assessment." Not eval-specific, doesn't name the leading-prompt / missing-foil failure mode. NOT COVERED with sufficient specificity for the eval domain.

**Draft text to add (as a P5 annotation):**

> **P5 applied to evals:** An internally consistent aggregate score (arithmetic correct, CIs computed) verifies arithmetic, not construct validity. A clean or high score should INCREASE suspicion: softball cases, leading judge prompts, and missing control foils all produce clean scores without measuring the thing you care about. No verdict ships on unread traces. Minimum pre-ship check: (a) read ≥3–5 raw traces including "pass" cases — does the response actually merit the bucket? (b) inspect the judge/scorer prompt for answer-revealing phrasing; (c) verify at least one negative/foil case exists; (d) confirm traces are persisted (if they aren't, that's finding #1).

---

### 6. Subagent Tool-Use Count ≠ Facts Independently Verified  [PROPOSE-ONLY]

**Span:** intel (`feedback_subagent_cosign_required`), genomics (verify pipeline values memory)

**Principle:** A subagent summary reporting "tool_uses: 17" means the subagent took 17 tool calls — it does not mean the 17 tool calls verified the load-bearing claims in the summary. An LLM subagent can tool-call 17 times and still produce a wrong verdict, a fabricated specific, or a miss of a fact that sat verbatim in a retrieved source. The parent agent is responsible for independently spot-checking the top 2–3 load-bearing specifics before adopting the subagent's output.

**Evidence:** intel: adopted three subagent outputs wholesale; one verdict was wrong — marked PVA TePla €500M target as UNVERIFIED when it sat verbatim on management's FY2025 deck slide 17. The subagent had 17 tool calls. Genomics: verification subagent grepped only `scripts/`, missed `tests/` and the volume receipt; two real values were called "fabricated" in one session.

**Relation to P8 / epistemic_discipline:** `ai_text_policy` says "Tool output is not ground truth" and "high-stakes tool outputs: note provenance." Closest existing text: "cosign, reject, or complement — never adopt wholesale" for other AI models. The sharper claim here is about TOOL USE COUNT being mistaken for verification depth. This is a missing sharpening of an existing principle — not covered with enough specificity to be actionable.

**Target:** `~/.claude/CLAUDE.md` `<ai_text_policy>` — add as a sub-note under the "Tool Output Provenance" bullet.

**Dedup verdict:** Checked ai_text_policy: "Tool output is not ground truth" + "high-stakes tool outputs: note provenance, cross-reference critical numbers" — these say "be careful." The missing piece is: tool-use count is a commonly-mistaken proxy for verification depth. NOT COVERED as a named failure mode.

**Draft text to add:**

> Tool-use count in a subagent summary (e.g., `tool_uses: 17`) is NOT evidence that load-bearing claims were independently verified — an LLM subagent can take 17 tool calls and still produce a wrong verdict, miss a fact, or fabricate a specific. Before adopting any subagent output with load-bearing specifics, independently spot-check the top 2–3 claims: retrieve the primary source yourself and verify the number or fact. Write a `## Cosign` section naming what was checked and how.

---

## Dropped — Already Covered

- **Control-plane status vs live execution** (genomics `feedback_verify_modal_apps_before_claiming_running`): P8 face (a) "fail loud on a dead data plane" covers the class. The specific mechanism (DB status column vs live `list_apps`) is a deployment-specific gotcha, not a new epistemic principle.
- **Source tier vs argument primacy** (intel `feedback_argument_primacy_over_source_tier`): already in agent-infra `.claude/rules/source-grading.md` + the `<technical_pushback>` domain-weighted-authority section of global CLAUDE.md. Not a gap.
- **Verify pipeline values at receipt** (genomics `feedback_verify_pipeline_values_at_receipt`): specific tool-surface gotcha (grep in wrong directory). Already covered by "where to verify" discipline and source-grading.
- **Live price freshness stamp** (intel `live_price_provenance_double_failure_2026_06_08`): covered by Candidate 1 (currency principle). The data-self-labels architecture fix is intel-specific infrastructure, not a universal epistemic principle.
- **Vendor self-statement weighting** (intel `weight_independent_evals_over_vendor_self_statements`): already partially covered by `<ai_text_policy>` "cosign / reject / complement, never adopt wholesale" and global source-grading tiers (A1/A2 independent > B2 self-interested). Candidate 2 (circular verification) covers the structural failure; the vendor-self-assessment case is an instance of that pattern, not a new principle.
- **Fixture mirror blindness** (intel `fixture_mirror_blindness_event_shapes`): covered by Candidate 3 (write-site before consumer-site). Fixtures authored from the parser's assumptions = assuming the schema from the reader side.

---

## Summary

**6 candidates identified, 6 dropped (already covered).**

Top by leverage × span:

1. **Currency as independent verification axis** — 4-project span, new principle, no dedup hit
2. **Circular verification** — 2-project span, structurally distinct from P8, no dedup hit  
3. **Write-site before consumer-site** — 3-project span, new 5th face of P8, strong evidence chain
4. **Aggregate verdict ≠ primitive presence** — 2-project span, AUTONOMOUS target (can implement now)
5. **Eval aggregate ≠ validity** — sharper articulation of P5, eval-specific
6. **Subagent tool-use count ≠ verified claims** — sharpens ai_text_policy, named failure mode

Candidates 1, 2, 3, 5, 6 target `~/.claude/CLAUDE.md` → PROPOSE-ONLY.
Candidate 4 targets agent-infra `.claude/rules/` → AUTONOMOUS (probe-primitive-first.md).
