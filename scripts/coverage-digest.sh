#!/usr/bin/env bash
# Coverage digest for novelty checking
# Generates ~1200-1500 token summary of existing findings, hooks, and rules.
# Used by: session-analyst (pre-Gemini dispatch), future novelty gate hook.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMPROVEMENT_LOG="${IMPROVEMENT_LOG:-${SCRIPT_DIR}/../improvement-log.md}"
GLOBAL_SETTINGS="${HOME}/.claude/settings.json"
META_SETTINGS="${SCRIPT_DIR}/../.claude/settings.json"

echo "## EXISTING FINDINGS (do NOT re-report these patterns):"
if [ -f "$IMPROVEMENT_LOG" ]; then
  grep "^### \[" "$IMPROVEMENT_LOG" | tail -50 | sed 's/^### //'
fi

echo ""
echo "## ACTIVE HOOKS (these patterns are already enforced architecturally):"
python3 -c "
import json, os, sys

HOOK_DESCRIPTIONS = {
    'pretool-bash-loop-guard.sh': 'blocks infinite bash for/while loops',
    'tool-tracker.sh': 'blocks duplicate file reads (>3x same file in recency window)',
    'pretool-search-burst.sh': 'blocks >5 search/web calls in 60s window',
    'pretool-llmx-guard.sh': 'blocks known-broken llmx patterns (-f with gemini, wrong flags)',
    'pretool-cost-guard.sh': 'warns when session cost exceeds threshold',
    'pretool-subagent-gate.sh': 'validates subagent dispatch (type, isolation, scope)',
    'pretool-commit-check.sh': 'validates commit message format and trailers',
    'pretool-source-remind.sh': 'reminds to tag claim sources on research file writes',
    'pretool-consensus-search.sh': 'warns against confirmation-only search patterns',
    'pretool-append-only-guard.sh': 'blocks deletion in append-only files (improvement-log, decisions/)',
    'pretool-shared-infra-guard.sh': 'warns on shared infrastructure file modifications',
    'pretool-ast-precommit.sh': 'validates Python syntax before commit',
    'pretool-goal-drift.sh': 'warns when edits drift from stated task goal',
    'pretool-regression-dag-gate.sh': 'blocks edits that would break dependency chains',
    'pretool-companion-remind.sh': 'suggests companion skills for current task',
    'permission-auto-allow.sh': 'auto-allows pre-approved permission patterns',
    'pretool-modal-cost-guard.sh': 'blocks Modal GPU requests above cost threshold',
    'prewrite-frontmatter-inject.sh': 'auto-injects frontmatter on new research files',
}

for path in sys.argv[1:]:
    if not os.path.exists(path):
        continue
    try:
        with open(path) as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, IOError):
        continue
    for event, matchers in cfg.get('hooks', {}).items():
        if not isinstance(matchers, list):
            continue
        for m in matchers:
            matcher = m.get('matcher', '*')
            for h in m.get('hooks', []):
                if h.get('command'):
                    name = os.path.basename(h['command'].split()[0])
                    desc = HOOK_DESCRIPTIONS.get(name, '')
                    if desc:
                        print(f'- [{event}:{matcher}] {name} — {desc}')
                elif h.get('prompt'):
                    prompt_short = h['prompt'][:80].replace('\n', ' ')
                    print(f'- [{event}:{matcher}] prompt-hook: {prompt_short}...')
" "$GLOBAL_SETTINGS" "$META_SETTINGS" 2>/dev/null

echo ""
echo "## KEY RULES (already in global CLAUDE.md — do NOT re-propose these):"
echo "- Rule 6: explore before converging (brainstorm 5+ alternatives for design tasks)"
echo "- Rule 7: probe before build (validate core assumption before wiring infrastructure)"
echo "- Rule 8: compare automation alternatives before building new scripts"
echo "- Rule 9: verify failure claims in logs before deploying architectural fixes"
echo "- Rule 10: write for structural rewrites (>3 sections → Write, not sequential Edit)"
echo "- Rule 11: verify implementation before documenting (run --help, grep, test)"
echo "- Rule 12: verify vendor claims before asserting (search-verify pricing, features, flags)"
echo "- Subagent rules: turn budget in prompt, output to file >1000 chars, inventory before dispatch"
echo "- Git rules: no branches, auto-commit to main, [scope] Verb thing — why format"
echo "- Environment: uv run python3, not bare python3; .py files over inline python3 -c"
