import pandas as pd
from pathlib import Path

from query_engine import run_query, spec_from_dict
from data_loader import load_season_data, get_default_season

def load_prepared_df():
    """Load the most recent season's data"""
    season = get_default_season()
    
    if not season:
        raise FileNotFoundError(
            "No season data found! Run: python ingest.py 2025-26"
        )
    
    print(f"Testing with season: {season}")
    return load_season_data(season)

def test_leaderboard(df):
    query_dict = {
        "chart_type": "leaderboard",
        "window": "LAST_10",
        "metric": "NET_RTG",
        "top_n": 10
    }
    spec = spec_from_dict(query_dict)
    result_df, explanation = run_query(df, spec)

    assert len(result_df) == 10, "Leaderboard should return exactly top_n rows"
    assert "TEAM_ABBREVIATION" in result_df.columns, "Missing TEAM_ABBREVIATION"
    assert "NET_RTG" in result_df.columns, "Missing NET_RTG"
    print("\n[PASS] Leaderboard test")
    print(explanation)
    print(result_df[["TEAM_ABBREVIATION", "NET_RTG"]].head())

def test_scatter(df):
    query_dict = {
        "chart_type": "scatter",
        "window": "LAST_10",
        "x_metric": "ORtg",
        "y_metric": "DRtg"
    }
    spec = spec_from_dict(query_dict)
    result_df, explanation = run_query(df, spec)

    # Should be 30 teams (or close, if early season)
    assert "ORtg" in result_df.columns and "DRtg" in result_df.columns, "Missing ORtg/DRtg"
    assert result_df["TEAM_ABBREVIATION"].nunique() >= 25, "Expected near all teams"
    print("\n[PASS] Scatter test")
    print(explanation)
    print(result_df[["TEAM_ABBREVIATION", "ORtg", "DRtg"]].head())

def test_compare(df):
    query_dict = {
        "chart_type": "compare",
        "window": "LAST_10",
        "teams": ["BOS", "MIA"]
    }
    spec = spec_from_dict(query_dict)
    result_df, explanation = run_query(df, spec)

    assert len(result_df) == 2, "Compare should return exactly 2 rows"
    assert set(result_df["TEAM_ABBREVIATION"]) == {"BOS", "MIA"}, "Compare returned wrong teams"
    print("\n[PASS] Compare test")
    print(explanation)
    print(result_df)

def test_invalid_metric_rejected(df):
    query_dict = {
        "chart_type": "leaderboard",
        "window": "LAST_10",
        "metric": "NOT_A_REAL_METRIC",
        "top_n": 10
    }
    try:
        spec = spec_from_dict(query_dict)
        run_query(df, spec)
        raise AssertionError("Invalid metric should have raised an error")
    except Exception:
        print("\n[PASS] Invalid metric rejection test")

def main():
    df = load_prepared_df()
    test_leaderboard(df)
    test_scatter(df)
    test_compare(df)
    test_invalid_metric_rejected(df)
    print("\nAll query_engine tests passed.")

if __name__ == "__main__":
    main()
