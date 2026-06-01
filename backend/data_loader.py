# data_loader.py
# Loads NBA data from local JSON files when available, falls back to live nba_api.

import functools
import time
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# Pre-fetched data lives here. Populate via: python scripts/fetch_data.py
DATA_DIR = Path(__file__).parent / "data"

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
        def wrapper(*args, **kwargs):
            key = (fn.__name__,) + args + tuple(sorted(kwargs.items()))
            now = _time.time()
            if key in _cache and (now - _cache_times.get(key, 0)) < ttl:
                return _cache[key]
            result = fn(*args, **kwargs)
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

VALID_SEASON_TYPES = {"Regular Season", "Playoffs"}


def validate_season_type(season_type: str) -> str:
    """Return a canonical season type or raise ValueError for API callers."""
    if season_type in VALID_SEASON_TYPES:
        return season_type
    raise ValueError(f"Unsupported season_type '{season_type}'. Use 'Regular Season' or 'Playoffs'.")


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
    Internal: Load team game logs — from local JSON file if available, otherwise live NBA API.
    Cached in-process for 1 hour.
    """
    season_type = validate_season_type(season_type)
    data_file = DATA_DIR / f"{season}.json"
    if season_type == "Playoffs":
        data_file = DATA_DIR / "playoffs" / f"{season}.json"
    if data_file.exists():
        df = pd.read_json(data_file, orient="records")
        if not df.empty:
            df["SEASON_TYPE"] = season_type
            return df

    from nba_api.stats.endpoints import LeagueGameLog

    def _call():
        time.sleep(0.3)
        lg = LeagueGameLog(season=season, season_type_all_star=season_type, timeout=30)
        df = lg.get_data_frames()[0].copy()
        if df.empty:
            raise ValueError(f"No games found for {season} {season_type}")
        df["SEASON_TYPE"] = season_type
        return df

    return _nba_api_call(_call)


@_ttl_cache(ttl=3600)
def _fetch_team_stats(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """
    Internal: Fetch season-level team stats from NBA API.
    Cached for 1 hour to avoid rate limiting.
    """
    season_type = validate_season_type(season_type)
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


def load_season_data(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
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
    season_type = validate_season_type(season_type)
    df_raw = _fetch_from_nba_api(season, season_type=season_type)

    wanted = [
        "SEASON_ID", "SEASON_TYPE", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME",
        "GAME_ID", "GAME_DATE", "MATCHUP", "WL",
        "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
        "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
        "MIN",
    ]

    available_cols = [col for col in wanted if col in df_raw.columns]
    df = df_raw[available_cols].copy()
    df["SEASON_TYPE"] = season_type

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


def _multi_col(df: pd.DataFrame, top: str, name: str):
    """Return a Series from flat or NBA multi-level response columns."""
    if isinstance(df.columns, pd.MultiIndex):
        key = (top, name)
        if key in df.columns:
            return df[key]
        for col in df.columns:
            if col[-1] == name:
                return df[col]
        return None

    if name in df.columns:
        return df[name]
    return None


def _restricted_area_fg_pct(df: pd.DataFrame):
    if isinstance(df.columns, pd.MultiIndex):
        for key in (("Restricted Area", "OPP_FG_PCT"), ("Restricted Area", "FG_PCT")):
            if key in df.columns:
                return df[key]
        return None

    fg_pct_positions = [
        i for i, col in enumerate(df.columns) if col in {"OPP_FG_PCT", "FG_PCT"}
    ]
    if fg_pct_positions:
        return df.iloc[:, fg_pct_positions[0]]
    return None


@_ttl_cache(ttl=3600)
def _fetch_opp_fgpct_rim(season: str, season_type: str) -> pd.DataFrame:
    """Fetch opponent restricted-area FG% from NBA shot-location splits."""
    season_type = validate_season_type(season_type)
    from nba_api.stats.endpoints import LeagueDashTeamShotLocations

    def _call():
        time.sleep(0.3)
        shot_locations = LeagueDashTeamShotLocations(
            season=season,
            season_type_all_star=season_type,
            measure_type_simple="Opponent",
            distance_range="By Zone",
            timeout=30,
        )
        df = shot_locations.get_data_frames()[0].copy()
        team_id = _multi_col(df, "", "TEAM_ID")
        fg_pct = _restricted_area_fg_pct(df)
        if df.empty or team_id is None or fg_pct is None:
            raise ValueError(f"No opponent rim FG% found for {season} {season_type}")
        return pd.DataFrame({
            "TEAM_ID": team_id.astype(int),
            "opp_fgpct_rim": pd.to_numeric(fg_pct, errors="coerce"),
        })

    return _nba_api_call(_call)


@_ttl_cache(ttl=3600)
def _fetch_clutch_net_rating(season: str, season_type: str) -> pd.DataFrame:
    """Fetch clutch net rating: score margin <= 5, last 5 minutes."""
    season_type = validate_season_type(season_type)
    from nba_api.stats.endpoints import LeagueDashTeamClutch

    def _call():
        time.sleep(0.3)
        clutch = LeagueDashTeamClutch(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Advanced",
            clutch_time="Last 5 Minutes",
            point_diff="5",
            timeout=30,
        )
        df = clutch.get_data_frames()[0].copy()
        if df.empty or "TEAM_ID" not in df.columns or "NET_RATING" not in df.columns:
            raise ValueError(f"No clutch net rating found for {season} {season_type}")
        return pd.DataFrame({
            "TEAM_ID": df["TEAM_ID"].astype(int),
            "clutch_net_rating": pd.to_numeric(df["NET_RATING"], errors="coerce"),
        })

    return _nba_api_call(_call)


def merge_supplemental_team_metrics(
    result: pd.DataFrame,
    season: str,
    season_type: str,
    requested_metrics: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Merge optional NBA split metrics onto an aggregated team result.

    These endpoints can be unavailable on some hosts/seasons, so failures leave
    the nullable placeholder columns intact instead of failing the whole query.
    """
    result = result.copy()
    requested_metrics = requested_metrics or {"opp_fgpct_rim", "clutch_net_rating"}

    if "opp_fgpct_rim" in requested_metrics:
        try:
            result = result.drop(columns=["opp_fgpct_rim"], errors="ignore").merge(
                _fetch_opp_fgpct_rim(season, season_type),
                on="TEAM_ID",
                how="left",
            )
        except RuntimeError:
            result["opp_fgpct_rim"] = float("nan")

    if "clutch_net_rating" in requested_metrics:
        try:
            result = result.drop(columns=["clutch_net_rating"], errors="ignore").merge(
                _fetch_clutch_net_rating(season, season_type),
                on="TEAM_ID",
                how="left",
            )
        except RuntimeError:
            result["clutch_net_rating"] = float("nan")

    return result


def get_standings(season: str) -> pd.DataFrame:
    """Public wrapper for cached standings."""
    return _fetch_standings(season)


def get_season_info(season: str, season_type: str = "Regular Season") -> dict:
    """Get metadata about a specific season's data."""
    season_type = validate_season_type(season_type)
    df = load_season_data(season, season_type=season_type)
    return {
        "season_type": season_type,
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
