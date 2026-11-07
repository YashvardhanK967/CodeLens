"""Regression tests for problems found by the hard-mode demo (B1-B16)."""
import pytest
from fastapi.testclient import TestClient

from engine.analysis_engine import analyze_user
from engine.normalizer import normalize_platform_name
from engine.topic_mapper import normalize_topic
from main import app
from models.input_models import AnalysisRequest, ProblemActivity, SolvedProblem, SubmissionActivity


def run(platforms):
    request = AnalysisRequest.model_validate({"platforms": platforms})
    return analyze_user(request.platforms).model_dump(mode="json")


def lc(**kwargs):
    return {"platform_name": "LeetCode", "username": "u", **kwargs}


def sub(sid, tags, accepted, problem="p"):
    return {"submission_id": sid, "platform_problem_id": problem, "tags": tags, "accepted": accepted}


# B1 / B2 -------------------------------------------------------------------------------------
def test_fractional_ratings_are_rounded():
    out = run([lc(current_rating=1823.45, contest_history=[
        {"timestamp": 1_700_000_000, "old_rating": 1810.2, "new_rating": 1823.6, "rating_change": 13.4}])])
    assert out["platform_comparison"][0]["current_rating"] == 1823
    assert out["contest_analytics"]["platforms"][0]["rating_history"][0]["rating"] == 1824


def test_millisecond_timestamps_are_converted():
    out = run([lc(contest_history=[{"timestamp": 1_700_000_000_000, "new_rating": 1500}])])
    assert out["contest_analytics"]["platforms"][0]["rating_history"][0]["date"] == "2023-11-14"


def test_absurd_timestamp_is_422_not_500():
    client = TestClient(app, raise_server_exceptions=False)
    body = {"platforms": [lc(contest_history=[{"timestamp": 10**16, "new_rating": 1500}])]}
    assert client.post("/api/v1/analysis", json=body).status_code == 422


# B3 / B4 / B10 -------------------------------------------------------------------------------
def test_hyphen_and_space_tags_merge():
    assert normalize_topic("divide-and-conquer") == normalize_topic("divide and conquer") == "Divide And Conquer"


@pytest.mark.parametrize("a,b", [
    ("dfs and similar", "Depth-First Search"), ("graph theory", "graphs"), ("bitmasks", "bit manipulation"),
    ("shortest paths", "shortest path"), ("hashing", "hash table"), ("sortings", "sorting"),
    ("Heap (Priority Queue)", "priority queue"),
])
def test_codeforces_and_leetcode_vocabularies_merge(a, b):
    assert normalize_topic(a) == normalize_topic(b)


def test_every_hyphenated_alias_has_a_space_twin():
    from engine.topic_mapper import _ALIASES
    for key, value in _ALIASES.items():
        assert _ALIASES.get(key.replace("-", " ").replace("_", " ")) == value, key


def test_platform_names_keep_official_capitalisation():
    assert normalize_platform_name("atcoder") == "AtCoder"
    assert normalize_platform_name("HackerRank") == "HackerRank"
    assert normalize_platform_name("MyJudge") == "MyJudge"
    assert normalize_platform_name("somejudge") == "Somejudge"


# B5 / B6 -------------------------------------------------------------------------------------
def test_total_solved_never_below_largest_profile():
    detailed = lc(total_solved=3, data_complete=True, problem_activity=[
        {"platform_problem_id": f"a{i}", "canonical_id": f"c{i}", "tags": ["math"], "solved": True} for i in range(3)])
    bare = {"platform_name": "GFG", "username": "g", "total_solved": 200, "data_complete": True}
    out = run([detailed, bare])
    assert out["overview"]["total_solved"] == 200
    assert out["overview"]["unique_solved_complete"] is False


