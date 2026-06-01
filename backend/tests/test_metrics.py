"""
tests/test_metrics.py

Unit tests for metrics.py.
All tests use the deterministic 2-team/3-game fixture from conftest.py.

Expected values (verified by hand):
  POSS per row      = 100.0   (FGA=80, TOV=20, FTA=0, OREB=0 → POSS_BASIC=100; game avg=100)
  BOS ORtg (season) = 112.0   (100 * 336 / 300)
  BOS DRtg (season) = 100.0   (100 * 300 / 300)
  BOS NET_RTG       = +12.0
  LAL NET_RTG       = -12.0
  PACE (both)       = 100.0   (300 poss / 3 games)
  BOS eFG (row)     = 0.55    ((40 + 0.5*8) / 80)
  BOS TS  (row)     = 0.70    (112 / (2*80))
  LAL eFG (row)     = 0.4875  ((36 + 0.5*6) / 80)
  LAL TS  (row)     = 0.625   (100 / (2*80))
"""

import pytest
import pandas as pd

from metrics import (
    normalize_team_game_df,
    add_possessions,
    add_shooting_metrics,
    apply_time_window_team_games,
    aggregate_team_offense,
    pair_team_opponent,
    aggregate_team_with_defense,
    aggregate_team_complete,
    prepare_team_games_for_metrics,
)


# ---------------------------------------------------------------------------
# normalize_team_game_df
# ---------------------------------------------------------------------------

class TestNormalize:

    def test_returns_copy(self, sample_game_log):
        result = normalize_team_game_df(sample_game_log)
        assert result is not sample_game_log

    def test_game_date_is_datetime(self, sample_game_log):
        result = normalize_team_game_df(sample_game_log)
        assert pd.api.types.is_datetime64_any_dtype(result["GAME_DATE"])

    def test_missing_required_column_raises(self, sample_game_log):
        bad = sample_game_log.drop(columns=["PTS"])
        with pytest.raises(ValueError, match="Missing required columns"):
            normalize_team_game_df(bad)

    def test_missing_game_id_raises(self, sample_game_log):
        bad = sample_game_log.drop(columns=["GAME_ID"])
        with pytest.raises(ValueError):
            normalize_team_game_df(bad)


# ---------------------------------------------------------------------------
# add_possessions
# ---------------------------------------------------------------------------

class TestAddPossessions:

    def test_poss_column_created(self, prepared_df):
        assert "POSS" in prepared_df.columns

    def test_poss_basic_temp_column_dropped(self, prepared_df):
        assert "POSS_BASIC" not in prepared_df.columns

    def test_poss_equals_100_every_row(self, prepared_df):
        # FTA=0, OREB=0 → POSS_BASIC = 80+20=100 for every row; game avg = 100
        assert prepared_df["POSS"].tolist() == pytest.approx([100.0] * len(prepared_df))

    def test_poss_no_nulls(self, prepared_df):
        assert prepared_df["POSS"].notna().all()


# ---------------------------------------------------------------------------
# add_shooting_metrics
# ---------------------------------------------------------------------------

