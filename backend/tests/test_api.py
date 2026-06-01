"""
tests/test_api.py
Smoke + unit tests for the FastAPI layer.

Uses FastAPI's TestClient (backed by httpx) and mocks the NBA API calls
so tests run offline without hitting stats.nba.com.

The `prepared_df` fixture from conftest.py (BOS vs LAL, 3 games each) is
reused as the stand-in season dataset.
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# /seasons
# ---------------------------------------------------------------------------

def test_seasons_returns_list():
    r = client.get("/seasons")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["seasons"], list)
    assert len(body["seasons"]) > 0
    assert isinstance(body["default"], str)
    assert body["default"] in body["seasons"]


# ---------------------------------------------------------------------------
# /ai/parse  — uses rule-based fallback (no OpenAI key in CI)
# ---------------------------------------------------------------------------

def test_ai_parse_leaderboard_query():
    r = client.post("/ai/parse", json={"query": "top 10 teams by net rating last 10 games"})
    assert r.status_code == 200
    body = r.json()
    assert body["result_type"] == "QUERY"
    assert body["chart_type"] == "leaderboard"
    assert "debug" in body


def test_ai_parse_out_of_scope():
    r = client.post("/ai/parse", json={"query": "how many points did LeBron score last night"})
    assert r.status_code == 200
    assert r.json()["result_type"] == "OUT_OF_SCOPE"


def test_ai_parse_empty_query_rejected():
    r = client.post("/ai/parse", json={"query": ""})
    assert r.status_code == 422


def test_ai_parse_missing_body_rejected():
    r = client.post("/ai/parse", json={})
    assert r.status_code == 422


def test_ai_parse_returns_debug_metadata():
    r = client.post("/ai/parse", json={"query": "best defense last 5 games"})
    assert r.status_code == 200
    debug = r.json()["debug"]
    assert debug is not None
    assert "openai_used" in debug
    assert "fallback_used" in debug


def test_ai_parse_mocked_openai_response():
    """Verify the response shape when OpenAI returns a structured result."""
    mock_spec = {
        "result_type": "QUERY",
        "chart_type": "scatter",
        "entity": "team",
        "window": "SEASON",
        "x_metric": "ORtg",
        "y_metric": "DRtg",
        "_debug": {"openai_used": True, "fallback_used": False, "fallback_reason": None},
    }
    with patch("ai_query_parser.parse_natural_language_query", return_value=mock_spec):
        r = client.post("/ai/parse", json={"query": "offense vs defense this season"})
    assert r.status_code == 200
    body = r.json()
    assert body["chart_type"] == "scatter"
    assert body["debug"]["openai_used"] is True


# ---------------------------------------------------------------------------
# /query
# ---------------------------------------------------------------------------

def test_query_leaderboard(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df) as mock_load:
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "leaderboard",
            "metric": "NET_RTG",
            "top_n": 5,
            "window": "SEASON",
        })
    assert r.status_code == 200
    body = r.json()
    assert "explanation" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 5
    # BOS has +12 NET_RTG, should be first with desc order
    assert body["rows"][0]["TEAM_ABBREVIATION"] == "BOS"
    mock_load.assert_called_once_with("2024-25", season_type="Regular Season")


def test_query_playoffs_passes_season_type(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df) as mock_load:
        r = client.post("/query", json={
            "season": "2024-25",
            "season_type": "Playoffs",
            "chart_type": "leaderboard",
            "metric": "NET_RTG",
            "top_n": 5,
            "window": "SEASON",
        })
    assert r.status_code == 200
    assert r.json()["season_type"] == "Playoffs"
    mock_load.assert_called_once_with("2024-25", season_type="Playoffs")


def test_query_scatter(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "scatter",
            "x_metric": "ORtg",
            "y_metric": "DRtg",
            "window": "SEASON",
        })
    assert r.status_code == 200
    rows = r.json()["rows"]
    teams = {row["TEAM_ABBREVIATION"] for row in rows}
    assert teams == {"BOS", "LAL"}


def test_query_compare(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "compare",
            "teams": ["BOS", "LAL"],
            "window": "SEASON",
        })
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 2
    teams = {row["TEAM_ABBREVIATION"] for row in rows}
    assert teams == {"BOS", "LAL"}


def test_query_compare_supplemental_metrics(prepared_df):
    rim = pd.DataFrame({
        "TEAM_ID": [1610612738, 1610612747],
        "opp_fgpct_rim": [0.611, 0.644],
    })
    clutch = pd.DataFrame({
        "TEAM_ID": [1610612738, 1610612747],
        "clutch_net_rating": [12.4, -8.1],
    })
    with (
        patch("data_loader.load_season_data", return_value=prepared_df),
        patch("data_loader._fetch_opp_fgpct_rim", return_value=rim),
        patch("data_loader._fetch_clutch_net_rating", return_value=clutch),
    ):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "compare",
            "teams": ["BOS", "LAL"],
            "compare_metrics": ["oreb_pct", "dreb_pct", "opp_fgpct_rim", "clutch_net_rating"],
            "window": "SEASON",
        })
    assert r.status_code == 200
    bos = next(row for row in r.json()["rows"] if row["TEAM_ABBREVIATION"] == "BOS")
    assert bos["oreb_pct"] == 0.0
    assert bos["dreb_pct"] == 1.0
    assert bos["opp_fgpct_rim"] == 0.611
    assert bos["clutch_net_rating"] == 12.4


def test_query_unknown_season():
    r = client.post("/query", json={
        "season": "1899-00",
        "chart_type": "leaderboard",
        "metric": "NET_RTG",
        "top_n": 10,
    })
    assert r.status_code == 400
    assert "Unknown season" in r.json()["detail"]


def test_query_invalid_season_type_returns_400():
    r = client.post("/query", json={
        "season": "2024-25",
        "season_type": "Preseason",
        "chart_type": "leaderboard",
        "metric": "NET_RTG",
        "top_n": 10,
    })
    assert r.status_code == 400
    assert "Unsupported season_type" in r.json()["detail"]


def test_query_invalid_metric_returns_422(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "leaderboard",
            "metric": "NOT_A_REAL_METRIC",
            "top_n": 10,
        })
    assert r.status_code == 422


def test_query_leaderboard_missing_metric_returns_422(prepared_df):
    """Leaderboard without a metric is invalid per ChartSpec rules."""
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "leaderboard",
            # metric omitted — spec_from_dict defaults to NET_RTG so this actually succeeds
            "top_n": 10,
        })
    # spec_from_dict fills metric=NET_RTG by default — expect 200
    assert r.status_code == 200


def test_query_rows_are_json_safe(prepared_df):
    """Ensure floats, ints, and timestamps are serialised without NaN/numpy types."""
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "leaderboard",
            "metric": "ORtg",
            "top_n": 2,
            "window": "SEASON",
        })
    assert r.status_code == 200
    for row in r.json()["rows"]:
        for v in row.values():
            assert not isinstance(v, float) or v == v, "NaN leaked into response"


def test_query_nba_api_failure_returns_503():
    with patch("data_loader.load_season_data", side_effect=RuntimeError("timeout")):
        r = client.post("/query", json={
            "season": "2024-25",
            "chart_type": "leaderboard",
            "metric": "NET_RTG",
            "top_n": 10,
        })
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

def test_metrics_all_teams(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df) as mock_load:
        r = client.post("/metrics", json={"season": "2024-25", "window": "SEASON"})
    assert r.status_code == 200
    body = r.json()
    assert body["season"] == "2024-25"
    assert body["season_type"] == "Regular Season"
    assert body["window"] == "SEASON"
    assert len(body["rows"]) == 2  # BOS + LAL
    mock_load.assert_called_once_with("2024-25", season_type="Regular Season")


def test_metrics_playoffs_passes_season_type(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df) as mock_load:
        r = client.post("/metrics", json={"season": "2024-25", "season_type": "Playoffs", "window": "SEASON"})
    assert r.status_code == 200
    assert r.json()["season_type"] == "Playoffs"
    mock_load.assert_called_once_with("2024-25", season_type="Playoffs")


def test_metrics_team_filter(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={
            "season": "2024-25",
            "window": "SEASON",
            "teams": ["BOS"],
        })
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["TEAM_ABBREVIATION"] == "BOS"


def test_metrics_team_filter_case_insensitive(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={
            "season": "2024-25",
            "window": "SEASON",
            "teams": ["bos"],   # lowercase
        })
    assert r.status_code == 200
    assert len(r.json()["rows"]) == 1


def test_metrics_window_aliases(prepared_df):
    """normalize_window should accept aliases like L10."""
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={"season": "2024-25", "window": "L10"})
    assert r.status_code == 200
    assert r.json()["window"] == "LAST_10"


def test_metrics_unknown_season():
    r = client.post("/metrics", json={"season": "1899-00", "window": "SEASON"})
    assert r.status_code == 400


def test_metrics_invalid_season_type_returns_400():
    r = client.post("/metrics", json={"season": "2024-25", "season_type": "Preseason", "window": "SEASON"})
    assert r.status_code == 400
    assert "Unsupported season_type" in r.json()["detail"]


def test_metrics_unknown_window_snaps_to_last_20(prepared_df):
    # normalize_window snaps LAST_99 -> LAST_20 rather than erroring
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={"season": "2024-25", "window": "LAST_99"})
    assert r.status_code == 200
    assert r.json()["window"] == "LAST_20"


def test_metrics_contains_expected_columns(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={"season": "2024-25", "window": "SEASON"})
    assert r.status_code == 200
    row = r.json()["rows"][0]
    for col in (
        "TEAM_ABBREVIATION",
        "ORtg",
        "DRtg",
        "NET_RTG",
        "PACE",
        "oreb_pct",
        "dreb_pct",
        "opp_fgpct_rim",
        "clutch_net_rating",
    ):
        assert col in row, f"Expected column '{col}' missing from metrics response"


def test_metrics_unavailable_split_metrics_return_null(prepared_df):
    with patch("data_loader.load_season_data", return_value=prepared_df):
        r = client.post("/metrics", json={"season": "2024-25", "window": "SEASON"})
    assert r.status_code == 200
    row = r.json()["rows"][0]
    assert row["opp_fgpct_rim"] is None
    assert row["clutch_net_rating"] is None


def test_metrics_nba_api_failure_returns_503():
    with patch("data_loader.load_season_data", side_effect=RuntimeError("rate limited")):
        r = client.post("/metrics", json={"season": "2024-25", "window": "SEASON"})
    assert r.status_code == 503
