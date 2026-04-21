-- Files with 5+ commits in the import window, ranked by commit count
-- Usage: runlog.py query churn_hotspots
SELECT * FROM v_churn_hotspots
ORDER BY commits DESC
LIMIT 20;
