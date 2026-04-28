"""
api/schemas.py
Pydantic request/response models for the NBA AI Analyzer REST API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    version: str


# ---------------------------------------------------------------------------
# GET /seasons
# ---------------------------------------------------------------------------
class SeasonsResponse(BaseModel):
    seasons: List[str]
    default: str


# ---------------------------------------------------------------------------
# POST /ai/parse
# ---------------------------------------------------------------------------
class AIParseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language query")


class AIParseResponse(BaseModel):
    """Mirrors QuerySpec from ai_query_parser.  Extra keys from the parser are ignored."""
    model_config = ConfigDict(extra="ignore")

    result_type: str
    chart_type: Optional[str] = None
    entity: Optional[str] = None
    window: Optional[str] = None
    metric: Optional[str] = None
    x_metric: Optional[str] = None
    y_metric: Optional[str] = None
    top_n: Optional[int] = None
    order: Optional[str] = None
    teams: Optional[List[str]] = None
    compare_metrics: Optional[List[str]] = None
    season: Optional[str] = None
    season_type: Optional[str] = None
    message: Optional[str] = None
    debug: Optional[Dict[str, Any]] = Field(None, description="Parser debug info (_debug key)")


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    season: str = Field(..., description="NBA season, e.g. '2024-25'")
    season_type: str = Field("Regular Season", description="'Regular Season' or 'Playoffs'")
    chart_type: Literal["leaderboard", "scatter", "compare"]
    entity: str = "team"
    window: str = Field("SEASON", description="SEASON | LAST_5 | LAST_10 | LAST_20")
    # leaderboard fields
    metric: Optional[str] = None
    top_n: Optional[int] = Field(None, ge=1, le=30)
    order: Optional[Literal["asc", "desc"]] = None
    # scatter fields
    x_metric: Optional[str] = None
    y_metric: Optional[str] = None
    # compare fields
    teams: Optional[List[str]] = None
    compare_metrics: Optional[List[str]] = None


class QueryResponse(BaseModel):
    season_type: str = "Regular Season"
    explanation: str
    rows: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# POST /metrics
# ---------------------------------------------------------------------------
class MetricsRequest(BaseModel):
    season: str = Field(..., description="NBA season, e.g. '2024-25'")
    season_type: str = Field("Regular Season", description="'Regular Season' or 'Playoffs'")
    window: str = Field("SEASON", description="SEASON | LAST_5 | LAST_10 | LAST_20")
    teams: Optional[List[str]] = Field(None, description="Filter to specific team abbreviations")


class MetricsResponse(BaseModel):
    season: str
    season_type: str = "Regular Season"
    window: str
    rows: List[Dict[str, Any]]
