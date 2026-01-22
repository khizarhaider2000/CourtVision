# CourtVision - AI-Powered NBA Analytics Platform
# A polished analytics product with AI natural language query support

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
from typing import Optional

from query_engine import run_query, spec_from_dict, TEAM_METRICS_ALLOWLIST
from visualize import render_chart
from ai_query_parser import parse_natural_language_query
from data_loader import get_available_seasons, load_season_data

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="CourtVision",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Custom CSS Styling
# ============================================================================

st.markdown("""
<style>
    /* Main color scheme - works in both light and dark mode */
    :root {
        --accent-orange: #FF6B35;
        --accent-orange-light: #FF8555;
        --border-color: rgba(128, 128, 128, 0.3);
        --card-bg: var(--background-color);
        --text-color: var(--text-color);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Typography improvements - inherit color for dark mode support */
    h1 {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.3rem !important;
    }

    h2 {
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.8rem !important;
    }

    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Card containers - adapt to theme */
    .card {
        background: transparent;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(128,128,128,0.15);
    }

    .card-header {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--accent-orange);
    }

    /* Filter chips - adapt to theme */
    .filter-chip {
        display: inline-block;
        background: rgba(128, 128, 128, 0.1);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 0.4rem 0.9rem;
        margin: 0.3rem 0.4rem 0.3rem 0;
        font-size: 0.85rem;
    }

    .filter-chip-label {
        font-weight: 600;
        opacity: 0.7;
    }

    /* Summary bullets */
    .summary-item {
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        font-size: 0.95rem;
    }

    .summary-item:last-child {
        border-bottom: none;
    }

    .summary-label {
        font-weight: 600;
        opacity: 0.7;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .summary-value {
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    /* Reduce spacing in main container */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Primary button override */
    .stButton > button[kind="primary"] {
        background-color: var(--accent-orange) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.6rem 2rem !important;
        border-radius: 6px !important;
        transition: all 0.2s !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-orange-light) !important;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3) !important;
    }

    /* Download button */
    .stDownloadButton > button {
        border-color: var(--accent-orange) !important;
        color: var(--accent-orange) !important;
        font-weight: 500 !important;
    }

    .stDownloadButton > button:hover {
        background-color: rgba(255, 107, 53, 0.1) !important;
    }

    /* Timestamp styling */
    .timestamp {
        opacity: 0.6;
        font-size: 0.85rem;
        font-style: italic;
    }

    /* Welcome message improvements - adapt to theme */
    .welcome-box {
        background: rgba(255, 107, 53, 0.08);
        border: 1px solid rgba(255, 107, 53, 0.2);
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }

    /* Metric cards for welcome screen */
    .metric-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 1.2rem;
        height: 100%;
    }

    .metric-card-title {
        font-weight: 600;
        color: var(--accent-orange);
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
    }

    .metric-card p {
        opacity: 0.8;
    }

    /* Reduce expander padding */
    .streamlit-expanderHeader {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }

    /* AI mode badge */
    .ai-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Data Loading Functions
# ============================================================================

@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_data(season: str):
    """Load and prepare data for a specific season (cached for performance)"""
    return load_season_data(season)

def get_dataset_timestamp(season: str) -> str:
    """Get the last modified timestamp of the dataset"""
    try:
        # Handle legacy file
        if "Legacy" in season or "Rename File" in season:
            file_path = Path("data/processed/team_game_stats.csv")
        else:
            season_slug = season.replace("-", "_")
            file_path = Path(f"data/processed/team_game_stats_{season_slug}.csv")

        if file_path.exists():
            timestamp = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        pass
    return "Unknown"

# ============================================================================
# Query Execution Functions
# ============================================================================

def execute_query(query_dict: dict, df: pd.DataFrame, season: str):
    """Execute a query and store results in session state"""
    try:
        # Convert dict to spec and run query
        spec = spec_from_dict(query_dict)
        result_df, explanation = run_query(df, spec)

        # Store in session state
        st.session_state['result_df'] = result_df
        st.session_state['spec'] = spec
        st.session_state['explanation'] = explanation
        st.session_state['query_dict'] = query_dict
        st.session_state['selected_season'] = season
        st.session_state['query_ran'] = True
        st.session_state['error'] = None

    except Exception as e:
        st.session_state['query_ran'] = False
        st.session_state['error'] = str(e)


def execute_ai_query(query_dict: dict, requested_season: Optional[str], available_seasons: list, current_season: str):
    """
    Execute AI query with automatic season switching if needed.
    Returns: (success: bool, season_used: str, error_message: Optional[str])
    """
    # Check if a specific season was requested
    if requested_season:
        # Validate the requested season exists
        season_names = [s for s, _ in available_seasons]
        if requested_season not in season_names:
            return False, current_season, f"Season {requested_season} data not available. Available seasons: {', '.join(season_names)}"

        # Load data for requested season
        try:
            df = load_data(requested_season)
            execute_query(query_dict, df, requested_season)
            return True, requested_season, None
        except Exception as e:
            return False, current_season, f"Failed to load {requested_season} data: {e}"
    else:
        # Use currently selected season
        try:
            df = load_data(current_season)
            execute_query(query_dict, df, current_season)
            return True, current_season, None
        except Exception as e:
            return False, current_season, f"Query execution failed: {e}"

# ============================================================================
# UI Helper Functions
# ============================================================================

def render_filter_chips(query_dict, season):
    """Display active filters as chips"""
    chips_html = f'<div style="margin: 1rem 0;">'

    # Season chip
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Season:</span> {season}</span>'

    # Window chip
    window_display = query_dict.get("window", "").replace("_", " ")
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Window:</span> {window_display}</span>'

    # Chart type chip
    chart_type = query_dict.get("chart_type", "").title()
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Type:</span> {chart_type}</span>'

    # Metric-specific chips
    if query_dict.get("metric"):
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Metric:</span> {query_dict["metric"]}</span>'

    if query_dict.get("top_n"):
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Top:</span> {query_dict["top_n"]}</span>'

    if query_dict.get("order"):
        order_text = "Highest first" if query_dict["order"] == "desc" else "Lowest first"
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Sort:</span> {order_text}</span>'

    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

def render_summary_card(spec, result_df, explanation, window):
    """Render the summary/insights card in the right column"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">Key Insights</div>', unsafe_allow_html=True)

    # Summary items based on chart type
    if spec.chart_type == "leaderboard" and len(result_df) > 0:
        top_team = result_df.iloc[0]

        st.markdown('<div class="summary-item">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label">Top Team</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-value">{top_team["TEAM_ABBREVIATION"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="summary-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-label">{spec.metric}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-value">{top_team[spec.metric]:.1f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif spec.chart_type == "scatter":
        avg_x = result_df[spec.x_metric].mean()
        avg_y = result_df[spec.y_metric].mean()

        st.markdown('<div class="summary-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-label">League Avg {spec.x_metric}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-value">{avg_x:.1f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="summary-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-label">League Avg {spec.y_metric}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-value">{avg_y:.1f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif spec.chart_type == "compare":
        teams = spec.teams or []
        st.markdown('<div class="summary-item">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label">Comparing</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-value">{" vs ".join(teams)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Teams analyzed
    st.markdown('<div class="summary-item">', unsafe_allow_html=True)
    st.markdown('<div class="summary-label">Teams Analyzed</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-value">{len(result_df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Window used
    window_display = window.replace("_", " ")
    st.markdown('<div class="summary-item">', unsafe_allow_html=True)
    st.markdown('<div class="summary-label">Time Window</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-value">{window_display}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # How it's calculated (collapsible)
    with st.expander("How it's calculated"):
        st.markdown(f"**Query Details:** {explanation}")

        # Add metric definitions
        if spec.chart_type == "leaderboard":
            metric = spec.metric
            if metric == "NET_RTG":
                st.markdown("**NET_RTG** = Offensive Rating - Defensive Rating. Positive values indicate scoring more points per 100 possessions than allowing.")
            elif metric == "ORtg":
                st.markdown("**ORtg** = Points scored per 100 possessions. Higher is better for offense.")
            elif metric == "DRtg":
                st.markdown("**DRtg** = Points allowed per 100 possessions. Lower is better for defense.")
            elif metric == "PACE":
                st.markdown("**PACE** = Possessions per game. Indicates game tempo.")
            elif metric == "eFG":
                st.markdown("**eFG** = Effective Field Goal %. Adjusts for 3-pointers being worth more (FGM + 0.5*3PM) / FGA.")
            elif metric == "TS":
                st.markdown("**TS** = True Shooting %. Accounts for 2s, 3s, and free throws: PTS / (2 * (FGA + 0.44*FTA)).")

        st.markdown("_All ratings use estimated possessions from team box scores. Possession estimate accuracy: ~99% vs play-by-play data._")

def render_results(result_df, spec, explanation, query_dict, season):
    """Render the complete results section with chart, summary, and table"""

    # Filter chips
    render_filter_chips(query_dict, season)

    # Two-column layout
    col_chart, col_summary = st.columns([0.65, 0.35])

    with col_chart:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Visualization</div>', unsafe_allow_html=True)

        try:
            fig = render_chart(spec, result_df)
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Chart rendering error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_summary:
        render_summary_card(spec, result_df, explanation, query_dict["window"])

    # Data table section
    st.markdown("### Data Table")

    # Format the dataframe for display
    display_df = result_df.copy()

    # Round numeric columns to 1 decimal place
    numeric_cols = display_df.select_dtypes(include=['float64', 'float32']).columns
    display_df[numeric_cols] = display_df[numeric_cols].round(1)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # Download button
    csv = result_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"nba_{spec.chart_type}_{spec.window}_{season}.csv",
        mime="text/csv"
    )

def render_welcome_screen():
    """Render the welcome/empty state screen"""
    st.markdown("""
    <div class="welcome-box">
        <h2 style="margin-top: 0;">Welcome to CourtVision</h2>
        <p style="font-size: 1.05rem; opacity: 0.8;">
            Use the sidebar to build a query manually or ask in natural language with AI.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Quick examples in cards
    st.markdown("### Analysis Examples")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Leaderboard</div>
            <p style="margin: 0; font-size: 0.9rem;">
                Rank teams by any metric. Perfect for identifying top performers in Net Rating, Offensive Efficiency, or Pace.
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem; font-style: italic; opacity: 0.6;">
                Try: "Top 10 teams by net rating"
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Scatter Plot</div>
            <p style="margin: 0; font-size: 0.9rem;">
                Compare two metrics across all teams. Visualize the offense vs defense landscape to find elite and struggling teams.
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem; font-style: italic; opacity: 0.6;">
                Try: "Show efficiency landscape"
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Team Comparison</div>
            <p style="margin: 0; font-size: 0.9rem;">
                Head-to-head comparison of key metrics between selected teams. See exactly how two teams stack up side-by-side.
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem; font-style: italic; opacity: 0.6;">
                Try: "Compare Celtics and Lakers"
            </p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# Sidebar Mode Functions
# ============================================================================

def render_manual_mode(df: pd.DataFrame, selected_season: str):
    """Manual query builder interface in sidebar"""
    st.sidebar.header("Manual Query Builder")

    chart_type = st.sidebar.selectbox(
        "Analysis Type",
        ["leaderboard", "scatter", "compare"],
        format_func=lambda x: {
            "leaderboard": "Leaderboard",
            "scatter": "Scatter Plot",
            "compare": "Team Comparison"
        }[x],
        help="Choose the type of analysis"
    )

    window_options = ["SEASON", "LAST_5", "LAST_10", "LAST_20"]
    window = st.sidebar.selectbox(
        "Time Window",
        window_options,
        index=2,
        format_func=lambda value: value.replace("_", " "),
        help="Filter games to this time window"
    )

    query_dict = {
        "chart_type": chart_type,
        "window": window,
    }

    if chart_type == "leaderboard":
        st.sidebar.markdown("**Leaderboard Options**")
        metric = st.sidebar.selectbox(
            "Metric",
            sorted(TEAM_METRICS_ALLOWLIST),
            index=sorted(TEAM_METRICS_ALLOWLIST).index("NET_RTG"),
            format_func=lambda value: value.replace("_", " ")
        )
        top_n = st.sidebar.number_input("Top N Teams", min_value=5, max_value=30, value=10)
        order = st.sidebar.radio("Sort Order", ["desc", "asc"],
                                 format_func=lambda x: "Highest first" if x == "desc" else "Lowest first")

        query_dict.update({
            "metric": metric,
            "top_n": top_n,
            "order": order
        })

    elif chart_type == "scatter":
        st.sidebar.markdown("**Scatter Options**")
        x_metric = st.sidebar.selectbox(
            "X-Axis Metric",
            sorted(TEAM_METRICS_ALLOWLIST),
            index=sorted(TEAM_METRICS_ALLOWLIST).index("ORtg"),
            format_func=lambda value: value.replace("_", " ")
        )
        y_metric = st.sidebar.selectbox(
            "Y-Axis Metric",
            sorted(TEAM_METRICS_ALLOWLIST),
            index=sorted(TEAM_METRICS_ALLOWLIST).index("DRtg"),
            format_func=lambda value: value.replace("_", " ")
        )

        query_dict.update({
            "x_metric": x_metric,
            "y_metric": y_metric
        })

    elif chart_type == "compare":
        st.sidebar.markdown("**Compare Options**")
        all_teams = sorted(df["TEAM_ABBREVIATION"].unique())

        team1 = st.sidebar.selectbox("Team 1", all_teams, index=0)
        team2 = st.sidebar.selectbox(
            "Team 2",
            [t for t in all_teams if t != team1],
            index=0
        )

        query_dict.update({
            "teams": [team1, team2]
        })

    if st.sidebar.button("Analyze", type="primary", use_container_width=True):
        with st.spinner("Computing metrics..."):
            execute_query(query_dict, df, selected_season)

    # Show error if any
    if st.session_state.get('error'):
        st.sidebar.error(f"Query failed: {st.session_state['error']}")


def render_ai_mode(df: pd.DataFrame, selected_season: str, available_seasons: list):
    """AI-powered natural language query interface in sidebar"""
    st.sidebar.header("AI Natural Language Query")
    st.sidebar.info("Ask a question about team performance in plain English!")

    # Example queries
    with st.sidebar.expander("Example Questions"):
        st.markdown("""
        - "Top 10 teams by net rating last 10 games"
        - "Show me the efficiency landscape"
        - "Compare Celtics vs Lakers"
        - "Worst 5 defenses this season"
        - "Best offenses in the last 5 games"
        - "Top teams by net rating in 2023-24"
        """)

    # Chat input
    user_query = st.sidebar.text_area(
        "Your Question:",
        placeholder="e.g., Show me the top 5 offenses in the last 10 games",
        height=120,
        key="ai_query_input"
    )

    if st.sidebar.button("Ask AI", type="primary", use_container_width=True):
        if not user_query.strip():
            st.sidebar.warning("Please enter a question!")
            return

        with st.spinner("Understanding your query..."):
            try:
                # Parse natural language to structured query
                query_dict = parse_natural_language_query(user_query)

                # Extract requested season (if any)
                requested_season = query_dict.pop("season", None)

                # Show what the AI understood
                st.sidebar.success("Query understood successfully!")
                with st.sidebar.expander("Parsed Query Structure"):
                    display_dict = query_dict.copy()
                    if requested_season:
                        display_dict["season"] = requested_season
                    st.json(display_dict)

                # Execute the query with season handling
                success, season_used, error = execute_ai_query(
                    query_dict, requested_season, available_seasons, selected_season
                )

                if success and requested_season and requested_season != selected_season:
                    st.sidebar.info(f"📅 Switched to {requested_season} season")
                elif not success:
                    st.sidebar.error(error)

            except ValueError as e:
                error_msg = str(e)

                # Handle CLARIFY responses
                if "CLARIFY:" in error_msg:
                    clarification = error_msg.replace("Failed to parse query: ", "").replace("CLARIFY:", "").strip()
                    st.sidebar.warning(f"🤔 Need clarification")
                    st.sidebar.info(clarification)

                # Handle OUT_OF_SCOPE responses
                elif "OUT_OF_SCOPE:" in error_msg:
                    scope_msg = error_msg.replace("Failed to parse query: ", "").replace("OUT_OF_SCOPE:", "").strip()
                    st.sidebar.error(f"⚠️ Query not supported")
                    st.sidebar.info(scope_msg)

                    # Show what IS supported
                    with st.sidebar.expander("See what you CAN ask"):
                        st.markdown("""
                        **Supported queries:**
                        - "Top 10 teams by net rating"
                        - "Show efficiency landscape"
                        - "Compare Celtics and Lakers"
                        - "Best offenses in the last 5 games"
                        - "Worst defenses this season"
                        """)

                # Generic parsing errors
                else:
                    st.sidebar.error(f"Failed to parse query: {e}")
                    st.sidebar.info("Try rephrasing your question or use the Manual Query Builder.")

            except Exception as e:
                st.sidebar.error(f"Unexpected error: {e}")
                st.sidebar.info("Try using the Manual Query Builder.")

    # Show error if any
    if st.session_state.get('error'):
        st.sidebar.error(f"Query execution failed: {st.session_state['error']}")

# ============================================================================
# Main Application
# ============================================================================

def main():
    # Header section
    col_title, col_badge = st.columns([4, 1])

    with col_title:
        st.title("CourtVision")
        st.markdown(
            '<p style="font-size: 1.05rem; opacity: 0.8; margin-bottom: 0.5rem;">AI-powered NBA team performance analytics</p>',
            unsafe_allow_html=True
        )

    with col_badge:
        st.markdown('<span class="ai-badge">AI POWERED</span>', unsafe_allow_html=True)

    # Get available seasons
    available_seasons = get_available_seasons()

    if not available_seasons:
        st.error("No season data found in your database.")
        st.info("Run `python ingest.py [SEASON]` to download data. Example: `python ingest.py 2024-25`")
        return

    # Season selector with session state for AI-triggered changes
    season_options = [season for season, _ in available_seasons]

    # Initialize or get the selected season from session state
    if 'ui_selected_season' not in st.session_state:
        st.session_state['ui_selected_season'] = season_options[0]

    # If a query was just run with a different season, update the UI selection
    if st.session_state.get('query_ran') and st.session_state.get('selected_season'):
        st.session_state['ui_selected_season'] = st.session_state['selected_season']

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Season Selection")

    with col2:
        # Find the index of the current season
        try:
            default_index = season_options.index(st.session_state['ui_selected_season'])
        except ValueError:
            default_index = 0

        selected_season = st.selectbox(
            "Season",
            season_options,
            index=default_index,
            label_visibility="collapsed",
            help="Select the NBA season to analyze",
            key="season_selector"
        )

        # Update session state when user manually changes season
        st.session_state['ui_selected_season'] = selected_season

    # Data timestamp
    today = datetime.now().strftime("%B %d, %Y")
    st.markdown(f'<p class="timestamp">Data as of: {today} (auto-refreshes daily)</p>', unsafe_allow_html=True)

    # Show warning if legacy file
    if "Legacy" in selected_season or "Rename" in selected_season:
        st.warning("Legacy file detected. Consider renaming for clarity.")

    st.markdown("---")

    # Load data for selected season
    try:
        df = load_data(selected_season)
    except Exception as e:
        st.error(f"Failed to load {selected_season} data: {e}")
        st.info(f"Run: `python ingest.py {selected_season.replace('-', '-')}` to download this season's data")
        return

    # ========================================================================
    # Sidebar: Mode Selection
    # ========================================================================

    mode = st.sidebar.radio(
        "Query Mode",
        ["Manual Query Builder", "AI Natural Language"],
        index=0,
        help="Choose how you want to build your query"
    )

    st.sidebar.markdown("---")

    # Render appropriate mode
    if mode == "Manual Query Builder":
        render_manual_mode(df, selected_season)
    else:
        render_ai_mode(df, selected_season, available_seasons)

    # ========================================================================
    # Results Section
    # ========================================================================

    # Display results or welcome screen
    if st.session_state.get('query_ran', False):
        result_df = st.session_state['result_df']
        spec = st.session_state['spec']
        explanation = st.session_state['explanation']
        query_dict = st.session_state['query_dict']
        selected_season = st.session_state['selected_season']

        if len(result_df) == 0:
            st.warning("No data found matching your criteria. Try adjusting your filters.")
        else:
            render_results(result_df, spec, explanation, query_dict, selected_season)
    else:
        render_welcome_screen()

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; opacity: 0.5; font-size: 0.85rem;">'
        'CourtVision | Data from nba_api | '
        'Metrics computed using estimated possessions'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
