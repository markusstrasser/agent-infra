-- Fix-of-fix chains: files fixed then fixed again within 3 days
-- Usage: runlog.py query fix_chains
SELECT * FROM v_fix_chains
ORDER BY fix1_date DESC
LIMIT 30;
