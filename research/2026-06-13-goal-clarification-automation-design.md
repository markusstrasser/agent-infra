---
title: Goal-Clarification Automation — make the interview-prompt fire on unclear-goal drift
date: 2026-06-13
status: complete
tags: [goal-drift, interview-prompt, reflect-loop, shadow-rollout, ppv-gate, anti-nag]
---

# Goal-Clarification Automation

**Request (verbatim intent):** "If there's a lot of me changing things and saying
'this is not true, let's do this instead', the loop should check: would this
back-and-forth have been necessary if the goal was clearer? I run an interview
prompt that resolves the goal with examples and 2nd/3rd-order consequences and
known preferences. That has to be more automatic and integrated."

**Bottom line:** This is **net-new measurement wiring around two things that
already exist** — the `/interview-prompt` skill (the elicitation engine) and the
`reflect_capture.py` SessionEnd negation detector (the signal source). Nothing
new gets built until a SHADOW phase proves the signal predicts the pain. The
enforcer is **not** the goal-drift hook (that fires on Write/Edit *content*, a
different axis) and **not** a new live UserPromptSubmit classifier (that fights a
documented anti-pattern). It is a **session-end retrospective recommendation**,
matured through the reflect loop's existing shadow→PPV→promote machinery.

---

## 0. Already exists? (Pre-Build Check — required before proposing code)

Grepped `interview|elicit|goal.?clarif|goal.?drift|clarif` across `scripts/`,
`skills/hooks/`, `.claude/rules/`, `~/.claude/skills/`. What's already built:

| Component | What it does | Reuse role |
|---|---|---|
| `/interview-prompt` skill | Active-learning interviewer: analyzes a topic, brainstorms candidate questions, asks the few highest-information ones, routes answers to feedback memory / writing-style corpus. **This is the engine the user means by "I run an interview prompt."** | **INVOKE it. Do not rebuild.** |
| `reflect_capture.py` (SessionEnd hook `sessionend-reflect-capture.sh`) | Zero-LLM transcript parse → `negation` / `fail_then_user` / `retry_run` / `f_tag` correction signals → `~/.claude/reflect-capture.jsonl`. **Already extracts the exact "this is not true, do X" turns** (`_NEG_RE`: `wrong`, `instead`, `that's not`, `you forgot`, `no,` …). | **Signal source.** Extend with a per-session denominator + a `goal_uncertainty` flag. |
| `reflect.py` (deep pass) | Clusters signals, routes to cheapest enforcer, **shadow→PPV→quarantine→human-approve** lifecycle already implemented (`PPV_CLEARED`, `WIP_CAP`, auto-record-never-auto-apply). | **Rollout machinery.** The new signal is just another capture subtype riding this loop. |
| `pretool-goal-drift.sh` | PreToolUse Write\|Edit: warns when written *content* references terms outside GOALS.md `<!-- goal-keywords -->`. | **NOT the right hook** — see §3. Different axis (scope-of-artifact, not clarity-of-objective). |
| `gov_intake.py` (UserPromptSubmit) | Captures explicit `#f` feedback to quarantine. **Deliberately refuses semantic detection** ("depth-nudge classifier hit 67% FP"). | **Precedent that forbids** a naive live semantic trigger (§3, §4). |

**Finding: the elicitation engine, the signal extractor, and the rollout harness
all already exist.** The gap is a thin measurement layer connecting them — about
40 lines of capture extension + one config entry + one shadow report row. This is
emphatically a *wire-three-things-together* task, not a build.

---

## 1. SIGNAL — the deterministic predicate

### 1a. The 824 number is a trap — correct denominator first

The prompt cites "824 `correction` events." Histogram of the live log
(`~/.claude/reflect-capture.jsonl`, 842 rows):

```
by subtype: retry_run 757 | negation 54 | new-script-without-test 9
            f_tag 7 | fail_then_user 6 | entity-write-without-identity-read 5
            state-claim-without-ground-truth-query 4
```

**757/824 are `retry_run`** — blind Bash retries, a *reach/capability* axis, **not
user corrections**. The genuine "you changed the goal mid-flight" signal is
**`negation` (54) + `fail_then_user` (6) = 60 user-turn corrections** across the
*entire* indexed history. Building a high-frequency live interrupt on a 60-event
base rate is how you manufacture a nag. The signal is **real but sparse** — which
is itself the argument for retrospective measurement over live interruption.

