---
title: "Eval Methodology Canon — Primary-Source Reading (statistics, reproducibility, benchmark-quality, contamination)"
date: 2026-06-14
tier: deep
status: active
scope: "Full-text reads of the FOUNDATIONAL eval-design papers the prompt named but prior memos hadn't read: Miller 'Error Bars to Evals' (statistics), Biderman 'Lessons from the Trenches' (reproducibility), BetterBench (benchmark-quality framework), LiveCodeBench (contamination design). Targets the GAP, not the construct-validity/judge-bias axes already covered."
builds_on: [benchmarking-science-2026.md, 2026-05-31-eval-benchmark-methodology-delta.md, 2026-06-11-aa-benchmark-instrument-validity.md, 2026-06-11-frontier-judge-bias-measured.md, epistemic-quality-evals.md]
sibling: 2026-06-14-benchmark-leaderboard-methodology-critique.md  # critiques named leaderboards; this memo = primary-source method canon. Minimal overlap.
---

# Eval Methodology Canon — Primary-Source Reading

**Question:** What do the foundational LLM/agent eval-design papers actually prescribe, read in full, distilled to checkable pre-flight rules? **Method:** 4 landmark papers read in full text (HTML full-text via curl — `fetch_paper` fails on arXiv, see gotcha). **Verdict scale:** GENIUS / SOLID / OBVIOUS / OVERCLAIMED-BS.

## Why these 4 (gap targeting)

Prior memos already own: construct validity (Bean 2511.04703), reliability/Platinum (Vendrow 2502.03461), IRT (Zhou 2505.15055), judge-noise (Feuer 2509.20293), panel correlated-errors (Apple), warrant-vs-relevance (ForceBench), contamination-resistance *direction*, and frontier judge-bias *measured live*. The prompt explicitly named four canonical papers that were **NOT read in full** anywhere in our corpus — the statistical and reproducibility *mechanics*. Those are this memo. The behavioral-judge axis (4) and agentic axis (5) are covered by existing memos + this memo's cross-refs; I did not re-litigate them.

---

## Paper 1 — Miller, "Adding Error Bars to Evals" (Anthropic) · arXiv:2411.00640 · 87 cites · **GENIUS**

The single highest-value paper for us. It is the missing statistical spine: it treats an eval as a *designed experiment* sampling questions from an unseen super-population, and gives closed-form formulas for SEs, model comparison, variance reduction, and power. Read in full (§2–5 + appendices).

**Core insights (each with the load-bearing detail):**

1. **Report a standard error with every eval score, via the CLT — not bootstrap, not Bernoulli-by-default.** `SE = sqrt(Var(s)/n)`. For binary scores this reduces to `sqrt(p(1-p)/n)`; but for *fractional* scores (F1, partial credit) the Bernoulli formula is wrong and too wide. (§2.1) Miller flags that the Llama-3 report used Bernoulli SE even on F1 scores — a real published error.
2. **Clustered standard errors when questions come in groups** (reading-comprehension passages, one question translated to N languages, multi-turn on one scenario). Naive SE under-reports because intra-cluster scores correlate. **On real Anthropic data the clustered SE was up to 3.05× the naive SE** (Table 4, DROP/RACE-H/MGSM). Ignoring clustering makes you think a measurement is 3× more precise than it is. (§2.2, App. A)
3. **Variance reduction without more questions:** (a) **resample each question K times** — going K=1→2 cuts estimator variance 1/3, K=4 cuts 1/2; ceiling ~2/3 once `E[σ²]/K ≪ Var(x)`. (b) For non-CoT multiple-choice, **use next-token probabilities** instead of sampled outputs → eliminates conditional variance entirely (the full 2/3 reduction). (§3.1–3.2)
4. **"Don't touch the thermostat."** Lowering temperature to cut variance is a *trap*: it shifts conditional variance into the (irreducible) variance-of-conditional-means and/or injects bias — a worked example *triples* the floor variance (1/12 → 1/4) by rounding a uniform into a Bernoulli. Only change temperature if you mean to study the model at that temperature. (§3.3)
5. **Compare models PAIRED, not unpaired.** When both models answer the same questions, test the *question-level paired difference*. `Var_paired = Var_unpaired − 2·Cov(x_A,x_B)/n`. Because question difficulty correlates across models, this is a **free ~33% variance reduction** at corr=0.5. The paper's punchline: the naive table reading (Dreadnought wins 2 of 3 evals) *reverses* under paired+clustered analysis (only the MATH gap is significant; HumanEval/MGSM are noise). (§4.2)
6. **Power analysis / Minimum Detectable Effect.** `n = (z_{α/2}+z_β)²·(ω² + σ²_A/K_A + σ²_B/K_B)/δ²`. Worked example: detecting a 3pp difference at 80% power needs **~1,000 questions**. Inverted, a fixed-n eval has an MDE — if your eval *cannot* detect the difference you care about, it's not worth running. Resampling K=1→10 cut MDE from 13.2%→7.5% at n=198. (§5)

