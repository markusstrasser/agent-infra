#!/usr/bin/env bash
# pdftotext all downloaded PDFs, cap to 80K chars (bounds codex context; drops figure-dump tails).
set -uo pipefail
OUT=/Users/alien/Projects/agent-infra/research/papers-2026-06-20
mkdir -p "$OUT/txt"
n=0
for pdf in "$OUT"/*.pdf; do
  id=$(basename "$pdf" .pdf)
  pdftotext -q "$pdf" - 2>/dev/null | head -c 80000 > "$OUT/txt/${id}.txt"
  c=$(wc -c < "$OUT/txt/${id}.txt")
  [ "$c" -lt 1500 ] && echo "THIN: $id ($c chars) — pdftotext may have failed" || n=$((n+1))
done
echo "converted_ok=$n / $(ls -1 $OUT/*.pdf | wc -l)"