class TestAddShootingMetrics:

    def test_efg_column_exists(self, prepared_df):
        assert "eFG" in prepared_df.columns

    def test_ts_column_exists(self, prepared_df):
        assert "TS" in prepared_df.columns

    def test_bos_efg(self, prepared_df):
        bos = prepared_df[prepared_df["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        # (40 + 0.5*8) / 80 = 44/80 = 0.55
        assert bos["eFG"] == pytest.approx(0.55)

    def test_bos_ts(self, prepared_df):
        bos = prepared_df[prepared_df["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        # 112 / (2 * 80) = 112/160 = 0.70
        assert bos["TS"] == pytest.approx(0.70)

    def test_lal_efg(self, prepared_df):
        lal = prepared_df[prepared_df["TEAM_ABBREVIATION"] == "LAL"].iloc[0]
        # (36 + 0.5*6) / 80 = 39/80 = 0.4875
        assert lal["eFG"] == pytest.approx(0.4875)

    def test_lal_ts(self, prepared_df):
        lal = prepared_df[prepared_df["TEAM_ABBREVIATION"] == "LAL"].iloc[0]
        # 100 / (2 * 80) = 0.625
        assert lal["TS"] == pytest.approx(0.625)


# ---------------------------------------------------------------------------
# apply_time_window_team_games
# ---------------------------------------------------------------------------

class TestTimeWindow:

    def test_season_returns_all_rows(self, prepared_df):
        result = apply_time_window_team_games(prepared_df, "SEASON")
        assert len(result) == len(prepared_df)

    def test_last_1_returns_one_row_per_team(self, prepared_df):
        result = apply_time_window_team_games(prepared_df, "LAST_1")
        assert len(result) == 2

    def test_last_2_returns_two_rows_per_team(self, prepared_df):
        result = apply_time_window_team_games(prepared_df, "LAST_2")
        assert len(result) == 4

    def test_last_10_with_only_3_returns_all(self, prepared_df):
        result = apply_time_window_team_games(prepared_df, "LAST_10")
        assert len(result) == len(prepared_df)

    def test_invalid_window_raises(self, prepared_df):
        with pytest.raises(ValueError):
            apply_time_window_team_games(prepared_df, "LAST_MONTH")

    def test_returns_copy_not_original(self, prepared_df):
        result = apply_time_window_team_games(prepared_df, "SEASON")
        assert result is not prepared_df


# ---------------------------------------------------------------------------
# aggregate_team_offense
# ---------------------------------------------------------------------------

class TestAggregateOffense:

    def test_two_teams_returned(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        assert len(agg) == 2

    def test_bos_games_count(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["GAMES"] == 3

    def test_bos_games_last_2(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "LAST_2")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["GAMES"] == 2

    def test_bos_ppg(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["PPG"] == pytest.approx(112.0)

    def test_bos_ortg(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        # 100 * 336 / 300 = 112.0
        assert bos["ORtg"] == pytest.approx(112.0)

    def test_bos_pace(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        # 300 poss / 3 games = 100.0
        assert bos["PACE"] == pytest.approx(100.0)

    def test_required_columns_present(self, prepared_df):
        agg = aggregate_team_offense(prepared_df, "SEASON")
        for col in ["GAMES", "PPG", "ORtg", "eFG", "TS", "AST_RATE", "TOV_RATE", "PACE"]:
            assert col in agg.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# pair_team_opponent
# ---------------------------------------------------------------------------

class TestPairTeamOpponent:

    def test_output_columns(self, prepared_df):
        paired = pair_team_opponent(prepared_df)
        for col in ["TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID",
                    "PTS_FOR", "PTS_AGAINST", "POSS_FOR", "POSS_AGAINST"]:
            assert col in paired.columns, f"Missing column: {col}"

    def test_no_self_matches(self, prepared_df):
        paired = pair_team_opponent(prepared_df)
        assert (paired["TEAM_ID"] != paired["OPP_TEAM_ID"]).all()

    def test_row_count(self, prepared_df):
        # 3 games × 2 teams = 6 paired rows
        paired = pair_team_opponent(prepared_df)
        assert len(paired) == 6

    def test_bos_pts_for(self, prepared_df):
        paired = pair_team_opponent(prepared_df)
        bos_rows = paired[paired["TEAM_ABBREVIATION"] == "BOS"]
        assert (bos_rows["PTS_FOR"] == 112).all()

    def test_bos_pts_against(self, prepared_df):
        paired = pair_team_opponent(prepared_df)
        bos_rows = paired[paired["TEAM_ABBREVIATION"] == "BOS"]
        assert (bos_rows["PTS_AGAINST"] == 100).all()


# ---------------------------------------------------------------------------
# aggregate_team_with_defense
# ---------------------------------------------------------------------------

class TestAggregateWithDefense:

    def test_two_teams_returned(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        assert len(agg) == 2

    def test_bos_ortg(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["ORtg"] == pytest.approx(112.0)

    def test_bos_drtg(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["DRtg"] == pytest.approx(100.0)

    def test_bos_net_rtg(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["NET_RTG"] == pytest.approx(12.0)

    def test_lal_net_rtg(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        lal = agg[agg["TEAM_ABBREVIATION"] == "LAL"].iloc[0]
        assert lal["NET_RTG"] == pytest.approx(-12.0)

    def test_pace(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["PACE"] == pytest.approx(100.0)

    def test_last_2_same_rating_as_season(self, prepared_df):
        # Same stats every game → LAST_2 ratings == SEASON ratings
        agg_s = aggregate_team_with_defense(prepared_df, "SEASON")
        agg_2 = aggregate_team_with_defense(prepared_df, "LAST_2")
        bos_s = agg_s[agg_s["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        bos_2 = agg_2[agg_2["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos_s["NET_RTG"] == pytest.approx(bos_2["NET_RTG"])

    def test_required_columns_present(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        for col in [
            "ORtg",
            "DRtg",
            "NET_RTG",
            "PACE",
            "Opp_TOV%",
            "oreb_pct",
            "dreb_pct",
            "opp_fgpct_rim",
            "clutch_net_rating",
        ]:
            assert col in agg.columns, f"Missing column: {col}"

    def test_opp_tov_pct_is_decimal(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["Opp_TOV%"] == pytest.approx(0.2)

    def test_rebound_rates(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["oreb_pct"] == pytest.approx(0.0)
        assert bos["dreb_pct"] == pytest.approx(1.0)

    def test_unavailable_split_metrics_are_null_placeholders(self, prepared_df):
        agg = aggregate_team_with_defense(prepared_df, "SEASON")
        assert agg["opp_fgpct_rim"].isna().all()
        assert agg["clutch_net_rating"].isna().all()


# ---------------------------------------------------------------------------
# aggregate_team_complete
# ---------------------------------------------------------------------------

class TestAggregateComplete:

    def test_has_both_offense_and_defense_cols(self, prepared_df):
        agg = aggregate_team_complete(prepared_df, "SEASON")
        for col in [
            "ORtg",
            "DRtg",
            "NET_RTG",
            "PACE",
            "eFG",
            "TS",
            "PPG",
            "AST_RATE",
            "TOV_RATE",
            "oreb_pct",
            "dreb_pct",
            "opp_fgpct_rim",
            "clutch_net_rating",
        ]:
            assert col in agg.columns, f"Missing column: {col}"

    def test_two_teams(self, prepared_df):
        agg = aggregate_team_complete(prepared_df, "SEASON")
        assert len(agg) == 2

    def test_bos_net_rtg_complete(self, prepared_df):
        agg = aggregate_team_complete(prepared_df, "SEASON")
        bos = agg[agg["TEAM_ABBREVIATION"] == "BOS"].iloc[0]
        assert bos["NET_RTG"] == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# prepare_team_games_for_metrics (end-to-end pipeline)
# ---------------------------------------------------------------------------

class TestPrepareEndToEnd:

    def test_output_has_poss(self, sample_game_log):
        result = prepare_team_games_for_metrics(sample_game_log)
        assert "POSS" in result.columns

    def test_output_has_efg(self, sample_game_log):
        result = prepare_team_games_for_metrics(sample_game_log)
        assert "eFG" in result.columns

    def test_original_not_mutated(self, sample_game_log):
        _ = prepare_team_games_for_metrics(sample_game_log)
        assert "POSS" not in sample_game_log.columns