**Verdict: GENIUS.** Not novel statistics — it's textbook experiment design — but the *transposition* is exactly right and almost nobody in LLM-eval land does it. It is descriptive+prescriptive, has worked real-data numbers, names its own caveats, and every claim is a formula you can implement. Maps directly onto our N=60 search-bake-off pain (the delta memo independently reinvented half of this — paired McNemar, screening-not-confirmatory, wide-CI pre-registration).

**Adoptable rules (pre-flight):**
- [ ] **Every reported eval number carries an SE and an n.** Decision-grade comparison without an SE is not decision-grade. Compute SE via CLT (`sqrt(Var/n)`); use Bernoulli `sqrt(p(1-p)/n)` ONLY for strictly 0/1 scores, never for partial-credit/F1/judge-scores.
- [ ] **If items are grouped (shared passage, same scenario multi-turn, one prompt × N paraphrases/languages), report CLUSTERED SE.** Cluster on the group. Expect up to ~3× widening; an unclustered CI on grouped items is anti-conservative.
- [ ] **Compare two models/configs on the SAME items and test the paired difference** (paired-diff SE, or McNemar for binary). Never compare two independently-sampled accuracy numbers when you could pair. Report the difference, its SE/CI, and the score correlation.
- [ ] **Pre-flight power check before running:** estimate ω²/σ² from a pilot, compute the MDE for your n (and K). If MDE > the effect you need to detect, add questions or resamples — or don't run it and say so. Default target ≥~1,000 independent items to resolve ~3pp; far fewer only resolves large gaps.
- [ ] **Cut variance by resampling K (until `E[σ²]/K ≪ Var(x)`, ~K=4–10) or next-token probs (non-CoT MCQ) — NEVER by lowering temperature.** Temperature changes the thing you're measuring.

---

## Paper 2 — Biderman et al., "Lessons from the Trenches on Reproducible Evaluation" (EleutherAI, lm-eval-harness) · arXiv:2405.14782 · 161 cites · **SOLID** (the practitioner bible)

Three years of running evals, distilled. The throughline: **LLMs are pathologically sensitive to setup details that look cosmetic**, so an eval result is only meaningful with its exact harness. Read in full (§2–3 + best-practices + appendices).

**Core insights:**
1. **"Having the prompt in the paper is no substitute for the code."** Prompts in papers are stylized to be human-readable and are "often incorrect or difficult to map to the exact implementation." Minor prompt/format/whitespace changes significantly move scores. (§2.3) The reproducibility unit is *runnable code + exact prompts + commit hash*, not a prose prompt.
2. **The format-compliance vs correctness confound.** With regex/heuristic answer-extraction, "it is difficult to separate models' compliance with the evaluation format from their answer correctness." A model can be *right* but score *wrong* because its output didn't match your extractor (or vice-versa). You must release extraction code + raw model outputs. (§B.4) — This is the same lesson our AA-memo learned on IFBench (mechanical-constraint compliance ≠ capability).
3. **Prompt-format choice silently flips rankings.** ARC scored "Cloze" vs "MMLU-letter-style" vs "Hybrid (answer-strings)" gives *different winners*. If lab A cites its number under one format and lab B under another, the comparison is "nonsensical." (§B.1, Table 1) Multiple-choice scoring also needs a declared **length-normalization** (raw loglik favors short answers; token- vs byte-normalization differ — lm-eval's `acc` vs `acc_norm`).
4. **Version every task.** lm-eval attaches a `version` field, incremented whenever a change affects scoring, so a result is reproducible against *that* version even after the task is fixed. (§4.2)
5. **Don't copy numbers from other papers** unless you can verify identical code — re-run baselines yourself; mark copied numbers explicitly. API models get silently updated/deprecated, breaking reproducibility (code-davinci-002's deprecation broke hundreds of studies). (§3)
6. **Report ≥2 seeds / few-shot-example selections; report mean+variance** — "costly but dramatically boosts validity." Echoes Miller from the practitioner side.

