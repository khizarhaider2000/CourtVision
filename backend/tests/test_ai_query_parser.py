"""
tests/test_ai_query_parser.py

Unit tests for ai_query_parser.py.

Run with:
    cd /path/to/nba-ai-analyzer
    python -m pytest tests/test_ai_query_parser.py -v
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Make sure project root is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_query_parser import (
    _rule_based_parser,
    _rule_based_parser_with_validation,
    parse_natural_language_query,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_key_env() -> dict:
    """Return os.environ without OPENAI_API_KEY."""
    return {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}


def _parse_no_key(query: str) -> dict:
    """Run parse_natural_language_query with no API key (forces rule-based path)."""
    with patch.dict(os.environ, _no_key_env(), clear=True):
        return parse_natural_language_query(query)


def _fake_openai_result(**kwargs) -> dict:
    """Minimal valid QUERY dict that _call_openai_structured might return."""
    base = {
        "result_type": "QUERY",
        "chart_type": "leaderboard",
        "entity": "team",
        "window": "LAST_10",
        "metric": "NET_RTG",
        "top_n": 10,
        "order": "desc",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Parser path selection
# ---------------------------------------------------------------------------

class TestParserPathSelection:

    def test_uses_openai_when_key_present(self):
        """When OPENAI_API_KEY is set, OpenAI path must be attempted and debug reflects it."""
        fake_response = _fake_openai_result()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("ai_query_parser._call_openai_structured", return_value=fake_response) as mock_call:
                result = parse_natural_language_query("top teams")

        mock_call.assert_called_once()
        assert result["_debug"]["openai_used"] is True
        assert result["_debug"]["fallback_used"] is False
        assert result["_debug"]["fallback_reason"] is None

    def test_fallback_when_key_missing(self):
        """When OPENAI_API_KEY is absent, rule-based path must be used."""
        result = _parse_no_key("top teams by net rating")

        assert result["_debug"]["openai_used"] is False
        assert result["_debug"]["fallback_used"] is True
        assert result["_debug"]["fallback_reason"] == "no_api_key"

    def test_fallback_when_openai_raises(self):
        """When OpenAI raises any exception, rule-based fallback must be used."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("ai_query_parser._call_openai_structured", side_effect=Exception("API timeout")):
                result = parse_natural_language_query("top teams by net rating")

        assert result["_debug"]["openai_used"] is False
        assert result["_debug"]["fallback_used"] is True
        assert "openai_error" in result["_debug"]["fallback_reason"]

    def test_openai_result_type_preserved(self):
        """Result returned by OpenAI is passed through unchanged when valid."""
        fake_response = _fake_openai_result(metric="PACE", window="LAST_5")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("ai_query_parser._call_openai_structured", return_value=fake_response):
                result = parse_natural_language_query("pace leaders last 5")

        assert result["result_type"] == "QUERY"
        assert result["metric"] == "PACE"
        assert result["window"] == "LAST_5"

    def test_debug_key_always_present(self):
        """_debug must be present in every return value regardless of path."""
        result = _parse_no_key("show efficiency landscape")
        assert "_debug" in result

        fake_response = _fake_openai_result()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("ai_query_parser._call_openai_structured", return_value=fake_response):
                result2 = parse_natural_language_query("top teams")
        assert "_debug" in result2


# ---------------------------------------------------------------------------
# 2. Common prompts → QUERY  (rule-based, no API key required)
# ---------------------------------------------------------------------------