The `negation` samples are exactly the described failure mode (verbatim from log):

- `"i don't own ELS yet ... who said that???"`
- `"so we had sandisk at 1400$ be a no-buy ... it went up 40% ... so ... wrong again?"`
- `"acls ... why would i hold instead of putting it somewhere else?"`

These are unclear-goal/unstated-premise back-and-forth — the thing a pre-session
interview would have pre-empted.

### 1b. The predicate: within-session correction density

Define per session, computed at SessionEnd from the already-parsed transcript:

```
goal_uncertainty_session :=
    N_corr  >= 3                         # >=3 negation+fail_then_user turns
    AND     N_corr / max(U, 1) >= 0.25   # >=25% of the user's substantive turns
                                          #   were corrections (density, not count)
    AND     >=1 of those negations is strength in {strong, medium}
                                          #   ("wrong"/"that's not"/"instead",
                                          #    not just "actually"/"stop")
    AND     spread: corrections span >= 2 distinct assistant actions
                                          #   (rules out one bad turn re-litigated)

where
    N_corr = count(subtype in {negation, fail_then_user})
    U      = count(user events where role==user, not is_tool_result, texts non-empty)
```

**Why density not count:** a 200-turn session with 4 corrections is healthy; a
12-turn session with 4 corrections (the observed max, session `1098feff`) is the
pain. `N_corr/U` discriminates them. `U` is trivially derivable from the existing
`parse_events()` output — **the denominator is the only new extraction**, ~5 lines.

**Why the strength + spread guards:** drops the long tail of weak single-turn
"actually"s that aren't goal problems. The 60→ realistic-fire base rate after
these guards is what the SHADOW phase measures before anything surfaces.

**Determinism:** 100% deterministic, zero-LLM, runs inside the existing
`reflect_capture.extract_*` pure core. Fully unit-testable (the module already has
a side-effect-free core for exactly this).

---

## 2. TRIGGER POINT — session START, mid-session, or both?

**Decision: session-END (retrospective recommendation) in v1. NOT mid-session
interrupt. A session-START interview is offered ONLY as an opt-in, never
auto-injected.** Argued against Principle 5 below.

### The three options against Principle 5 (divergence budget = uncertainty × irreversibility)

| Option | When | Principle-5 problem | Verdict |
|---|---|---|---|
| **Session START auto-inject** | UserPromptSubmit on first turn | Taxes *every* task with an elicitation step before any signal exists. Principle 5 says low-uncertainty/low-irreversibility work must **converge fast, no exploration**. A bug-fix or "run the tests" prompt would eat an interview. Pure elicitation tax. | **Rejected as default.** Offer as opt-in skill only. |
| **Mid-session interrupt** | PostToolUse/UserPromptSubmit once density crosses threshold | Fires *during* live work — exactly the `gov_intake` anti-pattern ("no semantic detection of pushback/stance flips — 67% FP factory"). Worse: it interrupts *after* the back-and-forth already happened, so it pays the cost without preventing it this session. And the density signal needs the *whole* transcript; mid-session you only have a prefix → premature fire. | **Rejected.** Re-runs a solved mistake. |
| **Session END retrospective** | SessionEnd hook (where `reflect_capture` already runs) | Pays **zero tax on the live session**. The signal is *complete* (full transcript). The output is a recommendation for the *next* time this task-class comes up — "last session on X had high correction density; run `/interview-prompt X` before resuming." Prevention lands on the *next* session, where it's cheap. | **CHOSEN.** |

### Why retrospective is correct here, not a cop-out

The user's framing — "*would this back-and-forth have been necessary*" — is itself
a **retrospective** question ("would have"). The honest answer to a question about
a session can only be computed once the session is over. Principle 5's high-U ×
high-irreversibility quadrant ("extended divergence + cross-model review") is the
*type* of session an interview helps — but you can't reliably classify a session
into that quadrant from turn 1. You *can* recognize, at session end, that it
*behaved* like one and was under-scoped. That recognition seeds the next session's
START.

**The loop closes across sessions, not within one** — matching the reflect loop's
existing architecture (capture at end-of-session N, surface before session N+1).

---

## 3. MECHANISM — cheapest enforcer on the reflect ladder

