
from models.input_models import AnalysisRequest
from engine.analysis_engine import analyze_user


def make_profile(
    platform_name,
    username,
    solved,
    attempted,
    accepted,
    failed,
    problem_activity,
    submission_activity,
    rating=None,
    complete=True,
    pages=1,
    duplicate_records=0,
    missing_tags_lookup=0,
):
    return {
        "platform_name": platform_name,
        "username": username,
        "current_rating": rating,
        "total_solved": solved,
        "correct_submissions": accepted,
        "failed_submissions": failed,
        "total_attempted": attempted,
        "solved_problems": [],
        "problem_activity": problem_activity,
        "submission_activity": submission_activity,
        "contest_history": [],
        "daily_activity": {"2026-11-01": 3},
        "data_complete": complete,
        "pagination_pages": pages,
        "duplicate_submission_records": duplicate_records,
        "missing_submission_ids": 0,
        "problemset_lookup_misses": missing_tags_lookup,
        "problemset_entries_without_tags": 0,
    }


platforms = [

    # 1. CODEFORCES
    make_profile(
        "Codeforces", "demo_cf",
        2, 5, 3, 2,

        [
            {
                "platform_problem_id": "cf-1-A",
                "canonical_id": "shared:two-sum",
                "tags": ["arrays"],
                "solved": True,
            },
            {
                "platform_problem_id": "cf-2-B",
                "canonical_id": "cf:2:B",
                "tags": ["graphs"],
                "solved": True,
            },
            {
                "platform_problem_id": "cf-3-C",
                "canonical_id": "cf:3:C",
                "tags": ["dp"],
                "solved": False,
            },
            {
                # Deliberately missing canonical ID and tags.
                "platform_problem_id": "cf-4-D",
                "canonical_id": None,
                "tags": [],
                "solved": False,
            },
        ],

        [
            {"submission_id": "s1", "platform_problem_id": "cf-1-A",
             "tags": ["arrays"], "accepted": False},

            {"submission_id": "s2", "platform_problem_id": "cf-1-A",
             "tags": ["arrays"], "accepted": True},

            {"submission_id": "s3", "platform_problem_id": "cf-2-B",
             "tags": ["graphs"], "accepted": True},

            {"submission_id": "s4", "platform_problem_id": "cf-3-C",
             "tags": ["dp"], "accepted": False},

            {"submission_id": "s5", "platform_problem_id": "cf-4-D",
             "tags": [], "accepted": True},

            # Deliberate duplicate submission ID.
            {"submission_id": "s1", "platform_problem_id": "cf-1-A",
             "tags": ["arrays"], "accepted": False},
        ],

        rating=1700,
        complete=True,
        pages=2,
        duplicate_records=1,
        missing_tags_lookup=1,
    ),

    # 2. LEETCODE
    make_profile(
        "LeetCode", "demo_lc",
        2, 3, 2, 1,

        [
            {
                # Same underlying problem as Codeforces.
                "platform_problem_id": "lc-two-sum",
                "canonical_id": "shared:two-sum",
                "tags": ["arrays"],
                "solved": True,
            },
            {
                "platform_problem_id": "lc-array-2",
                "canonical_id": "lc:array-2",
                "tags": ["arrays"],
                "solved": True,
            },
            {
                "platform_problem_id": "lc-tree-1",
                "canonical_id": "lc:tree-1",
                "tags": ["trees"],
                "solved": False,
            },
        ],

        [
            {"submission_id": "l1", "platform_problem_id": "lc-two-sum",
             "tags": ["arrays"], "accepted": True},

            {"submission_id": "l2", "platform_problem_id": "lc-array-2",
             "tags": ["arrays"], "accepted": True},

            {"submission_id": "l3", "platform_problem_id": "lc-tree-1",
             "tags": ["trees"], "accepted": False},
        ],

        rating=1850,
        complete=True,
    ),

    # 3. GEEKSFORGEEKS
    make_profile(
        "GFG", "demo_gfg",
        1, 2, 1, 1,

        [
            {
                "platform_problem_id": "gfg-array-1",
                "canonical_id": "gfg:array-1",
                "tags": ["arrays"],
                "solved": True,
            },
            {
                "platform_problem_id": "gfg-graph-1",
                "canonical_id": "gfg:graph-1",
                "tags": ["graphs"],
                "solved": False,
            },
        ],

        [
            {"submission_id": "g1", "platform_problem_id": "gfg-array-1",
             "tags": ["arrays"], "accepted": True},

            {"submission_id": "g2", "platform_problem_id": "gfg-graph-1",
             "tags": ["graphs"], "accepted": False},
        ],

        # Rating unavailable and history incomplete.
        rating=None,
        complete=False,
    ),

    # 4. CODECHEF
    make_profile(
        "CodeChef", "demo_cc",
        1, 2, 1, 1,

        [
            {
                "platform_problem_id": "cc-stack-1",
                "canonical_id": "cc:stack-1",
                "tags": ["stacks"],
                "solved": True,
            },
            {
                "platform_problem_id": "cc-dp-1",
                "canonical_id": "cc:dp-1",
                "tags": ["dynamic programming"],
                "solved": False,
            },
        ],

        [
            {"submission_id": "c1", "platform_problem_id": "cc-stack-1",
             "tags": ["stacks"], "accepted": True},

            {"submission_id": "c2", "platform_problem_id": "cc-dp-1",
             "tags": ["dynamic programming"], "accepted": False},
        ],

        rating=1450,
        complete=True,
    ),
]


