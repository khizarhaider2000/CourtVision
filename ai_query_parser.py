# ai_query_parser.py
# Converts natural language queries into structured QuerySpec dictionaries
# Uses OpenAI structured outputs for schema-enforced responses

import json
import os
import re
from typing import Optional, TypedDict, Literal, List

# Type definitions
ResultType = Literal["QUERY", "CLARIFY", "OUT_OF_SCOPE"]
ChartType = Literal["leaderboard", "scatter", "compare"]
WindowType = Literal["SEASON", "LAST_5", "LAST_10", "LAST_20"]
OrderType = Literal["asc", "desc"]


class QuerySpec(TypedDict, total=False):
    """
    Structured response from the LLM parser.

    result_type is always required:
    - QUERY: Valid query, includes chart_type/entity/window and optional fields
    - CLARIFY: Needs clarification, includes message
    - OUT_OF_SCOPE: Unsupported request, includes message
    """
    result_type: ResultType

    # Required when result_type == "QUERY"
    chart_type: ChartType
    entity: Literal["team"]
    window: WindowType

    # Optional fields for QUERY
    metric: str
    x_metric: str
    y_metric: str
    top_n: int
    order: OrderType
    teams: List[str]
    season: str

    # Required when result_type == "CLARIFY" or "OUT_OF_SCOPE"
    message: str


# JSON Schema for OpenAI structured outputs - enforces conditional requirements
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
                "description": "QUERY for valid requests, CLARIFY for ambiguous, OUT_OF_SCOPE for unsupported"
            },
            "chart_type": {
                "type": ["string", "null"],
                "enum": ["leaderboard", "scatter", "compare", None],
                "description": "Required for QUERY: leaderboard, scatter, or compare"
            },
            "entity": {
                "type": ["string", "null"],
                "enum": ["team", None],
                "description": "Required for QUERY: only 'team' supported in v1"
            },
            "window": {
                "type": ["string", "null"],
                "enum": ["SEASON", "LAST_5", "LAST_10", "LAST_20", None],
                "description": "Required for QUERY: time window"
            },
            "metric": {
                "type": ["string", "null"],
                "description": "For leaderboard: ORtg, DRtg, NET_RTG, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE"
            },
            "x_metric": {
                "type": ["string", "null"],
                "description": "For scatter: X-axis metric"
            },
            "y_metric": {
                "type": ["string", "null"],
                "description": "For scatter: Y-axis metric"
            },
            "top_n": {
                "type": ["integer", "null"],
                "description": "For leaderboard: number of teams to show"
            },
            "order": {
                "type": ["string", "null"],
                "enum": ["asc", "desc", None],
                "description": "For leaderboard: sort order"
            },
            "teams": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "For compare: team abbreviations (e.g. ['BOS', 'LAL'])"
            },
            "season": {
                "type": ["string", "null"],
                "description": "Optional: season in YYYY-YY format (e.g. '2023-24')"
            },
            "message": {
                "type": ["string", "null"],
                "description": "Required for CLARIFY/OUT_OF_SCOPE: explanation or questions"
            }
        },
        "required": [
            "result_type", "chart_type", "entity", "window",
            "metric", "x_metric", "y_metric", "top_n", "order",
            "teams", "season", "message"
        ]
    }
}

# Minimal system prompt - relies on schema for structure
SYSTEM_PROMPT = """You are a query parser for an NBA team analytics app.

SCOPE: Team-only charts (no player stats). Chart types: leaderboard, scatter, compare.
Metrics: ORtg, DRtg, NET_RTG, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE.
Windows: SEASON, LAST_5, LAST_10, LAST_20.
Teams: ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS.

RULES:
- Do NOT guess missing info. If ambiguous, return CLARIFY with 1-2 short questions.
- If unsupported (player stats, custom dates, clutch, playoffs, predictions), return OUT_OF_SCOPE with brief explanation.
- For QUERY: set chart_type, entity="team", window, and relevant fields (metric/top_n/order for leaderboard; x_metric/y_metric for scatter; teams for compare).
- For defense rankings, use DRtg with desc order (higher = worse defense).
- Season format: "2023-24" if mentioned."""


