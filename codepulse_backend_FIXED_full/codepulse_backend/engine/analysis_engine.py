from typing import Optional

from models.input_models import PlatformData
from models.output_models import DashboardResponse
from .normalizer import normalize_platforms
from .aggregator import aggregate_platforms
from .contest_analyzer import analyze_contests, find_rating_dips
from .weakness_detector import classify_topics
from .performance_analyzer import build_chart_data
from .recommendation_engine import generate_recommendations


def _build_insights(
    aggregated: dict,
    topic_rows: list[dict],
    contest_data: dict,
    has_activity: bool,
) -> list[dict]:
    if aggregated["unique_solved_complete"]:
        overview_description = (
            f"CodePulse identified {aggregated['total_solved']} distinct solved problems "
            f"across {len(aggregated['platform_rows'])} connected profiles using canonical IDs."
        )
    elif aggregated.get("has_problem_details"):
        overview_description = (
            f"CodePulse verified {aggregated['total_solved']} distinct solved problems from the available "
            f"problem records. Platforms reported {aggregated['platform_reported_solved']} solved entries; "
            "some records could not be matched safely, so the unique count is incomplete."
        )
    else:
        overview_description = (
            f"Connected platforms reported {aggregated['platform_reported_solved']} solved entries in total. "
            "Problem-level records were not supplied, so cross-profile duplicates cannot yet be identified; "
            "the displayed total is not a verified unique-problem count."
        )

    insights: list[dict] = [{
        "type": "overview",
        "title": "Combined coding profile analysed",
        "description": overview_description,
    }]

    strong = [row for row in topic_rows if row["classification"] == "Strong"]
    weak = [row for row in topic_rows if row["classification"] == "Needs Improvement"]

    if strong:
        best = max(strong, key=lambda row: (row["submission_success_rate"], row["submission_count"]))
        insights.append({
            "type": "strength",
            "title": f"Strong submission accuracy in {best['topic']}",
            "description": (
                f"{best['accepted_submissions']} of {best['submission_count']} judged submissions were accepted "
                f"({best['submission_success_rate']}%)."
            ),
        })
    if weak:
        worst = min(weak, key=lambda row: (row["submission_success_rate"], -row["submission_count"]))
        insights.append({
            "type": "weakness",
            "title": f"{worst['topic']} may need more practice",
            "description": (
                f"{worst['accepted_submissions']} of {worst['submission_count']} judged submissions were accepted "
                f"({worst['submission_success_rate']}%). This is a practice signal, not a definitive skill assessment."
            ),
        })

    for dip in find_rating_dips(contest_data):
        insights.append({
            "type": "contest",
            "title": f"Recent {dip['platform']} rating dip",
            "description": (
                f"The last three recorded rating changes sum to {dip['recent_sum']}. "
                "Review those contests for recurring mistakes."
            ),
        })

    if not has_activity:
        insights.append({
            "type": "data",
            "title": "Daily activity data is unavailable",
            "description": "Daily activity was not supplied, so practice consistency trends cannot be calculated.",
        })
    return insights


