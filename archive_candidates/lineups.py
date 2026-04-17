# Fetches and processes lineup data from the NBA API
# Uses LeagueDashLineups to find top-performing multi-player combinations

from __future__ import annotations

import time

import pandas as pd
import streamlit as st
from nba_api.stats.static import teams as nba_teams


# Maps project metric names → LeagueDashLineups column names
METRIC_COLUMN_MAP = {
    "NET_RTG": "NET_RATING",
    "ORtg": "OFF_RATING",
    "DRtg": "DEF_RATING",
    "PACE": "PACE",
    "AST_RATE": "AST_PCT",
    "TOV_RATE": "TOV_PCT",
}

# Metrics where lower is better
ASC_METRICS = {"DRtg", "TOV_RATE"}

LINEUP_METRICS = list(METRIC_COLUMN_MAP.keys())

# NBA API occasionally ships minor column naming variants.
METRIC_COLUMN_ALIASES = {
    "NET_RTG": ("NET_RTG",),
    "ORtg": ("OFF_RTG", "OFFENSIVE_RATING"),
    "DRtg": ("DEF_RTG", "DEFENSIVE_RATING"),
    "AST_RATE": ("AST_RATIO",),
    "TOV_RATE": ("TOV_RATIO",),
}


def _team_abbrev_to_id(abbrev: str) -> int:
    """Convert team abbreviation (e.g. 'BOS') to nba_api team ID."""
    all_teams = nba_teams.get_teams()
    for team in all_teams:
        if team["abbreviation"] == abbrev:
            return team["id"]
    raise ValueError(f"Unknown team abbreviation: {abbrev}")


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_lineups(team_id: int, season: str, last_n_games: int = 0) -> pd.DataFrame:
    """
    Fetch lineup data from NBA API for a specific team.
    Uses PerGame mode so rating columns (NET_RATING, OFF_RATING, etc.) are available.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueDashLineups

    time.sleep(0.6)  # Respect API rate limits

    try:
        response = LeagueDashLineups(
            team_id_nullable=team_id,
            season=season,
            season_type_all_star="Regular Season",
            last_n_games=last_n_games,
            group_quantity=5,  # 5-man lineups
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
        )
        df = response.get_data_frames()[0]
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to fetch lineup data: {e}") from e


def _window_to_last_n(window: str) -> int:
    """Convert project window format to last_n_games parameter."""
    if window == "SEASON":
        return 0
    if window.startswith("LAST_"):
        return int(window.split("_")[1])
    return 0


def _resolve_api_metric_column(df: pd.DataFrame, metric: str) -> str:
    """Return the available column name for a metric, creating NET_RATING if needed."""
    preferred = METRIC_COLUMN_MAP[metric]
    if preferred in df.columns:
        return preferred

    for alias in METRIC_COLUMN_ALIASES.get(metric, ()):
        if alias in df.columns:
            return alias

    # Fallback: derive net rating when API omits the direct column.
    if metric == "NET_RTG" and {"OFF_RATING", "DEF_RATING"}.issubset(df.columns):
        df["NET_RATING"] = df["OFF_RATING"] - df["DEF_RATING"]
        return "NET_RATING"

    raise ValueError(
        f"Lineup metric '{metric}' is unavailable for this response. "
        f"Returned columns include: {', '.join(sorted(df.columns))}"
    )


def get_best_lineups_for_team(
    team_abbrev: str,
    metric: str,
    season: str,
    window: str = "SEASON",
    min_minutes: float = 50.0,
) -> pd.DataFrame:
    """
    Fetch and return the top 3 lineups for a team ranked by a given metric.

    Args:
        team_abbrev: Team abbreviation (e.g. 'BOS')
        metric: One of NET_RTG, ORtg, DRtg, PACE, AST_RATE, TOV_RATE
        season: Season in 'YYYY-YY' format
        window: Time window (SEASON, LAST_5, LAST_10, LAST_20)
        min_minutes: Minimum total minutes for lineup inclusion

    Returns:
        DataFrame with columns: LINEUP, TOTAL_MIN, GP, <metric>
    """
    if metric not in METRIC_COLUMN_MAP:
        raise ValueError(f"Unsupported lineup metric: {metric}. Use one of {LINEUP_METRICS}")

    team_id = _team_abbrev_to_id(team_abbrev)
    last_n = _window_to_last_n(window)

    raw = _fetch_lineups(team_id, season, last_n)

    if raw.empty:
        return pd.DataFrame(columns=["LINEUP", "TOTAL_MIN", "GP", metric])

    api_col = _resolve_api_metric_column(raw, metric)

    # Compute total minutes (MIN is per-game in PerGame mode)
    if "MIN" in raw.columns and "GP" in raw.columns:
        raw["TOTAL_MIN"] = raw["MIN"] * raw["GP"]
        raw = raw[raw["TOTAL_MIN"] >= min_minutes].copy()

    if raw.empty:
        return pd.DataFrame(columns=["LINEUP", "TOTAL_MIN", "GP", metric])

    # Sort: ascending for DRtg/TOV_RATE (lower = better), descending otherwise
    ascending = metric in ASC_METRICS
    raw = raw.sort_values(api_col, ascending=ascending)

    # Top 3 lineups
    result = raw.head(3).copy()

    # Clean up lineup names
    if "GROUP_NAME" in result.columns:
        result["LINEUP"] = result["GROUP_NAME"].str.replace(r"\s*-\s*", " - ", regex=True)
    else:
        result["LINEUP"] = "Unknown"

    # Rename API column to project metric name
    result[metric] = result[api_col]

    # Select output columns
    out_cols = ["LINEUP", "TOTAL_MIN", "GP", metric]
    available = [c for c in out_cols if c in result.columns]

    return result[available].reset_index(drop=True)