class TestCommonPromptsReturnQuery:
    """
    At least 70% of typical basketball analytics prompts must return QUERY.
    All tests here run against the rule-based parser (no network needed).
    """

    # ── "top teams lately" ──────────────────────────────────────────────────

    def test_top_teams_lately(self):
        result = _parse_no_key("top teams lately")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"

    def test_top_teams_right_now(self):
        result = _parse_no_key("best teams right now")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"

    def test_top_teams_generic(self):
        result = _parse_no_key("top teams")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"

    def test_top_teams_has_net_rtg_default(self):
        result = _parse_no_key("best teams")
        assert result["result_type"] == "QUERY"
        assert result.get("metric") == "NET_RTG"

    def test_top_teams_lately_window_last10(self):
        result = _parse_no_key("top teams lately")
        assert result.get("window") == "LAST_10"

    # ── "show efficiency landscape" ─────────────────────────────────────────

    def test_show_efficiency_landscape(self):
        result = _parse_no_key("show efficiency landscape")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "scatter"

    def test_efficiency_landscape_axes(self):
        result = _parse_no_key("efficiency landscape")
        assert result.get("x_metric") == "ORtg"
        assert result.get("y_metric") == "DRtg"

    def test_offense_vs_defense_scatter(self):
        """'offense vs defense' must yield scatter, NOT CLARIFY."""
        result = _parse_no_key("offense vs defense")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "scatter"

    def test_offense_vs_defense_season_window(self):
        result = _parse_no_key("show me offense vs defense")
        assert result.get("window") == "SEASON"

    # ── "worst defenses last 5" ─────────────────────────────────────────────

    def test_worst_defenses_last_5(self):
        result = _parse_no_key("worst defenses last 5")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"

    def test_worst_defenses_last_5_window(self):
        result = _parse_no_key("worst defenses last 5")
        assert result.get("window") == "LAST_5"

    def test_worst_defenses_metric_drtg(self):
        result = _parse_no_key("worst defenses last 5")
        assert result.get("metric") == "DRtg"

    def test_worst_defenses_order_asc(self):
        """Worst teams → ascending (lowest values shown first)."""
        result = _parse_no_key("worst 5 defenses")
        assert result.get("order") == "asc"

    # ── additional common prompts ────────────────────────────────────────────

    def test_best_offenses(self):
        result = _parse_no_key("best offenses this season")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"

    def test_best_offenses_metric_ortg(self):
        result = _parse_no_key("best offenses this season")
        assert result.get("metric") == "ORtg"

    def test_best_offenses_season_window(self):
        result = _parse_no_key("best offenses this season")
        assert result.get("window") == "SEASON"

    def test_pace_leaders(self):
        result = _parse_no_key("pace leaders last 10 games")
        assert result["result_type"] == "QUERY"
        assert result.get("metric") == "PACE"
        assert result.get("window") == "LAST_10"

    def test_top_10_net_rating(self):
        result = _parse_no_key("top 10 teams by net rating last 10 games")
        assert result["result_type"] == "QUERY"
        assert result.get("metric") == "NET_RTG"
        assert result.get("top_n") == 10

    def test_playoff_net_rating_detects_playoffs(self):
        result = _parse_no_key("best playoff net rating")
        assert result["result_type"] == "QUERY"
        assert result.get("season_type") == "Playoffs"
        assert result.get("metric") == "NET_RTG"

    def test_playoff_offenses_detects_ortg(self):
        result = _parse_no_key("top playoff offenses")
        assert result["result_type"] == "QUERY"
        assert result.get("season_type") == "Playoffs"
        assert result.get("metric") == "ORtg"

    def test_compare_playoff_teams_detects_playoffs(self):
        result = _parse_no_key("compare Lakers and Nuggets in the playoffs")
        assert result["result_type"] == "QUERY"
        assert result.get("season_type") == "Playoffs"
        assert "LAL" in result.get("teams", [])
        assert "DEN" in result.get("teams", [])

    def test_compare_two_teams(self):
        result = _parse_no_key("compare Lakers and Celtics")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "compare"
        assert "LAL" in result.get("teams", [])
        assert "BOS" in result.get("teams", [])

    def test_compare_teams_window_default(self):
        result = _parse_no_key("compare Lakers and Celtics")
        # no window specified → LAST_10
        assert result.get("window") == "LAST_10"

    def test_scatter_no_metrics_defaults_to_ortg_drtg(self):
        result = _parse_no_key("show me a scatter plot")
        assert result["result_type"] == "QUERY"
        assert result.get("x_metric") == "ORtg"
        assert result.get("y_metric") == "DRtg"

    def test_rank_teams_defaults_to_net_rtg(self):
        result = _parse_no_key("rank teams")
        assert result["result_type"] == "QUERY"
        assert result.get("metric") == "NET_RTG"

    def test_show_top_teams_leaderboard(self):
        result = _parse_no_key("show me the top teams")
        assert result["result_type"] == "QUERY"
        assert result["chart_type"] == "leaderboard"


# ---------------------------------------------------------------------------
# 3. OUT_OF_SCOPE prompts
# ---------------------------------------------------------------------------

class TestOutOfScope:

    def test_player_stats_lebron(self):
        result = _parse_no_key("show me LeBron James stats")
        assert result["result_type"] == "OUT_OF_SCOPE"

    def test_player_stats_curry(self):
        result = _parse_no_key("Steph Curry three point percentage")
        assert result["result_type"] == "OUT_OF_SCOPE"

    def test_live_prediction(self):
        result = _parse_no_key("predict who will win tonight")
        assert result["result_type"] == "OUT_OF_SCOPE"

    def test_clutch_stats(self):
        result = _parse_no_key("show clutch stats for the last 10 games")
        assert result["result_type"] == "OUT_OF_SCOPE"

    def test_shot_chart(self):
        result = _parse_no_key("show me a shot chart for the Warriors")
        assert result["result_type"] == "OUT_OF_SCOPE"


# ---------------------------------------------------------------------------
# 4. CLARIFY — only for compare with no team names
# ---------------------------------------------------------------------------

class TestClarifyOnlyWhenNecessary:

    def test_compare_no_teams_returns_clarify(self):
        result = _parse_no_key("compare two teams")
        assert result["result_type"] == "CLARIFY"

    def test_compare_one_team_returns_clarify(self):
        result = _parse_no_key("compare the Lakers to someone")
        assert result["result_type"] == "CLARIFY"

    def test_vague_leaderboard_returns_query_not_clarify(self):
        """The old parser CLARIFYed here; the new one must return QUERY."""
        result = _parse_no_key("show me the best teams")
        assert result["result_type"] == "QUERY"

    def test_offense_and_defense_returns_query_not_clarify(self):
        """The old parser CLARIFYed for 'offense vs defense'; new one must return QUERY."""
        result = _parse_no_key("show me offense and defense stats")
        assert result["result_type"] == "QUERY"
