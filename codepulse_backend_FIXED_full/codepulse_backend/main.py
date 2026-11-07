import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.input_models import AnalysisRequest
from models.output_models import DashboardResponse
from engine.analysis_engine import analyze_user

app = FastAPI(
    title="CodePulse API",
    description="Aggregates coding-platform profile data and returns dashboard-ready analytics.",
    version="1.0.0",
)

# Set CORS_ORIGINS in your environment to your frontend URL(s), comma-separated.
# Defaults cover common local React/Vite development addresses.
_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "CodePulse API",
        "status": "running",
        "docs": "/docs",
        "analysis_endpoint": "POST /api/v1/analysis",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/analysis", response_model=DashboardResponse)
def create_analysis(request: AnalysisRequest) -> DashboardResponse:
    return analyze_user(request.platforms, request.display_name)