def _build_data_quality(
    platforms: list[PlatformData],
    aggregated: dict,
    topic_rows: list[dict],
    has_activity: bool,
) -> dict:
    unavailable: list[str] = []
    notes: list[str] = [
        "Cross-profile deduplication uses canonical_id; titles and platform-specific IDs are not treated as globally unique.",
        "The importer must assign the same canonical_id to the same underlying problem on every platform.",
        "Ratings are kept separate by platform because rating scales are not directly comparable.",
        "Topic counts can overlap because one problem may have multiple topic tags.",
        "Topic completion rate is based on unique problems eventually solved; topic submission accuracy is based on judged submission events.",
        "A submission tagged with multiple topics contributes once to each of those topic-level submission totals.",
    ]

    if not aggregated["unique_solved_complete"]:
        unavailable.append("exact_cross_platform_unique_solved")
        if not aggregated.get("has_problem_details"):
            notes.append(
                f"The platforms reported {aggregated['platform_reported_solved']} solved entries, but no "
                "problem-level solved records were supplied. The displayed total preserves the reported "
                "sum for backward compatibility and is not an exact unique count."
            )
        elif aggregated["unresolved_solved_count"] > 0:
            notes.append(
                f"{aggregated['unresolved_solved_count']} solved entries lack a reliable canonical identity "
                "or detailed record. The unique solved count includes only verified canonical IDs and is a lower bound."
            )
        else:
            notes.append(
                "Every listed solved problem has a canonical ID, but at least one profile did not confirm that its "
                "full history was fetched, so the unique solved count may be missing older solves."
            )

    if not aggregated.get("topic_analytics_unique"):
        unavailable.append("exact_unique_topic_analytics")
        notes.append(
            "Problem-level topic activity was not supplied. Legacy aggregate topic totals are displayed, "
            "but they are added across profiles and may count the same problem more than once."
        )
    elif not aggregated.get("topic_analytics_complete"):
        unavailable.append("complete_unique_topic_analytics")
        missing_ids = aggregated.get("missing_problem_activity_canonical_ids", 0)
        missing_tags = aggregated.get("missing_problem_activity_tags", 0)
        notes.append(
            "Unique topic counts are calculated from the supplied problem records, but their coverage is incomplete. "
            f"{missing_ids} problem records lack canonical IDs and {missing_tags} problem records lack topic tags. "
            "Treat the displayed unique topic counts as a lower bound."
        )

    if not aggregated.get("topic_submission_accuracy_available"):
        unavailable.append("topic_submission_accuracy")
        has_submission_records = any(platform.submission_activity is not None for platform in platforms)
        if has_submission_records:
            notes.append(
                "Submission records were supplied, but none contained usable topic tags. "
                "Topic-specific submission accuracy cannot be calculated until submissions can be mapped to topics."
            )
        else:
            notes.append(
                "Submission-level topic tags and judged verdicts were not supplied, "
                "so topic-specific submission accuracy cannot be calculated."
            )
    elif not aggregated.get("topic_submission_accuracy_complete"):
        unavailable.append("complete_topic_submission_accuracy")
        notes.append(
            "Topic submission accuracy is calculated from the judged, tagged submissions provided, but coverage is partial. "
            f"{aggregated.get('untagged_submission_count', 0)} of "
            f"{aggregated.get('judged_submission_count', 0)} judged submissions could not be assigned to a topic."
        )

    if any(p.total_attempted is None for p in platforms):
        unavailable.append("combined_total_attempted")
    if not topic_rows or any(row["attempted"] is None for row in topic_rows):
        unavailable.append("topic_success_rate_for_all_topics")
    if not has_activity:
        unavailable.append("daily_activity_trend")
    if not any(p.contest_history for p in platforms):
        unavailable.append("contest_rating_trend")

    if not aggregated.get("history_complete"):
        notes.append(
            "Submission history is incomplete: at least one profile did not confirm that all available pages were fetched."
        )
    else:
        notes.append(
            "Submission-history pagination reached the end of the available history for every supplied profile. "
            "This does not guarantee that the platform itself exposes every historical event."
        )

    if aggregated.get("topic_tag_coverage_complete") is False:
        notes.append(
            f"Topic-tag coverage: {aggregated.get('tagged_submission_count', 0)} of "
            f"{aggregated.get('judged_submission_count', 0)} judged submissions were assigned to at least one topic "
            f"({aggregated.get('topic_tag_coverage_rate')}%). "
            f"{aggregated.get('untagged_submission_count', 0)} submissions had no usable topic tags. "
            f"Of those, {aggregated.get('problemset_lookup_misses', 0)} submissions referenced problems "
            "missing from the importer's problem/tag lookup, and "
            f"{aggregated.get('problemset_entries_without_tags', 0)} matched lookup entries had no tags."
        )

    if aggregated.get("canonical_id_coverage_complete") is False:
        notes.append(
            f"Canonical-ID coverage is incomplete: {aggregated.get('missing_problem_activity_canonical_ids', 0)} "
            "problem-activity records lack canonical IDs, so cross-profile unique topic counts may be understated."
        )

    if aggregated.get("duplicate_submission_records", 0):
        notes.append(
            f"The importer detected and excluded {aggregated['duplicate_submission_records']} repeated submission records."
        )
    if aggregated.get("missing_submission_ids", 0):
        notes.append(
            f"{aggregated['missing_submission_ids']} judged submission records had no submission ID; "
            "duplicate detection could not be guaranteed for those records."
        )

    legacy_merged = aggregated.get("legacy_topic_profiles_merged") or []
    if legacy_merged:
        unavailable.append("unique_topic_counts_include_legacy_profiles")
        notes.append(
            f"{', '.join(legacy_merged)} sent only aggregate topic totals (no problem-level records). Their counts were "
            "added to the unique counts from the other profiles and may double-count problems solved on several platforms."
        )

    for mismatch in aggregated.get("submission_total_mismatches") or []:
        if "consistent_submission_totals" not in unavailable:
            unavailable.append("consistent_submission_totals")
        notes.append(
            f"{mismatch['profile']} reported {mismatch['reported_accepted']} accepted / {mismatch['reported_failed']} failed "
            f"submissions, but its submission records contain {mismatch['record_accepted']} / {mismatch['record_failed']}. "
            "The overall success rate uses the reported totals; topic accuracy uses the records."
        )

    partial = bool(unavailable) or not aggregated.get("history_complete")
    return {
        "partial_data": partial,
        "history_complete": aggregated.get("history_complete"),
        "topic_tag_coverage_complete": aggregated.get("topic_tag_coverage_complete"),
        "canonical_id_coverage_complete": aggregated.get("canonical_id_coverage_complete"),
        "judged_submission_count": aggregated.get("judged_submission_count"),
        "tagged_submission_count": aggregated.get("tagged_submission_count"),
        "untagged_submission_count": aggregated.get("untagged_submission_count"),
        "topic_tag_coverage_rate": aggregated.get("topic_tag_coverage_rate"),
        "pagination_pages": aggregated.get("pagination_pages"),
        "duplicate_submission_records": aggregated.get("duplicate_submission_records"),
        "missing_submission_ids": aggregated.get("missing_submission_ids"),
        "pagination_integrity": aggregated.get("pagination_integrity"),
        "profiles_with_complete_history": aggregated.get("profiles_with_complete_history"),
        "profiles_total": aggregated.get("profiles_total"),
        "problem_activity_records": aggregated.get("problem_activity_records"),
        "untagged_problem_activity_records": aggregated.get("untagged_problem_activity_records"),
        "missing_problem_activity_canonical_ids": aggregated.get("missing_problem_activity_canonical_ids"),
        "missing_problem_activity_tags": aggregated.get("missing_problem_activity_tags"),
        "problemset_lookup_misses": aggregated.get("problemset_lookup_misses"),
        "problemset_entries_without_tags": aggregated.get("problemset_entries_without_tags"),
        "unavailable_metrics": unavailable,
        "notes": notes,
    }


