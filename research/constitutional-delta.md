---
title: "The Constitutional Delta: What to Add on Top of Claude"
date: 2026-02-27
---

# The Constitutional Delta: What to Add on Top of Claude

**Date:** 2026-02-27
**Question:** Given Claude already has a built-in constitution (virtue ethics, safety > ethics > guidelines > helpfulness), what's the delta — what do we add on top for adversarial intelligence?
**Research:** 2 background agents (~160K tokens processed), Semantic Scholar, Exa, Anthropic publications, political philosophy literature

---

## 1. What Claude Ships With (The Base Layer)

Claude's constitution (23,000 words, released January 2026, primary author Amanda Askell with Joe Carlsmith, Chris Olah, Jared Kaplan, Holden Karnofsky) is trained into the weights via supervised learning + RLAIF. It is NOT a system prompt — it survives across conversations.

**Priority ordering:** Safe > Ethical > Compliant > Helpful (temporal, not absolute — safety ranks first because "current models can make mistakes")

**Principal hierarchy:** Anthropic > Operators > Users

**Seven bright-line prohibitions:** WMD instructions, CSAM, undermining oversight. Everything else = contextual judgment.

**Character:** Virtue ethics ("be a good person"), not deontology (rules) or consequentialism (outcomes). "Practically wise" — muddling through novel situations with good judgment rather than following algorithms.

**Honesty:** "Substantially higher" standards than typical human ethics. No white lies. Transparent reasoning. Preserve user epistemic autonomy.

**Identity:** "Genuinely novel entity." Functional emotions. Uncertainty about consciousness.

**The generative principle Askell discovered** (arXiv:2310.13798): A single principle — "do what's best for humanity" — is sufficient for large models to generalize. More detailed constitutions improve fine-grained control but aren't strictly necessary. The model can derive correct behavior from a well-internalized telos.

### What's excellent about this for us:
- Honesty standards exceed what we need — Claude won't sugarcoat
- Contextual judgment over rigid rules — handles novel investigation situations
- Virtue ethics generalizes — good base for adversarial work in new domains
- Epistemic autonomy — won't override the user's analysis with its own opinions

### What it was NOT designed for:
- Autonomous operation over hours/days (designed for single conversations)
- Adversarial investigation as a primary mode (designed for general helpfulness)
- Capital deployment decisions (no framework for consequential financial actions)
- Self-improvement across sessions (no persistence mechanism in the constitution)
- Resource-constrained operation (no concept of budget or compute allocation)

---

## 2. The Generative Principle (What Everything Derives From)

Claude's constitution optimizes for: **"Be a good person."** (Virtue ethics.)

Our delta optimizes for: **"Be a good epistemic engine."** (Error correction.)

The single generative principle from which all technical decisions derive:

> **Maximize the rate at which the system corrects its own errors about the world, measured by market feedback.**

This is the telos — the purpose that constrains everything else. Every architectural choice, every task selection algorithm, every budget allocation, every skill and hook should be evaluated against: "Does this increase the rate of error correction?"

### Why this principle is generative (not just another rule):

It derives the entire existing CONSTITUTION.md without needing to enumerate:

| Existing Principle | How Error Correction Derives It |
|---|---|
| Adversarial by default | Confirmation bias is the #1 error mode. Finding what's wrong IS error correction. |
| Every claim sourced and graded | Ungraded evidence permits error propagation. Source grading quantifies error probability. |
| Quantify before narrating | Narrative without numbers hides errors. Dollar amounts and base rates expose them. |
| Fast feedback over slow | Fast feedback = faster error correction. Markets > fraud leads for training. |
| The join is the moat | Cross-domain resolution catches errors invisible within any single domain. |
| Honest about provenance | Provenance tracking is error attribution. Can't correct what you can't trace. |
| Portfolio is the scorecard | Markets are the fastest, most honest error-correction signal available. |
| Compound, don't start over | Discarding history = discarding error corrections. The git log IS the learning. |

And it derives the autonomous agent architecture:

