from typing import Any

from .contest_analyzer import find_rating_dips


def _rank_topics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank the most actionable topics first. Lower accuracy is worse; larger
    judged samples are preferred when accuracy is equal.
    """
    return sorted(
        rows,
        key=lambda row: (
            row.get("submission_success_rate") is None,
            row.get("submission_success_rate") if row.get("submission_success_rate") is not None else 101,
            -(row.get("submission_count") or 0),
            str(row.get("topic", "")).casefold(),
        ),
    )


def generate_recommendations(
    topic_rows: list[dict[str, Any]],
    contest_data: dict[str, Any],
    has_activity: bool,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []

    weak_topics = _rank_topics(
        [row for row in topic_rows if row.get("classification") == "Needs Improvement"]
    )
    developing_topics = _rank_topics(
        [row for row in topic_rows if row.get("classification") == "Developing"]
    )

    for row in weak_topics[:3]:
        recommendations.append({
            "priority": "High",
            "topic": row["topic"],
            "action": f"Practise {row['topic']} problems, starting with easy questions and gradually moving to medium difficulty.",
            "reason": (
                f"Your topic submission accuracy is {row['submission_success_rate']}%: "
                f"{row['accepted_submissions']} accepted out of {row['submission_count']} judged submissions."
            ),
        })

    for row in developing_topics[:2]:
        recommendations.append({
            "priority": "Medium",
            "topic": row["topic"],
            "action": f"Revise core {row['topic']} patterns and solve a small, consistent set of practice problems.",
            "reason": (
                f"Your topic submission accuracy is {row['submission_success_rate']}%: "
                f"{row['accepted_submissions']} accepted out of {row['submission_count']} judged submissions."
            ),
        })

    for dip in find_rating_dips(contest_data):  # worst dip first, independent of input order
        recommendations.append({
            "priority": "Medium",
            "topic": None,
            "action": f"Review your last three {dip['platform']} contests and identify recurring mistakes before entering another contest.",
            "reason": f"Your rating changes across the last three recorded {dip['platform']} contests sum to {dip['recent_sum']}.",
        })

    if not has_activity:
        recommendations.append({
            "priority": "Low",
            "topic": None,
            "action": "Enable daily activity data in the profile importer so CodePulse can show consistency trends.",
            "reason": "No daily activity records were supplied, so practice consistency cannot currently be assessed.",
        })

    return recommendations[:6]
