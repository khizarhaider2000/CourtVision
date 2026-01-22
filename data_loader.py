# data_loader.py
# Fetches NBA data LIVE from nba_api - no local files required

import pandas as pd
from typing import List, Tuple, Optional
import streamlit as st
from metrics import prepare_team_games_for_metrics

# Available seasons (hardcoded - NBA API supports these)
AVAILABLE_SEASONS = [
    "2025-26",
    "2024-25",
    "2023-24",
    "2022-23",
    "2021-22",
    "2020-21",
    "2019-20",
    "2018-19",
    "2017-18",
    "2016-17",
]


def _current_season_label() -> str:
    """Compute the current NBA season label (e.g., 2024-25)."""
    from datetime import datetime

    today = datetime.now()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def get_available_seasons() -> List[Tuple[str, None]]:
    """
    Return list of available NBA seasons.

    Returns:
        List of tuples: (season_display_name, None)
        Second element is None for backwards compatibility (was file path).
    """
    seasons = AVAILABLE_SEASONS or [_current_season_label()]
    return [(season, None) for season in seasons]


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_from_nba_api(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Internal: Fetch team game logs from NBA API.
    Cached for 1 hour to avoid rate limiting.

    Args:
        season: NBA season in 'YYYY-YY' format (e.g., '2024-25')
        season_type: 'Regular Season' or 'Playoffs'

    Returns:
        pd.DataFrame: Raw team game logs from NBA API

    Raises:
        RuntimeError: If API call fails
    """
    from nba_api.stats.endpoints import LeagueGameLog
    import time

    # Small delay to be respectful to the API
    time.sleep(0.6)

    try:
        lg = LeagueGameLog(
            season=season,
            season_type_all_star=season_type,
            timeout=60  # Longer timeout for slow connections
        )
        df = lg.get_data_frames()[0].copy()

        if df.empty:
            raise ValueError(f"No games found for {season} {season_type}")

        return df

    except Exception as e:
        raise RuntimeError(f"NBA API error: {str(e)}")


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_team_stats(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Internal: Fetch season-level team stats from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueDashTeamStats
    import time

    time.sleep(0.4)

    try:
        stats = LeagueDashTeamStats(
            season=season,
            season_type_all_star=season_type,
            timeout=60
        )
        df = stats.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No team stats found for {season} {season_type}")
        return df
    except Exception as e:
        raise RuntimeError(f"NBA API error: {str(e)}")


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_standings(season: str) -> pd.DataFrame:
    """
    Internal: Fetch league standings from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueStandingsV3
    import time

    time.sleep(0.4)

    try:
        standings = LeagueStandingsV3(season=season, timeout=60)
        df = standings.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No standings found for {season}")
        return df
    except Exception as e:
        raise RuntimeError(f"NBA API error: {str(e)}")


@st.cache_data(ttl=900, show_spinner=False)
def get_last_n_games(season: str, n: int, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Return the last N games per team (raw game log rows).
    Cached separately because this is smaller and queried frequently.
    """
    df = _fetch_from_nba_api(season, season_type=season_type).copy()
    if "GAME_DATE" in df.columns:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    return df.sort_values(["TEAM_ID", "GAME_DATE"], ascending=[True, False]).groupby(
        "TEAM_ID", group_keys=False
    ).head(n)


def load_season_data(season: str) -> pd.DataFrame:
    """
    Load and prepare data for a specific season from NBA API.

    This is the main entry point - fetches live data and applies
    all metric calculations to match what charts expect.

    Args:
        season: NBA season in 'YYYY-YY' format (e.g., '2024-25')

    Returns:
        pd.DataFrame: Processed DataFrame ready for queries/charts

    Raises:
        RuntimeError: If API fetch fails
    """
    # Fetch raw data (cached internally)
    df_raw = _fetch_from_nba_api(season)

    # Keep columns we need
    wanted = [
        "SEASON_ID", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME",
        "GAME_ID", "GAME_DATE", "MATCHUP", "WL",
        "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
        "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
        "MIN",
    ]

    # Only keep columns that exist in the response
    available_cols = [col for col in wanted if col in df_raw.columns]
    df = df_raw[available_cols].copy()

    if "MIN" not in df.columns:
        if "MINUTES" in df_raw.columns:
            df["MIN"] = df_raw["MINUTES"]
        else:
            df["MIN"] = 240

    # Apply metrics processing (adds ORtg, DRtg, etc.)
    df = prepare_team_games_for_metrics(df)

    return df


def load_season_data_legacy(season: str) -> pd.DataFrame:
    """Backwards-compatible alias for older imports."""
    return load_season_data(season)


def get_team_stats(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """Public wrapper for cached team stats."""
    return _fetch_team_stats(season, season_type=season_type)


def get_standings(season: str) -> pd.DataFrame:
    """Public wrapper for cached standings."""
    return _fetch_standings(season)


def get_season_info(season: str) -> dict:
    """
    Get metadata about a specific season's data.

    Returns:
        Dict with: teams, games, date_range, total_team_games
    """
    df = load_season_data(season)

    return {
        "teams": sorted(df["TEAM_ABBREVIATION"].unique().tolist()),
        "num_teams": df["TEAM_ABBREVIATION"].nunique(),
        "total_team_games": len(df),
        "date_range": (
            df["GAME_DATE"].min().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].min()) else "Unknown",
            df["GAME_DATE"].max().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].max()) else "Unknown"
        ),
    }


def get_default_season() -> Optional[str]:
    """
    Get the most recent season available.

    Returns:
        Season string (e.g., '2024-25')
    """
    if AVAILABLE_SEASONS:
        return AVAILABLE_SEASONS[0]
    return _current_season_label()


def get_dataset_timestamp(season: str) -> str:
    """Return current timestamp (data is always fresh from API)."""
    from datetime import datetime
    return datetime.now().strftime("%B %d, %Y at %I:%M %p")


# For testing (outside Streamlit)
if __name__ == "__main__":
    # Can't use st.cache_data outside Streamlit, so test differently
    print("Available seasons:", [s for s, _ in get_available_seasons()])
    print("Default season:", get_default_season())
