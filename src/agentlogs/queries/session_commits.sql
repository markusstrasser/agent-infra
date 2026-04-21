-- Session → commit attribution (requires runlog import for session data)
-- Usage: runlog.py query session_commits
SELECT * FROM v_session_commits
ORDER BY authored_at DESC
LIMIT 30;
