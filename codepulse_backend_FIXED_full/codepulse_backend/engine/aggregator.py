from collections import defaultdict
from typing import Any


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _clean_id(value: Any) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip().casefold()
    return cleaned or None


def _solved_records_for_profile(platform: dict[str, Any]) -> list[dict[str, Any]]:
    """Combine solved_problems with solved activity records without duplicating rows."""
    records = list(platform.get("solved_problems") or [])
    records.extend(
        problem for problem in (platform.get("problem_activity") or [])
        if problem.get("solved") is True
    )
    return records


def aggregate_platforms(platforms: list[dict[str, Any]]) -> dict[str, Any]:
    # Overall solved-problem deduplication.
    canonical_problem_ids: set[str] = set()
    canonical_profiles: dict[str, set[str]] = defaultdict(set)
    duplicate_solved = 0
    unresolved_problem_records = 0
    unlisted_solved = 0
    has_problem_details = False

    for platform in platforms:
        profile_key = f"{platform['platform']}::{platform['username']}".casefold()
        records = _solved_records_for_profile(platform)
        has_problem_details = has_problem_details or bool(records)

        seen_canonical: set[str] = set()
        seen_unresolved_ids: set[str] = set()
        canonical_local_ids: set[str] = set()
        unresolved_local_ids: set[str] = set()

        for problem in records:
            canonical_id = _clean_id(problem.get("canonical_id"))
            local_id = _clean_id(problem.get("platform_problem_id"))

            if canonical_id:
                if canonical_id in seen_canonical:
                    continue
                seen_canonical.add(canonical_id)
                if local_id:
                    canonical_local_ids.add(local_id)

                if canonical_id in canonical_profiles and profile_key not in canonical_profiles[canonical_id]:
                    duplicate_solved += 1
                canonical_problem_ids.add(canonical_id)
                canonical_profiles[canonical_id].add(profile_key)
            elif local_id:
                unresolved_local_ids.add(local_id)
            else:
                # The input model normally prevents this, but keep the aggregator safe
                # if it is called directly with unvalidated dictionaries.
                unresolved_local_ids.add(f"unidentified-{len(unresolved_local_ids)}")

        # If a duplicate row for the same local problem has one canonical ID and one
        # missing canonical ID, the canonical row is the safer identity.
        unresolved_local_ids.difference_update(canonical_local_ids)
        seen_unresolved_ids.update(unresolved_local_ids)
        unresolved_problem_records += len(seen_unresolved_ids)
        unique_listed_count = len(seen_canonical) + len(seen_unresolved_ids)
        unlisted_solved += max(0, platform["total_solved"] - unique_listed_count)

    platform_reported_solved = sum(p["total_solved"] for p in platforms)
    history_complete = all(p.get("data_complete", False) for p in platforms)
    # The verified canonical count is only a LOWER bound when some solves could not be identified.
    # A user can never have fewer unique solves than their biggest single profile reports, so the
    # headline number never drops below that (fixes 3-vs-200 when one profile has no problem records).
    largest_single_profile = max((p["total_solved"] for p in platforms), default=0)
    total_solved = (
        max(len(canonical_problem_ids), largest_single_profile)
        if has_problem_details else platform_reported_solved
    )
    unresolved_solved_count = unresolved_problem_records + unlisted_solved
    unique_solved_complete = (
        has_problem_details and unresolved_solved_count == 0 and history_complete
    )
    if not has_problem_details and platform_reported_solved == 0:
        unique_solved_complete = history_complete

    correct = sum(p["correct_submissions"] for p in platforms)
    failed = sum(p["failed_submissions"] for p in platforms)

    platform_rows = []
    activity: dict[str, int] = defaultdict(int)
    for platform in platforms:
        submissions = platform["correct_submissions"] + platform["failed_submissions"]
        contests = platform["contest_history"]
        platform_rows.append({
            "platform": platform["platform"],
            "username": platform["username"],
            "solved": platform["total_solved"],
            "current_rating": platform["current_rating"],
            "correct_submissions": platform["correct_submissions"],
            "failed_submissions": platform["failed_submissions"],
            "submission_success_rate": _rate(platform["correct_submissions"], submissions),
            "contests_participated": len(contests),
        })
        for day, count in platform["daily_activity"].items():
            activity[day] += count

    # Unique-problem topic analytics. A problem tagged with multiple topics appears
    # once in each applicable topic, but never twice in the same topic.
    has_activity_field = any(p.get("problem_activity") is not None for p in platforms)
    unresolved_topic_activity_records = 0
    problem_activity_records = 0
    missing_problem_activity_canonical_ids = 0
    missing_problem_activity_tags = 0
    all_profiles_supplied_activity = True
    topic_analytics_unique = has_activity_field
    topic_analytics_complete = False
    topic_rows: list[dict[str, Any]] = []

    if has_activity_field:
        global_problems: dict[str, dict[str, Any]] = {}
        for platform in platforms:
            records = platform.get("problem_activity")
            if records is None:
                all_profiles_supplied_activity = False
                continue

            # First collapse duplicate records inside this profile.
            profile_problems: dict[str, dict[str, Any]] = {}
            for record in records:
                problem_activity_records += 1
                canonical_id = _clean_id(record.get("canonical_id"))
                tags = {
                    str(tag).strip()
                    for tag in record.get("tags", [])
                    if str(tag).strip()
                }
                if not canonical_id:
                    missing_problem_activity_canonical_ids += 1
                if not tags:
                    missing_problem_activity_tags += 1
                if not canonical_id or not tags:
                    unresolved_topic_activity_records += 1
                if not canonical_id:
                    continue

                local = profile_problems.setdefault(
                    canonical_id,
                    {"tags": set(), "solved": False},
                )
                local["tags"].update(tags)
                local["solved"] = local["solved"] or bool(record.get("solved"))

            # Then merge profiles by canonical problem identity.
            for canonical_id, record in profile_problems.items():
                global_record = global_problems.setdefault(
                    canonical_id,
                    {"tags": set(), "solved": False},
                )
                global_record["tags"].update(record["tags"])
                global_record["solved"] = global_record["solved"] or record["solved"]

        topic_problem_ids: dict[str, set[str]] = defaultdict(set)
        topic_solved_ids: dict[str, set[str]] = defaultdict(set)
        for canonical_id, problem in global_problems.items():
            for topic in problem["tags"]:
                topic_problem_ids[topic].add(canonical_id)
                if problem["solved"]:
                    topic_solved_ids[topic].add(canonical_id)

        for topic in sorted(topic_problem_ids, key=str.lower):
            attempted = len(topic_problem_ids[topic])
            solved = len(topic_solved_ids[topic])
            completion_rate = _rate(solved, attempted)
            topic_rows.append({
                "topic": topic,
                "solved": solved,
                "attempted": attempted,
                # success_rate remains a compatibility alias for completion_rate.
                "success_rate": completion_rate,
                "completion_rate": completion_rate,
            })

        topic_analytics_complete = (
            all_profiles_supplied_activity
            and unresolved_topic_activity_records == 0
            and all(p["data_complete"] for p in platforms)
        )
    else:
        # Backward compatibility for older API clients. These aggregate counts are
        # still displayed, but they cannot be claimed as unique across profiles.
        legacy_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"solved": 0, "attempted_values": [], "attempts_complete": True}
        )
        for platform in platforms:
            for topic in platform["topics"]:
                bucket = legacy_buckets[topic["topic"]]
                bucket["solved"] += topic["solved"]
                if topic["attempted"] is None:
                    bucket["attempts_complete"] = False
                else:
                    bucket["attempted_values"].append(topic["attempted"])

        for topic, values in sorted(legacy_buckets.items(), key=lambda item: item[0].lower()):
            attempted = (
                sum(values["attempted_values"])
                if values["attempts_complete"] else None
            )
            completion_rate = _rate(values["solved"], attempted) if attempted is not None else None
            topic_rows.append({
                "topic": topic,
                "solved": values["solved"],
                "attempted": attempted,
                "success_rate": completion_rate,
                "completion_rate": completion_rate,
            })

    # Profiles that sent ONLY legacy aggregate `topics` while another profile sent problem_activity
    # must not vanish silently. Their counts are added on top (they cannot be de-duplicated), and the
    # profiles are reported so data_quality can say the topic numbers are no longer exact.
    legacy_topic_profiles_merged: list[str] = []
    if has_activity_field:
        rows_by_topic = {row["topic"]: row for row in topic_rows}
        for platform in platforms:
            if platform.get("problem_activity") is not None or not platform["topics"]:
                continue
            legacy_topic_profiles_merged.append(f"{platform['platform']}/{platform['username']}")
            for topic in platform["topics"]:
                row = rows_by_topic.get(topic["topic"])
                if row is None:
                    row = {"topic": topic["topic"], "solved": 0, "attempted": 0,
                           "success_rate": None, "completion_rate": None}
                    topic_rows.append(row)
                    rows_by_topic[topic["topic"]] = row
                row["solved"] += topic["solved"]
                if row["attempted"] is None or topic["attempted"] is None:
                    row["attempted"] = None
                else:
                    row["attempted"] += topic["attempted"]
        if legacy_topic_profiles_merged:
            for row in topic_rows:
                rate_value = _rate(row["solved"], row["attempted"]) if row["attempted"] is not None else None
                row["completion_rate"] = rate_value
                row["success_rate"] = rate_value

    # Submission accuracy is event-based and independent of problem-level data:
    # repeated attempts on one problem remain separate events. A submission tagged
    # with multiple topics contributes once to each relevant topic.
    submission_total_mismatches: list[dict[str, Any]] = []
    has_submission_activity = any(p.get("submission_activity") is not None for p in platforms)
    all_profiles_supplied_submissions = True
    unresolved_topic_submissions = 0
    judged_submission_count = 0
    tagged_submission_count = 0
    missing_submission_ids = 0
    duplicate_submission_records = 0
    pagination_pages = sum(p.get("pagination_pages", 0) for p in platforms)
    topic_submission_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"accepted": 0, "failed": 0}
    )

    if has_submission_activity:
        for platform in platforms:
            records = platform.get("submission_activity")
            if records is None:
                all_profiles_supplied_submissions = False
                continue

            # Collapse repeated submission IDs FIRST. If the same ID arrives twice with different
            # verdicts (e.g. an earlier non-final row and the final OK row) the accepted verdict wins
            # and tags are unioned, so the result no longer depends on record order.
            by_id: dict[str, dict[str, Any]] = {}
            events: list[dict[str, Any]] = []  # records with no ID cannot be de-duplicated
            observed_duplicate_ids = 0
            for submission in records:
                tags = {
                    str(tag).strip()
                    for tag in submission.get("tags", [])
                    if str(tag).strip()
                }
                accepted = submission.get("accepted") is True
                submission_id = _clean_id(submission.get("submission_id"))
                if not submission_id:
                    events.append({"tags": tags, "accepted": accepted})
                    continue
                existing = by_id.get(submission_id)
                if existing is None:
                    by_id[submission_id] = {"tags": set(tags), "accepted": accepted}
                else:
                    observed_duplicate_ids += 1
                    existing["accepted"] = existing["accepted"] or accepted
                    existing["tags"] |= tags
            observed_missing_ids = len(events)
            events.extend(by_id.values())

            observed_accepted = 0
            observed_failed = 0
            for event in events:
                judged_submission_count += 1
                if event["accepted"]:
                    observed_accepted += 1
                else:
                    observed_failed += 1
                if not event["tags"]:
                    unresolved_topic_submissions += 1
                    continue

                tagged_submission_count += 1
                bucket_key = "accepted" if event["accepted"] else "failed"
                for topic in event["tags"]:
                    topic_submission_stats[topic][bucket_key] += 1

            # Reconcile the importer's headline totals with the judged records it sent. Only meaningful
            # when the importer says it reached the end of history (otherwise records may be partial).
            if platform.get("data_complete") and (
                observed_accepted != platform["correct_submissions"]
                or observed_failed != platform["failed_submissions"]
            ):
                submission_total_mismatches.append({
                    "profile": f"{platform['platform']}/{platform['username']}",
                    "reported_accepted": platform["correct_submissions"],
                    "reported_failed": platform["failed_submissions"],
                    "record_accepted": observed_accepted,
                    "record_failed": observed_failed,
                })

            # Importer diagnostics and event-level checks can describe the same
            # records. Use the larger count to avoid reporting them twice.
            duplicate_submission_records += max(
                platform.get("duplicate_submission_records", 0), observed_duplicate_ids
            )
            missing_submission_ids += max(
                platform.get("missing_submission_ids", 0), observed_missing_ids
            )

    topic_rows_by_name = {row["topic"]: row for row in topic_rows}
    for topic in sorted(topic_submission_stats, key=str.lower):
        row = topic_rows_by_name.get(topic)
        if row is None:
            row = {
                "topic": topic,
                # No problem records for this topic, so "solved" is UNKNOWN (None), not zero.
                "solved": None,
                "attempted": None,
                "success_rate": None,
                "completion_rate": None,
            }
            topic_rows.append(row)
            topic_rows_by_name[topic] = row

    for row in topic_rows:
        stats = topic_submission_stats.get(row["topic"])
        accepted_count = stats["accepted"] if stats is not None else None
        failed_count = stats["failed"] if stats is not None else None
        submission_count = (
            accepted_count + failed_count
            if accepted_count is not None and failed_count is not None else None
        )
        row["accepted_submissions"] = accepted_count
        row["failed_submissions"] = failed_count
        row["submission_count"] = submission_count
        row["submission_success_rate"] = (
            _rate(accepted_count, submission_count)
            if submission_count is not None else None
        )

    topic_submission_accuracy_available = has_submission_activity and any(
        row["submission_count"] is not None for row in topic_rows
    )
    topic_tag_coverage_complete = (
        all_profiles_supplied_submissions
        and unresolved_topic_submissions == 0
        and history_complete
    ) if has_submission_activity else None
    topic_submission_accuracy_complete = topic_tag_coverage_complete is True
    canonical_id_coverage_complete = (
        all_profiles_supplied_activity
        and missing_problem_activity_canonical_ids == 0
        and history_complete
    ) if has_activity_field else None
    topic_analytics_complete = (
        topic_analytics_complete
        and missing_problem_activity_canonical_ids == 0
        and missing_problem_activity_tags == 0
    )

    topic_rows.sort(key=lambda row: row["topic"].lower())

    all_total_attempted_available = all(p["total_attempted"] is not None for p in platforms)
    total_attempted = (
        sum(p["total_attempted"] for p in platforms)
        if all_total_attempted_available else None
    )

    return {
        "total_solved": total_solved,
        "platform_reported_solved": platform_reported_solved,
        "duplicate_solved_across_platforms": duplicate_solved,  # retained for API compatibility
        "duplicate_solved_across_profiles": duplicate_solved,
        "unresolved_solved_count": unresolved_solved_count,
        "unique_solved_complete": unique_solved_complete,
        "has_problem_details": has_problem_details,
        "correct_submissions": correct,
        "failed_submissions": failed,
        "success_rate": _rate(correct, correct + failed),
        "total_attempted": total_attempted,
        "topic_analytics_unique": topic_analytics_unique,
        "topic_analytics_complete": topic_analytics_complete,
        "topic_submission_accuracy_available": topic_submission_accuracy_available,
        "topic_submission_accuracy_complete": topic_submission_accuracy_complete,
        "history_complete": history_complete,
        "topic_tag_coverage_complete": topic_tag_coverage_complete,
        "canonical_id_coverage_complete": canonical_id_coverage_complete,
        "judged_submission_count": judged_submission_count,
        "tagged_submission_count": tagged_submission_count,
        "untagged_submission_count": unresolved_topic_submissions,
        "topic_tag_coverage_rate": _rate(tagged_submission_count, judged_submission_count),
        "missing_submission_ids": missing_submission_ids,
        "pagination_pages": pagination_pages,
        "duplicate_submission_records": duplicate_submission_records,
        "pagination_integrity": (
            history_complete and duplicate_submission_records == 0 and missing_submission_ids == 0
        ) if any(p.get("pagination_pages", 0) > 0 for p in platforms) else None,
        "profiles_with_complete_history": sum(1 for p in platforms if p.get("data_complete", False)),
        "profiles_total": len(platforms),
        "problem_activity_records": problem_activity_records,
        "untagged_problem_activity_records": missing_problem_activity_tags,
        "missing_problem_activity_canonical_ids": missing_problem_activity_canonical_ids,
        "missing_problem_activity_tags": missing_problem_activity_tags,
        "problemset_lookup_misses": sum(p.get("problemset_lookup_misses", 0) for p in platforms),
        "problemset_entries_without_tags": sum(p.get("problemset_entries_without_tags", 0) for p in platforms),
        "unresolved_topic_submissions": unresolved_topic_submissions,
        "submission_total_mismatches": submission_total_mismatches,
        "legacy_topic_profiles_merged": legacy_topic_profiles_merged,
        "unresolved_topic_activity_records": unresolved_topic_activity_records,
        "platform_rows": sorted(platform_rows, key=lambda x: (x["platform"].lower(), x["username"].lower())),
        "topic_rows": topic_rows,
        "daily_activity": [
            {"date": day, "activity_count": activity[day]}
            for day in sorted(activity)
        ],
    }
