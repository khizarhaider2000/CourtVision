# ai_query_parser.py
# Converts natural language queries into structured QuerySpec dictionaries.
# Uses OpenAI structured outputs when OPENAI_API_KEY is set; falls back to
# a rule-based parser on any API/parse failure.

import json
import logging
import os
import re
from typing import List, Literal, Optional, TypedDict

# Load .env for local dev (no-op if already set or file missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

ResultType = Literal["QUERY", "CLARIFY", "OUT_OF_SCOPE"]
ChartType = Literal["leaderboard", "scatter", "compare"]
WindowType = Literal["SEASON", "LAST_5", "LAST_10", "LAST_20"]
OrderType = Literal["asc", "desc"]
SeasonType = Literal["Regular Season", "Playoffs"]


class QuerySpec(TypedDict, total=False):
    """
    Structured response from the parser.

    result_type is always present:
      QUERY        — valid, includes chart_type / window / metric fields
      CLARIFY      — needs more info, includes message
      OUT_OF_SCOPE — unsupported request, includes message

    _debug is always present and contains:
      openai_used     (bool)
      fallback_used   (bool)
      fallback_reason (str | None)  — None when OpenAI succeeded
    """
    result_type: ResultType

    # QUERY fields
    chart_type: ChartType
    entity: Literal["team"]
    window: WindowType
    metric: str
    x_metric: str
    y_metric: str
    top_n: int
    order: OrderType
    teams: List[str]
    compare_metrics: List[str]
    season: str
    season_type: SeasonType

    # CLARIFY / OUT_OF_SCOPE
    message: str

    # Internal — always injected by parse_natural_language_query()
    _debug: dict


# ---------------------------------------------------------------------------
# OpenAI JSON schema (unchanged — keeps app contract stable)
# ---------------------------------------------------------------------------

QUERY_SPEC_JSON_SCHEMA: dict = {
    "name": "QuerySpec",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "result_type": {
                "type": "string",
                "enum": ["QUERY", "CLARIFY", "OUT_OF_SCOPE"],
                "description": "QUERY for valid requests, CLARIFY only when truly ambiguous, OUT_OF_SCOPE for unsupported"
            },
            "chart_type": {
                "type": ["string", "null"],
                "enum": ["leaderboard", "scatter", "compare", None],
            },
            "entity": {
                "type": ["string", "null"],
                "enum": ["team", None],
            },
            "window": {
                "type": ["string", "null"],
                "enum": ["SEASON", "LAST_5", "LAST_10", "LAST_20", None],
            },
            "metric": {"type": ["string", "null"]},
            "x_metric": {"type": ["string", "null"]},
            "y_metric": {"type": ["string", "null"]},
            "top_n": {"type": ["integer", "null"]},
            "order": {
                "type": ["string", "null"],
                "enum": ["asc", "desc", None],
            },
            "teams": {
                "type": ["array", "null"],
                "items": {"type": "string"},
            },
            "season": {"type": ["string", "null"]},
            "season_type": {
                "type": ["string", "null"],
                "enum": ["Regular Season", "Playoffs", None],
            },
            "message": {"type": ["string", "null"]},
        },
        "required": [
            "result_type", "chart_type", "entity", "window",
            "metric", "x_metric", "y_metric", "top_n", "order",
            "teams", "season", "season_type", "message",
        ],
    },
}


# ---------------------------------------------------------------------------
# System prompt — generous defaults, CLARIFY is rare
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a query parser for an NBA team analytics app. Convert natural language into structured JSON. Be generous — prefer QUERY with sensible defaults over asking for clarification.

CHART TYPES: leaderboard, scatter, compare
METRICS: ORtg, DRtg, NET_RTG, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE, Opp_TOV%
WINDOWS: SEASON, LAST_5, LAST_10, LAST_20
SEASON TYPES: Regular Season, Playoffs
TEAMS: ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WAS

DEFAULT RULES — fill in missing details silently (never ask):
• No metric specified for leaderboard → NET_RTG
• No window specified → LAST_10
• No top_n → 10
• "best/top teams" → leaderboard, NET_RTG, LAST_10, order=desc
• "worst/bottom teams" → leaderboard, NET_RTG, LAST_10, order=asc
• "best defense" / "top defenses" → leaderboard, DRtg, LAST_10, order=asc  (lower DRtg = better)
• "best offense" / "top offenses" → leaderboard, ORtg, LAST_10, order=desc
• "efficiency landscape" / "offense vs defense" / "ORtg vs DRtg" → scatter, x=ORtg, y=DRtg, SEASON
• scatter with no metrics specified → ORtg vs DRtg, SEASON
• "lately" / "recently" → window=LAST_10
• "this season" / "season" / "all season" → window=SEASON
• "playoff" / "playoffs" / "postseason" / "finals" → season_type=Playoffs
• No playoff/postseason wording → season_type=Regular Season

