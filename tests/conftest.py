"""
tests/conftest.py

Shared fixtures for metric and query-engine tests.

Design notes:
- Two teams (BOS, LAL) play 3 games each against each other.
- FTA=0, OREB=0 → POSS_BASIC = FGA + TOV = 80 + 20 = 100 exactly per team per game.
- Both teams per game have POSS_BASIC=100, so game-averaged POSS=100.0 (no floating-point error).
- BOS scores 112 per game; LAL scores 100 per game → deterministic, integer-friendly ratings:
    BOS: ORtg=112.0, DRtg=100.0, NET_RTG=+12.0
    LAL: ORtg=100.0, DRtg=112.0, NET_RTG=-12.0
    PACE (both): 100.0
"""

import pandas as pd
import pytest

_GAME_ROWS = [
    # BOS rows
    {
        "GAME_ID": "G001", "GAME_DATE": "2025-01-01",
        "TEAM_ID": 1610612738, "TEAM_ABBREVIATION": "BOS",
        "PTS": 112, "FGA": 80, "FGM": 40, "FG3A": 20, "FG3M": 8,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 35,
        "AST": 25, "TOV": 20, "MIN": 240,
    },
    {
        "GAME_ID": "G002", "GAME_DATE": "2025-01-03",
        "TEAM_ID": 1610612738, "TEAM_ABBREVIATION": "BOS",
        "PTS": 112, "FGA": 80, "FGM": 40, "FG3A": 20, "FG3M": 8,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 35,
        "AST": 25, "TOV": 20, "MIN": 240,
    },
    {
        "GAME_ID": "G003", "GAME_DATE": "2025-01-05",
        "TEAM_ID": 1610612738, "TEAM_ABBREVIATION": "BOS",
        "PTS": 112, "FGA": 80, "FGM": 40, "FG3A": 20, "FG3M": 8,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 35,
        "AST": 25, "TOV": 20, "MIN": 240,
    },
    # LAL rows
    {
        "GAME_ID": "G001", "GAME_DATE": "2025-01-01",
        "TEAM_ID": 1610612747, "TEAM_ABBREVIATION": "LAL",
        "PTS": 100, "FGA": 80, "FGM": 36, "FG3A": 20, "FG3M": 6,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 38,
        "AST": 22, "TOV": 20, "MIN": 240,
    },
    {
        "GAME_ID": "G002", "GAME_DATE": "2025-01-03",
        "TEAM_ID": 1610612747, "TEAM_ABBREVIATION": "LAL",
        "PTS": 100, "FGA": 80, "FGM": 36, "FG3A": 20, "FG3M": 6,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 38,
        "AST": 22, "TOV": 20, "MIN": 240,
    },
    {
        "GAME_ID": "G003", "GAME_DATE": "2025-01-05",
        "TEAM_ID": 1610612747, "TEAM_ABBREVIATION": "LAL",
        "PTS": 100, "FGA": 80, "FGM": 36, "FG3A": 20, "FG3M": 6,
        "FTA": 0, "FTM": 0, "OREB": 0, "DREB": 38,
        "AST": 22, "TOV": 20, "MIN": 240,
    },
]


@pytest.fixture(scope="session")
def sample_game_log() -> pd.DataFrame:
    """Raw game-log DataFrame (pre-metrics)."""
    return pd.DataFrame(_GAME_ROWS)


@pytest.fixture(scope="session")
def prepared_df(sample_game_log) -> pd.DataFrame:
    """Game-log DataFrame after normalize + possessions + shooting metrics."""
    from metrics import prepare_team_games_for_metrics
    return prepare_team_games_for_metrics(sample_game_log)