def test_legacy_only_profile_is_merged_and_flagged():
    active = lc(total_solved=1, data_complete=True, problem_activity=[
        {"platform_problem_id": "a", "canonical_id": "c1", "tags": ["graph"], "solved": True}])
    legacy = {"platform_name": "GFG", "username": "g", "total_solved": 50, "data_complete": True,
              "topics": [{"tag_name": "graph", "solved_count": 30, "attempted_count": 40}]}
    out = run([active, legacy])
    graphs = next(r for r in out["topic_analytics"] if r["topic"] == "Graphs")
    assert (graphs["solved"], graphs["attempted"]) == (31, 41)
    assert "unique_topic_counts_include_legacy_profiles" in out["data_quality"]["unavailable_metrics"]


# B7 / B13 ------------------------------------------------------------------------------------
def test_rating_change_only_contests_still_trigger_dip():
    contests = [{"timestamp": 1_700_000_000 + i * 86400, "rating_change": c} for i, c in enumerate([-10, -20, -30, 5])]
    out = run([lc(contest_history=contests)])
    assert any("rating dip" in i["title"] for i in out["insights"])
    assert any("Review your last three" in r["action"] for r in out["recommendations"])


def test_output_does_not_depend_on_platform_order():
    def dipping(name):
        ch = [{"timestamp": 1_700_000_000 + i * 86400, "rating_change": c} for i, c in enumerate([-5, -5, -5])]
        return {"platform_name": name, "username": "u", "contest_history": ch}
    a = run([dipping("Codeforces"), dipping("CodeChef")])
    b = run([dipping("CodeChef"), dipping("Codeforces")])
    assert a["recommendations"] == b["recommendations"]
    assert [c["platform"] for c in a["contest_analytics"]["platforms"]] == [c["platform"] for c in b["contest_analytics"]["platforms"]]


# B8 / B14 / B15 / B16 -----------------------------------------------------------------------
def test_platform_totals_contradicting_records_are_flagged():
    out = run([lc(correct_submissions=500, failed_submissions=10, data_complete=True,
                  submission_activity=[sub(str(i), ["Trees"], False) for i in range(20)])])
    assert "consistent_submission_totals" in out["data_quality"]["unavailable_metrics"]


def test_matching_totals_are_not_flagged():
    out = run([lc(correct_submissions=1, failed_submissions=1, data_complete=True,
                  submission_activity=[sub("1", ["Trees"], True), sub("2", ["Trees"], False)])])
    assert "consistent_submission_totals" not in out["data_quality"]["unavailable_metrics"]


@pytest.mark.parametrize("flags", [[False, True], [True, False]])
def test_conflicting_duplicate_ids_are_order_independent(flags):
    out = run([lc(data_complete=True, submission_activity=[sub("1", ["Trees"], f) for f in flags])])
    row = out["topic_analytics"][0]
    assert (row["accepted_submissions"], row["failed_submissions"]) == (1, 0)


def test_notes_are_platform_neutral_and_not_nonsensical():
    out = run([lc(total_solved=1, data_complete=False, problemset_lookup_misses=2,
                  problem_activity=[{"platform_problem_id": "a", "canonical_id": "c", "tags": ["math"], "solved": True}],
                  submission_activity=[sub("1", [], True)])])
    notes = " ".join(out["data_quality"]["notes"])
    assert "Codeforces" not in notes
    assert "0 solved entries" not in notes


# B11 / B12 -----------------------------------------------------------------------------------
@pytest.mark.parametrize("model,extra", [(SolvedProblem, {}), (ProblemActivity, {}), (SubmissionActivity, {"accepted": True})])
def test_blank_required_problem_id_is_rejected(model, extra):
    with pytest.raises(ValueError):
        model(platform_problem_id="   ", **extra)


def test_submission_only_topic_has_unknown_solved_and_is_not_charted():
    out = run([lc(data_complete=True, submission_activity=[sub(str(i), ["Trees"], i % 2 == 0) for i in range(20)])])
    assert out["topic_analytics"][0]["solved"] is None
    assert out["charts"]["topic_distribution"] == []
