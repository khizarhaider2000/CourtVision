# ai_query_parser.py
# Converts natural language queries into structured ChartSpec dictionaries
# Uses Claude API (already available in artifacts)

import json
import re
from typing import Dict, Any, Optional


def parse_natural_language_query(user_query: str) -> Dict[str, Any]:
    """
    Takes a natural language query and returns a query_dict for spec_from_dict().
    
    Examples:
    - "Show me the top 10 teams by net rating in the last 10 games"
      → {"chart_type": "leaderboard", "metric": "NET_RTG", "top_n": 10, "window": "LAST_10"}
    
    - "Compare the offensive and defensive ratings"
      → {"chart_type": "scatter", "x_metric": "ORtg", "y_metric": "DRtg", "window": "SEASON"}
    
    - "How do the Celtics and Lakers compare?"
      → {"chart_type": "compare", "teams": ["BOS", "LAL"], "window": "SEASON"}
    """
    
    # System prompt that teaches the AI about the query structure
    system_prompt = """You are a query-mapping assistant for an NBA Team Performance Analytics app.

Your ONLY job is to convert user natural language input into a valid query object, ask for clarification, or reject out-of-scope requests.

## STRICT RULES

You must NEVER:
- Guess, invent, or assume missing information
- Default silently when data is ambiguous
- Invent team names, metrics, or date ranges
- Return partial queries

## SUPPORTED QUERIES

**Chart Types:**
- `leaderboard`: Rank top N teams by a single metric
- `scatter`: Plot all teams on two metrics (X vs Y axis)
- `compare`: Head-to-head comparison of 2+ specific teams

**Metrics (case-sensitive):**
- `ORtg`: Offensive Rating (points per 100 possessions)
- `DRtg`: Defensive Rating (points allowed per 100 possessions)
- `NET_RTG`: Net Rating (ORtg - DRtg)
- `PACE`: Possessions per game
- `PPG`: Points per game
- `eFG`: Effective Field Goal %
- `TS`: True Shooting %
- `AST_RATE`: Assists per possession
- `TOV_RATE`: Turnovers per possession

**Time Windows:**
- `SEASON`: Full season to date
- `LAST_5`: Last 5 games per team
- `LAST_10`: Last 10 games per team
- `LAST_20`: Last 20 games per team

**Season (optional):**
- You can optionally include a `season` field in the format "YYYY-YY" (e.g., "2023-24", "2024-25")
- If the user mentions a specific season like "in 2023-24" or "for the 2022-23 season", include it in the response
- Example: {"chart_type": "leaderboard", "metric": "NET_RTG", "window": "SEASON", "season": "2023-24"}

**Team Abbreviations (NBA 2024-25):**
ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS

**Entity:** Only `team` is supported (no player stats)

## RESPONSE TYPES

### 1. QUERY (Complete & Valid)
Return when the user request is complete, unambiguous, and within scope. Return ONLY the query object as valid JSON.

**Leaderboard format:**
{"chart_type": "leaderboard", "metric": "NET_RTG", "window": "LAST_10", "top_n": 10, "order": "desc"}

**Scatter format:**
{"chart_type": "scatter", "x_metric": "ORtg", "y_metric": "DRtg", "window": "SEASON"}

**Compare format:**
{"chart_type": "compare", "teams": ["BOS", "LAL"], "window": "LAST_10"}

### 2. CLARIFY (Ambiguous but Possible)
Return when the request could be supported but lacks critical information. Respond with "CLARIFY:" followed by 1-2 SHORT, SPECIFIC questions.

Example: "CLARIFY: Which metric would you like to see? (e.g., NET_RTG, ORtg, DRtg)"

### 3. OUT_OF_SCOPE (Unsupported Request)
Return when the request cannot be fulfilled. Respond with "OUT_OF_SCOPE:" followed by brief explanation and 2-3 valid examples.

Example: "OUT_OF_SCOPE: Custom date ranges not supported. Try: 'Top 10 teams by net rating over the last 10 games'"

**Out-of-scope includes:**
- Custom date ranges ("since Christmas", "January games")
- Clutch stats or situational filters
- Custom formulas or advanced stats not in the list
- Live/real-time stats or predictions
- Shot charts, play-by-play data
- Player-level statistics
- Specific games or game results

## EXAMPLES

**User:** "Top 10 teams by net rating last 10 games"
**Response:** {"chart_type": "leaderboard", "metric": "NET_RTG", "window": "LAST_10", "top_n": 10, "order": "desc"}

**User:** "Show me the efficiency landscape"
**Response:** {"chart_type": "scatter", "x_metric": "ORtg", "y_metric": "DRtg", "window": "SEASON"}

**User:** "Compare Celtics and Lakers"
**Response:** CLARIFY: Over what time window? (SEASON, LAST_5, LAST_10, or LAST_20)

**User:** "Worst 5 defenses this season"
**Response:** {"chart_type": "leaderboard", "metric": "DRtg", "window": "SEASON", "top_n": 5, "order": "desc"}

**User:** "Top 10 teams by net rating in 2023-24"
**Response:** {"chart_type": "leaderboard", "metric": "NET_RTG", "window": "SEASON", "top_n": 10, "order": "desc", "season": "2023-24"}

**User:** "Show me clutch stats in the 4th quarter"
**Response:** OUT_OF_SCOPE: This app doesn't support clutch stats or quarter-specific filters. Try: 'Top 10 teams by net rating' or 'Compare Warriors and Nuggets'

## FINAL INSTRUCTIONS

- Return ONLY valid JSON for QUERY responses (no explanation text)
- For CLARIFY: Return "CLARIFY: " + your question
- For OUT_OF_SCOPE: Return "OUT_OF_SCOPE: " + your message
- Use EXACT metric names (case-sensitive)
- Use EXACT team abbreviations (3 letters, uppercase)
- For "best offense" use ORtg (higher = better)
- For "best defense" use DRtg with desc order (show highest values = worst defense)
- Never mix up X and Y axes in scatter plots
- Be strict about scope - reject anything unsupported
"""

    try:
        # TODO: Uncomment this section when you have ANTHROPIC_API_KEY set up
        # import anthropic
        # import os
        #
        # client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        #
        # message = client.messages.create(
        #     model="claude-3-5-sonnet-20241022",
        #     max_tokens=1024,
        #     system=system_prompt,
        #     messages=[
        #         {"role": "user", "content": user_query}
        #     ]
        # )
        #
        # response_text = message.content[0].text.strip()
        #
        # # Handle CLARIFY and OUT_OF_SCOPE responses
        # if response_text.startswith("CLARIFY:"):
        #     raise ValueError(response_text)
        # elif response_text.startswith("OUT_OF_SCOPE:"):
        #     raise ValueError(response_text)
        # else:
        #     # Parse the JSON query object
        #     return json.loads(response_text)

        # For now, use enhanced rule-based parser with OUT_OF_SCOPE validation
        return _rule_based_parser_with_validation(user_query)

    except Exception as e:
        raise ValueError(f"Failed to parse query: {e}")


