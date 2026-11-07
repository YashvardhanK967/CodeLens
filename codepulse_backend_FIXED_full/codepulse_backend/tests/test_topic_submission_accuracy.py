from engine.aggregator import aggregate_platforms
from engine.normalizer import normalize_platforms
from engine.weakness_detector import classify_topics
from models.input_models import AnalysisRequest
from engine.analysis_engine import analyze_user


def _profile(username, problem_activity, submission_activity, total_solved=1, complete=True):
    return {
        "platform": "Codeforces",
        "username": username,
        "current_rating": 1500,
        "total_solved": total_solved,
        "correct_submissions": sum(1 for row in submission_activity or [] if row["accepted"]),
        "failed_submissions": sum(1 for row in submission_activity or [] if not row["accepted"]),
        "total_attempted": len(submission_activity or []),
        "topics": [],
        "solved_problems": [],
        "problem_activity": problem_activity,
        "submission_activity": submission_activity,
        "contest_history": [],
        "daily_activity": {},
        "data_complete": complete,
    }


def test_topic_submission_accuracy_counts_every_judged_attempt():
    profile = _profile(
        "alice",
        [
            {"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "solved": True},
        ],
        [
            {"submission_id": "s1", "platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "accepted": False},
            {"submission_id": "s2", "platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "accepted": False},
            {"submission_id": "s3", "platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "accepted": True},
        ],
    )
    result = aggregate_platforms([profile])
    row = result["topic_rows"][0]
    assert row["solved"] == 1
    assert row["attempted"] == 1
    assert row["completion_rate"] == 100.0
    assert row["accepted_submissions"] == 1
    assert row["failed_submissions"] == 2
    assert row["submission_count"] == 3
    assert row["submission_success_rate"] == 33.33


def test_submission_ids_prevent_duplicate_import_rows_but_not_repeated_problem_attempts():
    profile = _profile(
        "alice",
        [
            {"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["graphs"], "solved": True},
        ],
        [
            {"submission_id": "s1", "platform_problem_id": "p1", "tags": ["graphs"], "accepted": False},
            {"submission_id": "s1", "platform_problem_id": "p1", "tags": ["graphs"], "accepted": False},
            {"submission_id": "s2", "platform_problem_id": "p1", "tags": ["graphs"], "accepted": True},
        ],
    )
    row = aggregate_platforms([profile])["topic_rows"][0]
    assert row["submission_count"] == 2
    assert row["accepted_submissions"] == 1
    assert row["failed_submissions"] == 1
    assert row["submission_success_rate"] == 50.0


def test_submission_classification_does_not_use_eventual_problem_completion():
    topic_rows = [{
        "topic": "arrays",
        "solved": 1,
        "attempted": 1,
        "success_rate": 100.0,
        "completion_rate": 100.0,
        "accepted_submissions": 2,
        "failed_submissions": 8,
        "submission_count": 10,
        "submission_success_rate": 20.0,
    }]
    classified = classify_topics(topic_rows)
    assert classified[0]["classification"] == "Needs Improvement"


def test_missing_submission_tags_are_reported_as_incomplete():
    profile = _profile(
        "alice",
        [{"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["dp"], "solved": True}],
        [{"submission_id": "s1", "platform_problem_id": "p1", "tags": [], "accepted": True}],
        complete=True,
    )
    result = aggregate_platforms([profile])
    assert result["unresolved_topic_submissions"] == 1
    assert result["topic_submission_accuracy_complete"] is False
    assert result["topic_submission_accuracy_available"] is False


def test_model_and_normalizer_preserve_submission_activity_and_normalize_tags():
    request = AnalysisRequest.model_validate({
        "platforms": [{
            "platform_name": "Codeforces",
            "username": "alice",
            "submission_activity": [{
                "submission_id": "9001",
                "platform_problem_id": "cf-1-A",
                "canonical_id": "cf:1:A",
                "tags": ["dp", "DP", "graphs"],
                "accepted": True,
            }],
        }],
    })
    normalized = normalize_platforms(request.platforms)
    sub = normalized[0]["submission_activity"][0]
    assert sub["accepted"] is True
    assert sub["tags"] == ["Dynamic Programming", "Graphs"]


def test_full_engine_exposes_both_rates_and_uses_submission_rate_for_classification():
    first = {
        "platform_name": "Codeforces", "username": "alice", "total_solved": 1,
        "correct_submissions": 1, "failed_submissions": 9, "total_attempted": 10,
        "problem_activity": [
            {"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "solved": True},
        ],
        "submission_activity": [
            {"submission_id": f"s{i}", "platform_problem_id": "p1", "canonical_id": "p1", "tags": ["arrays"], "accepted": i == 10}
            for i in range(1, 11)
        ],
        "data_complete": True,
    }
    request = AnalysisRequest.model_validate({"display_name": "Demo", "platforms": [first]})
    result = analyze_user(request.platforms, "Demo").model_dump()
    row = result["topic_analytics"][0]
    assert row["completion_rate"] == 100.0
    assert row["success_rate"] == 100.0  # backward-compatible alias
    assert row["submission_success_rate"] == 10.0
    assert row["accepted_submissions"] == 1
    assert row["failed_submissions"] == 9
    assert row["classification"] == "Needs Improvement"
    assert "complete_topic_submission_accuracy" not in result["data_quality"]["unavailable_metrics"]


def test_submission_accuracy_can_be_calculated_without_problem_activity_records():
    profile = _profile(
        "alice",
        None,
        [
            {"submission_id": "s1", "platform_problem_id": "p1", "tags": ["math"], "accepted": True},
            {"submission_id": "s2", "platform_problem_id": "p2", "tags": ["math"], "accepted": False},
        ],
        total_solved=0,
    )
    profile["problem_activity"] = None
    result = aggregate_platforms([profile])
    math = result["topic_rows"][0]
    assert math["topic"] == "math"
    assert math["attempted"] is None
    assert math["accepted_submissions"] == 1
    assert math["failed_submissions"] == 1
    assert math["submission_success_rate"] == 50.0
    assert result["topic_submission_accuracy_available"] is True


def test_missing_problem_activity_tags_mark_unique_topic_counts_incomplete():
    profile = _profile(
        "alice",
        [{"platform_problem_id": "p1", "canonical_id": "p1", "tags": [], "solved": True}],
        [],
        complete=True,
    )
    result = aggregate_platforms([profile])
    assert result["unresolved_topic_activity_records"] == 1
    assert result["topic_analytics_complete"] is False


def test_data_quality_separates_history_from_tag_and_canonical_coverage():
    profile = {
        "platform_name": "Codeforces",
        "username": "alice",
        "total_solved": 1,
        "correct_submissions": 1,
        "failed_submissions": 1,
        "total_attempted": 2,
        "problem_activity": [
            {"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["graphs"], "solved": True},
            {"platform_problem_id": "p2", "canonical_id": None, "tags": ["math"], "solved": False},
        ],
        "submission_activity": [
            {"submission_id": "s1", "platform_problem_id": "p1", "canonical_id": "p1", "tags": ["graphs"], "accepted": True},
            {"submission_id": "s2", "platform_problem_id": "p2", "canonical_id": None, "tags": [], "accepted": False},
        ],
        "data_complete": True,
        "pagination_pages": 3,
        "duplicate_submission_records": 1,
    }
    request = AnalysisRequest.model_validate({"platforms": [profile]})
    result = analyze_user(request.platforms).model_dump()
    quality = result["data_quality"]

    assert quality["history_complete"] is True
    assert quality["topic_tag_coverage_complete"] is False
    assert quality["canonical_id_coverage_complete"] is False
    assert quality["judged_submission_count"] == 2
    assert quality["tagged_submission_count"] == 1
    assert quality["untagged_submission_count"] == 1
    assert quality["topic_tag_coverage_rate"] == 50.0
    assert quality["pagination_pages"] == 3
    assert quality["duplicate_submission_records"] == 1
    assert quality["pagination_integrity"] is False


def test_partial_history_cannot_be_reported_as_complete_unique_solved_total():
    profile = _profile(
        "alice",
        [{"platform_problem_id": "p1", "canonical_id": "p1", "tags": ["graphs"], "solved": True}],
        [{"submission_id": "s1", "platform_problem_id": "p1", "tags": ["graphs"], "accepted": True}],
        total_solved=1,
        complete=False,
    )
    result = aggregate_platforms([profile])
    assert result["total_solved"] == 1
    assert result["history_complete"] is False
    assert result["unique_solved_complete"] is False
    assert result["topic_analytics_complete"] is False
    assert result["topic_submission_accuracy_complete"] is False


def test_legacy_input_does_not_claim_zero_topic_tag_coverage():
    request = AnalysisRequest.model_validate({
        "platforms": [{
            "platform_name": "Codeforces",
            "username": "legacy",
            "total_solved": 10,
            "data_complete": True,
        }]
    })
    quality = analyze_user(request.platforms).model_dump()["data_quality"]
    assert quality["topic_tag_coverage_complete"] is None
    assert quality["canonical_id_coverage_complete"] is None
    assert quality["pagination_integrity"] is None
    assert not any("Topic-tag coverage: 0 of 0" in note for note in quality["notes"])
