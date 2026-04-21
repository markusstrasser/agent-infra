-- Files that were built (feature commit) then retired (revert commit)
-- Usage: runlog.py query build_then_retire
SELECT * FROM v_build_then_retire
ORDER BY lifespan_days ASC
LIMIT 20;
