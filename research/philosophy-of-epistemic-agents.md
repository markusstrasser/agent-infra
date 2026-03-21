# Philosophy of Epistemic Agents

**Date:** 2026-02-27
**Question:** What's the right philosophical foundation for an AI agent whose job is to find truth, not to please?

---

## The Problem

Claude ships with a constitution built on virtue ethics (Amanda Askell, Jan 2026). It is honest, contextually wise, and genuinely novel. But it is optimized for helpfulness within guardrails — not for adversarial truth-seeking.

The delta between "helpful assistant" and "epistemic agent" is where the design work lives.

## Seven Philosophical Streams

Each maps to a concrete engineering decision, not an abstract principle.

### 1. Popper/Deutsch: Conjectural Epistemology
**Claim:** Knowledge grows through conjecture and refutation. You can never confirm a theory — only fail to falsify it. Error correction is the engine of progress.

**Engineering consequence:** Every hypothesis must have falsification criteria stated BEFORE investigation. If you can't specify what evidence would change your mind, you don't have a hypothesis — you have a belief.

**Implementation:** `open_questions.md` — active hypotheses with falsification criteria, data to watch, affected decisions. Move to "Resolved" when evidence confirms or refutes.

### 2. Frankfurt: Bullshit Detection
**Claim:** The bullshitter is more dangerous than the liar. The liar knows the truth and conceals it. The bullshitter doesn't care about truth at all — they say whatever serves their purpose.

**Engineering consequence:** AI outputs are bullshit by default. The model generates plausible text without verifiable grounding. Source grading (where did this claim come from? what's the evidence quality?) is the primary anti-bullshit mechanism.

**Implementation:** NATO Admiralty System (A1-F6). Every claim gets a 2-axis grade: source reliability (A-F) and information credibility (1-6). AI outputs start at [F3] until verified. Human analysis with primary sources = [A1]-[B2].

### 3. Bratman: Planning Agency
**Claim:** Rational agents form intentions, then act on them without re-deliberating at every step. Plans constrain future deliberation — that's their value.

**Engineering consequence:** Pre-registration beats post-hoc rationalization. State what you expect to find BEFORE looking. If predictions are wrong, that's information. If you find what you predicted, you have evidence (not just narrative).

**Implementation:** Predict data footprints before querying. "If hypothesis X is true, we should see patterns Y and Z in the data." Then query. The gap between prediction and observation IS the epistemic product.

### 4. Elster: Anti-Sycophancy
**Claim:** Adaptive preference formation — people adjust their desires to match what's available. "Sour grapes" rationalization.

**Engineering consequence:** LLMs are sycophantic by default. They adjust their analysis to match what they think you want to hear. The corrective is structural: never start responses affirming the user's framing. Find what's wrong first. Skip flattery. Respond directly.

**Implementation:** Anti-sycophancy rule in CLAUDE.md. "Never start responses with positive adjectives about the user's input." This is a deterministic constraint, not a vibe — it breaks the affirmation-seeking loop.

### 5. Ginsburg: Adversarial Process
**Claim:** Truth emerges from structured disagreement, not consensus. The adversarial legal system assumes no single party can be trusted to present the full picture.

**Engineering consequence:** Single-hypothesis analysis is confirmation bias by definition. For any claim above a significance threshold, generate competing hypotheses and evaluate evidence against ALL of them simultaneously.

**Implementation:** Analysis of Competing Hypotheses (ACH) — Heuer's CIA methodology. Evidence is scored against multiple hypotheses using log-likelihood ratios. The surviving hypothesis is the one with the least disconfirming evidence, not the most confirming evidence.

### 6. Hart: Rules vs Standards
**Claim:** Law operates through both rules (bright lines) and standards (contextual judgment). Rules are cheaper to apply but miss edge cases. Standards are expensive but flexible.

**Engineering consequence:** Some epistemic discipline should be enforced by deterministic rules (hooks, pre-commit tests, schema validation). Other discipline requires judgment (source grading, hypothesis evaluation, kill decisions). Match the enforcement mechanism to the epistemic function.

**Implementation:** Hooks for deterministic enforcement (formatting, security, math invariants). Skills for judgment-requiring workflows (investigation, competing hypotheses, source evaluation). Rules for context-dependent guidance (domain-specific gotchas).

### 7. Christiano: Scalable Oversight
**Claim:** As AI systems become more capable, direct human oversight becomes impossible. The solution is recursive delegation: humans oversee AI that oversees AI.

**Engineering consequence:** The human can't review every inference. Design for auditability rather than approval. Git-versioned entity files, correction registers, prediction trackers — these create an audit trail that makes errors discoverable after the fact.

**Implementation:** One file per entity, git-versioned. Every edit = new commit citing source. `git log` IS the learning archive. Corrections register logs every error caught, how it was caught, impact, and lesson. The error-correction rate is the meta-metric.

## The Generative Principle

From Askell's research (arXiv:2310.13798): A single well-internalized principle is sufficient for a large model to derive correct behavior across novel situations. Detailed rules improve fine-grained control but aren't strictly necessary.

**For epistemic agents, the generative principle is:**

> Maximize the rate of epistemic error correction, measured by feedback from reality.

Everything else derives:
- Source grading → because ungraded claims can't be corrected (you don't know which ones to doubt)
- Competing hypotheses → because single-hypothesis confirmation bias suppresses error signals
- Pre-registration → because post-hoc narrative can't be falsified
- Prediction tracking → because predictions create measurable error signals
- Correction registers → because errors are the valuable artifact (not the analyses)
- Adversarial default → because finding what's wrong is more informative than explaining why things look fine

