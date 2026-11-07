"""Fetch two public Codeforces demo profiles and test the CodePulse engine.

The importer fetches submission history in pages. By default it continues until
Codeforces returns a short page. Set CODEFORCES_MAX_SUBMISSIONS to a positive
integer for a quicker, intentionally partial sample run.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

from models.input_models import AnalysisRequest
from engine.analysis_engine import analyze_user

API_BASE = "https://codeforces.com/api/"
DEMO_HANDLES = ["tourist", "Petr"]
PAGE_SIZE = 1000
# Set CODEFORCES_MAX_SUBMISSIONS to a positive integer for a quicker sample run.
# Leave it unset (default) to fetch the complete available submission history.
MAX_SUBMISSIONS = int(os.getenv("CODEFORCES_MAX_SUBMISSIONS", "0")) or None
REQUEST_DELAY_SECONDS = 2.2
MAX_API_RETRIES = 3


def api_get(endpoint: str, params: dict) -> dict | list:
    """Call one Codeforces API endpoint with basic transient-error retries."""
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}{endpoint}?{query}" if query else f"{API_BASE}{endpoint}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CodePulse-demo-profile-test/1.0"},
    )

    for attempt in range(MAX_API_RETRIES + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt >= MAX_API_RETRIES:
                raise
            retry_after = exc.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else 2 ** (attempt + 1)
            time.sleep(min(wait_seconds, 30))
            continue
        except urllib.error.URLError:
            if attempt >= MAX_API_RETRIES:
                raise
            time.sleep(min(2 ** (attempt + 1), 30))
            continue

        if payload.get("status") == "OK":
            return payload["result"]

        comment = payload.get("comment", f"Codeforces API failed: {endpoint}")
        retryable = "limit" in comment.lower() or "temporar" in comment.lower()
        if not retryable or attempt >= MAX_API_RETRIES:
            raise RuntimeError(comment)
        time.sleep(min(2 ** (attempt + 1), 30))

    raise RuntimeError(f"Codeforces API request failed after retries: {endpoint}")


def fetch_all_submissions_detailed(
    handle: str,
    page_size: int = PAGE_SIZE,
    max_submissions: int | None = MAX_SUBMISSIONS,
) -> tuple[list[dict], bool, dict]:
    """Fetch all available pages and return records plus pagination diagnostics.

    Offsets advance by the raw page length returned by Codeforces. Repeated
    submission IDs are excluded from the result, but still advance the offset
    because they occupied positions in the API response.
    """
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    if max_submissions is not None and max_submissions < 1:
        raise ValueError("max_submissions must be positive or None")

    unique_submissions: list[dict] = []
    seen_ids: set[str] = set()
    offset = 1
    page_count = 0
    raw_submission_count = 0
    duplicate_submission_records = 0
    missing_submission_ids = 0
    terminated_by_short_page = False
    cap_reached = False

    while True:
        remaining = None if max_submissions is None else max_submissions - raw_submission_count
        if remaining is not None and remaining <= 0:
            cap_reached = True
            break

        count = page_size if remaining is None else min(page_size, remaining)
        page = api_get("user.status", {"handle": handle, "from": offset, "count": count})
        if len(page) > count:
            raise RuntimeError(
                f"Codeforces returned {len(page)} records for a requested page size of {count}."
            )

        page_count += 1
        raw_submission_count += len(page)
        for submission in page:
            submission_id = submission.get("id")
            if submission_id is None:
                missing_submission_ids += 1
                unique_submissions.append(submission)
                continue

            normalized_id = str(submission_id).strip()
            if normalized_id in seen_ids:
                duplicate_submission_records += 1
                continue
            seen_ids.add(normalized_id)
            unique_submissions.append(submission)

        # The next API offset is based on the number of records returned, not
        # the number retained after duplicate filtering.
        offset += len(page)

        if len(page) < count:
            terminated_by_short_page = True
            break

        if max_submissions is not None and raw_submission_count >= max_submissions:
            cap_reached = True
            break

    history_complete = terminated_by_short_page and not cap_reached
    metadata = {
        "pages_fetched": page_count,
        "raw_submission_count": raw_submission_count,
        "unique_submission_count": len(unique_submissions),
        "duplicate_submission_records": duplicate_submission_records,
        "missing_submission_ids": missing_submission_ids,
        "terminated_by_short_page": terminated_by_short_page,
        "cap_reached": cap_reached,
    }
    return unique_submissions, history_complete, metadata


def fetch_all_submissions(
    handle: str,
    page_size: int = PAGE_SIZE,
    max_submissions: int | None = MAX_SUBMISSIONS,
) -> tuple[list[dict], bool]:
    """Backward-compatible wrapper returning (submissions, history_complete)."""
    submissions, history_complete, _ = fetch_all_submissions_detailed(
        handle, page_size=page_size, max_submissions=max_submissions
    )
    return submissions, history_complete


def fetch_profile(handle: str, problem_tags: dict) -> dict:
    info = api_get("user.info", {"handles": handle})[0]
    ratings = api_get("user.rating", {"handle": handle})
    submissions, history_complete, pagination = fetch_all_submissions_detailed(handle)
    print(
        f"  Retrieved {len(submissions)} unique submissions for {handle} "
        f"across {pagination['pages_fetched']} pages "
        f"({pagination['duplicate_submission_records']} repeated IDs removed)."
    )

    solved: dict[tuple[int, str], dict] = {}
    attempted: dict[tuple[int, str], dict] = {}
    accepted_submissions = 0
    failed_submissions = 0
    submission_activity = []
    problemset_lookup_misses = 0
    problemset_entries_without_tags = 0
    daily_activity: dict[str, int] = defaultdict(int)

    for submission in submissions:
        problem = submission.get("problem") or {}
        contest_id = problem.get("contestId")
        index = problem.get("index")
        if contest_id is None or index is None:
            continue

        key = (contest_id, index)
        attempted[key] = problem

        timestamp = submission.get("creationTimeSeconds")
        if timestamp:
            day = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
            daily_activity[day] += 1

        verdict = submission.get("verdict")
        # Ignore submissions that have not received a final verdict yet.
        if verdict is None or verdict == "TESTING":
            continue

        if verdict == "OK":
            accepted_submissions += 1
            solved[key] = problem
        else:
            failed_submissions += 1

        source_problem = problem_tags.get(key, problem)
        source_tags = source_problem.get("tags", [])
        if not source_tags:
            if key not in problem_tags:
                problemset_lookup_misses += 1
            else:
                problemset_entries_without_tags += 1
        submission_activity.append({
            "submission_id": str(submission.get("id")) if submission.get("id") is not None else None,
            "platform_problem_id": f"cf-{contest_id}-{index}",
            "canonical_id": f"cf:{contest_id}:{index}",
            "tags": source_tags,
            "accepted": verdict == "OK",
        })

    topic_solved: dict[str, set[tuple[int, str]]] = defaultdict(set)
    topic_attempted: dict[str, set[tuple[int, str]]] = defaultdict(set)

    for key, submitted_problem in attempted.items():
        source_problem = problem_tags.get(key, submitted_problem)
        for tag in source_problem.get("tags", []):
            topic_attempted[tag].add(key)

    for key, submitted_problem in solved.items():
        source_problem = problem_tags.get(key, submitted_problem)
        for tag in source_problem.get("tags", []):
            topic_solved[tag].add(key)

    topics = []
    for tag in sorted(set(topic_solved) | set(topic_attempted), key=str.lower):
        topics.append({
            "tag_name": tag,
            "solved_count": len(topic_solved[tag]),
            "attempted_count": len(topic_attempted[tag]),
        })

    contest_history = [
        {
            "contest_id": str(item["contestId"]),
            "contest_name": item["contestName"],
            "timestamp": item["ratingUpdateTimeSeconds"],
            "rating_change": item["newRating"] - item["oldRating"],
            "old_rating": item["oldRating"],
            "new_rating": item["newRating"],
            "rank": item["rank"],
        }
        for item in ratings
    ]

    # Codeforces' contestId + index is stable for identifying Codeforces problems.
    # It does NOT automatically match the same problem on LeetCode/GFG/etc.; a
    # cross-platform importer must map the same underlying problem to one shared ID.
    def canonical_codeforces_id(key: tuple[int, str]) -> str:
        contest_id, index = key
        return f"cf:{contest_id}:{index}"

    solved_problems = []
    for (contest_id, index), problem in solved.items():
        solved_problems.append({
            "platform_problem_id": f"cf-{contest_id}-{index}",
            "canonical_id": canonical_codeforces_id((contest_id, index)),
            "title": problem.get("name", f"{contest_id}-{index}"),
        })

    problem_activity = []
    for key, submitted_problem in attempted.items():
        contest_id, index = key
        source_problem = problem_tags.get(key, submitted_problem)
        problem_activity.append({
            "platform_problem_id": f"cf-{contest_id}-{index}",
            "canonical_id": canonical_codeforces_id(key),
            "title": source_problem.get("name", f"{contest_id}-{index}"),
            "tags": source_problem.get("tags", []),
            "solved": key in solved,
        })

    return {
        "platform_name": "Codeforces",
        "username": handle,
        "current_rating": info.get("rating"),
        "total_solved": len(solved),
        "correct_submissions": accepted_submissions,
        "failed_submissions": failed_submissions,
        # This field is a submission count, not a unique-problem count.
        "total_attempted": accepted_submissions + failed_submissions,
        "topics": topics,
        "contest_history": contest_history,
        "daily_activity": dict(daily_activity),
        "solved_problems": solved_problems,
        "problem_activity": problem_activity,
        "submission_activity": submission_activity,
        "data_complete": history_complete,
        "pagination_pages": pagination["pages_fetched"],
        "duplicate_submission_records": pagination["duplicate_submission_records"],
        "missing_submission_ids": pagination["missing_submission_ids"],
        "problemset_lookup_misses": problemset_lookup_misses,
        "problemset_entries_without_tags": problemset_entries_without_tags,
    }


def main() -> None:
    if MAX_SUBMISSIONS is None:
        print("Submission history mode: complete available history (paginated)")
    else:
        print(f"Submission history mode: capped sample ({MAX_SUBMISSIONS} submissions/profile)")

    print("Fetching Codeforces problem tags...")
    problemset = api_get("problemset.problems", {})
    problem_tags = {
        (problem["contestId"], problem["index"]): problem
        for problem in problemset["problems"]
        if "contestId" in problem and "index" in problem
    }

    platforms = []
    for handle in DEMO_HANDLES:
        print(f"Fetching {handle}...")
        platforms.append(fetch_profile(handle, problem_tags))

    request = AnalysisRequest.model_validate({
        "display_name": "CodePulse Demo",
        "platforms": platforms,
    })
    result = analyze_user(request.platforms, request.display_name)
    output = result.model_dump(mode="json")

    print("\n========== CODEPULSE RESULTS ==========\n")
    overview = output["overview"]
    print("OVERVIEW")
    print(f"Unique solved (known canonical IDs): {overview['total_solved']}")
    print(f"Profiles connected: {output['user_summary']['platforms_connected']}")
    print(f"Submission success rate: {overview['success_rate']}%")
    print(f"Duplicate solved across profiles: {overview['duplicate_solved_across_platforms']}")

    print("\nTOP 10 TOPICS (unique problems + submission accuracy)")
    for row in sorted(
        output["topic_analytics"],
        key=lambda item: (item["attempted"] or 0, item["topic"].lower()),
        reverse=True,
    )[:10]:
        print(
            f"{row['topic']}: unique_solved={row['solved']}, unique_attempted={row['attempted']}, "
            f"completion_rate={row['completion_rate']}%, accepted_submissions={row['accepted_submissions']}, "
            f"failed_submissions={row['failed_submissions']}, "
            f"submission_accuracy={row['submission_success_rate']}%, "
            f"classification={row['classification']}"
        )

    print("\nDATA QUALITY")
    quality = output["data_quality"]
    print(f"Partial data: {quality['partial_data']}")
    print(f"History complete: {quality['history_complete']}")
    print(
        f"Topic-tag coverage: {quality['tagged_submission_count']}/"
        f"{quality['judged_submission_count']} ({quality['topic_tag_coverage_rate']}%)"
    )
    print(f"Canonical-ID coverage complete: {quality['canonical_id_coverage_complete']}")
    print(f"Pagination pages: {quality['pagination_pages']}")
    print(f"Repeated submission records removed: {quality['duplicate_submission_records']}")
    print(f"Submission pagination integrity: {quality['pagination_integrity']}")
    print(
        "Untagged submission causes: "
        f"problemset lookup misses={quality['problemset_lookup_misses']}, "
        f"matched entries without tags={quality['problemset_entries_without_tags']}"
    )
    for note in quality["notes"]:
        print(f"- {note}")

    # Sanity checks for the returned unique-topic metrics.
    violations = [
        row for row in output["topic_analytics"]
        if row["attempted"] is not None and row["solved"] > row["attempted"]
    ]
    if violations:
        raise AssertionError(f"Topic validation failed: {violations[:3]}")
    print("\nTOPIC VALIDATION: PASSED — solved never exceeds attempted.")

    submission_violations = [
        row for row in output["topic_analytics"]
        if row["submission_count"] is not None
        and row["accepted_submissions"] + row["failed_submissions"] != row["submission_count"]
    ]
    if submission_violations:
        raise AssertionError(f"Submission validation failed: {submission_violations[:3]}")
    print("SUBMISSION VALIDATION: PASSED — accepted + failed equals judged submissions.")


if __name__ == "__main__":
    main()
