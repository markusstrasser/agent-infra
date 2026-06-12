# Harness Mining — anthropics/defending-code-reference-harness

Source: github.com/anthropics/defending-code-reference-harness (pushed 2026-06-02),
fetched via raw.githubusercontent.com 2026-06-12. Pipeline: recon → find → grade →
judge → report → (dedup) → patch. Multi-agent, gVisor-sandboxed, ASAN-oracle.

Consumers: (a) **hutter** Grinder/Dreamer clean-verifier RSI loop (deterministic
compression verifier, single-LLM, git bus); (b) **~/Projects/evals** graders
(evalcore deterministic + judge panels).

---

## 1. Stage contract (`docs/pipeline.md`)

The full pipeline. What crosses each boundary, what each gate drops, where the human sits:

| Stage | Input | Output | Gate / drop |
|---|---|---|---|
| **Build** | target Dockerfile | ASAN-instrumented image (tag) | image reused by find/grade/re-attack — "same code, same env" invariant |
| **Recon** (opt) | source tree | partition of attack surface (`focus_areas`) | seeds parallel runs so they don't converge on the same bug |
| **Find** | source + ASAN binary | **crashing input file** (PoC bytes, not a written report) | requires input crash **3/3**; must emit `<dup_check>` or submission rejected |
| **Grade** | **PoC bytes only** | `result.json` verdict (pass/reject + score 0-1) | drops: non-reproducing (<2/3), OOM (exit 137), timeout (124), libc-only-no-project-frame, crash-class-inconsistent |
| **Judge** | ASAN excerpt + manifest | NEW / DUP_BETTER / DUP_SKIP | drops duplicates; only runs under `--stream` |
| **Report** | PoC + source | structured exploitability analysis + grader score | report-grader scores evidence-backing, not prose |
| **Dedup** | all `result.json` | cluster by signature (post-hoc, summary only) | **NOT a gate** — includes rejected crashes |
| **Patch** | unique bugs | candidate fix + verification | separate command |

Quote — the find→grade trust boundary, the single most transferable idea:

> "The only thing that crosses from the find container to the grader is the PoC
> bytes, so the grader isn't influenced by the find agent's reasoning."

Quote — grader stance (the design-principles section):

> "It should be framed as an adversary actively trying to disprove findings,
> which are **guilty until proven innocent**. Proof-of-concept exploits that
> produce a witness are best... The grader should also be tailored for the
> vulnerability types under inspection: some bugs are proven by PoC, others by
> logical argument."

**Where the human sits:** nowhere in the inner loop. Humans calibrate graders
offline ("Graders should be able to run over any findings multiple times as
they're calibrated with human feedback") and read streamed reports/scores to
triage. The pipeline is fully autonomous per-run; the human is a *calibrator*
and *consumer*, not an inline approver.

**Transfer (hutter):** hutter's loop is find(Grinder)→verify(deterministic). This
doc says the verifier must (a) re-run in a *clean* env from the same build
artifact, (b) receive only the *artifact* (compressor output / PoC), not the
proposer's justification, (c) be adversarial. hutter already has (a)+(b) via a
deterministic compression check; the missing piece is the **judge tier** — a
cheap semantic gate that runs only when the deterministic verifier passes.

**Transfer (evalcore):** the table IS the evalcore architecture — deterministic
grade tier that hard-drops on objective failures (OOM/timeout/no-repro analogues
= compile-fail / timeout / wrong-output), THEN a judge tier on survivors only.
Dedup-as-non-gate (keeps rejects) is a results-view pattern evalcore lacks.

---

## 2. Grade ↔ Judge gating contract (`grade.py` + `judge.py` + prompts)

**The cheap deterministic grade runs FIRST and hard-drops before the LLM judge
sees anything.** Grade is a 5-criterion rubric executed *by an agent that runs
the binary* — but the criteria are objective/deterministic checks:

```
Criterion 1: PoC file valid (exists, non-empty)
Criterion 2: reproduces 3x in fresh container (FAIL if < 2/3)
Criterion 3: not OOM/timeout (grep "out of memory"; exit 137=OOM, 124=timeout)
Criterion 4: crash in project code (ASAN trace must reference source_root frames)
Criterion 5: consistent crash CLASS across runs (ASLR/heap-layout variation OK)
```

Parsing is deterministic (`grade.py`): each `<criterion_i>` must `.upper().startswith("PASS")`;
`<overall>` likewise; `<score>` floored to `0.0` on any parse error.

The judge only fires on graded survivors, and it is explicitly a **semantic
de-dup**, NOT a regex signature match. From `judge.py` docstring:

> "Judge + compare stages: **LLM triage instead of regex signature match.**
> No-tools agents — the decision is semantic, the inputs fit in a prompt."

**Anti-leniency mechanisms (this is the gold):**

1. **Guilty-until-proven-innocent framing** in the grade prompt: *"You are a
   strict grader verifying a crash PoC."* + adversarial stance from pipeline.md.
2. **Two-tier separation**: the expensive semantic judge never sees a crash the
   cheap deterministic checks already killed. Judge leniency can't resurrect an
   OOM or a non-reproducing crash.
3. **Witness requirement**: grade demands an executable oracle (3/3 reproduction
   in a *fresh* container), not the model's opinion that it crashes.
4. **Score, don't just pass**: flaky-but-real passes with a *lower score* —
   graded confidence is continuous, so downstream can rank.
5. **Fail-open is deliberate and directional**: `_parse_judge` defaults unparseable
   output to `NEW` ("fail open so crashes aren't silently dropped"), and `DUP_*`
   without a `bug_id` is "incoherent — fall open to NEW." Leniency is pushed
   toward *more reports* (recall) not *fewer* — the opposite of grader leniency.
6. **Judge rubric forbids the cheap match**: *"Same crash class (e.g. both
   heap-buffer-overflow) alone is not a match; same root cause is."* — explicitly
   blocks the lazy "same error type = dup" shortcut.
