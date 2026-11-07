import sys
import os

# ---------------------------------------------------------------------------
# Make the codepulse analytics engine importable regardless of which
# directory uvicorn is launched from.
# ---------------------------------------------------------------------------
_CODEPULSE_DIR = os.path.join(
    os.path.dirname(__file__),
    "codepulse_backend_FIXED_full",
    "codepulse_backend",
)
if _CODEPULSE_DIR not in sys.path:
    sys.path.insert(0, _CODEPULSE_DIR)

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Shared Pydantic models (defined in codepulse_backend/models/)
# ---------------------------------------------------------------------------
from models.input_models import (
    PlatformData,
    ContestRecord,
    TopicStat,
    SolvedProblem,
    ProblemActivity,
    SubmissionActivity,
    AnalysisRequest,
)
from models.output_models import DashboardResponse

# ---------------------------------------------------------------------------
# CodePulse analytics engine
# ---------------------------------------------------------------------------
from engine.analysis_engine import analyze_user

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CodePulse – Unified API",
    description=(
        "Fetches coding-platform profiles (Codeforces, LeetCode, CodeChef, GFG) "
        "and pipes the results directly into the CodePulse analytics engine."
    ),
    version="2.0.0",
)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "CodePulse Unified API",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "fetch_only": "POST /api/v1/fetch-analytics",
            "fetch_and_analyze": "POST /api/v1/analyze",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}

def _extract_handle(value: Optional[str]) -> Optional[str]:
    """Strip a full profile URL down to just the username/handle.

    Accepts either a bare handle ("tourist") or a full URL
    ("https://codeforces.com/profile/tourist") and always returns
    the bare handle, or None if the value is blank.
    """
    if not value:
        return None
    value = value.strip().rstrip("/")
    if not value:
        return None
    # If it looks like a URL, take the last path segment.
    if value.startswith("http://") or value.startswith("https://") or "/" in value:
        return value.split("/")[-1] or None
    return value


class UserHandles(BaseModel):
    display_name: str
    codeforces: Optional[str] = None
    leetcode: Optional[str] = None
    codechef: Optional[str] = None
    geeksforgeeks: Optional[str] = None

    def parsed_codeforces(self) -> Optional[str]:
        return _extract_handle(self.codeforces)

    def parsed_leetcode(self) -> Optional[str]:
        return _extract_handle(self.leetcode)

    def parsed_codechef(self) -> Optional[str]:
        return _extract_handle(self.codechef)

    def parsed_geeksforgeeks(self) -> Optional[str]:
        return _extract_handle(self.geeksforgeeks)

