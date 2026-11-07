from engine.recommendation_engine import generate_recommendations


def _topic(name, rate, count, classification):
    return {
        "topic": name,
        "submission_success_rate": rate,
        "submission_count": count,
        "accepted_submissions": round(rate * count / 100),
        "failed_submissions": count - round(rate * count / 100),
        "classification": classification,
    }


def test_recommendations_rank_worst_topics_before_alphabetical_order():
    rows = [
        _topic("Arrays", 35.0, 80, "Needs Improvement"),
        _topic("Graphs", 20.0, 25, "Needs Improvement"),
        _topic("Trees", 10.0, 18, "Needs Improvement"),
        _topic("Binary Search", 55.0, 100, "Developing"),
        _topic("Greedy", 48.0, 20, "Developing"),
    ]
    result = generate_recommendations(rows, {"platforms": []}, has_activity=True)
    assert [item["topic"] for item in result] == [
        "Trees", "Graphs", "Arrays", "Greedy", "Binary Search"
    ]


def test_equal_accuracy_prefers_larger_sample_size():
    rows = [
        _topic("Small Sample", 25.0, 12, "Needs Improvement"),
        _topic("Large Sample", 25.0, 90, "Needs Improvement"),
    ]
    result = generate_recommendations(rows, {"platforms": []}, has_activity=True)
    assert [item["topic"] for item in result] == ["Large Sample", "Small Sample"]
