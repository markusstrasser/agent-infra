# Runlog OTel / OpenInference Compatibility

This run store is local-first and domain-first. OTel / OpenInference is treated as a vocabulary source and later export target, not as the canonical storage model.

## Borrowed Now

| Runlog field | OTel / OpenInference analogue | Decision |
|---|---|---|
| `runs.provider_name` | `gen_ai.provider.name` | Direct map |
| `runs.model_requested`, `runs.model_resolved` | `gen_ai.request.model`, `gen_ai.response.model` | Direct map |
| `runs.transport` | transport / client attribute | Direct map |
| `tool_calls.tool_name` | tool name attributes | Direct map |
| `tool_calls.args_json`, `tool_calls.result_json` | tool args / result attributes | Direct map |
| `events.kind = tool_call` | `execute_tool`-style span/event | Direct map |
| `events.kind = assistant_message`, `user_message` | message items | Direct map |
| `events.kind = token_usage` | usage attributes | Direct map |

## Kept Custom

| Runlog field | Why it stays custom in v1 |
|---|---|
| `sessions` vs `runs` split | CLI artifacts expose long-lived conversation IDs and shorter analytic run units; current GenAI semconv does not capture this cleanly. |
| `sources`, `imports`, `record_refs` | Import provenance and byte-level traceability are outside current OTel trace concerns. |
| `run_edges` | Resume / fork / spawn lineage is central here and still under-specified in current agentic-semconv work. |
| `file_touches` | File-side effects matter for coding-agent forensics and are not well covered by current generic tool spans. |
| `permission_*` event kinds | Supervision lifecycle is an explicit local requirement. |
| `completeness`, `completeness_notes` | Needed to mark sparse Gemini passive imports honestly. |

## Export Stance

- Keep canonical storage in SQLite.
- Export views later if downstream tooling wants OTel-like traces.
- Do not force span hierarchy into the canonical schema until the agentic semantic conventions stabilize.

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: fb0eac7dfa71


end-knowledge-index -->