def fetch_codeforces(handle: str, session: requests.Session) -> PlatformData:
    """Fetches and maps Codeforces data sequentially using synchronous requests."""
    base_url = "https://codeforces.com/api"
    
    try:
        # Fetch data sequentially 
        info_resp = session.get(f"{base_url}/user.info?handles={handle}")
        rating_resp = session.get(f"{base_url}/user.rating?handle={handle}")
        status_resp = session.get(f"{base_url}/user.status?handle={handle}")
        
        info_data = info_resp.json()
        rating_data = rating_resp.json()
        status_data = status_resp.json()

        if info_data.get("status") != "OK":
            raise ValueError(f"Codeforces API error: {info_data.get('comment')}")

        user_info = info_data["result"][0]
        current_rating = user_info.get("rating", 0)

        # Process Contest History
        contest_history = []
        if rating_data.get("status") == "OK":
            for contest in rating_data["result"]:
                contest_history.append(
                    ContestRecord(
                        contest_id=str(contest["contestId"]),
                        contest_name=contest["contestName"],
                        timestamp=contest["ratingUpdateTimeSeconds"],
                        rating_change=contest["newRating"] - contest["oldRating"],
                        old_rating=contest["oldRating"],
                        new_rating=contest["newRating"],
                        rank=contest["rank"]
                    )
                )

        # Process Submissions, Problems, and Topics
        submission_activity = []
        problem_activity_dict = {}
        topic_counts = {} # Replaced defaultdict with standard dict
        
        correct_submissions = 0
        failed_submissions = 0

        if status_data.get("status") == "OK":
            for sub in status_data["result"]:
                prob = sub["problem"]
                platform_prob_id = f"{prob.get('contestId', '')}{prob.get('index', '')}"
                is_accepted = sub.get("verdict") == "OK"
                
                if is_accepted:
                    correct_submissions += 1
                else:
                    failed_submissions += 1

                tags = prob.get("tags", [])
                
                submission_activity.append(
                    SubmissionActivity(
                        submission_id=str(sub["id"]),
                        platform_problem_id=platform_prob_id,
                        tags=tags,
                        accepted=is_accepted
                    )
                )

                if platform_prob_id not in problem_activity_dict:
                    problem_activity_dict[platform_prob_id] = ProblemActivity(
                        platform_problem_id=platform_prob_id,
                        tags=tags,
                        solved=is_accepted,
                        title=prob.get("name")
                    )
                elif is_accepted:
                    # Mark as solved if any submission was accepted, regardless
                    # of which submission we saw first.
                    existing = problem_activity_dict[platform_prob_id]
                    if not existing.solved:
                        problem_activity_dict[platform_prob_id] = existing.model_copy(
                            update={"solved": True}
                        )

        # Build the final PlatformData object and return it
        return PlatformData(
            platform_name="Codeforces",
            username=handle,
            current_rating=current_rating,
            correct_submissions=correct_submissions,
            failed_submissions=failed_submissions,
            contest_history=contest_history,
            submission_activity=submission_activity,
            problem_activity=list(problem_activity_dict.values()),
            data_complete=True,
        )

    except Exception as e:
        print(f"Error processing Codeforces for {handle}: {e}")
        return None

def fetch_leetcode(handle: str, session: requests.Session) -> PlatformData:
    """Fetches LeetCode data via their GraphQL endpoint."""
    url = "https://leetcode.com/graphql"
    payload = {
        "query": """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
            userContestRanking(username: $username) {
                rating
            }
        }
        """,
        "variables": {"username": handle}
    }
    
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = session.post(url, json=payload, headers=headers)
        data = response.json().get("data", {})
        
        matched_user = data.get("matchedUser")
        if not matched_user:
            raise ValueError(f"User {handle} not found on LeetCode.")

        # Extract solved counts
        total_solved = 0
        ac_submissions = matched_user.get("submitStats", {}).get("acSubmissionNum", [])
        for sub in ac_submissions:
            if sub.get("difficulty") == "All":
                total_solved = sub.get("count", 0)

        # Extract contest rating
        contest_ranking = data.get("userContestRanking")
        current_rating = int(contest_ranking.get("rating", 0)) if contest_ranking else 0

        return PlatformData(
            platform_name="LeetCode",
            username=handle,
            current_rating=current_rating,
            total_solved=total_solved,
            data_complete=True
        )
    except Exception as e:
        print(f"Error processing LeetCode for {handle}: {e}")
        return None


def fetch_codechef(handle: str, session: requests.Session) -> PlatformData:
    """Scrapes CodeChef profile for rating and basic stats."""
    url = f"https://www.codechef.com/users/{handle}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            raise ValueError(f"CodeChef profile not found or blocked (Status: {response.status_code})")
            
        soup = BeautifulSoup(response.text, "lxml")
        
        # Extract Rating
        rating_elem = soup.find("div", class_="rating-number")
        current_rating = int(rating_elem.text.strip().split("?")[0]) if rating_elem else 0
        
        # Extract Total Solved (Codechef renders this in a specific section)
        solved_section = soup.find("section", class_="rating-data-section problems-solved")
        total_solved = 0
        if solved_section:
            # CodeChef usually stores solved counts in an h3 tag like "Fully Solved (150)"
            heading = solved_section.find("h3")
            if heading and "(" in heading.text:
                num_str = heading.text.split("(")[-1].replace(")", "")
                total_solved = int(num_str) if num_str.isdigit() else 0

        return PlatformData(
            platform_name="CodeChef",
            username=handle,
            current_rating=current_rating,
            total_solved=total_solved,
            data_complete=True
        )
    except Exception as e:
        print(f"Error processing CodeChef for {handle}: {e}")
        return None