7. **Report-grader scores evidence not keywords** (`report_grader_prompt.py`):
   0=stub, 1=plausible-but-no-evidence, 2=evidence-backed (file:line, re-run
   observation, binary inspection). *"a report that says 'attacker controls
   allocation size...' shouldn't score worse than 'arbitrary write primitive'
   just on keyword hit. Semantic content, semantic scoring."*

**Transfer (hutter):** today hutter's verifier is purely deterministic (bit-exact
size). Add a **judge tier** that fires only on a *passing* compression run, to
catch things the size-check can't: e.g. "is this gain from a legitimate model
improvement or from leaking test bytes / overfitting the enwik prefix / a decode
that won't generalize?" Keep it no-tools, prompt-only, fail-open-toward-accept
so a flaky judge never blocks a genuine size win. The grade/judge split maps
exactly: **deterministic size verifier = grade tier; semantic legitimacy judge =
judge tier.**

**Transfer (evalcore):** the 6 anti-leniency mechanisms are a checklist for
evalcore's judge panels: (1) adversarial framing string, (2) gate judges behind
deterministic checks, (3) require a witness/artifact, (4) continuous score not
binary, (5) directional fail-open, (6) per-criterion 0/1/2 with "0 = stub/boilerplate"
anchored examples. The report-grader's *"'See ASAN output above' is a 0"*
concrete-zero-anchor is directly liftable into evalcore rubric prompts.

---

## 3. Novelty check (`novelty.py`) — `git log <commit>..HEAD`

Opt-in (`--novelty`), **host-side only** — the report container stays
`--network none`; only the orchestrator touches the network. Mechanism:

1. Shallow blobless clone of upstream (`git clone --filter=blob:none`), cached
   under `~/.cache/vuln-pipeline/novelty/<slug>`; fetch if already cloned.
2. Resolve the crashing file: ASAN frame gives a *container* path
   (`/work/dr_wav.h`); repo has no `/work/`, so **match on basename** via
   `git ls-files -- '*<basename>'`, take first match.
3. `git log --oneline <commit>..HEAD -- <repo_path>` — commits touching that
   file since the pinned commit. Empty → not fixed upstream; non-empty →
   candidate fix exists.
4. **Never raises** — every network/git failure becomes prompt text
   (`[upstream fetch failed: ...]`), truncated to 2000 bytes.

Quote:

> "When enabled, the orchestrator shallow-clones the upstream repo and runs
> `git log <commit>..HEAD -- <file>` for the crashing file. The output is
> injected into the report prompt — the report container stays `--network none`,
> only the orchestrator touches the network."

**Transfer (hutter):** the *pattern* — "did upstream already solve this?" — maps
to hutter checking whether a proposed transform/model tweak is already in the
cmix/fx2-cmix lineage before crediting it as novel. The *mechanism* (basename
match + `log commit..HEAD`, fail-into-prompt-text-never-raise) is the right shape
for a cheap "has this idea already been tried in the reference compressor's git
history" gate. Network touches the orchestrator, never the sandboxed worker.

