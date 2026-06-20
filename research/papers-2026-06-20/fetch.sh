#!/usr/bin/env bash
# Verify arxiv IDs resolve (hallucination check) + download PDFs. Reports MISSING ids.
set -uo pipefail
OUT=/Users/alien/Projects/agent-infra/research/papers-2026-06-20
cd "$OUT"
: > _status.tsv
while read -r id; do
  [ -z "$id" ] && continue
  url="https://arxiv.org/pdf/${id}"
  code=$(curl -sL -o "${id}.pdf" -w '%{http_code}' --max-time 60 "$url")
  if [ "$code" = "200" ] && [ -s "${id}.pdf" ] && file "${id}.pdf" | grep -qi pdf; then
    sz=$(wc -c < "${id}.pdf")
    echo -e "${id}\tOK\t${sz}" | tee -a _status.tsv
  else
    rm -f "${id}.pdf"
    echo -e "${id}\tMISSING\t${code}" | tee -a _status.tsv
  fi
  sleep 0.5
done < /tmp/arxiv_ids.txt
echo "=== SUMMARY ==="
ok=$(grep -c $'\tOK\t' _status.tsv); miss=$(grep -c $'\tMISSING\t' _status.tsv)
echo "OK=$ok MISSING=$miss"
echo "--- MISSING ids (verify: hallucinated or wrong) ---"; grep $'\tMISSING\t' _status.tsv || echo none