def analyze_user(platforms: list[PlatformData], display_name: Optional[str] = None) -> DashboardResponse:
    """Validate platform data, calculate analytics, and return a dashboard response."""
    if not platforms:
        raise ValueError("At least one platform profile is required")

    # Sort once so contest lists, chart series and recommendations never depend on the order the
    # importer happened to send the profiles in (platform_comparison was already sorted).
    normalized = sorted(
        normalize_platforms(platforms),
        key=lambda p: (p["platform"].casefold(), p["username"].casefold()),
    )
    aggregated = aggregate_platforms(normalized)
    contest_data = analyze_contests(normalized)
    topic_rows = classify_topics(aggregated["topic_rows"])
    has_activity = any(bool(platform["daily_activity"]) for platform in normalized)

    charts = build_chart_data(aggregated, contest_data)
    recommendations = generate_recommendations(topic_rows, contest_data, has_activity)
    insights = _build_insights(aggregated, topic_rows, contest_data, has_activity)
    data_quality = _build_data_quality(platforms, aggregated, topic_rows, has_activity)

    active_days = len({
        point["date"]
        for point in aggregated["daily_activity"]
        if point["activity_count"] > 0
    })

    return DashboardResponse(
        user_summary={
            "username": display_name,
            "platforms_connected": len(platforms),
        },
        overview={
            "total_solved": aggregated["total_solved"],
            "platform_reported_solved": aggregated["platform_reported_solved"],
            "duplicate_solved_across_platforms": aggregated["duplicate_solved_across_platforms"],
            "unresolved_solved_count": aggregated["unresolved_solved_count"],
            "unique_solved_complete": aggregated["unique_solved_complete"],
            "correct_submissions": aggregated["correct_submissions"],
            "failed_submissions": aggregated["failed_submissions"],
            "total_attempted": aggregated["total_attempted"],
            "success_rate": aggregated["success_rate"],
            "total_contests": contest_data["total_contests"],
            "active_days": active_days if has_activity else None,
        },
        platform_comparison=aggregated["platform_rows"],
        topic_analytics=topic_rows,
        contest_analytics=contest_data,
        charts=charts,
        insights=insights,
        recommendations=recommendations,
        data_quality=data_quality,
    )