# Validate data against the actual Pydantic schema.
request = AnalysisRequest.model_validate({
    "display_name": "CodePulse Multi-Platform Demo",
    "platforms": platforms,
})

# Run the actual analysis engine.
result = analyze_user(
    request.platforms,
    request.display_name,
)

output = result.model_dump(mode="json")

print("\n========== MULTI-PLATFORM CODEPULSE TEST ==========\n")

overview = output["overview"]

print("OVERVIEW")
print("Profiles connected:", output["user_summary"]["platforms_connected"])
print("Platform-reported solved:", overview["platform_reported_solved"])
print("Unique solved:", overview["total_solved"])
print("Duplicate solved:", overview["duplicate_solved_across_platforms"])
print("Correct submissions:", overview["correct_submissions"])
print("Failed submissions:", overview["failed_submissions"])
print("Overall submission accuracy:", overview["success_rate"], "%")
print("Unique solved fully verified:", overview["unique_solved_complete"])

print("\nTOPIC ANALYTICS")

topic_rows = {
    row["topic"].casefold(): row
    for row in output["topic_analytics"]
}

for row in output["topic_analytics"]:
    print(
        row["topic"],
        "| Solved:", row["solved"],
        "| Attempted:", row["attempted"],
        "| Completion:", row["completion_rate"],
        "| Accepted:", row["accepted_submissions"],
        "| Failed:", row["failed_submissions"],
        "| Submission accuracy:", row["submission_success_rate"],
        "| Classification:", row["classification"],
    )

print("\nDATA QUALITY")
print("Partial data:", output["data_quality"]["partial_data"])
print("Unavailable metrics:", output["data_quality"]["unavailable_metrics"])

for note in output["data_quality"]["notes"]:
    print("-", note)

# Expected-value assertions.
assert output["user_summary"]["platforms_connected"] == 4

assert overview["platform_reported_solved"] == 6
assert overview["total_solved"] == 5
assert overview["duplicate_solved_across_platforms"] == 1

assert overview["correct_submissions"] == 7
assert overview["failed_submissions"] == 5
assert overview["success_rate"] == 58.33

# All listed solved records have canonical IDs, but one profile's
# submission history is incomplete.
assert overview["unique_solved_complete"] is False

assert topic_rows["arrays"]["solved"] == 3
assert topic_rows["arrays"]["attempted"] == 3
assert topic_rows["arrays"]["completion_rate"] == 100.0

assert topic_rows["graphs"]["solved"] == 1
assert topic_rows["graphs"]["attempted"] == 2
assert topic_rows["graphs"]["completion_rate"] == 50.0

assert topic_rows["dynamic programming"]["solved"] == 0
assert topic_rows["dynamic programming"]["attempted"] == 2

assert topic_rows["arrays"]["submission_success_rate"] == 80.0
assert topic_rows["graphs"]["submission_success_rate"] == 50.0
assert topic_rows["dynamic programming"]["submission_success_rate"] == 0.0

assert output["data_quality"]["partial_data"] is True

print("\nALL MULTI-PLATFORM EXPECTED-VALUE CHECKS PASSED!")
