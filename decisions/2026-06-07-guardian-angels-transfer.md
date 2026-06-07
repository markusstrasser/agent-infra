---
id: 2026-06-07-guardian-angels-transfer
concept: personalization-elicitation
repo: agent-infra
decision_date: 2026-06-07
recorded_date: 2026-06-07
provenance: contemporaneous
status: accepted
initial_leaning: assess Gwern's "Guardian Angels" essay for transferable mechanisms; expected most to be out of scope, write up the cosigns and reject the speculative builds
relations: []
---

# 2026-06-07: Guardian Angels (Gwern) — what transfers to agent-infra

## Context
Reviewed Gwern's essay *"Guardian Angels: LLM Personalization for Productivity
and Security"* (gwern.net, 2025–2026) against our systems. The essay's thesis:
personalize an LLM to *emulate the principal* (their personality/values/
preferences) rather than serve a generic assistant persona, via **in-weight
finetuning (dynamic evaluation)**, **active learning** (query the principal),
an **append-only log** UX, and **data augmentation** of the corpus before
training. The question: can we learn or integrate anything?

The essay's **spine is structurally out of scope** — dynamic evaluation means
finetuning your own model online. agent-infra is a harness/hooks/rules/memory
layer over **frozen** API models (Claude/GPT/Gemini). We cannot update weights.
So the assessment filters for analogies that survive the substrate swap
(frozen-model + harness, *not* finetuned weights).

## Alternatives considered
1. **Treat it as out-of-scope vision and move on** — defensible (we can't
   finetune), but throws away the transferable principles and the strategic
   frame. Rejected as too dismissive.
2. **Cosign the principles, build the one novel mechanism, reject the
   speculative one, record the ceiling** (chosen) — see Decision.
3. **Pursue in-weight personalization** (a personal "GBT") — rejected outright.
   That is a different company, not a meta-repo change; requires owning a model,
   training infra, and the security/hardware stack the essay itself spends half
   its length on. No.

## Counterevidence sought
Before deciding the GA mechanisms were mostly already-built cosigns, looked for
the inverse — a GA idea we *lack* and provably need:
- **Daydream loop** (recombine log items in downtime → novel connections):
  `grep -ril daydream` over the repo = **0 hits**, despite the constitution
  referencing the "DDL daydreaming loop." So it is a genuine gap, not a
  duplicate. But there is **no evidence we are missing cross-memory
  connections**, and a scheduled-LLM recombination job is generation-without-
  consumption (our #1 documented disease) and re-opens the API-cost surface the
  constitution deliberately closed 2026-04-24. Gap ≠ mandate. Rejected on
  maintenance + demand, not on novelty.
- **Interview-prompt active learning** (`grep -ril "interview prompt"` = only
  research memos, never implemented): a real, unbuilt mechanism with a clear
  consumer. This one survived — see Decision.

## Decision
Three-part outcome:

1. **Out of scope — in-weight personalization (the GA spine).** We operate on
   the harness layer Gwern explicitly names as the *clumsy workaround* for not
   being able to update weights. Not pursued. (See "the ceiling," below.)

2. **Cosign — the essay validates architecture we already shipped.** No build
   needed; the value is theoretical grounding worth citing:
   - **CIRL / learn-from-corrections / DAgger regret bounds** → our
     **session-learning loop** (`scripts/reflect.py`, FM dossiers,
     `/observe`→`/improve` route, [[session-learning-loop-design]] (memory)). Gwern's
     CIRL framing — agent errs, principal supplies the correct answer, agent
     need never err that way again — is the theory under our correction-mining.
   - **Append-only log as the core data structure** → memory (append-only),
     `git log is the learning`, daily logs. Constitutional already.
   - **Data augmentation closes the finetune↔in-context gap** → this *is* our
     `merge-before-mint / addressability ≠ generalization` invariant: raw
     captured corrections must be generalized + annotated, not stored verbatim.
   - **Personality emulation** → the `writing-style` skill (Markus's voice).

3. **Build — the interview-prompt elicitation skill** (SHIPPED this session,
   `~/Projects/skills/interview-prompt/`). The one genuinely-novel transferable
   mechanism: generate many candidate questions about a topic/draft, sketch
   hypothetical Markus-answers for each, score by information gain (answer
   variance × how much it would change a preference profile), ask the top
   1–3 via AskUserQuestion, route answers into `feedback` memory or the
   `writing-style` corpus. Passes our bars: **clear consumer** (writing-style +
   feedback memory — not generation-without-consumption), **low-maintenance**
   (a skill, not a scheduled job), and it **front-loads** learning to *reduce*
   the correction stream the reflect loop mines reactively. Gated for *use*, not
   existence — invoke before a writing session or to seed `writing-style`.

**Rejected — the daydream loop.** Maintenance + generation-without-consumption +
re-opens closed cost surface. Resurrect only on evidence we are losing
cross-memory connections that a $0 deterministic recombination (no scheduled
LLM) couldn't surface.

## The ceiling (the most valuable takeaway)
Read against our constitution, the essay is an argument that **agent-infra has a
ceiling**. Gwern names the harness approach — "modifying something else, such as
a harness, which is clumsy and difficult… every added instruction uses up more
context window and risks backfiring" — as the workaround for frozen weights.
That is the entire surface we operate on. Our constitution P1 ("instructions =
0% reliable → enforce with architecture") is the *same diagnosis*; our solution
(hooks/tests) is the very workaround he critiques. The largest personalization
gains live in a layer (in-weight) we structurally cannot touch, and our
~4:1 rule:hook pressure is us hitting that ceiling from below. Naming it beats
papering over it — it bounds what harness optimization can ever deliver.

## Evidence
- Source essay: gwern.net "Guardian Angels: LLM Personalization for Productivity
  and Security" (human-authored vision piece; empirical claims — e.g. Kim et al
  2025 5–17× sample-efficiency — treated as unverified-by-default per AI-text
  policy, not load-bearing for this assessment).
- `grep -ril daydream` = 0; `grep -ril "interview prompt"` = research memos only
  (no implementation) — confirms the gap/novelty split above.
- Existing session-learning loop: [[session-learning-loop-design]] (memory),
  memory `session-learning-loop-design`.

## Revisit if
- A concrete, recurring need for the daydream loop appears (we demonstrably miss
  cross-memory connections a deterministic $0 pass can't catch).
- The interview-prompt skill sees real use and its answers measurably sharpen
  `writing-style` / feedback memory — promote its scoring from heuristic to a
  logged information-gain metric.
- We ever own a model and the in-weight GA spine becomes reachable (different
  company; not foreseen).

## Revisions
**2026-06-07** — Smoke-tested the new `interview-prompt` skill on this very thesis
(route: feedback). Markus **confirmed "Accept it"** on the ceiling — no personal
GBT side bet, this doc stands. The interview also surfaced a finding sharper than
the doc assumed: the amplify-vs-automate boundary is **verifiability, not domain**
— "depends on… if there's a clear verifier/eval; STEM/eng/optimization → agents
better than me [automate]; art/writing/taste/visuals → is me [amplify]," and the
same rule governs voice-emulation by register (Q3 "depends on register"). Captured
as feedback memory `feedback-amplify-automate-by-verifiability`. Implication worth
flagging (not applied — constitution is human-gated): the Generative Principle's
unconditional "autonomy is the primary objective" is, per Markus, *conditional on
a verifier existing* — autonomy-max is correct only where ground-truth eval bounds
it.
