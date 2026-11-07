"""
Advanced synthetic CodePulse integration demo.

Run from the codepulse_backend project root:
    python test_advanced_demo.py

This is synthetic data (not live platform API data). It exercises:
- 4 connected platforms
- cross-platform canonical-ID deduplication
- repeated problem records within a profile
- multi-topic problems and submissions
- topic aliases / normalization
- repeated submission IDs and missing submission IDs
- untagged submissions and problem records
- incomplete history / pagination metadata
- contest rating histories and daily activity
- topic classifications with >= 10 judged submissions
"""

from datetime import datetime, timedelta, timezone

from models.input_models import AnalysisRequest
from engine.analysis_engine import analyze_user


PLATFORMS = [
    ("LeetCode", "demo_leetcode", 1842),
    ("Codeforces", "demo_codeforces", 1675),
    ("CodeChef", "demo_codechef", 1720),
    ("GeeksforGeeks", "demo_gfg", 0),
]

# Accepted submissions out of 12 per platform, for each topic.
# Across 4 platforms this gives 48 judged submissions per topic before
# the deliberately added multi-topic event.
TOPIC_ACCEPTED = {
    "Arrays": 11,                 # Strong
    "Graphs": 9,                  # Good
    "Dynamic Programming": 6,    # Developing
    "Trees": 3,                   # Needs Improvement
    "Greedy": 10,                 # Strong
}

# Keep canonical topic labels consistent in this stress test. The separate
# multi-topic event tests the rule that one submission contributes to each tag.
TOPIC_INPUT_NAMES = {topic: [topic] * 4 for topic in TOPIC_ACCEPTED}


def make_contests(platform_index: int) -> list[dict]:
    """Create 4 contest records per profile with different rating trajectories."""
    base = 1_790_000_000 + platform_index * 10_000
    changes_by_platform = [
        [42, 31, -18, 55],
        [35, -22, -41, 12],
        [-15, -28, -36, 20],
        [18, 24, -10, 33],
    ]
    rating = [1450, 1600, 1500, 1200][platform_index]
    contests = []
    for i, change in enumerate(changes_by_platform[platform_index]):
        new_rating = rating + change
        contests.append({
            "contest_id": f"{platform_index}-{100 + i}",
            "contest_name": f"Demo Contest {i + 1}",
            "timestamp": base + i * 86_400 * 14,
            "old_rating": rating,
            "new_rating": new_rating,
            "rating_change": change,
            "rank": 120 + i * 37 + platform_index * 9,
        })
        rating = new_rating
    return contests


def make_daily_activity(platform_index: int) -> dict[str, int]:
    today = datetime.now(timezone.utc).date()
    activity = {}
    for offset in range(29, -1, -1):
        # Different activity patterns; some zero-activity days are intentional.
        count = (offset * 3 + platform_index * 5) % 9
        if (offset + platform_index) % 4 == 0:
            count = 0
        if count:
            day = today - timedelta(days=offset)
            activity[day.isoformat()] = count
    return activity


