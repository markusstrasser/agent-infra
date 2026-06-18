---
title: Requirements Elicitation Best Practices for Single-Principal AI-Agent Kickoff
date: 2026-06-18
status: complete
axis: requirements elicitation (how one principal best specifies work for an executor, esp. AI agents)
relates:
  - skills/interview-prompt/SKILL.md
  - decisions/2026-06-07-guardian-angels-transfer.md
  - memory/feedback_question_scope.md
---

# Elicitation best practices for the agent-infra "plan contract"

## Scope / framing

We have the **proactive, principal-side info-gain mechanism** already:
`interview-prompt` (Gwern Guardian-Angels) = generate 2-3x candidate questions,
predict Markus's answers, ask only the high-variance ones, route to a concrete
artifact. That covers *which question to ask a human whose answer I can't
predict*.

This memo is the **DELTA**: what the kickoff "plan contract" needs that
interview-prompt does NOT supply. Two gaps, both confirmed by the literature:

1. **interview-prompt optimizes question *selection* over an UNTYPED candidate
   pool.** It never says *what fields a kickoff must cover* — it has no checklist
   of the requirement *categories* that get silently missed. RE canon does.
2. **interview-prompt is human-facing and answer-variance-driven.** The agent
   tooling (Spec Kit, Kiro) adds the **executor-side** move: by default *make a
   calibrated guess and record it*, and only escalate to a question when the
   unknown crosses a scope/experience threshold. interview-prompt only models
   "ask"; it never models "assume-and-mark."

So the contract = interview-prompt's *selector* + a *typed coverage checklist*
(what to elicit) + an *assume-vs-ask threshold* (when the agent guesses and logs
vs. interrupts the principal).

---

## Axis 1 — RE canon: what transfers to a 3-5 question kickoff

**Finding: the canon does NOT say "ask the right 3 questions." It says "cover the
right CATEGORIES, because the costly misses are the ones nobody volunteers."**
The transferable unit is a *coverage taxonomy*, not a question list.

- **The guessing game is the failure mode, and it's diagnosed late.** Wiegers:
  "the ultimate symptom of vague requirements is that developers have to ask many
  questions or guess about what is intended, and this guessing game might not be
  recognized until the project is far along and implementation has diverged from
  what is really required." This is precisely the agent freeze/proliferate/
  withhold failure we're designing against — an unspecified kickoff *defers* the
  cost, it doesn't remove it. (Wiegers, *Finding Requirements Wherever They Hide*
  / *10 Requirements Traps*.)
- **Scope is the #1 trap.** Recurring across the canon: "problems of scope … the
  boundary of the system is ill-defined" AND the inverse, stakeholders
  "specify unnecessary technical details that confuse overall system objectives."
  Both directions matter for us: an agent with no scope-OUT over-builds (we have
  a whole anti-over-build rule set); an agent given implementation detail it
  should have chosen itself gets steered off the deeper solution.
- **Straw-man-as-question-source (the highest-transfer canon technique).**
  Wiegers' good-practice: "use areas of uncertainty in straw man models as a
  source of questions" and "go into every session with a set of prepared
  questions." This is the RE-canon *parent* of interview-prompt's predict-step:
  you don't ask cold, you draft the artifact, and the *holes in your own draft*
  generate the questions. For us: the agent should produce a draft plan, and the
  questions are exactly the cells it could not fill confidently.
