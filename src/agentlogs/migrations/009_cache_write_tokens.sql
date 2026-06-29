-- 009: separate cache-write tokens from cache-read.
--
-- Anthropic usage reports cache_creation_input_tokens (first write of a cacheable
-- prefix, billed ~1.25x input) distinctly from cache_read_input_tokens (re-read,
-- ~0.1x). Folding them into one column loses a >12x price difference, and the old
-- field map dropped cache_creation entirely. Add a dedicated column; the indexer
-- now maps cache_creation_input_tokens here and cache_read_input_tokens to
-- cached_tokens. Codex/OpenAI have no cache-write concept, so this stays NULL there.

ALTER TABLE runs ADD COLUMN cache_write_tokens INTEGER;

PRAGMA user_version = 9;
