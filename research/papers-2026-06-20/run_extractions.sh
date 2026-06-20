#!/usr/bin/env bash
# Deep-read every paper via codex gpt-5.5 (read-only sandbox, $0 subscription).
# Structured extraction → extractions/<id>.md. Waves of 6 (codex MCP parallel limit).
set -uo pipefail
unset OPENAI_API_KEY
ROOT=/Users/alien/Projects/agent-infra
OUT=$ROOT/research/papers-2026-06-20
cd "$ROOT"
mkdir -p "$OUT/extractions"

extract() {
  local id="$1"
  [ -s "$OUT/extractions/${id}.md" ] && { echo "skip $id (done)"; return; }
  local P="You are an expert paper-reading agent. Read research/papers-2026-06-20/primer.md (OUR system) and research/papers-2026-06-20/txt/${id}.txt (a paper, full text) using your file tools. Then produce a STRUCTURED extraction with EXACTLY these markdown headers: (1) **IDs** — arxiv id + ACTUAL title from the text; flag any mismatch. (2) **Mechanism** — how it works, concretely, step by step. (3) **Why it works** — the causal/theoretical claim. (4) **Preconditions** — what must hold. (5) **Measured results** — exact numbers, what was measured, baseline, N/CIs, model(s) used (flag pre-frontier). (6) **Limitations / failure modes / non-transfer**. (7) **Integration into OUR system** — name the EXACT surface (act-drain, session-trace, skills/rules/hooks, MEMORY, /eval, predict-then-falsify, Workflow, ToolSearch) and the concrete bolt-on, or NOT-APPLICABLE + why. Be specific and skeptical; do not inflate vendor/paper numbers. End with the COMPLETE report as your final message. Do NOT create or modify any files."
  timeout 600 codex exec -s read-only -c model_reasoning_effort="medium" -o "$OUT/extractions/${id}.md" "$P" >"$OUT/extractions/${id}.log" 2>&1
  echo "done $id exit=$? size=$(wc -c < "$OUT/extractions/${id}.md" 2>/dev/null)"
}

ids=$(ls "$OUT"/txt/*.txt | xargs -n1 basename | sed 's/.txt$//')
i=0
for id in $ids; do
  extract "$id" &
  i=$((i+1))
  [ $((i % 6)) -eq 0 ] && wait && echo "=== wave $((i/6)) done ==="
done
wait
echo "=== ALL DONE: $(ls -1 $OUT/extractions/*.md | wc -l) extractions ==="