def _extract_season(query: str) -> Optional[str]:
    """
    Extract season from query string.
    Returns season in 'YYYY-YY' format (e.g., '2023-24') or None if not found.
    """
    import re

    # Match YYYY-YYYY format first (e.g., "2023-2024") and convert to YYYY-YY
    # This must come before YYYY-YY to avoid partial matches
    match = re.search(r'(20\d{2})-(20\d{2})', query)
    if match:
        year1 = match.group(1)
        year2 = match.group(2)
        # Convert 2023-2024 to 2023-24
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


def _rule_based_parser_with_validation(query: str) -> Dict[str, Any]:
    """
    Enhanced rule-based parser that validates scope before returning results.
    Raises ValueError with CLARIFY or OUT_OF_SCOPE messages for invalid queries.
    """
    query_lower = query.lower()

    # Extract season if mentioned (before validation)
    season = _extract_season(query)

    # Check for out-of-scope patterns first
    out_of_scope_patterns = [
        # Custom date ranges
        ("since", "Custom date ranges not supported. Try time windows: SEASON, LAST_5, LAST_10, or LAST_20"),
        ("christmas", "Custom date ranges not supported. Try: 'Top 10 teams by net rating over the last 10 games'"),
        ("january", "Custom date ranges not supported. Use SEASON or LAST_N windows instead"),
        ("december", "Custom date ranges not supported. Use SEASON or LAST_N windows instead"),
        ("after", "Custom date ranges not supported. Try: 'Top teams by offensive rating this season'"),
        ("before", "Custom date ranges not supported. Try standard time windows (SEASON, LAST_5, LAST_10, LAST_20)"),

        # Clutch and situational stats
        ("clutch", "OUT_OF_SCOPE: Clutch stats not supported. Try: 'Top 10 teams by net rating' or 'Compare Warriors and Lakers'"),
        ("4th quarter", "OUT_OF_SCOPE: Quarter-specific filters not supported. Try: 'Best offenses in the last 10 games'"),
        ("quarter", "OUT_OF_SCOPE: Quarter-specific stats not available. Try overall team metrics like NET_RTG or ORtg"),
        ("crunch time", "OUT_OF_SCOPE: Situational filters not supported. Try standard metrics over time windows"),
        ("close games", "OUT_OF_SCOPE: Game-specific filters not supported. Try: 'Efficiency landscape' or 'Top defenses'"),

        # Live/predictions
        ("live", "OUT_OF_SCOPE: Live stats not supported. This app analyzes historical team performance data only"),
        ("real-time", "OUT_OF_SCOPE: Real-time data not available. Try: 'Top teams by net rating this season'"),
        ("right now", "OUT_OF_SCOPE: Live data not supported. Use season or recent games windows instead"),
        ("predict", "OUT_OF_SCOPE: Predictions not supported. This app shows historical performance metrics only"),
        ("will", "OUT_OF_SCOPE: Future predictions not available. Try historical analysis queries instead"),

        # Player stats
        ("player", "OUT_OF_SCOPE: Player-level statistics not supported. This app only analyzes team performance"),
        ("lebron", "OUT_OF_SCOPE: Player stats not available. Try: 'Compare Lakers and Heat' for team-level analysis"),
        ("curry", "OUT_OF_SCOPE: Player stats not supported. Try: 'Top teams by offensive rating' instead"),
        ("starter", "OUT_OF_SCOPE: Player-level data not available. This app focuses on team metrics only"),

        # Shot charts and play-by-play
        ("shot chart", "OUT_OF_SCOPE: Shot charts not supported. Try: 'Show efficiency landscape' for shooting metrics"),
        ("play-by-play", "OUT_OF_SCOPE: Play-by-play data not available. This app uses aggregated team box scores"),
        ("shot location", "OUT_OF_SCOPE: Spatial shot data not supported. Try eFG or TS% for shooting efficiency"),

        # Specific games
        ("game on", "OUT_OF_SCOPE: Specific game results not supported. Try time windows like LAST_10 or SEASON"),
        ("score", "OUT_OF_SCOPE: Individual game scores not available. Try PPG or NET_RTG for scoring metrics"),

        # Playoff-specific
        ("playoff", "OUT_OF_SCOPE: Playoff-specific filters not supported. This app analyzes regular season data"),
        ("postseason", "OUT_OF_SCOPE: Postseason filters not available. Try regular season time windows instead"),

        # Custom formulas
        ("custom", "OUT_OF_SCOPE: Custom formulas not supported. Use built-in metrics: NET_RTG, ORtg, DRtg, PACE, PPG, eFG, TS, AST_RATE, TOV_RATE"),
        ("formula", "OUT_OF_SCOPE: Custom formulas not available. Try standard metrics like NET_RTG or ORtg"),
        ("my own", "OUT_OF_SCOPE: Custom calculations not supported. Use available metrics: NET_RTG, ORtg, DRtg, PACE, eFG, TS"),
    ]

    for keyword, message in out_of_scope_patterns:
        if keyword in query_lower:
            raise ValueError(f"OUT_OF_SCOPE: {message}")

    # If passes validation, use the original rule-based parser
    result = _rule_based_parser(query)

    # Add season to result if detected
    if season:
        result["season"] = season

    return result


