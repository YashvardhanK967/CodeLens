from typing import Any

from models.input_models import PlatformData
from .topic_mapper import normalize_topic

_PLATFORM_NAMES = {
    "leetcode": "LeetCode",
    "codeforces": "Codeforces",
    "codechef": "CodeChef",
    "geeksforgeeks": "GeeksforGeeks",
    "gfg": "GeeksforGeeks",
    "atcoder": "AtCoder",
    "hackerrank": "HackerRank",
    "hackerearth": "HackerEarth",
    "cses": "CSES",
    "spoj": "SPOJ",
    "topcoder": "TopCoder",
    "codewars": "Codewars",
    "kattis": "Kattis",
    "interviewbit": "InterviewBit",
    "codingninjas": "Coding Ninjas",
}


def normalize_platform_name(name: str) -> str:
    cleaned = name.strip()
    key = cleaned.lower().replace(" ", "")
    if key in _PLATFORM_NAMES:
        return _PLATFORM_NAMES[key]
    # Unknown platform: keep the importer's own capitalisation if it has any ("MyJudge"),
    # only title-case when it arrived all-lowercase.
    return cleaned if cleaned != cleaned.lower() else cleaned.title()


def normalize_platforms(platforms: list[PlatformData]) -> list[dict[str, Any]]:
    """Convert validated Pydantic input into predictable internal dictionaries."""
    normalized: list[dict[str, Any]] = []

    for item in platforms:
        # Keep aggregate topic counts for old clients. The aggregator will use
        # problem_activity instead whenever at least one profile supplies it.
        topic_totals: dict[str, dict[str, Any]] = {}
        for topic in item.topics:
            canonical = normalize_topic(topic.tag_name)
            row = topic_totals.setdefault(
                canonical,
                {"solved_count": 0, "attempted_values": [], "attempts_complete": True},
            )
            row["solved_count"] += topic.solved_count
            if topic.attempted_count is None:
                row["attempts_complete"] = False
            else:
                row["attempted_values"].append(topic.attempted_count)

        topics = []
        for name, values in topic_totals.items():
            attempted = (
                sum(values["attempted_values"])
                if values["attempts_complete"] else None
            )
            topics.append({
                "topic": name,
                "solved": values["solved_count"],
                "attempted": attempted,
            })

        problem_activity = None
        if item.problem_activity is not None:
            problem_activity = []
            for problem in item.problem_activity:
                raw = problem.model_dump()
                raw["tags"] = sorted({
                    normalize_topic(tag)
                    for tag in problem.tags
                    if tag and tag.strip()
                })
                problem_activity.append(raw)

        submission_activity = None
        if item.submission_activity is not None:
            submission_activity = []
            for submission in item.submission_activity:
                raw = submission.model_dump()
                raw["tags"] = sorted({
                    normalize_topic(tag)
                    for tag in submission.tags
                    if tag and tag.strip()
                })
                submission_activity.append(raw)

        normalized.append({
            "platform": normalize_platform_name(item.platform_name),
            "username": item.username,
            "current_rating": item.current_rating,
            "total_solved": item.total_solved,
            "correct_submissions": item.correct_submissions,
            "failed_submissions": item.failed_submissions,
            "total_attempted": item.total_attempted,
            "topics": topics,
            "solved_problems": [problem.model_dump() for problem in item.solved_problems],
            "problem_activity": problem_activity,
            "submission_activity": submission_activity,
            "contest_history": [record.model_dump() for record in item.contest_history],
            "daily_activity": dict(item.daily_activity),
            "data_complete": item.data_complete,
            "pagination_pages": item.pagination_pages,
            "duplicate_submission_records": item.duplicate_submission_records,
            "missing_submission_ids": item.missing_submission_ids,
            "problemset_lookup_misses": item.problemset_lookup_misses,
            "problemset_entries_without_tags": item.problemset_entries_without_tags,
        })

    return normalized
