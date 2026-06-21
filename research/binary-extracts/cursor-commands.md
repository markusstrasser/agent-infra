# Cursor CLI built-in commands (backend-injected `<cursor_commands>`)

> Auto-captured by scripts/cursor_commands_extract.py from the newest Cursor
> agent transcript carrying a <cursor_commands> block. These are NOT on disk;
> the inter-capture diff is Cursor's unpublished built-in-command changelog.

Commands seen: best-of-n

---

--- Cursor Command: best-of-n ---
Compare models on the same task.

Run the same task in parallel across multiple model picks. Keep each run fully isolated in its own git worktree.

**The primary worktree must remain completely unchanged while `/best-of-n` is running.** Never let a candidate read/write/edit/shell/git its way through the parent checkout once a dedicated worktree exists for that repo.

**This command does not include applying or merging** any run onto the main worktree. Never copy patches to main or re-implement the winning attempt on the parent workspace as part of best-of-n.

## Input Contract

Expected format:

`/best-of-n <model_csv> <task prompt>`

Example:

`/best-of-n opus,codex,composer pls do foobar`

- `model_csv`: first token after `/best-of-n`, split by commas.
- `task prompt`: everything after `model_csv`.
- Preserve duplicates in `model_csv` (duplicates mean independent parallel runs).

## Workflow

1. Parse `model_csv` and `task prompt`.
2. If either is missing, ask the user for model CSV and task prompt.
3. Build model runs from CSV (split, trim, drop empty, preserve order and duplicates).
4. The primary agent is only a coordinator. It must not do repo-local file reads, edits, shell commands, or git commands in the parent checkout for the task itself.
5. Launch one `best-of-n-runner` subagent per model token in parallel.
6. Each subagent must invoke `/worktree` first to create or attach to its own dedicated git worktree for the task, run any required worktree setup, and then do all repo-local work inside that worktree only. Do not fall back to the parent worktree.
7. If a subagent cannot get its worktree into a usable state, that run should fail and report the blocker instead of continuing in the main checkout.
8. After all complete: consolidated comparison and recommendation.
9. **Stop.** Do not run apply scripts or merge any run onto main.

## Per-Subagent Prompt Pattern

- Use the `best-of-n-runner` subagent type.
- Before doing task work, first invoke `/worktree` (the worktree command) for that run. Do not hand-roll an alternative worktree flow in the parent checkout.
- After `/worktree` succeeds, stay inside that dedicated worktree for all repo-local reads, edits, shell commands, and git commands for the task.
- Until `/worktree` succeeds, do not perform repo-local reads, edits, shell commands, or git commands against the parent checkout.
- Return the worktree path and a concise outcome.
- If worktree creation or setup fails, stop that run and report the failure. Do not continue in the primary worktree.

## Output Format

- Parsed model runs
- One result block per run (including duplicates, plus its worktree path)
- Final comparison and recommendation

Can you figure out how to unify and make our RSI loops and self-improvement more tight an autonomous (without degrading quality or goodharting)
--- End Command ---