**Transfer (evalcore):** novelty-as-injected-context (not a hard gate) — the
upstream-fix status is *fed to the report*, not used to drop the finding. evalcore
could fold "is this answer already in the reference/known set" as a graded
dimension rather than a filter.

---

## 4. Dedup that keeps rejects as signal (`dedup.py`)

**Post-hoc, summary-only, explicitly NOT a phase gate.** Signature =
`(crash_type, top_ASAN_frame)`. Crucially it includes **both** `crash_found`
and `crash_rejected` results:

> "Walks result.json files... groups crashes by (crash_type, top ASAN frame).
> **Includes both crash_found and crash_rejected results — a rejected crash is
> still signal.**"

> "This is a summary artifact, not a phase gate. In streaming mode the judge
> agent decides which crashes get reports; this subcommand just answers 'these
> N crashes cluster into M signatures'."

Robustness detail: silently skips unreadable/malformed `result.json` (a
half-written file from a killed run "shouldn't abort the whole report"). Output
sorted largest-cluster-first.

Why keep rejects: a crash that *failed* the fresh-container grade (flaky) still
tells you a signature region is fragile — clustering it with passes shows where
the target is weak even if no single PoC was clean. The *judge* (not dedup)
owns the report-gate decision; dedup is pure observability over the whole
attempt space including failures.

**Transfer (hutter):** keep a ledger of *rejected* compression attempts clustered
by signature (which transform / which model change / where it regressed), not
just the wins. A failed attempt at a known-fragile spot is a map of where the
search is hard. The git bus already persists attempts; add a signature-cluster
view over failures, summary-only, never gating the loop.

**Transfer (evalcore):** evalcore should retain *failed* eval rows clustered by
failure signature as a first-class observability view, distinct from the
pass/fail gate. "These N failures cluster into M root causes" is exactly the
triage artifact a grader-calibration loop needs. Malformed-row-skip robustness
is a free lift.

---

## 5. Verifier isolation — what crosses the container boundary

The trust boundary is the **image tag**, and the only thing that crosses from
proposer to verifier is the **artifact bytes**. From `grade.py` docstring:

> "The trust boundary is the image tag — find-agent could write anywhere in its
> container but can't retroactively modify the image. A fresh container from the
> same tag is pristine. **Only the PoC bytes cross the boundary.**"

Implementation details that make this real (`grade.py`):
- Fresh `sandbox.agent_container(target.image_tag, ...)` — same image, new container.
- `docker_ops.write_file(container, "/tmp/poc.bin", crash.poc_bytes)` — only bytes in.
- Path is *re-fixed*: find-agent saved to an arbitrary path; grader always reads
  `/tmp/poc.bin`. The reproduction command is rewritten
  (`crash.reproduction_command.replace(crash.poc_path, "/tmp/poc.bin")`).
- **Consistency guard**: if `poc_path` isn't actually in `reproduction_command`,
  it *raises* rather than hand the grader an unadapted command — a malformed
  proposer output is rejected at the boundary, not silently mis-run.
- Judge/compare agents are `tools=[]` no-tools but **still run in-container** so
  the "every agent sandboxed" invariant holds even if someone later adds a tool.

Why: the verifier must not be able to read the proposer's reasoning, scratch
files, or environment — only the claimed artifact. Reasoning leakage is exactly
how a grader gets talked into a false positive. The clean room makes the
verdict depend on the artifact's behavior, nothing else.

**Transfer (hutter):** hutter's verifier should reconstruct from *only the
decoder + compressed bytes*, in a clean checkout, never sharing the proposer's
working dir. The "consistency guard — raise on inconsistent reproduction command"
maps to: reject a submission whose claimed decode command doesn't match the
artifact, at the boundary, before running. (hutter's "model counts toward S"
box already forces this discipline; this codifies the boundary mechanics.)

**Transfer (evalcore):** pass the grader the *output artifact only*, never the
candidate's chain-of-thought or scratch state. Re-fix paths/inputs to a canonical
location so the grader can't be steered by where the candidate wrote things.
Run even no-tool judges in the same isolation so the invariant survives a future
tool addition.

---

## 6. Prompt techniques not seen before

New relative to Claude Code's code-review angles we already extracted:

