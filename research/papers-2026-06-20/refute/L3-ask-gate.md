**Overall Verdict**
L3 should be downgraded from `MED-HIGH` to `MED/EXPERIMENTAL`. The plan is right to make this a behavioral eval first, but the cited papers do not yet justify a runtime threshold ask-gate. The main unsupported leap is treating prompt-elicited `u_t` plus `u_t >= theta` as likely to reduce over-ask without increasing wrong-action rate in a single-operator local Claude/Codex/Cursor harness.

**2606.19559.md — VERDICT: NARROW**

Strongest objection: The mechanism really is uncertainty decomposition plus deterministic clarification routing, so the citation is directionally faithful. But the paper’s own evidence is much narrower than the plan’s “ask-gate” framing: it uses synthetic underspecification labels, fixed threshold routing, prompt-only self-reported uncertainty, and reports capability dilution, overconfidence, threshold sensitivity, and success-rate drops. The raw paper explicitly says no single threshold dominates and that prompt-based uncertainty competes with task-solving budget; that is exactly the risk for our over-ask problem.

Concrete correction: Rewrite L3 to remove “route to clarify only when `u_t>=theta`” as the intended mechanism. Use `request_uncertainty` only as an offline label/explanation feature in an eval lane, and require local acceptance criteria: reduced unjustified asks, no increase in wrong-action/correction rate, and comparison against a cheap-probe-first baseline. Any threshold must be locally calibrated on agentlogs, not imported as `theta=0.5`.

Anchors: plan L3 at [research/2026-06-20-paper-integration-plan.md](/Users/alien/Projects/agent-infra/research/2026-06-20-paper-integration-plan.md:105); extraction caveats at [2606.19559.md](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/extractions/2606.19559.md:174); raw threshold/capability dilution/overconfidence at [2606.19559.txt](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.19559.txt:828), [2606.19559.txt](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.19559.txt:959), [2606.19559.txt](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.19559.txt:974).

**2606.13603.md — VERDICT: REFUTED**

Strongest objection: This paper does not support an over-ask uncertainty-decomposition ask-gate. Its mechanism is commitment-boundary detection in open-weight reasoning traces using truncation, logprobs, hidden states, answer-forcing suffixes, and extractable final answers; it explicitly does not study closed frontier APIs, tool-using agents, long-horizon workflows, or clarification decisions. “Epiphenomenal-tail = over-deliberation” may support a separate offline verbosity/commitment-point analysis, but it does not reinforce `u_t` elicitation or threshold routing for ask-vs-act decisions.

Concrete correction: Remove 2606.13603 from L3’s support list. Move it to a separate eval idea: “post-commitment tail / over-deliberation replay,” limited to offline transcript-prefix analysis where there is a stable final answer/action and a verifier. Do not use it as evidence for request-uncertainty reliability or ask-gate threshold safety.

Anchors: extraction preconditions and non-transfer at [2606.13603.md](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/extractions/2606.13603.md:35), [2606.13603.md](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/extractions/2606.13603.md:100), [2606.13603.md](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/extractions/2606.13603.md:132). Raw text confirms the same limits at [2606.13603.txt](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.13603.txt:960) and [2606.13603.txt](/Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.13603.txt:1032).

**Required Plan Patch Concept**
Change L3’s claim to: “Build an over-ask behavioral eval that labels ask-vs-probe-vs-act failures. Test whether a request-underspecification feature helps distinguish missing user preference from execution uncertainty. Ship no live ask-gate unless local replay shows fewer unjustified asks without higher wrong-action/correction rate.”

Complete report.