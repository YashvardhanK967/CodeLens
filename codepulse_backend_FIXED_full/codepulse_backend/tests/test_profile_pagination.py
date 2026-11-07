import test_real_profiles


def test_fetches_multiple_pages_until_short_page(monkeypatch):
    calls = []

    pages = [
        [{"id": 1}, {"id": 2}, {"id": 3}],
        [{"id": 4}, {"id": 5}, {"id": 6}],
        [{"id": 7}],
    ]

    def fake_api_get(endpoint, params):
        calls.append(params.copy())
        return pages[len(calls) - 1]

    monkeypatch.setattr(test_real_profiles, "api_get", fake_api_get)

    submissions, complete, metadata = (
        test_real_profiles.fetch_all_submissions_detailed(
            "tourist",
            page_size=3,
            max_submissions=None,
        )
    )

    assert len(submissions) == 7
    assert complete is True
    assert metadata["pages_fetched"] == 3
    assert metadata["raw_submission_count"] == 7
    assert metadata["unique_submission_count"] == 7
    assert metadata["terminated_by_short_page"] is True

    assert [call["from"] for call in calls] == [1, 4, 7]


def test_stops_after_first_short_page(monkeypatch):
    calls = []

    def fake_api_get(endpoint, params):
        calls.append(params.copy())
        return [{"id": 1}, {"id": 2}]

    monkeypatch.setattr(test_real_profiles, "api_get", fake_api_get)

    submissions, complete, metadata = (
        test_real_profiles.fetch_all_submissions_detailed(
            "tourist",
            page_size=5,
            max_submissions=None,
        )
    )

    assert len(submissions) == 2
    assert complete is True
    assert metadata["pages_fetched"] == 1
    assert metadata["terminated_by_short_page"] is True
    assert len(calls) == 1


def test_duplicate_ids_are_removed_but_offset_uses_raw_page_length(
    monkeypatch,
):
    calls = []

    pages = [
        [{"id": 1}, {"id": 2}, {"id": 3}],
        [{"id": 3}, {"id": 4}, {"id": 5}],
        [{"id": 6}],
    ]

    def fake_api_get(endpoint, params):
        calls.append(params.copy())
        return pages[len(calls) - 1]

    monkeypatch.setattr(test_real_profiles, "api_get", fake_api_get)

    submissions, complete, metadata = (
        test_real_profiles.fetch_all_submissions_detailed(
            "tourist",
            page_size=3,
            max_submissions=None,
        )
    )

    ids = [item["id"] for item in submissions]

    assert ids == [1, 2, 3, 4, 5, 6]
    assert len(ids) == 6
    assert complete is True

    assert metadata["raw_submission_count"] == 7
    assert metadata["unique_submission_count"] == 6
    assert metadata["duplicate_submission_records"] == 1

    # The second page starts at 4, not 3.
    # The duplicate still occupied a position in the API response.
    assert [call["from"] for call in calls] == [1, 4, 7]


def test_cap_marks_history_as_incomplete(monkeypatch):
    calls = []

    def fake_api_get(endpoint, params):
        calls.append(params.copy())
        return [{"id": 1}, {"id": 2}, {"id": 3}]

    monkeypatch.setattr(test_real_profiles, "api_get", fake_api_get)

    submissions, complete, metadata = (
        test_real_profiles.fetch_all_submissions_detailed(
            "tourist",
            page_size=3,
            max_submissions=3,
        )
    )

    assert len(submissions) == 3
    assert complete is False
    assert metadata["cap_reached"] is True
    assert metadata["terminated_by_short_page"] is False
    assert metadata["raw_submission_count"] == 3
    assert len(calls) == 1


def test_rejects_invalid_page_size():
    try:
        test_real_profiles.fetch_all_submissions_detailed(
            "tourist",
            page_size=0,
            max_submissions=None,
        )
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "page_size" in str(error)