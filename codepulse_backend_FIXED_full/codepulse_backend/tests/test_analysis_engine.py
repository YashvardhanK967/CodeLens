import json
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from models.input_models import AnalysisRequest
from engine.analysis_engine import analyze_user

ROOT = Path(__file__).resolve().parents[1]


def load_sample():
    return json.loads((ROOT / "sample_data" / "sample_request.json").read_text(encoding="utf-8"))


def test_engine_combines_topic_aliases_and_platform_counts():
    request = AnalysisRequest.model_validate(load_sample())
    result = analyze_user(request.platforms, request.display_name)
    assert result.overview.total_solved == 550
    dp = next(topic for topic in result.topic_analytics if topic.topic == "Dynamic Programming")
    assert dp.solved == 65
    assert dp.attempted == 145


def test_ratings_stay_separate_by_platform():
    request = AnalysisRequest.model_validate(load_sample())
    result = analyze_user(request.platforms)
    assert len(result.contest_analytics.platforms) == 3
    assert len(result.charts.contest_rating_by_platform) == 2
    assert all(series.platform in {"LeetCode", "Codeforces"} for series in result.charts.contest_rating_by_platform)


def test_data_quality_discloses_unique_problem_limitation():
    request = AnalysisRequest.model_validate(load_sample())
    result = analyze_user(request.platforms)
    assert any("unique_solved" in metric for metric in result.data_quality.unavailable_metrics)
    assert result.data_quality.partial_data is True


def test_fastapi_endpoint_returns_dashboard_json():
    client = TestClient(app)
    response = client.post("/api/v1/analysis", json=load_sample())
    assert response.status_code == 200
    body = response.json()
    assert body["overview"]["total_solved"] == 550
    assert "charts" in body
    assert "recommendations" in body


def test_invalid_daily_activity_date_is_rejected():
    body = load_sample()
    body["platforms"][0]["daily_activity"] = {"01-11-2026": 3}
    client = TestClient(app)
    response = client.post("/api/v1/analysis", json=body)
    assert response.status_code == 422
