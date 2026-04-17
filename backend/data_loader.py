# data_loader.py
# Fetches NBA data LIVE from nba_api - no local files required

import functools
import time
import time as _time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from metrics import prepare_team_games_for_metrics
from nba_api.stats.library.http import NBAStatsHTTP

# NBA API requires browser-like headers or it times out/blocks requests
NBAStatsHTTP.HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

# ---------------------------------------------------------------------------
# Simple in-process TTL cache (replaces Streamlit's @st.cache_data)
# ---------------------------------------------------------------------------

_cache: Dict = {}
_cache_times: Dict = {}


def _ttl_cache(ttl: int):
    """Lightweight TTL cache decorator."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args):
            key = (fn.__name__,) + args
            now = _time.time()
            if key in _cache and (now - _cache_times.get(key, 0)) < ttl:
                return _cache[key]
            result = fn(*args)
            _cache[key] = result
            _cache_times[key] = now
            return result

        return wrapper

    return decorator


def _nba_api_call(fn, max_retries: int = 3):
    """
    Call an NBA API function with exponential backoff retries.
    stats.nba.com frequently times out on cold requests - retrying usually succeeds.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"NBA API error: {str(e)}")
            wait = 1.0 + attempt  # 1s, 2s
            time.sleep(wait)


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


@_ttl_cache(ttl=3600)
def _fetch_from_nba_api(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Internal: Fetch team game logs from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueGameLog

    def _call():
        time.sleep(0.3)
        lg = LeagueGameLog(season=season, season_type_all_star=season_type, timeout=30)
        df = lg.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No games found for {season} {season_type}")
        return df

    return _nba_api_call(_call)


@_ttl_cache(ttl=3600)
def _fetch_team_stats(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Internal: Fetch season-level team stats from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueDashTeamStats

    def _call():
        time.sleep(0.3)
        stats = LeagueDashTeamStats(season=season, season_type_all_star=season_type, timeout=30)
        df = stats.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No team stats found for {season} {season_type}")
        return df

    return _nba_api_call(_call)


@_ttl_cache(ttl=3600)
def _fetch_standings(season: str) -> pd.DataFrame:
    """
    Internal: Fetch league standings from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    from nba_api.stats.endpoints import LeagueStandingsV3

    def _call():
        time.sleep(0.3)
        standings = LeagueStandingsV3(season=season, timeout=30)
        df = standings.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No standings found for {season}")
        return df

    return _nba_api_call(_call)


@_ttl_cache(ttl=900)
def get_last_n_games(season: str, n: int, season_type: str = "Regular Season") -> pd.DataFrame:
    """Return the last N games per team (raw game log rows)."""
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
    df_raw = _fetch_from_nba_api(season)

    wanted = [
        "SEASON_ID", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME",
        "GAME_ID", "GAME_DATE", "MATCHUP", "WL",
        "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
        "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
        "MIN",
    ]

    available_cols = [col for col in wanted if col in df_raw.columns]
    df = df_raw[available_cols].copy()

    if "MIN" not in df.columns:
        if "MINUTES" in df_raw.columns:
            df["MIN"] = df_raw["MINUTES"]
        else:
            df["MIN"] = 240

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
    """Get metadata about a specific season's data."""
    df = load_season_data(season)
    return {
        "teams": sorted(df["TEAM_ABBREVIATION"].unique().tolist()),
        "num_teams": df["TEAM_ABBREVIATION"].nunique(),
        "total_team_games": len(df),
        "date_range": (
            df["GAME_DATE"].min().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].min()) else "Unknown",
            df["GAME_DATE"].max().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].max()) else "Unknown",
        ),
    }


def get_default_season() -> Optional[str]:
    """Get the most recent season available."""
    if AVAILABLE_SEASONS:
        return AVAILABLE_SEASONS[0]
    return _current_season_label()


def get_dataset_timestamp(season: str) -> str:
    """Return current timestamp (data is always fresh from API)."""
    return datetime.now().strftime("%B %d, %Y at %I:%M %p")
