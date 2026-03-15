"""
tests/test_query_engine.py

Unit tests for query_engine.py — normalize_window, spec_from_dict,
validate_spec, and run_query — using the deterministic fixture from conftest.py.
"""

import pytest

from query_engine import (
    ChartSpec,
    normalize_window,
    spec_from_dict,
    validate_spec,
    run_query,
)


# ---------------------------------------------------------------------------
# normalize_window
# ---------------------------------------------------------------------------

class TestNormalizeWindow:

    def test_none_returns_season(self):
        assert normalize_window(None) == "SEASON"

    def test_season_string(self):
        assert normalize_window("SEASON") == "SEASON"

    def test_full_season_alias(self):
        assert normalize_window("FULL_SEASON") == "SEASON"

    def test_ytd_alias(self):
        assert normalize_window("YTD") == "SEASON"

    def test_last_5(self):
        assert normalize_window("LAST_5") == "LAST_5"

    def test_l5_alias(self):
        assert normalize_window("L5") == "LAST_5"

    def test_last_10(self):
        assert normalize_window("LAST_10") == "LAST_10"

    def test_l10_alias(self):
        assert normalize_window("L10") == "LAST_10"

    def test_last_20(self):
        assert normalize_window("LAST_20") == "LAST_20"

    def test_l20_alias(self):
        assert normalize_window("L20") == "LAST_20"

    def test_last_3_snaps_to_last_5(self):
        assert normalize_window("LAST_3") == "LAST_5"

    def test_last_7_snaps_to_last_10(self):
        assert normalize_window("LAST_7") == "LAST_10"

    def test_last_15_snaps_to_last_20(self):
        assert normalize_window("LAST_15") == "LAST_20"

    def test_case_insensitive(self):
        assert normalize_window("last_10") == "LAST_10"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_window("LAST_WEEK")

    def test_unknown_string_raises(self):
        with pytest.raises(ValueError):
            normalize_window("MONTHLY")


# ---------------------------------------------------------------------------
# spec_from_dict
# ---------------------------------------------------------------------------

class TestSpecFromDict:

    def test_leaderboard_basic(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "NET_RTG", "top_n": 5, "window": "LAST_10"})
        assert spec.chart_type == "leaderboard"
        assert spec.metric == "NET_RTG"
        assert spec.top_n == 5
        assert spec.window == "LAST_10"

    def test_leaderboard_default_window(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "ORtg", "top_n": 10})
        assert spec.window == "SEASON"

    def test_leaderboard_top_n_cast_to_int(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "NET_RTG", "top_n": "5"})
        assert spec.top_n == 5
        assert isinstance(spec.top_n, int)

    def test_drtg_order_defaults_asc(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "DRtg", "top_n": 5})
        assert spec.order == "asc"

    def test_non_drtg_order_defaults_desc(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "NET_RTG", "top_n": 5})
        assert spec.order == "desc"

    def test_explicit_order_overrides_default(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "DRtg", "top_n": 5, "order": "desc"})
        assert spec.order == "desc"

    def test_scatter_basic(self):
        spec = spec_from_dict({"chart_type": "scatter", "x_metric": "ORtg", "y_metric": "DRtg"})
        assert spec.chart_type == "scatter"
        assert spec.x_metric == "ORtg"
        assert spec.y_metric == "DRtg"

    def test_scatter_default_metrics(self):
        spec = spec_from_dict({"chart_type": "scatter"})
        assert spec.x_metric == "ORtg"
        assert spec.y_metric == "DRtg"

    def test_compare_basic(self):
        spec = spec_from_dict({"chart_type": "compare", "teams": ["BOS", "LAL"]})
        assert spec.chart_type == "compare"
        assert "BOS" in spec.teams
        assert "LAL" in spec.teams

    def test_compare_default_window(self):
        spec = spec_from_dict({"chart_type": "compare", "teams": ["BOS", "LAL"]})
        assert spec.window == "SEASON"

    def test_window_aliased_correctly(self):
        spec = spec_from_dict({"chart_type": "leaderboard", "metric": "NET_RTG",
                                "top_n": 5, "window": "L10"})
        assert spec.window == "LAST_10"

    def test_invalid_chart_type_raises(self):
        with pytest.raises(ValueError):
            spec_from_dict({"chart_type": "bar_chart"})

    def test_missing_chart_type_raises(self):
        with pytest.raises(ValueError):
            spec_from_dict({"metric": "NET_RTG"})


# ---------------------------------------------------------------------------
# validate_spec
# ---------------------------------------------------------------------------