- **Combine techniques / triangulate.** Canon consensus (Pacheco SLR 2018; the
  interview "family of experiments", Spoletini et al. 2020): no single technique
  is sufficient; interviews + scenarios + prototyping triangulate because each
  surfaces a different *category* of requirement. The kickoff analogue: a single
  free-text prompt is one technique; pair it with a scenario ("walk me through
  the one run that must succeed") and a negative ("what would make this wrong").

**Caveat (frontier timeliness):** the controlled interview experiments
(Spoletini/Ferrari, ScienceDirect 2020) and the SLR (Pacheco, IET 2018) predate
LLM agents and study human-human elicitation. The *taxonomy of what gets missed*
is scale-independent and transfers; the *interview-conduct findings* (interviewer
mistakes, ambiguity in spoken interviews) transfer only by analogy.

---

## Axis 2 — Info-gain question selection NEWER than Gwern's GA

interview-prompt's selector = "score candidates by answer-variance × update-
magnitude." The 2025-26 literature gives a **sharper, formal** criterion and one
concrete upgrade.

- **Active Task Disambiguation (Kobalczyk et al., ICLR 2025, arXiv:2502.04485,
  18 cites).** Frames clarifying-question choice as **Bayesian experimental
  design** maximizing expected information gain — and the load-bearing finding is
  a correction to naive practice: *reason in the SOLUTION space, not the QUESTION
  space.* Questions generated "solely within the space of questions" are weaker;
  effective questions are chosen by *how their answers partition the set of viable
  solutions / eliminate invalid solution paths.* **This is the upgrade to
  interview-prompt:** its current variance proxy scores how much *answers* differ;
  this says score how much the answer *splits the set of plans the agent would
  actually produce.* A question with high answer-variance but where every answer
  yields the same implementation is worthless; a question that looks low-variance
  but forks the architecture is the one to ask.
- **Uncertainty-Aware Clarification with Information Gain (Deng et al., 2026,
  arXiv:2606.03135).** Goal-oriented clarification for *agents* (not chat):
  aligns the decision-to-ask with *latent uncertainty over user intent that would
  otherwise cause an erroneous tool action.* I.e. ask iff the uncertainty would
  change what the agent *does*, not merely what it *believes*. (No DOI/OA text
  yet — abstract-level; flag as fresh-but-unread.)
- **Modeling Future Conversation Turns (Zhang/Knox/Choi, 2024,
  arXiv:2410.13788, 74 cites).** Trains the ask/answer decision by *simulating
  the rest of the conversation* and rewarding the action that leads to the better
  eventual outcome — a lookahead version of interview-prompt's "predict the
  answer" step (predict the whole downstream trajectory, not just the next reply).
- **Teaching LMs to Gather Information Proactively (Huang et al., EMNLP 2025,
  arXiv:2507.21389).** Documents the *default failure*: current LLMs "default to
  passive responses or narrow clarifications" on ambiguous problems. Direct
  support for *architecting* the kickoff rather than trusting the model to ask —
  agents under-ask by default, so the contract must force the coverage.

**Net delta for interview-prompt:** replace/augment the "answer-variance" proxy
with **solution-space split** (EIG over the set of plans the agent would emit).
That is the single most-cited, most-defensible improvement available.

---

## Axis 3 — Eliciting tacit / underivable knowledge vs over-asking

This is the heart of a "plan contract": the small set of things the agent
*cannot derive from the repo, memory, or reasoning* and therefore MUST get from
the principal — and the discipline to NOT ask anything else.

- **The tacit-knowledge problem is real and old.** Nyshadham & Reichental (2006),
  *Effectiveness of interview techniques in the elicitation of tacit knowledge
  for RE in small software projects* — directly our setting (one analyst, small
  scope). Tacit/assumed requirements are the ones stakeholders treat as
  "everybody knows," so they go unstated and surface as divergence later. The
  classic taxonomy of what's tacit: **authority/priority (whose call when values
  conflict), exception/edge behavior, quality-attribute thresholds ("how
  good is good enough"), and explicit scope-OUT.** None of these are derivable
  from code.
- **What is genuinely underivable (ask) vs derivable (never ask):**
  - **Underivable → MUST elicit:** *telos* (why this, what it's for), *authority
    split* (which decisions are Markus's vs the agent's — our
    `feedback_question_scope`: taste/intent/risk/business are his), *exit
    criteria / definition-of-done*, *scope-OUT* (what NOT to build — the
    anti-over-build boundary), *irreversibility/stakes* (what a wrong move costs),
    and *hard constraints* (a named live boundary, a forbidden dependency).
  - **Derivable → NEVER ask:** anything in the repo, in MEMORY.md, in a vetoed-
    decisions file, or decidable by the agent's own competence (implementation,
    naming, library choice). Asking these is the over-ask failure.
- **The over-asking guard is itself in the canon and the agent tooling.** Spec
  Kit's actual template (verified against
  `github/spec-kit/templates/commands/specify.md`, 2026) does NOT mark every
  unknown — it instructs the AI to **make an informed guess by default** and
  reserve `[NEEDS CLARIFICATION]` markers for cases that **"significantly impact
  scope or experience,"** plus a dedicated `/speckit.clarify` step to resolve
  those interactively before planning. This is a **calibrated threshold**, and it
  maps 1:1 onto our two stored feedbacks: `feedback_question_scope` (only ask
  taste/intent/telos/risk) and `feedback-see-it-through-when-confident` (don't
  ask on reversible/no-tradeoff). The literature, the tool, and our own memory
  converge: **ask only when the unknown is (a) underivable AND (b) high-impact
  (scope/experience/irreversible); otherwise assume-and-record.**