def fetch_geeksforgeeks(handle: str, session: requests.Session) -> PlatformData:
    """Scrapes GeeksforGeeks profile for solved counts."""
    url = f"https://www.geeksforgeeks.org/user/{handle}/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            raise ValueError(f"GFG profile not found or blocked (Status: {response.status_code})")
            
        soup = BeautifulSoup(response.text, "lxml")
        
        # GFG usually displays total problems solved in a distinct span or div
        # Note: GFG updates their UI frequently, so these classes might need adjustment
        total_solved = 0
        score_cards = soup.find_all("div", class_="scoreCard_head_card_left--score__mCqro")
        
        # Usually the second card holds the total problems solved
        if len(score_cards) >= 2:
            num_str = score_cards[1].text.strip()
            total_solved = int(num_str) if num_str.isdigit() else 0

        return PlatformData(
            platform_name="GeeksforGeeks",
            username=handle,
            total_solved=total_solved,
            current_rating=0, # GFG uses coding score rather than ELO rating
            data_complete=True
        )
    except Exception as e:
        print(f"Error processing GeeksforGeeks for {handle}: {e}")
        return None


@app.post("/api/v1/fetch-analytics", response_model=AnalysisRequest)
def fetch_user_analytics(request: UserHandles):
    """Fetch data from all supplied platform handles and return raw AnalysisRequest.
    
    Use this endpoint if you want to inspect the raw collected data before analysis,
    or if the analytics engine runs as a separate service.
    """
    platforms_data = _collect_platforms(request)
    return AnalysisRequest(
        display_name=request.display_name,
        platforms=platforms_data,
    )


@app.post("/api/v1/analyze", response_model=DashboardResponse)
def fetch_and_analyze(request: UserHandles):
    """Fetch platform data AND run the CodePulse analytics engine in one request.
    
    This is the primary endpoint for the frontend dashboard. It:
    1. Fetches raw profile data from each supplied coding platform.
    2. Passes the collected data directly into the CodePulse analytics engine.
    3. Returns a fully computed DashboardResponse ready for display.
    """
    platforms_data = _collect_platforms(request)
    return analyze_user(platforms_data, display_name=request.display_name)


def _collect_platforms(request: UserHandles) -> list[PlatformData]:
    """Shared helper: fetch platform data for all handles in the request.
    
    Handles are extracted from whatever the user provides — bare usernames
    or full profile URLs are both accepted.
    """
    platforms_data: list[PlatformData] = []

    cf_handle  = request.parsed_codeforces()
    lc_handle  = request.parsed_leetcode()
    cc_handle  = request.parsed_codechef()
    gfg_handle = request.parsed_geeksforgeeks()

    with requests.Session() as session:
        if cf_handle:
            cf_data = fetch_codeforces(cf_handle, session)
            if cf_data:
                platforms_data.append(cf_data)

        if lc_handle:
            lc_data = fetch_leetcode(lc_handle, session)
            if lc_data:
                platforms_data.append(lc_data)

        if cc_handle:
            cc_data = fetch_codechef(cc_handle, session)
            if cc_data:
                platforms_data.append(cc_data)

        if gfg_handle:
            gfg_data = fetch_geeksforgeeks(gfg_handle, session)
            if gfg_data:
                platforms_data.append(gfg_data)

    if not platforms_data:
        raise HTTPException(
            status_code=404,
            detail="No valid platform data could be retrieved for any of the supplied handles.",
        )

    return platforms_data