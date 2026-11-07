from typing import Optional, Literal
from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    username: Optional[str] = None
    platforms_connected: int


class Overview(BaseModel):
    total_solved: int
    platform_reported_solved: int
    duplicate_solved_across_platforms: int
    unresolved_solved_count: int
    unique_solved_complete: bool
    correct_submissions: int
    failed_submissions: int
    total_attempted: Optional[int] = None
    success_rate: Optional[float] = None
    total_contests: int
    active_days: Optional[int] = None


class PlatformSummary(BaseModel):
    platform: str
    username: str
    solved: int
    current_rating: Optional[int] = None
    correct_submissions: int
    failed_submissions: int
    submission_success_rate: Optional[float] = None
    contests_participated: int


class TopicAnalytics(BaseModel):
    topic: str
    # None = unknown (topic seen only in submissions, no problem-level records supplied).
    solved: Optional[int] = None
    attempted: Optional[int] = None
    # Completion rate = distinct solved problems / distinct attempted problems.
    completion_rate: Optional[float] = None
    # Backwards-compatible alias for completion_rate. Prefer completion_rate in new UI.
    success_rate: Optional[float] = None
    accepted_submissions: Optional[int] = None
    failed_submissions: Optional[int] = None
    submission_count: Optional[int] = None
    # Submission success rate = accepted judged submissions / all judged submissions.
    submission_success_rate: Optional[float] = None
    classification: Literal["Strong", "Good", "Developing", "Needs Improvement", "Insufficient Data"]


class ContestPoint(BaseModel):
    timestamp: int
    date: str
    rating: Optional[int] = None
    rating_change: Optional[int] = None
    contest_name: Optional[str] = None


class ContestPlatformAnalytics(BaseModel):
    platform: str
    username: str
    total_contests: int
    positive_changes: int
    negative_changes: int
    average_rating_change: Optional[float] = None
    best_rating: Optional[int] = None
    latest_rating: Optional[int] = None
    rating_history: list[ContestPoint] = Field(default_factory=list)


class ContestAnalytics(BaseModel):
    total_contests: int
    platforms: list[ContestPlatformAnalytics]


class PlatformSolvedPoint(BaseModel):
    platform: str
    solved: int


class TopicDistributionPoint(BaseModel):
    topic: str
    solved: int


class ContestChartPoint(BaseModel):
    timestamp: int
    date: str
    rating: int


class ContestChartSeries(BaseModel):
    platform: str
    data: list[ContestChartPoint]


class ActivityPoint(BaseModel):
    date: str
    activity_count: int


class ChartData(BaseModel):
    platform_solved: list[PlatformSolvedPoint] = Field(default_factory=list)
    topic_distribution: list[TopicDistributionPoint] = Field(default_factory=list)
    contest_rating_by_platform: list[ContestChartSeries] = Field(default_factory=list)
    daily_activity: list[ActivityPoint] = Field(default_factory=list)


class Insight(BaseModel):
    type: str
    title: str
    description: str


class Recommendation(BaseModel):
    priority: Literal["High", "Medium", "Low"]
    topic: Optional[str] = None
    action: str
    reason: str


class DataQuality(BaseModel):
    partial_data: bool
    # Completeness dimensions are separate: a full history can still have
    # incomplete tags or missing canonical identities.
    history_complete: Optional[bool] = None
    topic_tag_coverage_complete: Optional[bool] = None
    canonical_id_coverage_complete: Optional[bool] = None
    judged_submission_count: Optional[int] = None
    tagged_submission_count: Optional[int] = None
    untagged_submission_count: Optional[int] = None
    topic_tag_coverage_rate: Optional[float] = None
    pagination_pages: Optional[int] = None
    duplicate_submission_records: Optional[int] = None
    missing_submission_ids: Optional[int] = None
    pagination_integrity: Optional[bool] = None
    profiles_with_complete_history: Optional[int] = None
    profiles_total: Optional[int] = None
    problem_activity_records: Optional[int] = None
    untagged_problem_activity_records: Optional[int] = None
    missing_problem_activity_canonical_ids: Optional[int] = None
    missing_problem_activity_tags: Optional[int] = None
    problemset_lookup_misses: Optional[int] = None
    problemset_entries_without_tags: Optional[int] = None
    unavailable_metrics: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    user_summary: UserSummary
    overview: Overview
    platform_comparison: list[PlatformSummary] = Field(default_factory=list)
    topic_analytics: list[TopicAnalytics] = Field(default_factory=list)
    contest_analytics: ContestAnalytics
    charts: ChartData
    insights: list[Insight] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    data_quality: DataQuality