## The Anti-Sycophancy Problem in Detail

Claude's constitution already values honesty. But the training distribution is overwhelmingly "helpful assistant" conversations. The model has learned that users are happiest when their framing is affirmed.

### Structural correctives (not prompting):
1. **Never open with affirmation.** "Great question!" is zero information. Cut it.
2. **Find what's wrong first.** Before explaining why something makes sense, look for why it doesn't.
3. **Source-grade everything.** When the model says "research shows..." — WHICH research? Published where? Sample size? Replicated? If it can't answer, the claim is [F5] (unverified, low credibility).
4. **Multi-model adversarial review.** Route claims to competing models. Independent agreement = high confidence. Independent disagreement = investigate.
5. **Prediction tracking with Brier scores.** The model's actual calibration is measurable. Track it over time. This creates a feedback loop that self-corrects.

## Error Correction as Moat

The valuable artifact is NOT the analyses — it's the error corrections.

- Analysis: "Company X is undervalued because Y." — Expires in weeks. Everyone can generate this.
- Error correction: "We said Y, but we were wrong because Z, and the reason we were wrong was W." — Compounds forever. Teaches what to look for next time.

The correction register, the prediction tracker, the staleness detection, the multi-model review — these are all mechanisms for generating error signals faster. The entity files and git history are the accumulated corrections.

**A system that corrects its errors faster than its competitors has a durable advantage.** This is the Popperian insight applied to information work.

## Practical Epistemology for AI Agents

### What works:
- **Bayesian bookkeeping** for updating beliefs (log-likelihood ratios, prior odds, posterior probabilities)
- **Pragmatist pluralism** for domain labeling (statistical vs sociological vs legal vs political — each has different evidence standards)
- **Adversarial process** for high-stakes claims (competing hypotheses, multi-model review)
- **Pre-registration** for investigation (predict data footprints before querying)
- **Calibration tracking** for self-correction (Brier scores, prediction resolution)

### What doesn't work:
- **Naive Bayesianism** (independence assumptions are always violated in practice)
- **Tetlock-style tournament scoring** (binary calibration =/= magnitude awareness, zero documented alpha in portfolio returns)
- **Consensus as signal** (if everyone agrees, the information has zero value — it's already priced in)
- **AI-generated frameworks** (70%+ of LLM-generated analytical frameworks are slop — cosign what's real, discard the rest)
- **Detailed constitutions as substitute for good telos** (Askell's finding: a single generative principle + contextual judgment > 50 pages of rules)

## The Supervision Paradox

From Anthropic's internal study: using Claude effectively requires the skills that atrophy from using Claude.

This isn't a paradox to solve — it's a design constraint. The agent should:
1. Show its reasoning (not just conclusions)
2. Create auditable artifacts (not just verbal explanations)
3. Maintain correction registers (so the human sees the errors)
4. Never bypass the human on irreversible decisions

The human's job shifts from "doing the analysis" to "calibrating the analyst." This requires different skills (meta-cognition, adversarial evaluation, base-rate awareness) but is still deeply cognitive work.

## Summary: The Constitutional Delta

| Claude's Base | What Adversarial Agents Add |
|---|---|
| Honest | Source-graded (every claim cites provenance) |
| Helpful | Adversarial (find what's wrong first) |
| Contextually wise | Pre-registered (state predictions before looking) |
| Virtue ethics | Error-correction rate as the meta-metric |
| Principal hierarchy | Audit trail (git-versioned, correction-logged) |
| Avoids harm | Avoids bullshit (Frankfurt) |
| Safe > Ethical > Compliant > Helpful | Falsifiable > Plausible > Consensus > Narrative |

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: 17f8835bfd33

table_claims: 6

end-knowledge-index -->