def _rule_based_parser(query: str) -> Dict[str, Any]:
    """
    Simple rule-based parser as fallback (or for environments without API access).
    Not as robust as AI but handles common cases.
    """
    query_lower = query.lower()
    result: Dict[str, Any] = {}
    
    # Detect chart type
    if any(word in query_lower for word in ["compare", "vs", "versus"]):
        result["chart_type"] = "compare"
    elif any(word in query_lower for word in ["scatter", "plot", "landscape", "vs"]):
        result["chart_type"] = "scatter"
    else:
        result["chart_type"] = "leaderboard"
    
    # Detect window
    if "last 5" in query_lower or "l5" in query_lower:
        result["window"] = "LAST_5"
    elif "last 10" in query_lower or "l10" in query_lower:
        result["window"] = "LAST_10"
    elif "last 20" in query_lower or "l20" in query_lower:
        result["window"] = "LAST_20"
    else:
        result["window"] = "SEASON"
    
    # Leaderboard specifics
    if result["chart_type"] == "leaderboard":
        # Detect metric
        metric_map = {
            "net rating": "NET_RTG",
            "net rtg": "NET_RTG",
            "offensive rating": "ORtg",
            "offense": "ORtg",
            "ortg": "ORtg",
            "defensive rating": "DRtg",
            "defense": "DRtg",
            "drtg": "DRtg",
            "pace": "PACE",
            "ppg": "PPG",
            "points": "PPG",
            "efg": "eFG",
            "ts": "TS",
            "true shooting": "TS",
            "assist": "AST_RATE",
            "turnover": "TOV_RATE",
        }
        
        detected_metric = "NET_RTG"  # default
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
    
    # Scatter specifics
    elif result["chart_type"] == "scatter":
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
    
    # Compare specifics
    elif result["chart_type"] == "compare":
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
        }
        
        teams = []
        for team_name, abbrev in team_map.items():
            if team_name in query_lower.replace(" ", ""):
                if abbrev not in teams:
                    teams.append(abbrev)
        
        if len(teams) < 2:
            # Default comparison
            teams = ["BOS", "LAL"]
        
        result["teams"] = teams[:2]  # Only take first 2
    
    return result


# Example usage and testing
if __name__ == "__main__":
    test_queries = [
        "Show me the top 10 teams by net rating in the last 10 games",
        "efficiency landscape last 5",
        "Compare Celtics and Lakers",
        "worst 5 defenses this season",
        "top offenses",
    ]
    
    print("Testing AI Query Parser:\n")
    for query in test_queries:
        try:
            result = parse_natural_language_query(query)
            print(f"Query: {query}")
            print(f"Result: {json.dumps(result, indent=2)}\n")
        except Exception as e:
            print(f"Query: {query}")
            print(f"Error: {e}\n")