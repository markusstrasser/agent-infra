-- Commit type distribution by project
-- Usage: runlog.py query commit_type_summary
SELECT
    project,
    commit_type,
    COUNT(*) as n,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY project), 1) as pct
FROM git_commits
GROUP BY project, commit_type
ORDER BY project, n DESC;