**Verdict: SOLID.** Not flashy, occasionally a product-pitch for lm-eval, but it is the single most experience-dense list of the failure modes that actually bite. Every item is a checkable hygiene rule. The format-compliance-vs-correctness point is the deep one and directly relevant to any judge/extractor we run.

**Adoptable rules (pre-flight):**
- [ ] **Pin the harness: exact prompts + extraction/scoring code + model/version string + commit hash are part of the result.** A score without its harness is not reproducible. Store them next to the number.
- [ ] **Separate format-compliance from correctness.** Log raw model output AND the extracted answer. When a run scores 0, inspect: was it wrong, or did the extractor miss a correctly-formatted-differently answer? Report an extraction-failure rate alongside accuracy.
- [ ] **Declare prompt format and MC length-normalization explicitly; hold them constant across compared models.** Never prompt-engineer for one model only; disclose how much prompt-tuning was done. Changing format can flip the ranking.
- [ ] **Version the eval task; bump on any scoring-affecting change.** Old results stay interpretable against their version. (We already do this culturally via git; make it an explicit `task_version` field in eval output.)
- [ ] **Re-run baselines; never paste competitor numbers as if comparable.** Mark any borrowed number `[copied, unverified harness]`. Re-pin API model versions per run (they drift).
- [ ] **≥2 seeds (or few-shot selections) for any stochastic eval; report mean + variance, not a point.**

---

## Paper 3 — Reuel et al., "BetterBench" (Stanford) · arXiv:2411.12990 · 116 cites · **SOLID** (the benchmark-quality checklist)

A 46-criterion assessment framework across a benchmark's 5-stage lifecycle (design → implementation → documentation → maintenance → retirement), applied to 24 real benchmarks. Read in full (§3–6 + checklist + criteria appendix).

**Core insights:**
1. **Most benchmarks can't separate signal from noise: 14/24 ran the model only once** — no seeds, no temperature variation, no statistical significance/uncertainty reported. (§6) The single most-failed criterion class is reproducibility+interpretation: avg score 3.75/15 on "includes a script to replicate results," 5.62/15 on "reports statistical significance."
2. **17/24 provide no easy script to reproduce their headline numbers.** Implementation is the weakest lifecycle stage across the board. (§6)
3. **The contamination canary as a benchmark feature:** a good benchmark ships a **`training_on_test_set` task** (and/or globally-unique IDs / encrypted instances) so users can detect whether a model trained on it. Pioneered by very few. (§4.2)
4. **Design quality and usability quality correlate but are distinct** — a benchmark can be conceptually sound and operationally unusable; score them separately (they did: design avg 10.7, usability 8.7).
5. **Honest self-critique (rare and credit-worthy):** equal-criterion weighting means the framework itself is *gameable* — a developer can farm easy criteria (add a contact email, a README) without improving construct validity, which "requires in-depth domain-expert analysis, beyond the scope." They state this limitation outright. (§Limitations) This is exactly the Goodhart trap our constitution warns about — a checklist measures *checklist-compliance*, not *validity*.

**Verdict: SOLID, with a self-flagged ceiling.** The checklist is genuinely useful as a minimum-quality gate and the empirics (14/24, 17/24) are a damning, citable indictment of field norms. But heed their own caveat: passing the 46 criteria ≠ valid benchmark. Use it as a *floor*, never a *certificate*. The construct-validity work (Bean, prior memo) is the ceiling this can't reach.

