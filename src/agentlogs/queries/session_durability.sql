-- Session durability: which sessions produce fragile code?
-- Usage: runlog.py query session_durability
SELECT * FROM v_session_durability
WHERE commits_produced >= 2
ORDER BY fragility_pct DESC
LIMIT 20;