class TestValidateSpec:

    def test_valid_leaderboard(self):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=10, order="desc")
        validate_spec(spec)  # must not raise

    def test_leaderboard_missing_metric_raises(self):
        spec = ChartSpec(chart_type="leaderboard", metric=None, top_n=10)
        with pytest.raises(ValueError, match="metric"):
            validate_spec(spec)

    def test_leaderboard_unsupported_metric_raises(self):
        spec = ChartSpec(chart_type="leaderboard", metric="POINTS_SCORED", top_n=10)
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_leaderboard_zero_top_n_raises(self):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=0)
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_leaderboard_negative_top_n_raises(self):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=-1)
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_all_allowlisted_metrics_valid(self):
        from query_engine import TEAM_METRICS_ALLOWLIST
        for metric in TEAM_METRICS_ALLOWLIST:
            spec = ChartSpec(chart_type="leaderboard", metric=metric, top_n=5)
            validate_spec(spec)  # must not raise

    def test_valid_scatter(self):
        spec = ChartSpec(chart_type="scatter", x_metric="ORtg", y_metric="DRtg")
        validate_spec(spec)  # must not raise

    def test_scatter_missing_x_raises(self):
        spec = ChartSpec(chart_type="scatter", x_metric=None, y_metric="DRtg")
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_scatter_missing_y_raises(self):
        spec = ChartSpec(chart_type="scatter", x_metric="ORtg", y_metric=None)
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_scatter_invalid_metric_raises(self):
        spec = ChartSpec(chart_type="scatter", x_metric="ORtg", y_metric="BOGUS")
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_valid_compare(self):
        spec = ChartSpec(chart_type="compare", teams=["BOS", "LAL"])
        validate_spec(spec)  # must not raise

    def test_compare_one_team_raises(self):
        spec = ChartSpec(chart_type="compare", teams=["BOS"])
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_compare_no_teams_raises(self):
        spec = ChartSpec(chart_type="compare", teams=None)
        with pytest.raises(ValueError):
            validate_spec(spec)

    def test_compare_empty_list_raises(self):
        spec = ChartSpec(chart_type="compare", teams=[])
        with pytest.raises(ValueError):
            validate_spec(spec)


# ---------------------------------------------------------------------------
# run_query
# ---------------------------------------------------------------------------

class TestRunQuery:

    def test_leaderboard_returns_dataframe_and_str(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=5)
        result, explanation = run_query(prepared_df, spec)
        import pandas as pd
        assert isinstance(result, pd.DataFrame)
        assert isinstance(explanation, str)

    def test_leaderboard_top_n_respected(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=1)
        result, _ = run_query(prepared_df, spec)
        assert len(result) == 1

    def test_leaderboard_desc_bos_first(self, prepared_df):
        # BOS NET_RTG=+12, LAL=-12 → BOS first when sorted desc
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=2, order="desc")
        result, _ = run_query(prepared_df, spec)
        assert result.iloc[0]["TEAM_ABBREVIATION"] == "BOS"

    def test_leaderboard_asc_lal_first(self, prepared_df):
        # Ascending → worst (LAL -12) first
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=2, order="asc")
        result, _ = run_query(prepared_df, spec)
        assert result.iloc[0]["TEAM_ABBREVIATION"] == "LAL"

    def test_leaderboard_net_rtg_values(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=2, order="desc")
        result, _ = run_query(prepared_df, spec)
        bos_row = result[result["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos_row["NET_RTG"] == pytest.approx(12.0)

    def test_scatter_returns_all_teams(self, prepared_df):
        spec = ChartSpec(chart_type="scatter", x_metric="ORtg", y_metric="DRtg")
        result, _ = run_query(prepared_df, spec)
        assert len(result) == 2

    def test_scatter_has_metric_columns(self, prepared_df):
        spec = ChartSpec(chart_type="scatter", x_metric="ORtg", y_metric="DRtg")
        result, _ = run_query(prepared_df, spec)
        assert "ORtg" in result.columns
        assert "DRtg" in result.columns

    def test_compare_filters_teams(self, prepared_df):
        spec = ChartSpec(chart_type="compare", teams=["BOS", "LAL"])
        result, _ = run_query(prepared_df, spec)
        assert set(result["TEAM_ABBREVIATION"]) == {"BOS", "LAL"}

    def test_compare_uppercase_normalisation(self, prepared_df):
        # run_query upcases teams internally
        spec = ChartSpec(chart_type="compare", teams=["bos", "lal"])
        result, _ = run_query(prepared_df, spec)
        assert len(result) == 2

    def test_explanation_non_empty(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=5)
        _, explanation = run_query(prepared_df, spec)
        assert len(explanation) > 0

    def test_explanation_contains_chart_type(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=5)
        _, explanation = run_query(prepared_df, spec)
        assert "leaderboard" in explanation.lower()

    def test_window_last_10_with_3_games_returns_both_teams(self, prepared_df):
        # Only 3 games exist, LAST_10 should return data for both teams
        spec = ChartSpec(chart_type="leaderboard", metric="NET_RTG", top_n=5, window="LAST_10")
        result, _ = run_query(prepared_df, spec)
        assert len(result) == 2

    def test_invalid_spec_raises(self, prepared_df):
        spec = ChartSpec(chart_type="leaderboard", metric=None, top_n=5)
        with pytest.raises(ValueError):
            run_query(prepared_df, spec)
