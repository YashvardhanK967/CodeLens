from typing import Any


def build_chart_data(aggregated: dict[str, Any], contests: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform_solved": [
            {"platform": row["platform"], "solved": row["solved"]}
            for row in aggregated["platform_rows"]
        ],
        "topic_distribution": [
            {"topic": row["topic"], "solved": row["solved"]}
            for row in aggregated["topic_rows"]
            if row["solved"] is not None  # unknown is not zero: leave it off the chart
        ],
        "contest_rating_by_platform": contests["chart_series"],
        "daily_activity": aggregated["daily_activity"],
    }
