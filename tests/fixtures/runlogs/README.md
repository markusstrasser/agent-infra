# Runlog Fixtures

This fixture corpus is scrubbed and synthetic. It preserves only the structural shapes needed for parser tests:

- Claude main-session transcript, tool error, and subagent lineage
- Codex session metadata, tool lifecycle, and MCP call shape
- Gemini rich `session-*.json` chat export plus sparse `logs.json` fallback

The fixtures are intentionally small. Their job is to lock parser behavior and provenance handling, not to approximate full production transcripts.