RETURN QUERY (the default — be generous):
• Any leaderboard / scatter / compare intent, even vague → fill missing fields with defaults above
• "top teams" → leaderboard, NET_RTG, LAST_10, desc, 10
• "top teams lately" → leaderboard, NET_RTG, LAST_10, desc, 10
• "best teams right now" → leaderboard, NET_RTG, LAST_10, desc, 10
• "worst teams" → leaderboard, NET_RTG, LAST_10, asc, 10
• "worst 5 defenses" → leaderboard, DRtg, LAST_10, asc, 5
• "show efficiency" → scatter, ORtg, DRtg, SEASON
• "pace leaders last 5" → leaderboard, PACE, LAST_5, desc, 10
• "compare Lakers Celtics" → compare, [LAL, BOS], LAST_10
• "top playoff offenses" → leaderboard, ORtg, LAST_10, Playoffs
• "best playoff net rating" → leaderboard, NET_RTG, LAST_10, Playoffs
• "compare Lakers and Nuggets in the playoffs" → compare, [LAL, DEN], LAST_10, Playoffs

RETURN CLARIFY only for these rare cases:
• compare chart where ZERO team names can be identified from the query
• Two genuinely conflicting chart types in a single query

RETURN OUT_OF_SCOPE for:
• Player stats (not team stats) — e.g. "LeBron's points", "Curry shooting %"
• Live betting odds or real-time predictions — e.g. "who will win tonight"
• Custom date ranges — e.g. "since Christmas", "after January 1"
• Clutch / 4th quarter / situational splits
• Play-by-play, shot charts, shot locations
NEVER return CLARIFY just because metric or window is unspecified — apply the defaults above and return QUERY."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_natural_language_query(user_query: str) -> QuerySpec:
    """
    Parse natural language into a structured QuerySpec dict.

    When OPENAI_API_KEY is set, always attempts the OpenAI path first.
    Falls back to the rule-based parser only on actual API / parse failure.

    The returned dict always contains a '_debug' key:
        {
            "openai_used":     bool,
            "fallback_used":   bool,
            "fallback_reason": str | None,   # None when OpenAI succeeded
        }
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        # --- Primary path: OpenAI ---
        try:
            result = _call_openai_structured(user_query, api_key)
            logger.info("ai_query_parser: OpenAI path used successfully")

            # Validate QUERY results against query_engine rules
            if result.get("result_type") == "QUERY":
                validation_error = _validate_query_spec(result)
                if validation_error is not None:
                    validation_error["_debug"] = {
                        "openai_used": True,
                        "fallback_used": False,
                        "fallback_reason": "validation_failed",
                    }
                    return validation_error

            result["_debug"] = {
                "openai_used": True,
                "fallback_used": False,
                "fallback_reason": None,
            }
            return result

        except Exception as exc:
            fallback_reason = f"openai_error: {type(exc).__name__}: {exc}"
            logger.warning("ai_query_parser: OpenAI failed — using rule-based fallback. %s", fallback_reason)
            result = _rule_based_parser_with_validation(user_query)
            result["_debug"] = {
                "openai_used": False,
                "fallback_used": True,
                "fallback_reason": fallback_reason,
            }
            return result

    else:
        # --- Fallback path: rule-based (no API key) ---
        logger.info("ai_query_parser: No OPENAI_API_KEY — using rule-based parser")
        result = _rule_based_parser_with_validation(user_query)
        result["_debug"] = {
            "openai_used": False,
            "fallback_used": True,
            "fallback_reason": "no_api_key",
        }
        return result


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _call_openai_structured(user_query: str, api_key: str) -> QuerySpec:
    """Call OpenAI with json_schema response format. Returns cleaned QuerySpec dict."""
    from openai import OpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": QUERY_SPEC_JSON_SCHEMA,
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from OpenAI API")

    parsed = json.loads(content)
    # Strip null values so downstream code can use .get() with defaults cleanly
    return {k: v for k, v in parsed.items() if v is not None}


# ---------------------------------------------------------------------------
# Validation (QUERY → CLARIFY only on hard schema failures)
# ---------------------------------------------------------------------------

def _validate_query_spec(result: QuerySpec) -> Optional[QuerySpec]:
    """
    Run spec_from_dict + validate_spec on a QUERY result.
    Returns None if valid, or a CLARIFY QuerySpec if validation fails hard.
    """
    from query_engine import spec_from_dict, validate_spec

    try:
        query_dict = {k: v for k, v in result.items()
                      if k not in ("result_type", "message", "season", "_debug")}
        spec = spec_from_dict(query_dict)
        validate_spec(spec)
        return None  # valid

    except ValueError as exc:
        error_msg = str(exc)
        if "metric" in error_msg.lower():
            msg = "Which metric would you like? Options: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE, Opp_TOV%"
        elif "window" in error_msg.lower():
            msg = "Over what time period? SEASON, LAST_5, LAST_10, or LAST_20"
        elif "teams" in error_msg.lower():
            msg = "Which teams would you like to compare? Specify at least 2 (e.g. BOS, LAL)"
        elif "x_metric" in error_msg.lower() or "y_metric" in error_msg.lower():
            msg = "Which metrics for X and Y axes? Options: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS"
        else:
            msg = f"Could not process that request: {error_msg}. Try rephrasing."
        return {"result_type": "CLARIFY", "message": msg}


# ---------------------------------------------------------------------------
# Season extraction helper
# ---------------------------------------------------------------------------

def _extract_season(query: str) -> Optional[str]:
    """Return season string in YYYY-YY format if found, else None."""
    # 2023-2024
    m = re.search(r'(20\d{2})-(20\d{2})', query)
    if m:
        return f"{m.group(1)}-{m.group(2)[2:]}"
    # 2023-24
    m = re.search(r'(20\d{2})-(\d{2})', query)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # 2023 24 or 2023/24
    m = re.search(r'(20\d{2})[\s/](\d{2})', query)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def _detect_season_type(query_lower: str) -> str:
    """Detect whether a natural-language query asks for playoff data."""
    if any(w in query_lower for w in ["playoff", "playoffs", "postseason", "finals", "conference finals"]):
        return "Playoffs"
    return "Regular Season"


# ---------------------------------------------------------------------------
# Rule-based fallback — generous defaults, minimal CLARIFY
# ---------------------------------------------------------------------------

# Team name → abbreviation map (used by both compare detection and OUT_OF_SCOPE player check)
_TEAM_MAP: dict = {
    "celtics": "BOS", "celts": "BOS", "bos": "BOS",
    "lakers": "LAL", "lal": "LAL",
    "warriors": "GSW", "gsw": "GSW", "dubs": "GSW",
    "heat": "MIA", "miami": "MIA", "mia": "MIA",
    "bucks": "MIL", "milwaukee": "MIL", "mil": "MIL",
    "nuggets": "DEN", "denver": "DEN", "den": "DEN",
    "suns": "PHX", "phoenix": "PHX", "phx": "PHX",
    "sixers": "PHI", "76ers": "PHI", "phi": "PHI", "philadelphia": "PHI",
    "nets": "BKN", "brooklyn": "BKN", "bkn": "BKN",
    "knicks": "NYK", "newyork": "NYK", "nyk": "NYK",
    "clippers": "LAC", "lac": "LAC",
    "mavericks": "DAL", "mavs": "DAL", "dal": "DAL", "dallas": "DAL",
    "grizzlies": "MEM", "memphis": "MEM", "mem": "MEM",
    "cavaliers": "CLE", "cavs": "CLE", "cle": "CLE", "cleveland": "CLE",
    "hawks": "ATL", "atlanta": "ATL", "atl": "ATL",
    "raptors": "TOR", "toronto": "TOR", "tor": "TOR",
    "bulls": "CHI", "chicago": "CHI", "chi": "CHI",
    "pistons": "DET", "detroit": "DET", "det": "DET",
    "pacers": "IND", "indiana": "IND", "ind": "IND",
    "hornets": "CHA", "charlotte": "CHA", "cha": "CHA",
    "magic": "ORL", "orlando": "ORL", "orl": "ORL",
    "wizards": "WAS", "washington": "WAS", "was": "WAS",
    "rockets": "HOU", "houston": "HOU", "hou": "HOU",
    "spurs": "SAS", "sanantonio": "SAS", "sas": "SAS",
    "pelicans": "NOP", "neworleans": "NOP", "nop": "NOP",
    "timberwolves": "MIN", "wolves": "MIN", "minnesota": "MIN", "min": "MIN",
    "thunder": "OKC", "okc": "OKC",
    "blazers": "POR", "trailblazers": "POR", "portland": "POR", "por": "POR",
    "jazz": "UTA", "utah": "UTA", "uta": "UTA",
    "kings": "SAC", "sacramento": "SAC", "sac": "SAC",
}

_METRIC_MAP: dict = {
    "net rating": "NET_RTG", "net rtg": "NET_RTG", "net_rtg": "NET_RTG", "netrtg": "NET_RTG",
    "offensive rating": "ORtg", "ortg": "ORtg", "offrtg": "ORtg",
    "defensive rating": "DRtg", "drtg": "DRtg", "defrtg": "DRtg",
    "pace": "PACE",
    "ppg": "PPG", "points per game": "PPG", "points": "PPG",
    "efg": "eFG", "effective field goal": "eFG", "effective fg": "eFG",
    "true shooting": "TS",
    "assist rate": "AST_RATE", "ast rate": "AST_RATE", "ast_rate": "AST_RATE",
    "turnover rate": "TOV_RATE", "tov rate": "TOV_RATE", "tov_rate": "TOV_RATE",
    "opp_tov": "Opp_TOV%", "opponent turnover": "Opp_TOV%", "forced turnover": "Opp_TOV%",
    "opp tov": "Opp_TOV%",
}

# "ts" is short and collides with many words — only match as a standalone word
_TS_PATTERN = re.compile(r'\bts\b', re.IGNORECASE)


def _detect_metric(query_lower: str) -> Optional[str]:
    """Return the first metric matched in the query, or None."""
    for key, value in _METRIC_MAP.items():
        if key in query_lower:
            return value
    if _TS_PATTERN.search(query_lower):
        return "TS"
    return None


def _detect_teams(query_lower: str) -> List[str]:
    """Return list of unique team abbreviations found in the query."""
    normalized = query_lower.replace(" ", "")
    teams: List[str] = []
    for name, abbrev in _TEAM_MAP.items():
        if name in normalized and abbrev not in teams:
            teams.append(abbrev)
    return teams


def _detect_window(query_lower: str, default: str = "LAST_10") -> str:
    if "last 5" in query_lower or " l5" in query_lower:
        return "LAST_5"
    if "last 10" in query_lower or " l10" in query_lower:
        return "LAST_10"
    if "last 20" in query_lower or " l20" in query_lower:
        return "LAST_20"
    if any(w in query_lower for w in ["lately", "recently", "right now", "current"]):
        return "LAST_10"
    if any(w in query_lower for w in ["all season", "this season", "full season", "season", "year"]):
        return "SEASON"
    return default


def _rule_based_parser_with_validation(query: str) -> QuerySpec:
    """
    OUT_OF_SCOPE guard → rule-based parse → season injection.
    Returns a QuerySpec without _debug (caller injects that).
    """
    query_lower = query.lower()
    season = _extract_season(query)
    season_type = _detect_season_type(query_lower)

    # --- OUT_OF_SCOPE checks ---
    _oos: list = [
        (["since", "christmas", "after january", "after december", "before october", "custom date"],
         "Custom date ranges are not supported. Use windows: SEASON, LAST_5, LAST_10, LAST_20."),
        (["clutch", "4th quarter", "crunch time", "close games"],
         "Clutch/situational stats are not supported. Try: 'Top 10 teams by net rating'."),
        (["live", "real-time", "tonight", "predict", "who will win", "will they"],
         "Live data and predictions are not available. This app analyses historical team performance."),
        (["lebron", "curry", "durant", "jokic", "giannis", "tatum", "starter", "player stats", "player prop"],
         "Player stats are not supported. This app only analyses team performance."),
        (["shot chart", "play-by-play", "shot location", "zone"],
         "Shot charts and play-by-play are not available. Try: 'Show efficiency landscape'."),
        (["custom formula", "my own metric", "create metric"],
         "Custom formulas are not supported. Use built-in metrics: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS."),
    ]
    for keywords, message in _oos:
        if any(kw in query_lower for kw in keywords):
            return {"result_type": "OUT_OF_SCOPE", "message": message}

    result = _rule_based_parser(query)
    if season and result.get("result_type") == "QUERY":
        result["season"] = season
    if result.get("result_type") == "QUERY":
        result["season_type"] = season_type
    return result


def _rule_based_parser(query: str) -> QuerySpec:
    """
    Core rule-based logic. Defaults liberally — CLARIFY only for compare
    with zero identifiable teams.
    """
    query_lower = query.lower()

    has_offense = any(w in query_lower for w in ["offense", "ortg", "offensive rating", "offens"])
    has_defense = any(w in query_lower for w in ["defense", "drtg", "defensive rating", "defens"])
    has_scatter = any(w in query_lower for w in ["scatter", "plot", "landscape"])
    has_compare = any(w in query_lower for w in ["compare", "versus"])
    # "vs" between team names → compare; standalone "vs" → scatter
    has_vs = " vs " in query_lower or " vs." in query_lower

    detected_teams = _detect_teams(query_lower)

    # ── Chart type detection ────────────────────────────────────────────────
    if (has_compare or (has_vs and len(detected_teams) >= 2)):
        chart_type = "compare"
    elif has_scatter or (has_offense and has_defense):
        # "offense vs defense" → efficiency scatter, not ambiguous
        chart_type = "scatter"
    else:
        chart_type = "leaderboard"

    # ── Window ──────────────────────────────────────────────────────────────
    # Scatter defaults to SEASON for a full-picture view; everything else LAST_10
    scatter_default = "SEASON" if chart_type == "scatter" else "LAST_10"
    window = _detect_window(query_lower, default=scatter_default)

    # ── Metric ──────────────────────────────────────────────────────────────
    detected_metric = _detect_metric(query_lower)

    # Infer metric from defense/offense keywords when no explicit metric found
    if detected_metric is None:
        if has_defense and not has_offense:
            detected_metric = "DRtg"
        elif has_offense and not has_defense:
            detected_metric = "ORtg"
        else:
            detected_metric = "NET_RTG"   # safe universal default

    # ── Build result ─────────────────────────────────────────────────────────
    result: QuerySpec = {
        "result_type": "QUERY",
        "chart_type": chart_type,
        "entity": "team",
        "window": window,
    }

    if chart_type == "leaderboard":
        result["metric"] = detected_metric

        top_n_match = re.search(r'(?:top|bottom|worst|best)\s+(\d+)', query_lower)
        result["top_n"] = int(top_n_match.group(1)) if top_n_match else 10

        # Ascending for "worst/bottom/lowest" or when metric is DRtg (lower = better)
        if any(w in query_lower for w in ["worst", "bottom", "lowest"]):
            result["order"] = "asc"
        elif detected_metric == "DRtg":
            result["order"] = "asc"
        else:
            result["order"] = "desc"

    elif chart_type == "scatter":
        if "shooting" in query_lower:
            result["x_metric"] = "eFG"
            result["y_metric"] = "TS"
        else:
            # Default: efficiency landscape
            result["x_metric"] = "ORtg"
            result["y_metric"] = "DRtg"

    elif chart_type == "compare":
        # Detect any metrics the user mentioned for the compare chart
        compare_metric_patterns = [
            ("net rating", "NET_RTG"), ("net_rtg", "NET_RTG"), ("net rtg", "NET_RTG"),
            ("ortg", "ORtg"), ("offensive rating", "ORtg"), ("offrtg", "ORtg"),
            ("drtg", "DRtg"), ("defensive rating", "DRtg"), ("defrtg", "DRtg"),
            ("pace", "PACE"),
            ("points per game", "PPG"), ("ppg", "PPG"),
            ("efg", "eFG"), ("effective fg", "eFG"),
            ("true shooting", "TS"), ("ts%", "TS"),
            ("assist", "AST_RATE"), ("ast_rate", "AST_RATE"),
            ("tov%", "TOV_RATE"), ("turnover", "TOV_RATE"),
            ("opp_tov", "Opp_TOV%"), ("opponent turnover", "Opp_TOV%"),
        ]
        requested_metrics = []
        for pattern, col in compare_metric_patterns:
            if pattern in query_lower and col not in requested_metrics:
                requested_metrics.append(col)
        if requested_metrics:
            result["compare_metrics"] = requested_metrics

        if len(detected_teams) >= 2:
            result["teams"] = detected_teams[:2]
        elif len(detected_teams) == 1:
            return {
                "result_type": "CLARIFY",
                "message": (
                    f"Found {detected_teams[0]}, but a comparison needs at least 2 teams. "
                    "Which other team would you like to compare?"
                ),
            }
        else:
            # No team names at all → only case where CLARIFY is warranted
            return {
                "result_type": "CLARIFY",
                "message": "Which teams would you like to compare? E.g. 'Compare Celtics and Lakers'.",
            }

    return result


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _samples = [
        "top teams lately",
        "best teams right now",
        "worst 5 defenses last 5 games",
        "show efficiency landscape",
        "offense vs defense",
        "compare Lakers and Celtics",
        "pace leaders last 10",
        "top 10 by net rating in 2023-24",
        "show me LeBron's stats",       # OUT_OF_SCOPE
        "predict who will win tonight",  # OUT_OF_SCOPE
        "compare the warriors",          # CLARIFY (only 1 team)
    ]
    print("Testing rule-based parser (no API key)\n" + "=" * 55)
    for q in _samples:
        r = _rule_based_parser_with_validation(q)
        rt = r.get("result_type")
        detail = r.get("chart_type") or r.get("message", "")
        print(f"  [{rt:12s}]  {q!r:45s}  → {detail}")
