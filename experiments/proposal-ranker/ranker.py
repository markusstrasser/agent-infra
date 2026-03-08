"""Proposal ranker. This is the file the agent optimizes.

Scores work proposals by priority. Higher score = more urgent.
Input: a proposal dict with fields like category, title, metadata.
Output: a float score (higher = do first).
"""


def rank(proposal: dict) -> float:
    """Score a work proposal. Higher = more urgent."""
    category = proposal.get("category", "")
    title = proposal.get("title", "")
    metadata = proposal.get("metadata", {})

    # Base priority by category
    base = {
        "health": 80,
        "orchestrator": 70,
        "staleness": 40,
        "improvement-log": 30,
        "hook-roi": 20,
    }.get(category, 10)

    # Severity modifier
    if "FAIL" in title:
        base += 20
    elif "WARN" in title:
        base += 5

    # Age boost for unresolved items
    age_days = metadata.get("age_days", 0)
    if age_days > 14:
        base += min(age_days - 14, 20)

    # Staleness boost
    days_ago = metadata.get("days_ago", 0)
    if days_ago > 7:
        base += 10

    # Hook ROI: high block rate (false positives) is urgent
    block_rate = metadata.get("block_rate", 0)
    if block_rate > 0.3:
        base += 30

    # Recurring failures are worse
    consecutive = metadata.get("consecutive_failures", 0)
    if consecutive > 1:
        base += consecutive * 5

    # Autonomy-related findings get priority over cosmetic
    tags = metadata.get("tags", [])
    if "autonomy" in tags or "hook" in tags:
        base += 15

    return float(base)