---

## Axis 4 — 2025-26 AI-agent / spec-driven elicitation patterns

How shipping agent tools elicit intent up front (Spec Kit, Kiro, Cursor,
Antigravity, OpenSpec, BMAD — all shipped an SDD flavor in 2025-26;
Thoughtworks 2025; arXiv:2602.00180).

- **The spec is a typed contract, not a prompt.** The cross-tool consensus spec
  has **six elements: outcomes, scope boundaries, constraints, prior decisions,
  task breakdown, verification/acceptance criteria** (Thoughtworks; BCMS 2026
  guide; arXiv:2602.00180). This is the *coverage checklist* our plan contract is
  missing — and notably it is mostly the *underivable* set from Axis 3
  (outcomes/scope/constraints/prior-decisions/acceptance), plus task-breakdown
  which the agent can draft.
- **Phased: constitution → specify → plan → tasks → implement** (Spec Kit). The
  "constitution" = standing principles that don't change per task (we already
  have one). "Specify" = the per-task contract. The separation matters: standing
  context (constitution/memory) should NOT be re-elicited per kickoff — only the
  per-task delta.
- **Make-a-guess-and-mark, then /clarify** (Spec Kit, verified above) — the
  executor-side discipline interview-prompt lacks.
- **Human role is verify, not steer.** Spec Kit framing: "your role isn't just to
  steer, it's to verify" via explicit checkpoints. The principal's scarce
  attention goes to *checking the draft contract + answering the few marked
  clarifications*, not authoring the spec. This is exactly our amplify-not-
  automate stance (`feedback-amplify-automate-by-verifiability`).

**AI-text caveat:** the SDD blog ecosystem is vendor marketing and LLM-written
think-pieces (Medium "definitive guide" posts). I grounded the load-bearing
claims (Spec Kit marker behaviour, six-element spec) against the actual Spec Kit
repo template and the Thoughtworks engineering post, not the Medium pieces.

---

## RANKED — techniques that transfer to our kickoff contract

Ranked by value-to-our-design (each is a concrete addition, not a restatement of
interview-prompt):

1. **Adopt the six-element typed coverage checklist** (outcomes · scope-OUT ·
   constraints · prior-decisions · acceptance/exit-criteria · authority-split).
   This is the biggest gap: interview-prompt selects questions but never enforces
   *what a kickoff must cover.* Source: SDD cross-tool consensus +
   Wiegers scope-trap + Axis-3 tacit taxonomy. **The kickoff fails if any of the
   first five cells is empty.**
2. **Switch the question-selection proxy from answer-variance to SOLUTION-SPACE
   split** (expected information gain over *the set of plans the agent would
   emit*). A question earns a slot only if its answers fork the actual plan.
   Source: Active Task Disambiguation, ICLR 2025 (arXiv:2502.04485). This is the
   single best-supported upgrade to interview-prompt's mechanism.
3. **Add the assume-vs-ask threshold (make-a-guess-and-mark).** Default: the
   agent records a calibrated assumption inline; it interrupts the principal ONLY
   when the unknown is underivable AND crosses scope/experience/irreversibility.
   Source: Spec Kit `[NEEDS CLARIFICATION]` (verified) + our
   `feedback-see-it-through-when-confident`. This is what stops over-asking — the
   failure mode interview-prompt can produce if every low-confidence cell becomes
   a question.
4. **Straw-man-first: the agent drafts the plan, the holes ARE the questions.**
   Don't elicit cold. Produce a draft contract; the cells the agent can't fill
   confidently become the (filtered) question set. Source: Wiegers "straw man
   models as a source of questions." Operationally unifies #1-#3: draft the six
   cells → mark the unfillable → keep only the solution-space-splitting marks.
5. **Triangulate the free-text ask with a scenario + a negative.** One prompt is
   one technique. Add "the one run/output that MUST succeed" (scenario → surfaces
   acceptance criteria) and "what would make this wrong / what should it NOT do"
   (negative → surfaces scope-OUT, the most-missed category). Source: RE
   multi-technique consensus (Pacheco SLR 2018) + scope-trap canon.
6. **Separate standing context from per-task delta.** Don't re-elicit what's in
   the constitution/MEMORY/vetoed-decisions. Only the per-kickoff delta is
   in-scope to ask. Source: Spec Kit constitution/specify split; our own
   prior-context hooks already do this for prompts — the kickoff should inherit
   it.

