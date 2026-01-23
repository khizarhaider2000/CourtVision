# src/query_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, List, Tuple, Dict, Any, TypedDict, NotRequired

import pandas as pd

from metrics import aggregate_team_offense, aggregate_team_with_defense, aggregate_team_complete


ChartType = Literal["leaderboard", "scatter", "compare"]
WindowType = Literal["SEASON", "LAST_5", "LAST_10", "LAST_20"]
EntityType = Literal["team"]

# Keep this list aligned with your v1 scope
TEAM_METRICS_ALLOWLIST = {
    # Ratings table provides these:
    "ORtg", "DRtg", "NET_RTG", "PACE",
    # Offense table provides these:
    "PPG", "eFG", "TS", "AST_RATE", "TOV_RATE",
}

DEFAULTS = {
    "entity": "team",
    "window": "SEASON",
    "top_n": 10,
    "x_metric": "ORtg",
    "y_metric": "DRtg",
    "metric": "NET_RTG",
}

def normalize_window(raw: Any) -> WindowType:
    """
    Accepts lots of common inputs and returns one of:
    SEASON, LAST_5, LAST_10, LAST_20
    """
    if raw is None:
        return "SEASON"

    s = str(raw).strip().upper().replace("-", "_").replace(" ", "_")

    aliases = {
        "SEASON": "SEASON",
        "FULL_SEASON": "SEASON",
        "YTD": "SEASON",

        "LAST5": "LAST_5",
        "LAST_5": "LAST_5",
        "L5": "LAST_5",
        "LAST_FIVE": "LAST_5",

        "LAST10": "LAST_10",
        "LAST_10": "LAST_10",
        "L10": "LAST_10",
        "LAST_TEN": "LAST_10",

        "LAST20": "LAST_20",
        "LAST_20": "LAST_20",
        "L20": "LAST_20",
        "LAST_TWENTY": "LAST_20",
    }

    # Handle cases like "LAST_15" by snapping to nearest supported value (optional)
    if s.startswith("LAST_"):
        try:
            n = int(s.split("_")[1])
            if n <= 5:
                return "LAST_5"
            if n <= 10:
                return "LAST_10"
            return "LAST_20"
        except Exception:
            pass

    if s in aliases:
        return aliases[s]

    raise ValueError(f"Unsupported window: {raw}")



@dataclass(frozen=True)
class ChartSpec:
    chart_type: ChartType
    entity: EntityType = "team"
    window: WindowType = "SEASON"

    # Leaderboard
    metric: Optional[str] = None
    top_n: Optional[int] = None
    order: Literal["asc", "desc"] = "desc"

    # Scatter
    x_metric: Optional[str] = None
    y_metric: Optional[str] = None

    # Compare
    teams: Optional[List[str]] = None  # team abbreviations, e.g. ["BOS", "MIA"]


# Validation function
def validate_spec(spec: ChartSpec) -> None:
    
    #only allows teams for v1
    if spec.entity != "team":
        raise ValueError("v1 supports entity='team' only.")

    if spec.window not in {"SEASON", "LAST_5", "LAST_10", "LAST_20"}:
        raise ValueError(f"Unsupported window: {spec.window}")

    if spec.chart_type == "leaderboard":
        if not spec.metric:
            raise ValueError("Leaderboard requires 'metric'.")
        if spec.metric not in TEAM_METRICS_ALLOWLIST:
            raise ValueError(f"Unsupported metric: {spec.metric}")
        if spec.top_n is None or spec.top_n <= 0:
            raise ValueError("Leaderboard requires top_n > 0.")

    if spec.chart_type == "scatter":
        if not spec.x_metric or not spec.y_metric:
            raise ValueError("Scatter requires x_metric and y_metric.")
        if spec.x_metric not in TEAM_METRICS_ALLOWLIST or spec.y_metric not in TEAM_METRICS_ALLOWLIST:
            raise ValueError("Scatter uses unsupported metric(s).")

    if spec.chart_type == "compare":
        if not spec.teams or len(spec.teams) < 2:
            raise ValueError("Compare requires at least two team abbreviations in 'teams'.")