def build_profile(platform_index: int) -> dict:
    platform_name, username, rating = PLATFORMS[platform_index]
    problem_activity = []
    submission_activity = []

    accepted_total = 0
    failed_total = 0

    # Create 12 attempted problems per topic per platform.
    # The first 3 IDs in each topic are intentionally shared across platforms.
    for topic_index, (topic, _) in enumerate(TOPIC_ACCEPTED.items()):
        raw_tag = TOPIC_INPUT_NAMES[topic][platform_index]

        for problem_index in range(12):
            if problem_index < 3:
                canonical_id = f"shared:{topic.lower().replace(' ', '-')}:p{problem_index}"
            else:
                canonical_id = (
                    f"{platform_name.lower()}:{topic.lower().replace(' ', '-')}:"
                    f"p{problem_index}"
                )

            solved = problem_index < [8, 7, 5, 4, 9][(topic_index + platform_index) % 5]
            problem_activity.append({
                "platform_problem_id": f"{platform_index}-{topic_index}-{problem_index}",
                "canonical_id": canonical_id,
                "title": f"{topic} Practice Problem {problem_index + 1}",
                "tags": [raw_tag],
                "solved": solved,
            })

        # 12 judged submissions per topic. Keep repeated attempts as separate
        # events; the success ratio differs by topic to exercise classification.
        accepted_count = TOPIC_ACCEPTED[topic]
        for attempt_index in range(12):
            accepted = attempt_index < accepted_count
            accepted_total += int(accepted)
            failed_total += int(not accepted)

            submission_activity.append({
                "submission_id": f"{platform_index}-{topic_index}-sub-{attempt_index}",
                "platform_problem_id": f"{platform_index}-{topic_index}-{attempt_index % 12}",
                "canonical_id": (
                    f"shared:{topic.lower().replace(' ', '-')}:p{attempt_index % 3}"
                    if attempt_index % 12 < 3
                    else f"{platform_name.lower()}:{topic.lower().replace(' ', '-')}:p{attempt_index % 12}"
                ),
                "tags": [raw_tag],
                "accepted": accepted,
            })

    # Multi-topic submission: it contributes once to BOTH topic buckets.
    submission_activity.append({
        "submission_id": f"{platform_index}-multi-topic-event",
        "platform_problem_id": f"{platform_index}-multi-topic-problem",
        "canonical_id": f"{platform_name.lower()}:multi-topic-problem",
        "tags": ["Arrays", "Bit Manipulation"],
        "accepted": platform_index != 2,
    })
    if platform_index != 2:
        accepted_total += 1
    else:
        failed_total += 1

    # One event with no tags: it counts in overall submission totals but cannot
    # contribute to topic-specific accuracy.
    submission_activity.append({
        "submission_id": f"{platform_index}-untagged-event",
        "platform_problem_id": f"{platform_index}-unknown-problem",
        "canonical_id": None,
        "tags": [],
        "accepted": False,
    })
    failed_total += 1

    # One event with a missing submission ID, deliberately untagged so it does
    # not alter the five topic classification ratios.
    if platform_index == 1:
        submission_activity.append({
            "submission_id": None,
            "platform_problem_id": "codeforces-missing-submission-id",
            "canonical_id": None,
            "tags": [],
            "accepted": False,
        })
        failed_total += 1

    # One repeated submission ID. Aggregator should count it only once.
    repeated = dict(submission_activity[0])
    submission_activity.append(repeated)

    # Add a solved problem with no canonical ID for one profile. This must not
    # be guessed/deduplicated by title or platform-local ID.
    if platform_index == 2:
        problem_activity.append({
            "platform_problem_id": "codechef-unmapped-solved-999",
            "canonical_id": None,
            "title": "Unmapped solved problem",
            "tags": ["Arrays"],
            "solved": True,
        })

    # One problem with no usable tags for another profile.
    if platform_index == 3:
        problem_activity.append({
            "platform_problem_id": "gfg-untagged-888",
            "canonical_id": "gfg:untagged:888",
            "title": "Problem missing topic metadata",
            "tags": [],
            "solved": False,
        })

    solved_count = sum(bool(problem["solved"]) for problem in problem_activity)

    # The source-level totals represent deduplicated judged submissions.
    # The repeated ID above is intentionally excluded from these totals.
    return {
        "platform_name": platform_name,
        "username": username,
        "current_rating": rating if rating else None,
        "total_solved": solved_count,
        "correct_submissions": accepted_total,
        "failed_submissions": failed_total,
        "total_attempted": accepted_total + failed_total,
        "problem_activity": problem_activity,
        "submission_activity": submission_activity,
        "contest_history": make_contests(platform_index),
        "daily_activity": make_daily_activity(platform_index),
        "data_complete": platform_index != 3,  # GFG history deliberately partial
        "pagination_pages": [8, 12, 5, 3][platform_index],
        "duplicate_submission_records": 1,
        "missing_submission_ids": 1 if platform_index == 1 else 0,
        "problemset_lookup_misses": 1 if platform_index == 2 else 0,
        "problemset_entries_without_tags": 1 if platform_index == 3 else 0,
    }


