"""
api/main.py
FastAPI wrapper around the NBA AI Analyzer business logic.

Run from the backend/ directory:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AIParseRequest,
    AIParseResponse,
    HealthResponse,
    MetricsRequest,
    MetricsResponse,
    QueryRequest,
    QueryResponse,
    SeasonsResponse,
)

app = FastAPI(
    title="NBA AI Analyzer API",
    version="0.1.0",
    description="REST wrapper around CourtVision analytics logic.",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# In production set CORS_ORIGINS env var to your Vercel frontend URL,
# e.g. CORS_ORIGINS=https://your-app.vercel.app
_extra_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        *_extra_origins,
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a DataFrame to a JSON-safe list of dicts."""
    records = []
    for row in df.to_dict(orient="records"):
        clean: Dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            elif isinstance(v, np.integer):
                clean[k] = int(v)
            elif isinstance(v, np.floating):
                clean[k] = round(float(v), 4)
            elif isinstance(v, pd.Timestamp):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        records.append(clean)
    return records


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


# ---------------------------------------------------------------------------
# GET /seasons
# ---------------------------------------------------------------------------

@app.get("/seasons", response_model=SeasonsResponse, tags=["meta"])
def seasons() -> SeasonsResponse:
    from data_loader import get_available_seasons, get_default_season  # lazy import

    available = [s for s, _ in get_available_seasons()]
    default = get_default_season() or available[0]
    return SeasonsResponse(seasons=available, default=default)


# ---------------------------------------------------------------------------
# POST /ai/parse
# ---------------------------------------------------------------------------

@app.post("/ai/parse", response_model=AIParseResponse, tags=["ai"])
def ai_parse(req: AIParseRequest) -> AIParseResponse:
    """
    Parse a natural language query into a structured QuerySpec.
    Uses OpenAI when OPENAI_API_KEY is set, otherwise falls back to
    the rule-based parser.
    """
    from ai_query_parser import parse_natural_language_query

    result = parse_natural_language_query(req.query)
    debug = result.pop("_debug", None)
    return AIParseResponse.model_validate({**result, "debug": debug})


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

@app.post("/query", response_model=QueryResponse, tags=["analytics"])
def query(req: QueryRequest) -> QueryResponse:
    """
    Execute a structured query against a season's game-log data.

    Loads season data from the NBA API (cached 1 hr), builds a ChartSpec,
    runs the query engine, and returns the result rows as JSON.
    """
    from data_loader import AVAILABLE_SEASONS, load_season_data
    from query_engine import run_query, spec_from_dict

    if req.season not in AVAILABLE_SEASONS:
        raise HTTPException(status_code=400, detail=f"Unknown season '{req.season}'. See GET /seasons.")

    try:
        df = load_season_data(req.season)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"NBA API unavailable: {exc}") from exc

    spec_dict = req.model_dump(exclude={"season"}, exclude_none=True)

    try:
        spec = spec_from_dict(spec_dict)
        result_df, explanation = run_query(df, spec)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return QueryResponse(explanation=explanation, rows=_df_to_records(result_df))


# ---------------------------------------------------------------------------
# POST /metrics
# ---------------------------------------------------------------------------

@app.post("/metrics", response_model=MetricsResponse, tags=["analytics"])
def metrics(req: MetricsRequest) -> MetricsResponse:
    """
    Return all computed team metrics for a season/window.

    Optionally filter to a subset of teams via the `teams` field
    (e.g. ["BOS", "LAL"]).
    """
    from data_loader import AVAILABLE_SEASONS, load_season_data
    from metrics import aggregate_team_complete
    from query_engine import normalize_window

    if req.season not in AVAILABLE_SEASONS:
        raise HTTPException(status_code=400, detail=f"Unknown season '{req.season}'. See GET /seasons.")

    try:
        df = load_season_data(req.season)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"NBA API unavailable: {exc}") from exc

    try:
        window = normalize_window(req.window)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = aggregate_team_complete(df, window)

    if req.teams:
        upper = {t.upper() for t in req.teams}
        result = result[result["TEAM_ABBREVIATION"].isin(upper)]

    return MetricsResponse(season=req.season, window=window, rows=_df_to_records(result))
