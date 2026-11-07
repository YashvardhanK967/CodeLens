from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

# 2100-01-01 UTC. Anything later is certainly a units mistake, so reject it with a 422
# instead of letting datetime.fromtimestamp() blow up later with a 500.
MAX_UNIX_SECONDS = 4_102_444_800
# Values at or above this can only be milliseconds (as seconds it would be the year ~5138).
_MILLIS_THRESHOLD = 100_000_000_000


def _round_rating(value):
    """Some platforms (e.g. LeetCode) report fractional ratings; the engine works in whole numbers."""
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("rating must be a finite number")
        return int(round(value))
    return value


def _strip_optional(value):
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_non_blank(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be blank")
    return value


class ContestRecord(BaseModel):
    """One contest result from one coding platform."""

    model_config = ConfigDict(extra="ignore")

    contest_id: Optional[str] = None
    contest_name: Optional[str] = None
    timestamp: int = Field(ge=0, le=MAX_UNIX_SECONDS, description="Unix timestamp in seconds")
    rating_change: Optional[int] = None
    old_rating: Optional[int] = None
    new_rating: Optional[int] = None
    rank: Optional[int] = Field(default=None, ge=1)

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalise_timestamp(cls, value):
        """Accept seconds; quietly convert millisecond timestamps; floats are truncated."""
        if isinstance(value, bool):
            return value
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError("timestamp must be a finite number")
            value = int(value)
        if isinstance(value, int) and value >= _MILLIS_THRESHOLD:
            value //= 1000
        return value

    @field_validator("rating_change", "old_rating", "new_rating", mode="before")
    @classmethod
    def round_ratings(cls, value):
        return _round_rating(value)


class TopicStat(BaseModel):
    """Legacy aggregate topic statistics reported by a platform."""

    model_config = ConfigDict(extra="ignore")

    tag_name: str = Field(min_length=1)
    solved_count: int = Field(default=0, ge=0)
    attempted_count: Optional[int] = Field(default=None, ge=0)

    @field_validator("tag_name")
    @classmethod
    def clean_tag_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("tag_name cannot be blank")
        return value


class SolvedProblem(BaseModel):
    """A solved problem with an identity supplied by the platform importer.

    canonical_id must identify the same underlying problem consistently across
    platforms. Platform-specific IDs alone are not globally comparable.
    """

    model_config = ConfigDict(extra="ignore")

    platform_problem_id: str = Field(min_length=1)
    canonical_id: Optional[str] = Field(default=None, min_length=1)
    title: Optional[str] = None
    url: Optional[str] = None
    difficulty: Optional[str] = None

    @field_validator("platform_problem_id")
    @classmethod
    def require_problem_id(cls, value: str) -> str:
        return _require_non_blank(value, "platform_problem_id")

    @field_validator("canonical_id", "title", "url", "difficulty")
    @classmethod
    def strip_optional_strings(cls, value):
        return _strip_optional(value)


class ProblemActivity(BaseModel):
    """One unique problem a profile has attempted.

    `solved` should be True when the user has an accepted solution for the
    problem at least once. `canonical_id` must be shared across platforms for
    the same underlying problem; without it, cross-profile deduplication is
    not safe. `tags` are the problem's topic labels from the source platform.
    """

    model_config = ConfigDict(extra="ignore")

    platform_problem_id: str = Field(min_length=1)
    canonical_id: Optional[str] = Field(default=None, min_length=1)
    tags: list[str] = Field(default_factory=list)
    solved: bool = False
    title: Optional[str] = None
    url: Optional[str] = None

    @field_validator("platform_problem_id")
    @classmethod
    def require_problem_id(cls, value: str) -> str:
        return _require_non_blank(value, "platform_problem_id")

    @field_validator("canonical_id", "title", "url")
    @classmethod
    def strip_optional_strings(cls, value):
        return _strip_optional(value)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            tag = value.strip()
            key = tag.casefold()
            if tag and key not in seen:
                cleaned.append(tag)
                seen.add(key)
        return cleaned


class SubmissionActivity(BaseModel):
    """One judged submission event, used for topic-specific accuracy.

    Unlike ProblemActivity, submission events are NOT deduplicated by problem:
    every judged attempt counts, including repeated attempts on the same problem.
    """

    model_config = ConfigDict(extra="ignore")

    submission_id: Optional[str] = None
    platform_problem_id: str = Field(min_length=1)
    canonical_id: Optional[str] = Field(default=None, min_length=1)
    tags: list[str] = Field(default_factory=list)
    accepted: bool

    @field_validator("platform_problem_id")
    @classmethod
    def require_problem_id(cls, value: str) -> str:
        return _require_non_blank(value, "platform_problem_id")

    @field_validator("submission_id", "canonical_id")
    @classmethod
    def strip_optional_strings(cls, value):
        return _strip_optional(value)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            tag = value.strip()
            key = tag.casefold()
            if tag and key not in seen:
                cleaned.append(tag)
                seen.add(key)
        return cleaned


class PlatformData(BaseModel):
    """Standardized profile data for a single coding-platform account."""

    model_config = ConfigDict(extra="ignore")

    platform_name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    current_rating: Optional[int] = None
    total_solved: int = Field(default=0, ge=0)
    correct_submissions: int = Field(default=0, ge=0)
    failed_submissions: int = Field(default=0, ge=0)
    total_attempted: Optional[int] = Field(default=None, ge=0)
    topics: list[TopicStat] = Field(default_factory=list)
    solved_problems: list[SolvedProblem] = Field(default_factory=list)
    # None means the importer did not provide problem-level activity.
    # An empty list means the importer explicitly provided no attempted problems.
    problem_activity: Optional[list[ProblemActivity]] = None
    # One record per judged submission; unlike problem_activity, repeats count.
    submission_activity: Optional[list[SubmissionActivity]] = None
    contest_history: list[ContestRecord] = Field(default_factory=list)
    # Keys must be YYYY-MM-DD. Values are activity counts reported by the source.
    daily_activity: dict[str, int] = Field(default_factory=dict)
    # data_complete means the importer reached the end of available submission history.
    data_complete: bool = False
    pagination_pages: int = Field(default=0, ge=0)
    duplicate_submission_records: int = Field(default=0, ge=0)
    missing_submission_ids: int = Field(default=0, ge=0)
    problemset_lookup_misses: int = Field(default=0, ge=0)
    problemset_entries_without_tags: int = Field(default=0, ge=0)

    @field_validator("current_rating", mode="before")
    @classmethod
    def round_current_rating(cls, value):
        return _round_rating(value)

    @field_validator("platform_name", "username")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("daily_activity")
    @classmethod
    def validate_daily_activity(cls, value: dict[str, int]) -> dict[str, int]:
        cleaned: dict[str, int] = {}
        for day, count in value.items():
            try:
                datetime.strptime(day, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"daily_activity key {day!r} must use YYYY-MM-DD") from exc
            if count < 0:
                raise ValueError("daily_activity counts cannot be negative")
            cleaned[day] = count
        return cleaned


class AnalysisRequest(BaseModel):
    """Request body accepted by POST /api/v1/analysis."""

    display_name: Optional[str] = None
    platforms: list[PlatformData] = Field(min_length=1)
