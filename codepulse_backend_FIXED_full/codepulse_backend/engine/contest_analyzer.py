from datetime import datetime, timezone
from typing import Any


def analyze_contests(platforms: list[dict[str, Any]]) -> dict[str, Any]:
    platform_results = []
    chart_series = []
    total_contests = 0

    for platform in platforms:
        records = sorted(platform["contest_history"], key=lambda item: item["timestamp"])
        total_contests += len(records)
        changes = [r["rating_change"] for r in records if r.get("rating_change") is not None]
        ratings = []
        points = []

        for record in records:
            rating = record.get("new_rating")
            if rating is None and record.get("old_rating") is not None and record.get("rating_change") is not None:
                rating = record["old_rating"] + record["rating_change"]
            if rating is not None:
                ratings.append(rating)
                date = datetime.fromtimestamp(record["timestamp"], tz=timezone.utc).date().isoformat()
                points.append({
                    "timestamp": record["timestamp"],
                    "date": date,
                    "rating": rating,
                    "rating_change": record.get("rating_change"),
                    "contest_name": record.get("contest_name"),
                })

        current_rating = platform["current_rating"]
        if current_rating is None and ratings:
            current_rating = ratings[-1]

        platform_results.append({
            "platform": platform["platform"],
            "username": platform["username"],
            "total_contests": len(records),
            "positive_changes": sum(1 for value in changes if value > 0),
            "negative_changes": sum(1 for value in changes if value < 0),
            "average_rating_change": round(sum(changes) / len(changes), 2) if changes else None,
            "best_rating": max(ratings) if ratings else None,
            "latest_rating": current_rating,
            "rating_history": points,
            # Chronological rating_change values for EVERY contest that has one, including contests
            # without old/new ratings (those cannot be plotted but still count for dip detection).
            "rating_changes": changes,
        })
        if points:
            chart_series.append({
                "platform": platform["platform"],
                "data": [{"timestamp": p["timestamp"], "date": p["date"], "rating": p["rating"]} for p in points],
            })

    return {
        "total_contests": total_contests,
        "platforms": platform_results,
        "chart_series": chart_series,
    }


def find_rating_dips(contest_data: dict[str, Any], window: int = 3) -> list[dict[str, Any]]:
    """Platforms whose last `window` rating changes sum below zero, worst dip first.

    Sorted by (sum, platform name) so the result never depends on the order platforms were sent in.
    """
    dips = []
    for platform in contest_data["platforms"]:
        changes = platform.get("rating_changes")
        if changes is None:  # callers that build contest_data by hand
            changes = [p["rating_change"] for p in platform["rating_history"] if p["rating_change"] is not None]
        if len(changes) >= window and sum(changes[-window:]) < 0:
            dips.append({"platform": platform["platform"], "recent_sum": sum(changes[-window:])})
    dips.sort(key=lambda d: (d["recent_sum"], d["platform"].casefold()))
    return dips