## What to ADD to interview-prompt specifically

interview-prompt stays the *selector*. Three concrete edits make it kickoff-grade:

- **Add a Step-0 coverage gate (the six cells).** Before brainstorming questions,
  enumerate the six contract cells and mark each derivable / assumed / unknown.
  Questions may ONLY target `unknown` cells. This bolts the typed checklist onto
  the front and structurally prevents asking derivable things (#1, #3, #6).
- **Re-define the scoring proxy.** Today: "answer variance × update-magnitude"
  (step 3). Change to: **expected split of the agent's *solution/plan* set** —
  for each candidate, sketch the 2-3 plans each answer would produce; keep
  questions where the plans *diverge*, drop where they converge even if the
  worded answers differ (#2). This is a one-paragraph edit to step 3 with an
  ICLR-2025 citation.
- **Add the assume-and-mark branch.** interview-prompt currently has only "ask"
  and "drop (I can answer it)." Add a third outcome: **"assume + record"** — for
  unknown-but-low-impact cells, write the assumption into the draft contract
  instead of asking. Only underivable-AND-high-impact unknowns become
  AskUserQuestion items (#3). This is the over-ask guard, and it makes the skill
  consistent with `feedback-see-it-through-when-confident`.

Net: interview-prompt becomes "fill the six-cell contract by drafting, assume the
low-stakes holes, and ask only the high-stakes holes whose answers fork the plan."

---

## Sources

- Karl Wiegers, *10 Requirements Traps to Avoid* — http://users.csc.calpoly.edu/~csturner/courses/300f06/readings/reqtraps.pdf
- Karl Wiegers, *Finding Requirements Wherever They Hide* — https://medium.com/analysts-corner/finding-requirements-wherever-they-hide-b160b602ef40
- Karl Wiegers, *16 Good Practices for Requirements Elicitation* — https://medium.com/analysts-corner/16-good-practices-for-requirements-elicitation-9a805c663c84
- Pacheco et al., *Requirements elicitation techniques: a systematic literature review based on maturity* (IET Software 2018) — https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-sen.2017.0144
- Spoletini/Ferrari et al., *Requirements elicitation methods based on interviews in comparison: a family of experiments* (Inf. & Software Tech. 2020) — https://www.sciencedirect.com/science/article/abs/pii/S0950584920301282
- Nyshadham & Reichental, *Effectiveness of interview techniques in the elicitation of tacit knowledge for RE in small software projects* (2006) — S2 CorpusId:108114784
- Kobalczyk et al., *Active Task Disambiguation with LLMs* (ICLR 2025) — https://arxiv.org/abs/2502.04485
- Deng et al., *Uncertainty-Aware Clarification in LLM Agents with Information Gain* (2026) — https://arxiv.org/abs/2606.03135
- Zhang, Knox, Choi, *Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying Questions* (2024) — https://arxiv.org/abs/2410.13788
- Huang et al., *Teaching Language Models To Gather Information Proactively* (EMNLP 2025) — https://arxiv.org/abs/2507.21389
- Thoughtworks, *Spec-driven development: unpacking one of 2025's key new AI-assisted engineering practices* (2025) — https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices
- GitHub, *Spec-driven development with AI: open-source toolkit (Spec Kit)* — https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- GitHub Spec Kit specify template (verified: make-a-guess + [NEEDS CLARIFICATION] threshold + /speckit.clarify) — https://github.com/github/spec-kit/blob/main/templates/commands/specify.md
- *Spec-Driven Development: From Code to Contract in the Age of AI Coding Assistants* (arXiv:2602.00180) — https://arxiv.org/html/2602.00180v1

## Provenance / gotchas
- `mcp__research__fetch_paper` failed on both arXiv targets (DOI route + no-OA-URL); used arXiv /abs via WebFetch for the mechanism. Consistent with prior memos — arXiv full-text needs the HTML route, not fetch_paper.
- Wiegers `reqtraps.pdf` = cert error on WebFetch; the Medium twin truncated. The load-bearing Wiegers claims (scope trap, guessing-game-discovered-late, straw-man-as-question-source) came through the WebSearch result snippet, not full-text — graded accordingly.
- Spec Kit marker behaviour: GitHub blog *denied* the marker exists; `verify_claim` against the actual repo template *contradicted the blog* and confirmed the calibrated-threshold design. Primary (repo) beats secondary (blog).