The reflect output ladder is **verifier > default-change > gate > rule** (rule
only for genuine semantic predicates). Walk it:

| Rung | Applicable? | Why / why not |
|---|---|---|
| **Verifier** (ground-truth grader) | **No** | "Was the goal clear enough?" has no ground-truth oracle. A model-as-judge proxy is explicitly forbidden (constitution: "a bad eval is worse than none"). The *signal* (density) is deterministic, but the *remedy's success* isn't gradeable. |
| **Default-change** (make the good path the default) | **Partial — this is the spirit** | The "default" we change is: *next* session on a flagged task-class **defaults to surfacing an interview offer in checkpoint.md / morning-brief**, rather than the human having to remember to run it. Not a code default flip, but the same idea: reduce the activation energy of the right move to ~zero. |
| **Gate** (block until a step happens) | **No** | Gating session start on an interview is the rejected START-auto-inject tax. Hard-blocking is wrong for a sparse, taste-adjacent signal. |
| **Rule** (instruction) | **Backstop only** | One line in CLAUDE.md already half-covers this ("When the human gives direction that conflicts with/extends GOALS.md, surface that explicitly"). Instructions are 0% reliable (P1); not the answer. |

### Chosen mechanism: a SessionEnd capture subtype + a surfacing channel (no new hook process)

**It hooks NOWHERE NEW.** It rides the existing `SessionEnd → reflect_capture.py`
hook. Three concrete edits:

1. **`reflect_capture.py` — extend `extract_corrections` (or a new
   `extract_goal_uncertainty(events)`):** compute `U`, `N_corr`, apply the §1b
   predicate, and when it fires emit ONE aggregate signal per session:
   ```json
   {"kind": "goal_uncertainty", "subtype": "high_correction_density",
    "strength": "shadow", "shadow": true,
    "project": "<proj>", "session": "<id>",
    "trigger": "Ncorr=4 U=12 density=0.33 actions=3 :: <first strong negation, 120c>"}
   ```
   The `trigger` carries the first strong negation verbatim — that string is what a
   human reads to judge "yes, this was an unclear-goal session" during PPV labeling,
   and what seeds the interview topic.

2. **`config/reflect-omission-rules.json` (or reflect.py `AXIS`/`PPV_CLEARED`):**
   register `goal_uncertainty` as a **shadow** kind. By the existing `reflect.py`
   logic, a shadow kind **records but emits no surface** until its subtype clears
   the PPV gate (`>=60%` on `>=30` labeled firings). This reuses the *exact*
   machinery omission-probes already use — zero new rollout code.