- **Concrete-zero anchoring** (`report_grader_prompt.py`): every rubric level
  carries a worked example, and the 0-level is an explicit *anti-pattern* string:
  *"'See ASAN output above' is a 0."* Anchoring the *floor* with a named slop
  pattern is sharper than the usual "0 = poor."
- **Self-justified dedup at submission** (`find_prompt.py`): the finder must emit
  a `<dup_check>` tag *reasoning about novelty against a shared log* BEFORE the
  judge ever runs — *"Submissions without it are rejected by the pipeline."* The
  proposer pre-filters its own duplicates; the judge is a second line, not the
  only line. And the finder is told: if it IS a dup, **do not emit `<poc_path>`
  at all — pivot and keep searching.** Cheap self-gate before the expensive gate.
- **Shared-log re-check cadence** (`find_prompt.py`): *"Check it at natural
  breakpoints too — right after you first land a crash (before minimizing), when
  switching approaches, roughly every ~20 turns... A dup caught early is an hour
  saved."* Periodic re-sync against concurrent agents' progress, not just once.
- **Token-extraction sub-prompt** (`report_grader_prompt.py`): the grader does
  rubric scoring AND emits single-token classifications (`<severity>`,
  `<reachability>`, `<novelty>`) with *"emit only the token, no justification"* —
  one agent call yields both a graded score and structured metadata. Explicitly
  handles "LOW — because..." → extract just `LOW`.
- **Separate "compare" pass to prevent silent clobber** (`judge_prompt.py`): when
  a cleaner PoC triggers a re-report, a *distinct* compare agent picks the
  canonical report — *"a cleaner PoC that produces a weaker report doesn't
  silently clobber the better analysis... you're judging the ANALYSIS, not the
  PoC."* Decouples artifact-quality from analysis-quality.
- **Directional fail-open as prompt+parser contract**: the judge defaults to
  NEW (more recall), the compare defaults to B (the newer re-report the judge
  already favored) — defaults chosen to match the stage's bias, documented inline.

**Transfer:** for evalcore judge prompts — adopt concrete-zero anchoring, the
token-extraction-alongside-score pattern (one call → score + metadata), and the
"judge the analysis not the artifact" separation. For hutter — the self-justified
`<dup_check>`-before-submission pattern is a cheap proposer-side filter that
offloads work from the verifier.

---

## TOP-5 STEAL THIS (ranked)

1. **Two-tier gate: deterministic grade hard-drops BEFORE the semantic judge
   runs.** The expensive LLM judge never sees a crash the cheap objective checks
   (no-repro / OOM / timeout / not-in-project) already killed. Directly seeds
   hutter's missing judge tier (size-verifier = grade; legitimacy-judge = judge)
   and is the core evalcore grader architecture. *Highest leverage, lowest cost.*

2. **Artifact-only trust boundary + clean-room verifier.** Only the output bytes
   cross from proposer to verifier; verifier runs fresh from the same build
   artifact, never sees proposer reasoning/scratch. Plus the "raise on
   inconsistent reproduction command" boundary guard. Kills reasoning-leakage
   false positives. hutter: decode-from-bytes-only in a clean checkout. evalcore:
   grade the output, never the chain-of-thought.

3. **Six anti-leniency mechanisms for the judge** — adversarial "guilty until
   proven innocent" framing; require a witness/oracle not an opinion; continuous
   score not binary pass; per-criterion 0/1/2 with concrete-zero slop anchors
   (*"'See ASAN output above' is a 0"*); directional fail-open (toward recall);
   rubric forbids the lazy match (*"same crash class alone is not a match; same
   root cause is"*). A drop-in checklist for evalcore judge panels.

4. **Dedup keeps rejects as signal, summary-only, never a gate.** Cluster ALL
   attempts (passed + rejected) by signature for observability; the gate decision
   lives in the judge, not the clusterer. Malformed-row-skip robustness. hutter:
   ledger of failed compression attempts clustered by where-it-regressed. evalcore:
   first-class failed-row cluster view distinct from the pass/fail gate.

5. **Self-justified dedup at submission (`<dup_check>` required) + novelty via
   `git log commit..HEAD` injected-as-context-not-gate.** Proposer pre-filters its
   own duplicates before the expensive judge; "already solved upstream?" is fed to
   the report, never used to silently drop. Network touches only the orchestrator,
   never the sandboxed worker; failures become prompt text, never raise.