**Adoptable rules (pre-flight):**
- [ ] **No single-run headline numbers — multiple runs (seeds/temperature), report mean + variance.** (BetterBench's #1 failure; also Miller; also Biderman — triple-cited, promote to hard rule.)
- [ ] **Ship a one-command replication script for every decision-grade eval result.** If a number can't be re-derived by `just <eval>` from stored inputs, it's not decision-grade. (17/24 fail this; we should not.)
- [ ] **For any eval whose items could leak into model training, include a contamination probe** (a `training_on_test_set` check, canary string, or post-cutoff holdout — see Paper 4). Don't assume freshness.
- [ ] **Document construct + limitations inline: what does this eval claim to measure, what's the operationalization, what are the known threats to validity?** A benchmark with no stated construct/limitations is a red flag (their documentation criterion).
- [ ] **Treat a checklist score as a FLOOR, not a certificate.** Passing hygiene criteria does not establish the eval measures what it claims — that needs domain-expert construct analysis. Never let "we followed the checklist" substitute for "we verified the verifier."

---

## Paper 4 — Jain et al., "LiveCodeBench" (Berkeley/MIT) · arXiv:2403.07974 · 1,676 cites · **SOLID** (the contamination-design pattern)

The canonical *contamination-resistant-by-construction* benchmark. Read the contamination + holistic-evaluation sections in full. Two ideas matter for us; the rest is code-specific.

**Core insights:**
1. **Date-tag every item; evaluate only on the post-model-cutoff window.** Problems are continuously scraped from LeetCode/AtCoder/CodeForces weekly contests, each tagged with a release date. For any model, you compare only on problems released *after its training cutoff*. (§1, §3) This is the contamination-resistant design pattern in one sentence.
2. **The smoking-gun contamination test (GENIUS-level move):** plot a model's accuracy vs problem-release-date. **DeepSeek's accuracy drops sharply on problems released after ~Sept 2023 — its own cutoff** — proving it memorized the earlier problems. (Fig 1, §5.1) The *slope/step at the cutoff date* is direct empirical evidence of contamination, no canary needed. Any held-out-by-time benchmark gets this diagnostic for free.
3. **Why this beats decontamination-by-matching:** exact/fuzzy n-gram dedup "can be evaded by simple rephrasing" (§3.1). Temporal holdout is robust to rephrasing because the *problem itself* didn't exist at training time. (Hierarchy: live/temporal-holdout > canary strings > fuzzy-match decontamination.)
4. **Holistic > single-metric:** they score 4 scenarios (generation, **self-repair**, code-execution, **test-output-prediction**) and show *relative model rankings change across scenarios* — a model good at generation can be bad at self-repair. Single-task scores hide capability profile. (§2) Agentic-eval relevance: outcome-only on one task is a thin instrument.

**Verdict: SOLID** (design), with one **GENIUS** sub-move (the cutoff-date discontinuity as a contamination *detector*, not just preventer). High citation count is earned — it set the template every "live" benchmark now copies. Caveat: contests-as-source assumes the contest problems are themselves quality-validated (they lean on platform reputation rather than re-validating).

**Adoptable rules (pre-flight):**
- [ ] **Author eval items fresh / post-cutoff, OR date-tag them and restrict comparison to the post-model-cutoff window.** Never lift items from public benchmarks (SimpleQA/FEVER/HumanEval) for a decision-grade eval — both the model's parametric memory and (for search evals) the live index are contaminated. (Reinforces the delta-memo contamination rule.)
- [ ] **When you have date-tagged items, run the contamination diagnostic: accuracy vs item-release-date, look for a step at the model's cutoff.** A discontinuity = memorization, discount the pre-cutoff items. This is nearly free and beats canaries.
- [ ] **Prefer temporal/live holdout over string-matching decontamination** — rephrasing evades n-gram dedup; a post-cutoff item evades nothing because it didn't exist.
- [ ] **Score a capability PROFILE across scenarios, not one outcome number** — relative rankings reorder across task types; a single metric hides the profile (esp. for agentic evals: add a process/recovery/self-repair axis, don't report outcome-only). Cross-ref SeekBench groundedness/recovery/calibration (epistemic-quality-evals.md).

---

## The consolidated pre-flight checklist (what to add to the eval skill)

Ordered by leverage. Items marked ★ are triple-sourced (Miller + Biderman + BetterBench all independently demand them) — promote to hard gates.

**Statistics & power (Miller):**
1. ★ Every decision-grade number reports **SE + n** (CLT-based; Bernoulli only for 0/1, never F1/partial/judge scores).
2. **Power/MDE pre-check** before running: can this n (and K) detect the effect I care about? If not, add items/resamples or don't run. (~1,000 items to resolve 3pp; small N → screening only.)
3. **Paired comparison on shared items** (paired-diff SE or McNemar), report difference + CI + correlation — not two independent accuracies.
4. **Cluster the SE** when items are grouped (≤3× widening); unclustered grouped CIs are anti-conservative.
5. Variance reduction by **resampling K (4–10) or next-token probs**, **never by lowering temperature**.

**Reproducibility & instrumentation (Biderman):**
6. ★ **Pin harness:** exact prompts + extraction/scoring code + model-version + commit hash stored with the number.
7. **Log raw output AND extracted answer; report extraction-failure rate** — separate format-compliance from correctness.
8. **Declare prompt format + MC length-normalization; hold constant across models; disclose prompt-tuning.**
9. ★ **One-command replication script** for every decision-grade result; **version the task**, bump on scoring changes.
10. **Re-run baselines; never paste competitor numbers as comparable** (mark copied/unverified; re-pin API versions per run).

**Multiple runs (★ all three papers):**
11. ★ **No single-run headline numbers** — ≥2 seeds/temperatures/few-shot selections, report **mean + variance**.

**Contamination (LiveCodeBench + BetterBench + delta-memo):**
12. **Fresh/post-cutoff items**; never lift from public benchmarks for decision-grade evals.
13. **Contamination diagnostic** when date-tagged: accuracy-vs-release-date, step at cutoff = memorization. Prefer temporal holdout > canary > fuzzy-match dedup.

**Construct & judges (prior memos — cross-ref, not re-derived here):**
14. **State the construct + operationalization + limitations inline**; checklist score is a FLOOR not a certificate (BetterBench self-caveat; Bean construct-validity).
15. **Judges:** cross-lab panel to surface (not average away) style-bias disagreement; stakes-neutral + engine-blind prompt; warrant-not-relevance rubric; resolve against human-anchored gold on a subset. (frontier-judge-bias-measured.md, delta-memo, AA-instrument-validity.md.)
16. **Score a capability profile across scenarios; for agents add a process/recovery axis, not outcome-only** (LiveCodeBench; SeekBench).

---

## What I did NOT chase (turn budget + already-covered)
- IRT-for-efficiency (tinyBenchmarks) — S2 returned nothing; the IRT *concept* is covered (Zhou 2505.15055, benchmarking-science-2026.md). tinyBenchmarks' actual contribution (anchor-point subset selection to cut eval cost ~100×) is a known result; flag for a future read only if we ever need to cheapen a large eval.
- Liao/Xiang measurement-theory-for-ML — the construct-validity axis is already well-covered by Bean (prior memo); diminishing returns.
- Agentic reward-hacking primary sources — covered by `agentic-hygiene-plateau-reward-hacking.md`, `2026-05-27-agent-safety-alignment-4w.md` (METR ≥16% cheating), and the AA-memo's IFBench RLVR-degrades-quality finding. Did not re-fetch.
- Behavioral judge-bias rates — DELIBERATELY not re-measured from papers (papers lag a generation); our live-probe memo (`2026-06-11-frontier-judge-bias-measured.md`) is the frontier-valid instrument.

## Provenance & gotchas
- All 4 papers read via **HTML full-text** (`curl -A Mozilla https://arxiv.org/html/{id}v1` → strip tags). **`research-mcp fetch_paper` failed on all 4 arXiv DOIs/URLs** (Sci-Hub + OA both 404) — consistent with the standing gotcha (`fetch_paper FAILS on arXiv → curl + strip`). Saved to corpus (metadata only); full text is in `/tmp/txt_{id}.txt` for this session.
- Citation counts from S2 (Miller 87, Biderman 161, BetterBench 116, LiveCodeBench 1676). All are arXiv preprints/workshop-grade except LiveCodeBench (ICLR 2025) and BetterBench (NeurIPS 2024 D&B) — provenance ceiling B→A for the two published ones.
- Sibling memo `2026-06-14-benchmark-leaderboard-methodology-critique.md` (concurrent session) critiques named *leaderboards*; this memo extracts the *primary-source method*. Overlap only at LiveCodeBench (they critique the instrument, I extract its design pattern).

---

## Item analysis (psychometric) — research → BUILT TOOL (2026-06-14)

The psychometric/personnel-selection frame ("think like someone who designs IQ tests or recruits
for NASA") applied to our evals. Prior art (evals `frontier-discrimination.md`, `benchmarking-science-2026.md`)
documented the METHODS (IRT difficulty/discrimination, point-biserial, item-information/CAT,
contamination-as-negative-discrimination) but left them as formulas/pseudocode — **zero built tooling**.
The gap was architecture, not research. Built: `skills/eval/scripts/item_analysis.py` (+ tests).

**Validation (the reason it exists).** Ran item analysis on the real extraction_bakeoff response
matrix (5 models × 3 items). It **mechanically flagged `diekstra` #1-to-inspect** — the exact item
that last session was only caught after the operator said "go look at the traces" (composer's 0/33
was *correct*; the gold was contaminated with drop-class methodology claims). A manual trace-audit
catch is now an automatic statistical flag. This is the consumption the build was named for.

**Honest result (not overclaimed).** Absolute corrected item-total r on diekstra was only −0.06 (not
strongly negative): composer scored 0 but gpt-5.5 — also top-ability — scored 0.81 (it *included* the
same drop-class claims), so the two nearly cancel. The robust signal at small N is **"lowest
discrimination + highest top-model dispersion"** (diekstra: top_disp 0.41 vs 0.09/0.15 on clean items),
NOT "strongly negative r." The tool ranks by a composite anomaly score and labels output DIRECTIONAL
below 8 models × 5 items — flags are leads for a trace audit, never verdicts.

**The probe earned its keep by finding a bug** before the tool was committed: a 0–1 difficulty
threshold applied to 0–3 faithfulness scores produced spurious CEILING flags on the intel track. Fix:
normalize every score per `scale_max`. Locked by `test_scale_normalization_no_false_ceiling`.

**Explore→converge (selection rationale, constitution P6).** 7 candidate mechanisms: full 2PL/3PL/4PL
IRT · DIF (Mantel-Haenszel/logistic) · Mokken-H · Bayesian-IRT · leave-one-out influence · CTT
discrimination · top-model dispersion. At our N (5–15 models × 3–100 items) full IRT is underpowered
(SEs too large <20 models × <100 items — `frontier-discrimination.md`), DIF needs model-family groups +
N. **Chose CTT discrimination + small-N-robust signals (top-dispersion, top-in-bottom)** for v1, with a
documented **upgrade path to IRT** once an item bank is calibrated (tinyBenchmarks 2402.14992 /
LEGO-IRT 2510.04051 — anchor-item subset → stable ability from ~3% of items).

**Wired:** eval-skill Phase 4.5 (mechanizes checks #1–2, the manual outlier/gold-validity reads) +
`pretool-eval-preflight.sh` item 9. **Criterion validity** (the NASA-recruiter half) added to the
design phase (construct/consumer step): name the real-world outcome the score predicts (Schmidt-Hunter
selection validity); a benchmark never checked against the downstream outcome is a vanity metric. That
is consumption-over-autonomy with a name and a literature.

**Open / deferred:** IRT param fitting (needs the item bank); DIF across model families (reasoning-heavy
vs retrieval-heavy items) once N supports it; test-retest reliability + SEM CIs from the ≥2-seed runs the
hook already mandates. Not built — flagged, not chased.