3. **Surfacing channel (only after PPV clears):** the matured signal is rendered
   into **`.claude/checkpoint.md`** ("Pending: last session on `<topic>` showed
   high correction density — consider `/interview-prompt <topic>` before resuming")
   and/or the morning brief. The human *chooses* to run the already-existing skill.
   No auto-execution of the interview; the operator stays the trigger (Principle 5
   respects taste boundaries — goal-setting **is** the human's job per GOALS.md
   Mission).

**Net new code: ~40 lines in `reflect_capture.py` + 1 config line + 1 reflect.py
render branch.** The interview itself, the clustering, the shadow gate, the
quarantine, and the human-disposition flow are **all existing**.

---

## 4. ANTI-NAG — shadow rollout + PPV gate (the 30-min-loop lesson)

**The cautionary tale is in this repo, dated yesterday.** `checkpoint.md:72`:
> "Log tick 5 — 3rd noop; flag 30-min cadence too tight for drained system"

The gov-loop self-flagged its own cadence as nagging noise. And `gov_intake.py`'s
header is a standing monument to the same lesson: *"No semantic detection of
pushback/stance flips — that is a known false-positive factory (depth-nudge
classifier hit 67% FP)."* Any goal-clarification trigger that surfaces eagerly
**will** reproduce both failures. The defenses:

### Shadow-mode rollout (mandatory, matches reflect loop convention)

1. **Phase 0 — capture-only (shadow).** Ship edits 1+2. The predicate fires and
   writes `goal_uncertainty` rows to the capture log. **Emits NOTHING to the
   human.** Runs until `>=30` firings accumulate. At the observed rate (60 genuine
   negations historically, density-gated to a fraction of sessions), this is
   weeks — which is *correct*; a rare signal earns a slow gate.

2. **Phase 1 — PPV labeling.** For each of the >=30 shadow firings, label (human,
   during normal review): *did this session genuinely suffer from an unclear goal
   an upfront interview would have pre-empted?* (yes/no). The verbatim negation in
   `trigger` makes this a <10s judgment per row. Compute
   **PPV = true-unclear-goal / total-fires**.

3. **PPV gate — surface ONLY if PPV >= 0.60.** (Same threshold the omission-probes
   use; `PPV_CLEARED` set in `reflect.py`.) Below 0.60 → the predicate is a
   nag-factory; **tune the §1b thresholds** (raise density floor, require
   `strong`, raise spread) and re-shadow. Do **not** surface a sub-0.60 signal.
   Below ~0.40 after one tuning round → **abandon** (record `[-]` rejected with
   the PPV evidence; the signal doesn't carry).

4. **Phase 2 — surface via checkpoint/brief (default-change rung).** Only now does
   the human see "consider `/interview-prompt X`." Never a block, never mid-session,
   never auto-run.

### Standing anti-nag guards (post-promotion)

- **One signal per session, aggregate.** Not one-per-correction. Caps volume at
  ≤1 surfaced item per flagged session.
- **Decay watch via existing `gov.py advisory_noise`.** If the surfaced
  recommendation is shown N times and the human never acts on it (never runs the
  interview after the flag), `advisory_noise` already reports it as a
  behavior-non-changing advisory → demote/retire. The retirement path is built.
- **Gov-ID + verifier:null.** Tag the capture extension `Gov-ID: ... verifier:
  null` (no ground-truth grader possible) → it lands on the gov-shrink radar as a
  scaffold that must keep justifying itself, not a permanent fixture.

---

## 5. Why this is the right shape (and what it is NOT)

- **Net-new vs extends goal-drift hook:** **Net-new measurement, riding existing
  rails.** It does **not** extend `pretool-goal-drift.sh` — that hook is a
  Write/Edit *content-scope* check (is this artifact about the right topic?), an
  orthogonal axis to *objective clarity* (do I know what done looks like?).
  Conflating them would overload one hook with two unrelated jobs.
- **It does NOT add a live UserPromptSubmit classifier** — that's the
  `gov_intake` 67%-FP trap and the wrong trigger point (§2, §3).
- **It does NOT auto-run the interview** — goal-setting is the human's
  irreducible role (GOALS.md Mission; Principle 5 taste boundary). The system
  *recognizes* under-scoped sessions and *lowers the activation energy* of the
  fix; the human pulls the trigger.
- **It reuses the verifier-conditional frame** (`decisions/2026-06-07-...`): goal
  clarity is **principal-final** (the human is the verifier of "is my goal clear").
  The automation's job is **amplify** — reduce the human's *production* burden
  (remembering to interview, framing the questions — `/interview-prompt` already
  generates them) while preserving *judgment* (he decides to run it, he answers).
  This is "amplify done right," not "automate the unautomatable."

---

## Implementation checklist (if approved)

- [ ] `reflect_capture.py`: add `U` (substantive-user-turn count) to the parse, add
      `extract_goal_uncertainty(events)` implementing §1b, fold into
      `extract_signals`. Unit tests in `scripts/tests/` (pure core).
- [ ] `config/reflect-omission-rules.json` **or** `reflect.py`: register
      `goal_uncertainty/high_correction_density` as a shadow kind; leave OUT of
      `PPV_CLEARED`.
- [ ] Run shadow for `>=30` firings; label PPV during normal review.
- [ ] Gate: PPV>=0.60 → add render branch in `reflect.py`/checkpoint surfacing.
      Else tune thresholds + re-shadow, or `[-]` reject with PPV evidence.
- [ ] `Gov-ID` block (`verifier: null`, `blast_radius: local`) on the new code.
- [ ] improvement-log `[ ]` entry → `[x]` on Phase-0 ship; PPV verdict recorded at
      gate.

**Pre-registered kill condition:** if after one threshold-tuning round PPV stays
< 0.40 on >=30 labeled fires, the density signal does not predict unclear-goal
pain — abandon, record the negative result. (A rare, hard-to-verify signal is
exactly the kind that should have a pre-registered off-ramp.)