def _build_explanation(spec: ChartSpec) -> str:
    # Keep this short in v1; you can expand later.
    
    # chart type, what data, time window
    parts = [
        f"Chart type: {spec.chart_type}",
        f"Entity: {spec.entity}",
        f"Window: {spec.window}",
    ]

    if spec.chart_type == "leaderboard":
        parts.append(f"Metric: {spec.metric} (sorted {spec.order}, top_n={spec.top_n})")
        if spec.metric == "NET_RTG":
            parts.append("NET_RTG = ORtg - DRtg")
        if spec.metric in {"ORtg", "DRtg", "NET_RTG", "PACE"}:
            parts.append("Ratings computed from opponent-paired games using estimated possessions.")
        else:
            parts.append("Metric computed from aggregated team box score totals over the window.")

    if spec.chart_type == "scatter":
        parts.append(f"X: {spec.x_metric}, Y: {spec.y_metric}")
        parts.append("Each point is one team aggregated over the selected window.")

    if spec.chart_type == "compare":
        parts.append(f"Teams: {', '.join(spec.teams or [])}")
        parts.append("Comparison uses the same metric definitions as leaderboards.")

    return " | ".join(parts)


def run_query(df_team_games_prepared: pd.DataFrame, spec: ChartSpec) -> Tuple[pd.DataFrame, str]:
    """
    df_team_games_prepared: output of prepare_team_games_for_metrics(df_raw)
    Returns: (result_df, explanation)
    """
    validate_spec(spec)
    explanation = _build_explanation(spec)
    
    # Decide which aggregated table to compute
    if spec.chart_type == "scatter":
        # Scatter plots need ALL metrics available
        base = aggregate_team_complete(df_team_games_prepared, spec.window)
    elif spec.chart_type == "compare":
        # Compare also needs all metrics
        base = aggregate_team_complete(df_team_games_prepared, spec.window)
    elif spec.chart_type == "leaderboard":
        # For leaderboard, use appropriate aggregation based on metric
        if spec.metric in {"ORtg", "DRtg", "NET_RTG", "PACE"}:
            base = aggregate_team_with_defense(df_team_games_prepared, spec.window)
        else:
            # For other metrics, use complete to have everything
            base = aggregate_team_complete(df_team_games_prepared, spec.window)
    else:
        raise ValueError(f"Unhandled chart_type: {spec.chart_type}")

    # Apply chart-specific transformations
    if spec.chart_type == "leaderboard":
        ascending = (spec.order == "asc")
        result = base.sort_values(spec.metric, ascending=ascending).head(spec.top_n).reset_index(drop=True)
        return result, explanation

    if spec.chart_type == "scatter":
        # Scatter uses the full table; caller can plot it
        return base.reset_index(drop=True), explanation

    if spec.chart_type == "compare":
        teams = set([t.upper() for t in (spec.teams or [])])
        result = base[base["TEAM_ABBREVIATION"].isin(teams)].reset_index(drop=True)
        return result, explanation

    raise ValueError(f"Unhandled chart_type: {spec.chart_type}")


def spec_from_dict(d: Dict[str, Any]) -> ChartSpec:
    """
    Utility to convert a dict (e.g., from AI JSON) into ChartSpec with defaults.
    """
    chart_type = d.get("chart_type")
    if chart_type not in {"leaderboard", "scatter", "compare"}:
        raise ValueError("chart_type must be one of: leaderboard, scatter, compare")

    entity = d.get("entity", DEFAULTS["entity"])
    window = normalize_window(d.get("window", DEFAULTS["window"]))

    metric = d.get("metric", DEFAULTS["metric"])
    top_n = d.get("top_n", DEFAULTS["top_n"])
    
    # Smart default for order: ascending for DRtg (lower is better), descending otherwise
    if "order" in d:
        order = d.get("order")
    else:
        order = "asc" if metric == "DRtg" else "desc"

    x_metric = d.get("x_metric", DEFAULTS["x_metric"])
    y_metric = d.get("y_metric", DEFAULTS["y_metric"])

    teams = d.get("teams")

    # Only keep relevant fields based on chart type
    if chart_type == "leaderboard":
        return ChartSpec(chart_type="leaderboard", entity=entity, window=window,
                         metric=metric, top_n=int(top_n), order=order)
    if chart_type == "scatter":
        return ChartSpec(chart_type="scatter", entity=entity, window=window,
                         x_metric=x_metric, y_metric=y_metric)
    if chart_type == "compare":
        return ChartSpec(chart_type="compare", entity=entity, window=window,
                         teams=teams)

    raise ValueError("Invalid chart_type.")