def parse_natural_language_query(user_query: str) -> QuerySpec:
    """
    Parse natural language into structured QuerySpec.

    Returns a QuerySpec dict with result_type:
    - QUERY: Proceed to chart rendering
    - CLARIFY: Show message to user, do not render
    - OUT_OF_SCOPE: Show message to user, do not render

    Falls back to rule-based parser on API errors.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # No API key - use rule-based parser
        return _rule_based_parser_with_validation(user_query)

    try:
        result = _call_openai_structured(user_query, api_key)

        # If LLM returned QUERY, validate via query_engine
        if result.get("result_type") == "QUERY":
            validation_result = _validate_query_spec(result)
            if validation_result is not None:
                return validation_result  # Returns CLARIFY if validation failed

        return result

    except Exception as e:
        # Fallback to rule-based parser on any error (quota, timeout, schema, etc.)
        error_str = str(e).lower()
        if any(err in error_str for err in ["rate limit", "quota", "timeout", "connection", "api"]):
            return _rule_based_parser_with_validation(user_query)
        # For other errors, still try rule-based as fallback
        return _rule_based_parser_with_validation(user_query)


def _call_openai_structured(user_query: str, api_key: str) -> QuerySpec:
    """
    Call OpenAI API with structured output (json_schema response_format).
    """
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
            "json_schema": QUERY_SPEC_JSON_SCHEMA
        }
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from API")

    parsed = json.loads(content)

    # Remove null values for cleaner result
    return {k: v for k, v in parsed.items() if v is not None}


def _validate_query_spec(result: QuerySpec) -> Optional[QuerySpec]:
    """
    Validate a QUERY result using query_engine's spec_from_dict and validate_spec.
    Returns None if valid, or a CLARIFY QuerySpec if validation fails.
    """
    from query_engine import spec_from_dict, validate_spec

    try:
        # Build dict for spec_from_dict (it expects chart_type, window, etc.)
        query_dict = {
            "chart_type": result.get("chart_type"),
            "entity": result.get("entity", "team"),
            "window": result.get("window"),
        }

        # Add chart-type specific fields
        if result.get("metric"):
            query_dict["metric"] = result["metric"]
        if result.get("top_n"):
            query_dict["top_n"] = result["top_n"]
        if result.get("order"):
            query_dict["order"] = result["order"]
        if result.get("x_metric"):
            query_dict["x_metric"] = result["x_metric"]
        if result.get("y_metric"):
            query_dict["y_metric"] = result["y_metric"]
        if result.get("teams"):
            query_dict["teams"] = result["teams"]

        # Convert to ChartSpec and validate
        spec = spec_from_dict(query_dict)
        validate_spec(spec)

        return None  # Valid

    except ValueError as e:
        # Validation failed - return CLARIFY with helpful message
        error_msg = str(e)

        # Generate specific clarification questions based on error
        if "metric" in error_msg.lower():
            message = "Which metric would you like to see? Options: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE"
        elif "window" in error_msg.lower():
            message = "Over what time period? Options: SEASON, LAST_5, LAST_10, LAST_20"
        elif "teams" in error_msg.lower():
            message = "Which teams would you like to compare? Please specify at least 2 team abbreviations (e.g., BOS, LAL)"
        elif "x_metric" in error_msg.lower() or "y_metric" in error_msg.lower():
            message = "Which metrics would you like on the X and Y axes? Options: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS"
        else:
            message = f"Could not process request: {error_msg}. Please try rephrasing."

        return {
            "result_type": "CLARIFY",
            "message": message
        }


def _extract_season(query: str) -> Optional[str]:
    """
    Extract season from query string.
    Returns season in 'YYYY-YY' format (e.g., '2023-24') or None if not found.
    """
    # Match YYYY-YYYY format first (e.g., "2023-2024") and convert to YYYY-YY
    match = re.search(r'(20\d{2})-(20\d{2})', query)
    if match:
        year1 = match.group(1)
        year2 = match.group(2)
        return f"{year1}-{year2[2:]}"

    # Match YYYY-YY format (e.g., "2023-24")
    match = re.search(r'(20\d{2})-(\d{2})', query)
    if match:
        year1 = match.group(1)
        year2 = match.group(2)
        return f"{year1}-{year2}"

    # Pattern: Written out like "2023 24" or "2023/24"
    match = re.search(r'(20\d{2})[\s/](\d{2})', query)
    if match:
        year1 = match.group(1)
        year2 = match.group(2)
        return f"{year1}-{year2}"

    return None


def _rule_based_parser_with_validation(query: str) -> QuerySpec:
    """
    Rule-based parser fallback. Returns structured QuerySpec.
    Validates scope before returning results.
    """
    query_lower = query.lower()
    season = _extract_season(query)

    # Check for out-of-scope patterns first
    out_of_scope_checks = [
        (["since", "christmas", "january", "december", "after", "before"],
         "Custom date ranges not supported. Use time windows: SEASON, LAST_5, LAST_10, LAST_20"),
        (["clutch", "4th quarter", "quarter", "crunch time", "close games"],
         "Clutch/situational stats not supported. Try: 'Top 10 teams by net rating'"),
        (["live", "real-time", "right now", "predict", "will"],
         "Live/prediction data not available. This app analyzes historical team performance."),
        (["player", "lebron", "curry", "starter"],
         "Player stats not supported. This app only analyzes team performance."),
        (["shot chart", "play-by-play", "shot location"],
         "Shot charts and play-by-play not available. Try: 'Show efficiency landscape'"),
        (["playoff", "postseason"],
         "Playoff-specific data not supported. This app analyzes regular season data."),
        (["custom", "formula", "my own"],
         "Custom formulas not supported. Use built-in metrics: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS"),
    ]

    for keywords, message in out_of_scope_checks:
        if any(kw in query_lower for kw in keywords):
            return {
                "result_type": "OUT_OF_SCOPE",
                "message": message
            }

    # Parse the query
    result = _rule_based_parser(query)

    # Add season if detected
    if season:
        result["season"] = season

    return result


def _rule_based_parser(query: str) -> QuerySpec:
    """
    Simple rule-based parser for common query patterns.
    Returns structured QuerySpec with result_type=QUERY.
    """
    query_lower = query.lower()

    # Detect chart type
    if any(word in query_lower for word in ["compare", "vs", "versus"]):
        chart_type = "compare"
    elif any(word in query_lower for word in ["scatter", "plot", "landscape"]):
        chart_type = "scatter"
    else:
        chart_type = "leaderboard"

    # Detect window
    if "last 5" in query_lower or "l5" in query_lower:
        window = "LAST_5"
    elif "last 10" in query_lower or "l10" in query_lower:
        window = "LAST_10"
    elif "last 20" in query_lower or "l20" in query_lower:
        window = "LAST_20"
    else:
        window = "SEASON"

    result: QuerySpec = {
        "result_type": "QUERY",
        "chart_type": chart_type,
        "entity": "team",
        "window": window,
    }

    if chart_type == "leaderboard":
        # Detect metric
        metric_map = {
            "net rating": "NET_RTG", "net rtg": "NET_RTG",
            "offensive rating": "ORtg", "offense": "ORtg", "ortg": "ORtg",
            "defensive rating": "DRtg", "defense": "DRtg", "drtg": "DRtg",
            "pace": "PACE",
            "ppg": "PPG", "points": "PPG",
            "efg": "eFG",
            "ts": "TS", "true shooting": "TS",
            "assist": "AST_RATE",
            "turnover": "TOV_RATE",
        }

        detected_metric = "NET_RTG"
        for key, value in metric_map.items():
            if key in query_lower:
                detected_metric = value
                break

        result["metric"] = detected_metric

        # Detect top_n
        top_n_match = re.search(r'top\s+(\d+)', query_lower)
        result["top_n"] = int(top_n_match.group(1)) if top_n_match else 10

        # Detect order
        if any(word in query_lower for word in ["worst", "bottom", "lowest"]):
            result["order"] = "asc"
        else:
            result["order"] = "desc"

    elif chart_type == "scatter":
        # Common patterns
        if "efficiency" in query_lower or ("ortg" in query_lower and "drtg" in query_lower):
            result["x_metric"] = "ORtg"
            result["y_metric"] = "DRtg"
        elif "shooting" in query_lower:
            result["x_metric"] = "eFG"
            result["y_metric"] = "TS"
        else:
            # Default to efficiency landscape
            result["x_metric"] = "ORtg"
            result["y_metric"] = "DRtg"

    elif chart_type == "compare":
        # Team name mapping
        team_map = {
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

        teams = []
        query_normalized = query_lower.replace(" ", "")
        for team_name, abbrev in team_map.items():
            if team_name in query_normalized:
                if abbrev not in teams:
                    teams.append(abbrev)

        if len(teams) >= 2:
            result["teams"] = teams[:2]
        elif len(teams) == 1:
            # Only one team found - need clarification
            return {
                "result_type": "CLARIFY",
                "message": f"Found {teams[0]}, but comparison needs at least 2 teams. Which other team would you like to compare?"
            }
        else:
            # No teams found - need clarification
            return {
                "result_type": "CLARIFY",
                "message": "Which teams would you like to compare? Please specify at least 2 teams (e.g., 'Compare Celtics and Lakers')"
            }

    return result


# Example usage and testing
if __name__ == "__main__":
    test_queries = [
        "Show me the top 10 teams by net rating in the last 10 games",
        "efficiency landscape last 5",
        "Compare Celtics and Lakers",
        "worst 5 defenses this season",
        "top offenses",
        "Show me clutch stats",  # Out of scope
        "Compare Lakers",  # Missing second team
    ]

    print("Testing AI Query Parser:\n")
    for query in test_queries:
        result = parse_natural_language_query(query)
        print(f"Query: {query}")
        print(f"Result: {json.dumps(result, indent=2)}\n")