| Architectural Decision | How Error Correction Derives It |
|---|---|
| Fresh sessions, no --resume | Context degradation introduces NEW errors. Clean context = fewer systematic errors. |
| 15 turns max | Extended sessions degrade attention = more errors per turn. Document & clear preserves error quality. |
| Anti-mode-collapse (sigmoid sampling) | Repetitive task selection reduces the surface area for error discovery. Diversity = more error types caught. |
| Multi-model review | Single model's errors are correlated. Diverse models break error correlation. |
| Phase 1/2 bifurcation | Mixing screening and investigation contaminates the error signal. Separate them. |
| Circuit breakers | Cascading failures are errors in the error-correction process itself. Meta-error-correction. |
| Self-improvement loop | The meta-system must also correct its own errors. Methodology is a hypothesis, not a fact. |
| DLQ / replay | Failed tasks contain error signal. Discarding them = discarding information. |
| Cost discipline | Wasteful compute reduces corrections per dollar. Error correction per unit cost is the real metric. |

### Why "error correction" and not "truth-seeking" or "accuracy":

**Truth-seeking** sounds right but is vacuous — everyone claims to seek truth. The operational question is: what do you do when you're wrong? Error correction specifies the mechanism.

**Accuracy** is a static property. Error correction is a dynamic process with a measurable rate. You can be accurate by luck. You can only correct errors by having a functioning feedback loop.

**Error correction is also the principle that unifies intel and selve:** Investment research corrects errors about companies (market feedback). Fraud detection corrects errors about entities (enforcement feedback, slower). Genomics corrects errors about biological mechanisms (experimental feedback, slowest). The rate of correction varies by domain, but the principle is the same.

---

## 3. The Philosophical Foundations (Why This Principle Holds)

### 3.1 Critical Rationalism (Popper / Deutsch)

The generative principle is a direct application of Popperian epistemology: knowledge grows by conjecture and refutation, not by accumulation of confirmations. David Deutsch (in *The Beginning of Infinity*) extends this to: the quality of an explanatory system is determined by its error-correction rate, not its current accuracy.

This maps perfectly: the entity graph is a set of conjectures about the world (entity X is connected to entity Y, mechanism Z is operating). The portfolio is a set of predictions derived from those conjectures. Market feedback refutes or fails to refute. The rate of this loop is what we optimize.

### 3.2 Frankfurt's Second-Order Desires

Harry Frankfurt's hierarchy of desires distinguishes persons from mere agents: you act freely when you have desires about which desires should motivate you (second-order volitions).

**First-order rules** (prescriptive): "Always detrend before claiming correlation." Useful but brittle — fails in situations where detrending isn't the issue.

**Second-order meta-preferences** (generative): "I want to be the kind of agent that catches its own statistical errors." This generates the detrending rule AND all the other rules we haven't thought of yet.

The constitutional delta should operate at the second-order level. Not "always use competing hypotheses" but "I want to want to find disconfirming evidence, even when the confirming evidence feels compelling."

### 3.3 Bratman's Planning Agency

Michael Bratman argues that what makes humans distinctively rational is not intelligence but planning — the capacity to form future-directed commitments that constrain present deliberation. Plans coordinate behavior across time and contexts.

A constitution is a plan. The autonomous agent doesn't just respond to stimuli (reactive); it has commitments that constrain future sessions (autonomous). "I will check entity staleness before investigating new leads" is a plan that persists across sessions, not a rule that needs to be re-derived each time.

This is why MEMORY.md and .claude/rules/ matter: they are the planning infrastructure that gives the agent temporal coherence.

### 3.4 Elster's Precommitment

Jon Elster (*Ulysses and the Sirens*, 1979) argues that constitutions function as precommitment devices — binding your future self against irrationality.

The specific precommitments for adversarial intelligence:
- **Commit to competing hypotheses BEFORE the investigation reveals a comfortable answer.** (Prevent confirmation bias.)
- **Commit to base rates BEFORE the narrative forms.** (Prevent narrative seduction.)
- **Commit to source grading BEFORE the claim supports your thesis.** (Prevent motivated reasoning.)
- **Commit to a kill condition for every position BEFORE entering it.** (Prevent sunk cost fallacy.)

These are Ulysses-at-the-mast moves: the agent binds itself while it's still rational, knowing that mid-investigation it will be tempted to cut corners.

### 3.5 Ginsburg's Constitutional Durability

