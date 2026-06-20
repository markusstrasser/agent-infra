#!/usr/bin/env bash
# Adversarial refute pass: per plan-claim, codex re-reads cited papers and tries to REFUTE
# "the integration faithfully uses the mechanism". read-only, $0. 6 claims, one wave.
set -uo pipefail
unset OPENAI_API_KEY
ROOT=/Users/alien/Projects/agent-infra
OUT=$ROOT/research/papers-2026-06-20
cd "$ROOT"
mkdir -p "$OUT/refute"

PRE='You are an ADVERSARIAL reviewer. Read research/2026-06-20-paper-integration-plan.md, then read the extraction files and (where needed) the raw paper text under research/papers-2026-06-20/txt/ for the IDs listed. Your job: try to REFUTE the claim that the proposed integration for CLAIM_TAG faithfully uses each cited paper PAPERS_ACTUAL mechanism. Hunt for: (a) the paper mechanism does NOT do what the plan says; (b) a precondition the paper REQUIRES does not hold in a single-operator LOCAL Claude/Codex/Cursor harness; (c) the evidence is too weak/narrow/pre-frontier to support the bolt-on; (d) the integration smuggles in something the paper never supports. For EACH cited paper give: VERDICT = HOLDS | NARROW | REFUTED + the single strongest objection (2-3 sentences) + one concrete correction to the plan. Be a skeptic, default to finding weakness, do not rubber-stamp. End with the COMPLETE report as your final message. Do NOT create or modify any files. '

refute() { local tag="$1"; local body="$2"; timeout 600 codex exec -s read-only -c model_reasoning_effort="high" -o "$OUT/refute/${tag}.md" "${PRE}${body}" >"$OUT/refute/${tag}.log" 2>&1; echo "done $tag exit=$? size=$(wc -c <"$OUT/refute/${tag}.md" 2>/dev/null)"; }

refute F1-trace-IR 'CLAIM_TAG=F1 (session-trace typed IR). PAPERS_ACTUAL: extractions 2606.06324.md, 2605.01920.md, 2606.11213.md, 2606.12329.md, 2605.26494.md. Especially scrutinize whether HTIR (2606.06324) actually compiles transcripts into a typed IR that yields the held-out gains, and whether the gains depend on something we lack.' &
refute F2-memory-links 'CLAIM_TAG=F2 (MEMORY condensed->raw provenance links). PAPERS_ACTUAL: extractions 2601.22436.md, 2606.09900.md, 2606.13177.md, 2606.14571.md. Especially scrutinize whether 2601.22436 really shows agents rely MORE on raw than condensed experience, or whether that is overread.' &
refute F3-predict-falsify 'CLAIM_TAG=F3 (predict-then-falsify gate). PAPERS_ACTUAL: extractions 2606.03108.md, 2606.20408.md. Especially scrutinize whether EvoTrainer (2606.03108) supports a per-edit mechanism-fired acceptance gate, or whether that is a different (RL training) regime that does not transfer to a prompt/rule/hook harness.' &
refute L1-anti-accretion 'CLAIM_TAG=L1 (act-drain anti-accretion). PAPERS_ACTUAL: extractions 2606.01619.md, 2606.03056.md, 2606.14571.md, 2606.07412.md. Especially scrutinize whether SkillDAG typed edges and ReSkill ADD/MODIFY/DELETE are demonstrated to reduce accretion, or merely asserted.' &
refute L2-eval-lanes 'CLAIM_TAG=L2 (/eval local harness-eval lanes). PAPERS_ACTUAL: extractions 2601.11868.md, 2605.10912.md, 2606.09426.md, 2606.05342.md, 2606.20408.md. Especially scrutinize the model-by-harness claim (WildClawBench 2605.10912) and whether trajectory-aware judging (WeaveBench 2606.09426) is reproducible locally without their infra.' &
refute L3-ask-gate 'CLAIM_TAG=L3 (over-ask uncertainty-decomposition ask-gate). PAPERS_ACTUAL: extractions 2606.19559.md, 2606.13603.md. Especially scrutinize whether request-uncertainty u_t is reliably elicitable from current models and whether the threshold routing actually reduces over-ask without raising wrong-action rate.' &
wait
echo "=== REFUTE DONE: $(ls -1 $OUT/refute/*.md | wc -l)/6 ==="