def main() -> None:
    raw_profiles = [build_profile(i) for i in range(len(PLATFORMS))]
    request = AnalysisRequest.model_validate({
        "display_name": "CodePulse Advanced Demo",
        "platforms": raw_profiles,
    })

    response = analyze_user(request.platforms, request.display_name)
    output = response.model_dump(mode="json")

    overview = output["overview"]
    quality = output["data_quality"]

    print("\n========== CODEPULSE ADVANCED DEMO ==========\n")
    print("SYNTHETIC INPUT")
    print(f"Connected profiles: {len(raw_profiles)}")
    print(f"Problem activity records: {sum(len(p['problem_activity']) for p in raw_profiles)}")
    print(f"Submission event records (including repeated IDs): {sum(len(p['submission_activity']) for p in raw_profiles)}")

    print("\nOVERVIEW")
    for key in (
        "platform_reported_solved",
        "total_solved",
        "duplicate_solved_across_platforms",
        "unresolved_solved_count",
        "unique_solved_complete",
        "correct_submissions",
        "failed_submissions",
        "total_attempted",
        "success_rate",
        "total_contests",
        "active_days",
    ):
        print(f"{key}: {overview.get(key)}")

    print("\nPLATFORM COMPARISON")
    for row in output["platform_comparison"]:
        print(
            f"{row['platform']:16} user={row['username']:18} "
            f"solved={row['solved']:3} rating={str(row['current_rating']):5} "
            f"accepted={row['correct_submissions']:3} failed={row['failed_submissions']:3} "
            f"acceptance={row['submission_success_rate']}%"
        )

    print("\nTOPIC ANALYTICS")
    for row in output["topic_analytics"]:
        print(
            f"{row['topic']:24} unique_solved={str(row['solved']):>3} "
            f"unique_attempted={str(row['attempted']):>3} "
            f"completion={str(row['completion_rate']):>6}% "
            f"accepted={str(row['accepted_submissions']):>3} "
            f"failed={str(row['failed_submissions']):>3} "
            f"judged={str(row['submission_count']):>3} "
            f"accuracy={str(row['submission_success_rate']):>6}% "
            f"classification={row['classification']}"
        )

    print("\nCONTEST ANALYTICS")
    for platform in output["contest_analytics"]["platforms"]:
        print(f"{platform['platform']}: {len(platform['rating_history'])} contest records")

    print("\nINSIGHTS")
    for item in output["insights"]:
        print(f"- [{item['type']}] {item['title']}: {item['description']}")

    print("\nRECOMMENDATIONS")
    for item in output["recommendations"]:
        print(f"- [{item['priority']}] {item['topic']}: {item['action']}")
        print(f"  Reason: {item['reason']}")

    print("\nDATA QUALITY")
    for key, value in quality.items():
        if key != "notes":
            print(f"{key}: {value}")
    for note in quality["notes"]:
        print(f"- {note}")

    # -------------------- Assertions --------------------
    assert output["user_summary"]["platforms_connected"] == 4
    assert overview["platform_reported_solved"] == sum(p["total_solved"] for p in raw_profiles)
    assert overview["total_solved"] <= overview["platform_reported_solved"]
    assert overview["duplicate_solved_across_platforms"] > 0
    assert 0 <= overview["success_rate"] <= 100

    topics = {row["topic"]: row for row in output["topic_analytics"]}
    for topic in ("Arrays", "Graphs", "Dynamic Programming", "Trees", "Greedy"):
        assert topic in topics, f"Missing expected topic: {topic}"
        row = topics[topic]
        assert row["submission_count"] >= 10, f"{topic} did not reach classification threshold"
        assert row["accepted_submissions"] + row["failed_submissions"] == row["submission_count"]

    assert topics["Arrays"]["classification"] == "Strong"
    assert topics["Graphs"]["classification"] == "Good"
    assert topics["Dynamic Programming"]["classification"] == "Developing"
    assert topics["Trees"]["classification"] == "Needs Improvement"
    assert topics["Greedy"]["classification"] == "Strong"

    assert quality["partial_data"] is True
    assert quality["history_complete"] is False
    assert quality["topic_tag_coverage_complete"] is False
    assert quality["canonical_id_coverage_complete"] is False
    assert quality["duplicate_submission_records"] >= 1
    assert quality["missing_submission_ids"] >= 1

    # A multi-tag submission should appear in both topic buckets.
    assert topics["Bit Manipulation"]["submission_count"] == 4

    print("\nALL ADVANCED DEMO CHECKS PASSED.")


if __name__ == "__main__":
    main()