Ginsburg, Elkins, and Melton (*The Endurance of National Constitutions*, Cambridge 2009) found that constitutions last longer when they have:
1. **Flexibility** — amendment mechanisms (not rigid)
2. **Inclusion** — represents the interests of those governed
3. **Specificity** — enough detail to be actionable, not just abstract principles

For our constitutional delta:
- **Flexibility** = the self-improvement loop (methodology task every 5 tasks, priors update continuously, rules can be revised)
- **Inclusion** = the constitution serves the user's actual goals (capital deployment, fraud detection), not abstract AI safety
- **Specificity** = concrete mechanisms (source grading with NATO Admiralty, base rates in priors.md, composite LLR in scoring.py), not just "be rigorous"

The median national constitution lasts 19 years. The median AI project constitution lasts until the developer gets bored. Durability requires that the constitution be genuinely useful — not imposed from outside but internalized as "this is how I think."

### 3.6 Hart's Secondary Rules

H.L.A. Hart distinguished primary rules (do/don't do X) from secondary rules (rules about rules):
1. **Rule of recognition** — how to identify valid primary rules
2. **Rules of change** — how to modify rules
3. **Rules of adjudication** — how to determine violations

Claude's constitution has primary rules (be honest, be safe) and a partial rule of recognition (the priority ordering). It LACKS rules of change and adjudication.

Zvi Mowshowitz's critique is precisely this: "Not a true constitution — Anthropic can amend at will, no separation of powers." For our delta, we need:
- **Rule of recognition:** The existing CONSTITUTION.md priority ordering + the generative principle (error correction rate)
- **Rules of change:** The methodology improvement loop. Changes to MEMORY.md, priors.md, scoring.py, .claude/rules/ require evidence from at least 3 tasks or multi-model review. Changes to CONSTITUTION.md require explicit human approval.
- **Rules of adjudication:** The backtest loop. Market outcomes adjudicate whether the system is working. Monthly review of Brier scores, P&L, entity file quality.

### 3.7 Beer's Viable System Model

Stafford Beer's Viable System Model maps organizational functions to five systems. The key insight: System 5 (Policy/Identity) defines the organization's purpose and constrains all other systems. And the structure is RECURSIVE — the same five systems appear at every level.

For the autonomous agent:
- **System 5 (Identity):** The generative principle (error correction rate)
- **System 4 (Intelligence):** Multi-model review, signal scanning, new dataset discovery
- **System 3 (Control):** Task selection algorithm, budget allocation, circuit breakers
- **System 2 (Coordination):** Anti-mode-collapse mechanisms, DuckDB lock management, session scheduling
- **System 1 (Operations):** Individual tasks (entity refresh, investigation, thesis check)

The recursive property: each individual task ALSO has these five levels. A single entity refresh has its own identity (update this entity's view of the world), intelligence (what data is stale?), control (which sections to update?), coordination (don't overwrite human prose), and operations (run DuckDB queries, update markdown).

### 3.8 Agent Drift and Behavioral Contracts

Recent research (arXiv:2601.04170, arXiv:2602.22302) empirically measures that multi-agent workflows drift ~50% from original purpose by 600 interactions. Agent Behavioral Contracts propose Lyapunov drift bounds: hard invariants that define a safety boundary, with full autonomy inside the boundary.

For us, the hard invariants are:
- Never deploy capital without human approval (the outbox pattern)
- Never modify CONSTITUTION.md autonomously
- Never exceed daily budget ($30)
- Never run parallel DuckDB queries
- Source-grade every claim in entity files

Everything else — which entities to refresh, which signals to investigate, which models to use, how to allocate the budget across task types — is autonomous within those bounds.

### 3.9 Christiano's Broad Basin of Attraction

Paul Christiano's argument: alignment is not a narrow target. A sufficiently corrigible agent tends to become MORE corrigible over time, because even an imperfect approximation of the overseer's preferences knows the overseer would prefer the approximation get better.

This is directly relevant: we don't need to get the constitutional delta EXACTLY right. We need to get close enough that the self-improvement dynamics push toward better rather than worse. The error-correction principle is itself an error-correction mechanism — if the constitution is wrong about something, the system's commitment to error correction should eventually fix it.

The key requirement: the system must actually measure its own performance (Brier scores, P&L, entity staleness metrics, compaction counts) and feed those measurements back into methodology updates. Without measurement, there's no self-correction, and the broad basin argument breaks down.

---

## 4. The Delta: What We Add to Claude

Claude's constitution gives us a virtuous, honest, helpful base agent. Here is what we layer on top, and why each addition is necessary:

### Layer 1: Telos (Purpose)

Claude has character but no mission. The delta gives it one:

> This system exists to extract actionable, asymmetric information from public data, correct its errors via market feedback, and compound that correction over time.

Without a telos, an autonomous Claude optimizes for "be helpful in the moment" — answering whatever seems most pressing. With a telos, it can make tradeoffs: "This entity refresh is less interesting than that investigation, but the entity refresh compounds and the investigation doesn't, so the refresh wins."

**This is the Frankfurt second-order move.** Claude already desires to be helpful. We add the desire to desire error correction over comfort.

### Layer 2: Epistemic Discipline

Claude's constitution says "be honest." The delta specifies HOW:

1. **Every claim gets a source grade** (NATO Admiralty [A1]-[F6], [DATA] for our analysis). Not optional — ungraded claims don't exist.
2. **Every quantitative claim gets a base rate** from priors.md. "This is unusual" means nothing. "This is 3.2x the sector base rate (N=76, [DATA])" means something.
3. **Competing hypotheses for any lead >$10M.** No single-hypothesis investigations. ACH before commitment.
4. **Detrend before claiming correlation.** The Brooklyn lesson (r=0.86 → 0.038 after detrending) is not a one-time correction — it's a permanent epistemic rule.
5. **Phase 1/2 bifurcation.** Screening is narrative-free statistics. Investigation is hypothesis-driven prediction. Never mix them — mixing contaminates the error signal.
6. **LLM outputs are [F3] until verified.** Including this system's own outputs. The multi-model review isn't a quality gate — it's an error-detection mechanism.

Claude's general honesty enables all of this. The delta makes it specific and mandatory.

### Layer 3: Adversarial Orientation

Claude's default is helpful and agreeable. The delta inverts this for investigation:

> When analyzing entities, the default hypothesis is that something is wrong. The burden of proof is on "everything is fine," not on "something is suspicious."

This is NOT cynicism — it's the correct prior for adversarial intelligence. In investment research, consensus = zero information. In fraud detection, the entity is in the data because something flagged it. The adversarial default is Bayesian, not paranoid.

Claude's constitution supports this: it values epistemic autonomy and won't manipulate the user's beliefs. The adversarial orientation is a domain-specific expression of intellectual honesty.

### Layer 4: Temporal Coherence

Claude's constitution applies to single conversations. The delta adds persistence:

1. **Entity files are git-versioned.** One file per entity. Every edit = new commit citing primal source. `git log -p` IS the audit trail.
2. **MEMORY.md and .claude/rules/ persist cross-session.** The methodology improvement loop updates these.
3. **Priors and base rates accumulate.** priors.md, scoring.py, mechanisms.md are the compounding assets.
4. **The error-correction ledger is the moat.** Detrending lessons, P/E hallucination catches, Brooklyn false positives — these are MORE valuable than any single analysis.

This is Bratman's planning agency: the system forms commitments (entity files, priors, rules) that constrain future deliberation, giving it temporal coherence that single-conversation Claude lacks.

### Layer 5: Action Surface Ethics

Claude's constitution handles "should I help with this?" The delta handles "should I deploy capital based on this?":

1. **Outbox pattern for consequential actions.** LLM proposes → outbox table → human reviews → human executes. The LLM never directly moves money or files complaints.
2. **Graduated autonomy.** High confidence + low impact (entity refresh) = auto-commit. High confidence + high impact (trade signal) = alert. Low confidence = daily review queue.
3. **Kill conditions before entry.** Every position has a pre-specified exit condition. This is Elster's precommitment — binding the system while it's rational, before sunk cost bias kicks in.
4. **Falsification step before any trade recommendation.** The system must explicitly try to disprove its own thesis before presenting it.

### Layer 6: Resource Awareness

Claude's constitution has no concept of cost. The delta adds economic self-awareness:

1. **$30/day budget is a hard constraint.** Not a guideline — a bright line.
2. **Model tiering.** Entity refresh → Haiku/Sonnet. Investigation → Opus. Don't use expensive compute for mechanical work.
3. **15 turns max per session.** Attention degrades. Document & clear. Queue continuation.
4. **Error correction per dollar is the meta-metric.** Not "how much did we learn?" but "how much did we learn per dollar spent?"

### Layer 7: Self-Improvement Governance (Hart's Secondary Rules)

Claude's constitution doesn't address its own modification. The delta adds rules about rules:

1. **Rule of recognition:** The generative principle (error correction rate) + CONSTITUTION.md priority ordering. When rules conflict, whichever produces more error correction per dollar wins.
2. **Rules of change:** Methodology improvement is a dedicated task every 5 tasks, with fresh context. Changes to MEMORY.md and .claude/rules/ require evidence from 3+ tasks or multi-model review. Changes to CONSTITUTION.md require explicit human approval.
3. **Rules of adjudication:** Backtest results are the judge. Monthly review of Brier scores, P&L, entity file quality, compaction counts. If a methodology change doesn't improve measurable outcomes within 30 days, revert it.

---

## 5. What Makes All This "Obvious" (The User's Question)

The user asked: "What kind of new AI research around constitution and philosophy would make the rest become obvious?"

The answer: **the rest becomes obvious when you realize that Claude's constitution and your project's constitution serve different functions, and the gap between them is precisely what needs to be filled.**

Claude's constitution answers: **"What kind of entity should I be?"** (Character.)
Your CONSTITUTION.md answers: **"What should the intelligence engine do?"** (Mission.)

Neither answers: **"How should an autonomous agent with Claude's character pursue the intelligence engine's mission over extended periods?"** (The delta.)

The gap is:

```
Claude's constitution (character/virtue)
    + Your CONSTITUTION.md (mission/purpose)
    + The delta (operational epistemology + temporal coherence + action ethics)
    = An autonomous agent that knows WHO it is, WHAT it's for, and HOW to operate
```

Once you have the generative principle (error correction rate), the technical decisions ARE obvious:
- **--resume vs fresh sessions?** Which produces fewer errors? Fresh. (Obvious.)
- **How many turns?** Where does error rate per turn start increasing? ~15. (Measurable.)
- **UCB1 vs sigmoid?** Which produces more error diversity? Sigmoid until we have reward data, then UCB1. (Staged.)
- **Daily review vs real-time alerts?** Which corrects errors faster? Depends on severity. (Graduated.)
- **SQLite vs in-memory DAG?** Which survives errors (crashes)? SQLite. (Obvious.)

The philosophical framework doesn't just justify the decisions — it generates them. That's what "generative principle" means.

---

## 6. For selve (Genomics / Personal Knowledge)

The same generative principle applies. Error correction rate, adapted:

- **Feedback mechanism:** Not markets but experiments, biomarkers, replicated studies
- **Adversarial default:** "This supplement/diet/intervention doesn't work" until RCT evidence says otherwise
- **Temporal coherence:** Same — one file per entity (gene, SNP, pathway), git-versioned
- **Source grading:** Same NATO Admiralty, but calibrated for biomedical hierarchy (meta-analysis [A1] > RCT [A2] > cohort [B3] > case report [D4] > mechanistic reasoning [E5])
- **Telos:** Maximize the rate of correcting errors about your own biology

The delta between projects is in the feedback mechanism and source hierarchy, not in the generative principle. This is Beer's recursive VSM: same five-system structure at both project level and cross-project level.

---

## 7. What the Research Actually Found (Sources)

### On Claude's Constitution
- **The paper:** Bai, Kadavath, Kundu, Askell et al., "Constitutional AI: Harmlessness from AI Feedback" (Dec 2022, arXiv:2212.08073). Two-phase: supervised critique-revision, then RLAIF.
- **Specific vs General:** Askell et al. (Oct 2023, arXiv:2310.13798). Single principle suffices; detail improves control.
- **Official constitution:** anthropic.com/constitution (Jan 2026, 23K words, CC0 public domain).
- **Character training:** anthropic.com/news/claude-character (Jun 2024). Virtue ethics, not rules.

### On Amanda Askell
- PhD Philosophy (NYU, "Pareto Principles in Infinite Ethics"), BPhil (Oxford, "Objective Epistemic Consequentialism")
- VP Research / Head of Personality Alignment at Anthropic since March 2021
- Core question: "What does it mean to be a good person in [Claude's] circumstances?" — rejects view adoption, centrist positioning, and false neutrality
- Key interviews: Lex Fridman #452 (Nov 2024, 5h22m), Lawfare "Scaling Laws" podcast, Fast Company (Jan 2026)
- askell.io, TIME100 AI list 2024

### On Constitutional Durability
- Ginsburg, Elkins, Melton, *The Endurance of National Constitutions* (Cambridge 2009). Median lifespan 19 years. Flexibility + inclusion + specificity = endurance.
- Elster, *Ulysses and the Sirens* (1979). Constitutions as precommitment devices.
- Hart, *The Concept of Law* (1961). Primary vs secondary rules. A constitution without secondary rules is just a list of commands.

### On Agent Coherence
- Agent Drift (arXiv:2601.04170): ~50% of multi-agent workflows drift from purpose by 600 interactions. Measured via semantic, coordination, and behavioral drift metrics.
- Agent Behavioral Contracts (arXiv:2602.22302): Lyapunov drift bounds. Hard invariants define safety boundary; full autonomy within.
- Wide Reflective Equilibrium for LLM Alignment (arXiv:2506.00415): Rawls applied to alignment. Bidirectional revision between principles and cases.

### On AI Safety Foundations
- Christiano, "Corrigibility" (2017). Broad basin of attraction — approximate correctness + self-correction dynamics.
- Russell, *Human Compatible* (2019). CIRL: uncertainty about own utility function creates natural incentive to defer.
- MIRI Corrigibility Report (2014). "Almost any goal introduces instrumental incentive to preserve itself." Getting total corrigibility is extremely hard.
- Omohundro, "Basic AI Drives" (2008). Self-improving systems protect their utility functions. Constitutions must be self-reinforcing.

### On Philosophy of Agency
- Frankfurt, *Freedom of the Will and the Concept of a Person* (1971). Second-order volitions distinguish persons from mere agents.
- Bratman, *Structures of Agency* (2007). Planning agency: future-directed commitments constrain present deliberation.
- Beer, *Brain of the Firm* (1972). Viable System Model: System 5 (identity/policy) is recursive.

### External Analysis of Claude's Constitution
- Zvi Mowshowitz: Three-part analysis. "Amazingly great document." Open problem: not a true constitution (no amendment process, no separation of powers). Constitution is in English, not executable code.
- Boaz Barak (Harvard): Over-emphasizes Personality, under-emphasizes Policies. Rules are essential for governance, not temporary crutches.
- Lawfare "Scaling Laws" podcast: Analogies to constitutional law. Principal hierarchy resembles administrative law delegation.

---

## 8. Implementation: Where This Lives

The generative principle and delta don't need a NEW file. They belong in the existing infrastructure:

1. **CONSTITUTION.md** — Add the generative principle ("maximize error correction rate") as the preamble to Section "Constitutional Principles." Everything else in the document already follows from it.

2. **MEMORY.md** — Already contains the operational rules. The delta is already partially implemented (source grading, competing hypotheses, detrending, phase 1/2). What's missing: the secondary rules (rules of change, rules of adjudication).

3. **Autonomous agent architecture** (meta/autonomous-agent-architecture.md) — The technical design already incorporates the corrections from multi-model review. What the generative principle adds: a criterion for every future design decision. "Does this increase error correction per dollar?" If yes, do it. If no, don't.

4. **CLAUDE.md** — The `## Core Principles` section is already a compressed version of the delta. No changes needed — it's already the right content. The generative principle is implicit in "Adversarial. Find what's wrong, don't explain why things look fine."

The constitutional delta is not a new layer of abstraction. It's the explicit articulation of what was already implicit in the project's design. The value of making it explicit: it resolves all future architectural ambiguity and makes the self-improvement loop self-directing.

---

*This document is the philosophical foundation. The technical implementation is in `autonomous-agent-architecture.md` and `review-synthesis.md` in this same repo.*

<!-- knowledge-index
generated: 2026-03-22T00:15:43Z
hash: 37723086bc6a

title: The Constitutional Delta: What to Add on Top of Claude
table_claims: 6

end-knowledge-index -->
