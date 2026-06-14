---
id: 2026-06-10-silent-proxy-as-truth
concept: completion-verification
repo: agent-infra
decision_date: 2026-06-10
recorded_date: 2026-06-10
provenance: contemporaneous
status: accepted
initial_leaning: "transcript-mining over 2 days surfaced the same root cause four times across three repos; record it as one named failure class generalizing the single-face 2026-05-28 record, with the fix family per face"
relations:
  - type: generalizes
    target: 2026-05-28-verify-against-ground-truth-not-model-text
  - type: relates_to
    target: 2026-06-07-verifier-conditional-autonomy
---

# 2026-06-10: Silent proxy-as-truth — one failure class, four faces

## Context
A two-day transcript-mining sweep (intel, phenome, hutter; sessions below) surfaced the
**same root cause four times** in unrelated domains: *a derived / proxy / rendered signal
silently stood in for ground truth, and the system trusted it.* The 2026-05-28 record
(`verify-against-ground-truth-not-model-text`) named **one face** of this — model-emitted
text used as a completion verifier. This record generalizes it: the proxy need not be
model text. It can be a fallback data source, a prose projection of structured data, a
screen metric in the wrong unit, or a measurement platform that lies. Same disease, same
fix shape.

## The four faces (all observed 2026-06-08..10)

| Face | Session | What happened | Cost |
|------|---------|---------------|------|
| **Dead data plane → silent fallback** | intel `d22cb587` | an eval hit a dead prices view, silently fell back to FMP, and emitted hit-rates *as alpha* | a day of wasted effort chasing fake numbers |
| **Projection used as a source** | phenome `7d97db7d` | CPIC level extracted from a *prose render* of PharmGKB: 0/21; from the structured origin: 395/395 | near-total extraction loss, looked like a parser bug |
| **Wrong screen unit** | hutter `019eac6a`/`e576f568` | length-changing transforms scored in bpc not total bytes → the loop declared its *correct* strategy DEAD (QUEUE_006), retracted hours later | nearly abandoned the right strategic wedge |
| **Lying platform ruler** | hutter `e576f568` | macOS memory-compression masked ~2× RSS → *every config ever scored was illegal* (10–20 GB vs the 10 GB cap), invisible for the project's whole history | the entire scoreboard was demonstration-track only |

## Decision
**Never let a proxy stand in for the principal check.** Concretely, by face:

- **(a) Fail loud on a dead data plane.** A resolver / eval / report that depends on a live
  data source must assert liveness and emit `[DEGRADED]` (or refuse) when the source is
  dead — never silently substitute a different source and present the result as equivalent.
  Reference implementation: intel's `assert_data_plane_live(view)` (intel-local; approved
  in-session).
- **(b) Extract from the structured origin, never from a projection of it.** A prose / HTML
  / markdown page rendered *from* structured data is a lossy projection. If a categorical or
  numeric value exists as a typed field upstream, read the upstream field. "Pages as
  projection, never pages as source."
- **(c) The screen's unit must match the objective's unit.** For any length- or
  shape-changing move, a cheap screen scored in a normalized unit (bpc, %, per-token) can
  reward the move while the objective (total shipped bytes) gets worse. Score the screen in
  the unit the objective lives in, or the screen lies about whole classes of move.
- **(d) Measure on the platform that judges.** A dev box can silently misreport the binding
  constraint (RSS, latency, determinism). Provision the verifier-platform measurement before
  trusting any number that gates a decision.

The unifying test: **before trusting a value that gates a decision, ask "is this the
principal check, or a proxy standing in for it?"** A proxy is acceptable as an explicit,
labeled screen; it is never acceptable as a silent substitute for the gate.

## Counterevidence sought
- *Is this just four unrelated bugs?* No — each is the same structural move (trust a
  cheaper-to-read stand-in for an expensive-to-read ground truth) and each was invisible
  precisely because the stand-in returned a plausible value. Plausibility is the tell: a
  silent proxy fails *quietly*, which is why it survives.
- *Is it already covered?* Partially — 2026-05-28 covers face (a)-as-model-text and the
  hook layer; the constitution's verifier-conditioned scope (`2026-06-07`) covers *which*
  verifier to trust. Neither names the cross-domain pattern that the proxy can be data,
  prose, a unit, or a platform. This record is the generalization, not a new mechanism.

## Enforcement / consumer
- **No new meta hook** (no incident history in agent-infra's own surface; the failures are
  in intel/phenome/hutter, each fixed at its own boundary). Enforcement lives where the data
  plane lives: intel's `assert_data_plane_live`, phenome's source-adapter discipline
  (consume structured-at-origin triples), hutter's screen-unit + verifier-platform moves
  (see `clean-verifier-evolver-pattern.md` move 8 and the screen-unit anti-pattern).
- **Meta consumer:** this record is cited by design reviews and by the global
  `epistemic_discipline` point added 2026-06-10 ("never let a proxy stand in for the
  principal check"). The discriminator runs at review time, not as a deterministic gate
  (semantic predicate, P1 exception).

## Revisit if
- A *fifth* face appears in a domain where a boundary-local fix is impractical and a shared
  meta mechanism would pay — then a hook at that boundary, not a global text rule.
- Any meta verification gate is found trusting a proxy (migrate it to the principal check).

## Supersedes
None. Generalizes `2026-05-28-verify-against-ground-truth-not-model-text` (which remains the
canonical record for the model-text-as-completion-verifier face and its hook layer).

## Revisions
- **2026-06-14 — fifth face: clobberable-identity proxy (this record's "Revisit if" fired).**
  A long single-operator session ran beside 3+ concurrent peer agent-infra sessions on one
  checkout. Its friction was almost entirely P8, each instance caught by the human (= supervision
  load, the anti-objective) — and each was a clobberable/estimated proxy standing in for an
  available deterministic principal: (1) a subagent audit reported **chars as tokens** (modal-dx
  "9.4k" vs the real 2,335 from `context-budget.py`); (2) audit recs were **stale on state**
  (modal-dx→skill + intel glob already done — `git log`/the live file was truth); (3) a cross-repo
  apply-subagent's **worktree branched stale `origin/main`** (23 behind the target HEAD); (4) the
  Stop-hook auto-checkpoint could fall back to the **clobberable `current-session-id`** for file
  ownership and committed a peer's unattributed output.
- **Boundary-local fix that paid (#4):** skills@f12a1cd — the auto-checkpoint now fails CLOSED when
  a ledger producer exists but this session's ledger is empty (the clobber-race), surfacing
  unattributed files instead of sweeping them. #1/#2 → dispatch discipline (measurement subagents
  return judgment; the coordinator computes the numbers from the tool, never the subagent's
  estimate). #3 → cross-repo apply-subagents edit the live checkout, never `isolation:worktree`.
  No new GLOBAL meta hook — consistent with this record (fix at the boundary where the
  identity/data plane lives).
- **Generative framing — "principal-by-default":** every clobberable/estimated proxy has a cheap
  deterministic principal available (the tool's number, `git`, the target HEAD, the per-session
  ledger). Action rule: before surfacing a number / state / ownership claim, route it through the
  principal — the human catching a proxy is supervision the architecture should have spent. The
  actionable restatement of `epistemic_discipline` #8.
