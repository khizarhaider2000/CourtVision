# CourtVision - AI-Powered NBA Analytics Platform
# Mobile-first, single-column layout with tabs for query modes

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional

from query_engine import run_query, spec_from_dict, TEAM_METRICS_ALLOWLIST
from visualize import render_chart
from ai_query_parser import parse_natural_language_query
from data_loader import get_available_seasons, get_default_season, load_season_data

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="CourtVision",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# Custom CSS
# ============================================================================

st.markdown("""
<style>
    :root {
        --accent-orange: #FF6B35;
        --accent-orange-light: #FF8555;
        --border-color: rgba(128, 128, 128, 0.3);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Constrain content width for readability */
    .block-container {
        max-width: 860px !important;
        margin: 0 auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    /* Typography */
    h1 {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.2rem !important;
    }
    h2 {
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        margin-top: 1.2rem !important;
        margin-bottom: 0.6rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Hero section */
    .hero {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        margin-bottom: 0.5rem;
    }
    .hero h1 {
        font-size: 2.5rem !important;
        margin-bottom: 0.1rem !important;
    }
    .hero .tagline {
        font-size: 1.05rem;
        opacity: 0.7;
        margin-bottom: 0.3rem;
    }
    .ai-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.25rem 0.7rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Query input focus */
    .stTextArea textarea:focus {
        border-color: var(--accent-orange) !important;
        box-shadow: 0 0 0 2px rgba(255,107,53,0.15) !important;
    }

    /* AI feedback cards */
    .ai-feedback-success {
        background: rgba(76,175,80,0.08);
        border-left: 4px solid #4CAF50;
        border-radius: 4px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
    }
    .ai-feedback-clarify {
        background: rgba(255,193,7,0.08);
        border-left: 4px solid #FFC107;
        border-radius: 4px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
    }
    .ai-feedback-error {
        background: rgba(244,67,54,0.08);
        border-left: 4px solid #F44336;
        border-radius: 4px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
    }

    /* Filter chips */
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

    /* Card containers */
    .card {
        background: transparent;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(128,128,128,0.15);
    }
    .card-header {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--accent-orange);
    }

    /* Primary button */
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

    /* Timestamp */
    .timestamp {
        opacity: 0.6;
        font-size: 0.85rem;
        font-style: italic;
    }

    /* Welcome box */
    .welcome-box {
        background: rgba(255, 107, 53, 0.08);
        border: 1px solid rgba(255, 107, 53, 0.2);
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        margin: 1.5rem 0;
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

    /* Expander */
    .streamlit-expanderHeader {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }

    /* Mobile adjustments */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .hero h1 { font-size: 2rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Data Loading
# ============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(season: str):
    """Load and prepare data for a specific season from NBA API (cached)"""
    return load_season_data(season)

# ============================================================================
# Query Execution
# ============================================================================

def execute_query(query_dict: dict, df: pd.DataFrame, season: str):
    """Execute a query and store results in session state"""
    try:
        spec = spec_from_dict(query_dict)
        result_df, explanation = run_query(df, spec)

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
    """Execute AI query with automatic season switching if needed."""
    if requested_season:
        season_names = [s for s, _ in available_seasons]
        if requested_season not in season_names:
            return False, current_season, f"Season {requested_season} data not available. Available: {', '.join(season_names)}"
        try:
            df = load_data(requested_season)
            execute_query(query_dict, df, requested_season)
            return True, requested_season, None
        except Exception as e:
            return False, current_season, f"Failed to load {requested_season} data: {e}"
    else:
        try:
            df = load_data(current_season)
            execute_query(query_dict, df, current_season)
            return True, current_season, None
        except Exception as e:
            return False, current_season, f"Query execution failed: {e}"

# ============================================================================
# UI Components
# ============================================================================

def render_hero(season_options):
    """Render centered hero header with season selector"""
    st.markdown("""
    <div class="hero">
        <h1>CourtVision</h1>
        <p class="tagline">AI-powered NBA team performance analytics</p>
        <span class="ai-badge">AI POWERED</span>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_season = st.columns([3, 1])

    with col_left:
        today = datetime.now().strftime("%B %d, %Y")
        st.markdown(f'<p class="timestamp">Data as of {today}</p>', unsafe_allow_html=True)

    with col_season:
        if 'ui_selected_season' not in st.session_state:
            st.session_state['ui_selected_season'] = season_options[0]

        if st.session_state.get('query_ran') and st.session_state.get('selected_season'):
            st.session_state['ui_selected_season'] = st.session_state['selected_season']

        try:
            default_index = season_options.index(st.session_state['ui_selected_season'])
        except ValueError:
            default_index = 0

        selected_season = st.selectbox(
            "Season",
            season_options,
            index=default_index,
            label_visibility="collapsed",
            key="season_selector"
        )
        st.session_state['ui_selected_season'] = selected_season

    return selected_season


def render_ai_feedback(parsed_result):
    """Render styled AI feedback inline in the main area"""
    result_type = parsed_result.get("result_type")
    message = parsed_result.get("message", "")

    if result_type == "CLARIFY":
        st.markdown(f"""
        <div class="ai-feedback-clarify">
            <strong>Need a bit more detail</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)

    elif result_type == "OUT_OF_SCOPE":
        st.markdown(f"""
        <div class="ai-feedback-error">
            <strong>Not supported</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)
        with st.expander("What you CAN ask"):
            st.markdown("""
            - "Top 10 teams by net rating"
            - "Show efficiency landscape"
            - "Compare Celtics and Lakers"
            - "Best offenses in the last 5 games"
            - "Worst defenses this season"
            """)

    elif result_type == "QUERY":
        query_display = {k: v for k, v in parsed_result.items() if k not in ("result_type", "message")}
        st.markdown("""
        <div class="ai-feedback-success">
            <strong>Query understood</strong>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Parsed query"):
            st.json(query_display)


def render_ai_tab(selected_season, available_seasons):
    """AI natural language query tab content"""
    st.markdown("Ask a question about NBA team performance in plain English.")

    user_query = st.text_area(
        "Your question",
        placeholder='e.g. "Top 10 teams by net rating last 10 games"',
        height=100,
        key="ai_query_input",
        label_visibility="collapsed"
    )

    with st.expander("Example questions"):
        st.markdown("""
        - "Top 10 teams by net rating last 10 games"
        - "Show me the efficiency landscape"
        - "Compare Celtics vs Lakers"
        - "Worst 5 defenses this season"
        - "Best offenses in the last 5 games"
        - "Top teams by net rating in 2023-24"
        """)

    if st.button("Analyze", type="primary", use_container_width=True, key="ai_analyze"):
        if not user_query.strip():
            st.warning("Please enter a question.")
            return

        with st.status("Analyzing your question...", expanded=True) as status:
            status.update(label="Parsing natural language...")
            try:
                parsed_result = parse_natural_language_query(user_query)
                st.session_state['ai_feedback'] = parsed_result
                result_type = parsed_result.get("result_type")

                if result_type in ("CLARIFY", "OUT_OF_SCOPE"):
                    status.update(label="Needs clarification", state="complete")
                    return

                if result_type == "QUERY":
                    status.update(label="Running query...")
                    query_dict = {k: v for k, v in parsed_result.items()
                                  if k not in ("result_type", "message", "season")}
                    requested_season = parsed_result.get("season")

                    success, _, error = execute_ai_query(
                        query_dict, requested_season, available_seasons, selected_season
                    )

                    if success:
                        if requested_season and requested_season != selected_season:
                            st.session_state['ai_feedback_note'] = f"Switched to {requested_season} season"
                        status.update(label="Done!", state="complete")
                    else:
                        st.session_state['error'] = error
                        status.update(label="Query failed", state="error")
                else:
                    status.update(label="Unexpected response", state="error")

            except Exception as e:
                st.session_state['ai_feedback'] = {
                    "result_type": "OUT_OF_SCOPE",
                    "message": f"Unexpected error: {e}. Try rephrasing or use the Manual Builder tab."
                }
                status.update(label="Error", state="error")

    # Show persisted AI feedback
    if st.session_state.get('ai_feedback'):
        render_ai_feedback(st.session_state['ai_feedback'])

    if st.session_state.get('ai_feedback_note'):
        st.info(st.session_state['ai_feedback_note'])

    if st.session_state.get('error'):
        st.error(st.session_state['error'])


def render_manual_tab(df, selected_season):
    """Manual query builder tab content"""
    col1, col2 = st.columns(2)

    with col1:
        chart_type = st.selectbox(
            "Analysis Type",
            ["leaderboard", "scatter", "compare"],
            format_func=lambda x: {"leaderboard": "Leaderboard", "scatter": "Scatter Plot", "compare": "Team Comparison"}[x]
        )
    with col2:
        window = st.selectbox(
            "Time Window",
            ["SEASON", "LAST_5", "LAST_10", "LAST_20"],
            index=2,
            format_func=lambda v: v.replace("_", " ")
        )

    query_dict = {"chart_type": chart_type, "window": window}

    if chart_type == "leaderboard":
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            metric = st.selectbox("Metric", sorted(TEAM_METRICS_ALLOWLIST),
                                  index=sorted(TEAM_METRICS_ALLOWLIST).index("NET_RTG"))
        with col_b:
            top_n = st.number_input("Top N", min_value=5, max_value=30, value=10)
        with col_c:
            order = st.radio("Sort", ["desc", "asc"],
                             format_func=lambda x: "Highest first" if x == "desc" else "Lowest first")
        query_dict.update({"metric": metric, "top_n": top_n, "order": order})

    elif chart_type == "scatter":
        col_a, col_b = st.columns(2)
        with col_a:
            x_metric = st.selectbox("X-Axis", sorted(TEAM_METRICS_ALLOWLIST),
                                    index=sorted(TEAM_METRICS_ALLOWLIST).index("ORtg"))
        with col_b:
            y_metric = st.selectbox("Y-Axis", sorted(TEAM_METRICS_ALLOWLIST),
                                    index=sorted(TEAM_METRICS_ALLOWLIST).index("DRtg"))
        query_dict.update({"x_metric": x_metric, "y_metric": y_metric})

    elif chart_type == "compare":
        all_teams = sorted(df["TEAM_ABBREVIATION"].unique())
        col_a, col_b = st.columns(2)
        with col_a:
            team1 = st.selectbox("Team 1", all_teams, index=0)
        with col_b:
            team2 = st.selectbox("Team 2", [t for t in all_teams if t != team1], index=0)
        query_dict.update({"teams": [team1, team2]})

    if st.button("Analyze", type="primary", use_container_width=True, key="manual_analyze"):
        with st.spinner("Computing metrics..."):
            execute_query(query_dict, df, selected_season)

    if st.session_state.get('error'):
        st.error(st.session_state['error'])


def render_filter_chips(query_dict, season):
    """Display active filters as chips"""
    chips_html = '<div style="margin: 0.8rem 0;">'
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Season:</span> {season}</span>'

    window_display = query_dict.get("window", "").replace("_", " ")
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Window:</span> {window_display}</span>'

    chart_type = query_dict.get("chart_type", "").title()
    chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Type:</span> {chart_type}</span>'

    if query_dict.get("metric"):
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Metric:</span> {query_dict["metric"]}</span>'
    if query_dict.get("top_n"):
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Top:</span> {query_dict["top_n"]}</span>'
    if query_dict.get("order"):
        order_text = "Highest first" if query_dict["order"] == "desc" else "Lowest first"
        chips_html += f'<span class="filter-chip"><span class="filter-chip-label">Sort:</span> {order_text}</span>'

    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)


def render_insights_row(spec, result_df):
    """Render key insights as st.metric() widgets in a row"""
    if spec.chart_type == "leaderboard" and len(result_df) > 0:
        top_team = result_df.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Top Team", top_team["TEAM_ABBREVIATION"])
        col2.metric(spec.metric, f"{top_team[spec.metric]:.1f}")
        col3.metric("Teams Shown", len(result_df))

    elif spec.chart_type == "scatter":
        avg_x = result_df[spec.x_metric].mean()
        avg_y = result_df[spec.y_metric].mean()
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Avg {spec.x_metric}", f"{avg_x:.1f}")
        col2.metric(f"Avg {spec.y_metric}", f"{avg_y:.1f}")
        col3.metric("Teams Plotted", len(result_df))

    elif spec.chart_type == "compare":
        teams = spec.teams or []
        col1, col2 = st.columns(2)
        col1.metric("Comparing", " vs ".join(teams))
        col2.metric("Metrics Shown", "All key metrics")


def render_results(result_df, spec, explanation, query_dict, season):
    """Render results in single-column layout"""
    # Auto-scroll to chart results on render
    import streamlit.components.v1 as components
    components.html("""
        <script>
            window.parent.document.querySelector('[data-testid="stVerticalBlockBorderWrapper"]')
                ?.closest('section')
                ?.scrollIntoView({behavior: 'smooth', block: 'start'});
            // Fallback: scroll parent window down past the tabs
            window.parent.scrollTo({top: window.parent.document.body.scrollHeight * 0.4, behavior: 'smooth'});
        </script>
    """, height=0)

    render_filter_chips(query_dict, season)

    # Chart - full width
    try:
        fig = render_chart(spec, result_df)
        st.pyplot(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart rendering error: {e}")

    # Key insights row
    st.markdown("### Key Insights")
    render_insights_row(spec, result_df)

    # How it's calculated
    with st.expander("How it's calculated"):
        st.markdown(f"**Query:** {explanation}")

        if spec.chart_type == "leaderboard":
            metric = spec.metric
            defs = {
                "NET_RTG": "**NET_RTG** = Offensive Rating - Defensive Rating. Positive = outscoring opponents per 100 possessions.",
                "ORtg": "**ORtg** = Points scored per 100 possessions. Higher is better.",
                "DRtg": "**DRtg** = Points allowed per 100 possessions. Lower is better.",
                "PACE": "**PACE** = Possessions per game. Indicates tempo.",
                "eFG": "**eFG** = Effective FG%. Adjusts for 3-pointers: (FGM + 0.5*3PM) / FGA.",
                "TS": "**TS** = True Shooting%. Accounts for 2s, 3s, and FTs: PTS / (2 * (FGA + 0.44*FTA)).",
            }
            if metric in defs:
                st.markdown(defs[metric])

        st.markdown("_Ratings use estimated possessions (~99% accuracy vs play-by-play)._")

    # Data table
    st.markdown("### Data Table")
    display_df = result_df.copy()
    numeric_cols = display_df.select_dtypes(include=['float64', 'float32']).columns
    display_df[numeric_cols] = display_df[numeric_cols].round(1)

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

    csv = result_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"nba_{spec.chart_type}_{spec.window}_{season}.csv",
        mime="text/csv"
    )


def render_welcome_screen():
    """Render welcome/empty state"""
    st.markdown("""
    <div class="welcome-box">
        <h2 style="margin-top: 0;">Welcome to CourtVision</h2>
        <p style="font-size: 1.05rem; opacity: 0.8;">
            Use the AI Query or Manual Builder tab above to start analyzing NBA team performance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Analysis Examples")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Leaderboard</div>
            <p style="margin: 0; font-size: 0.9rem;">
                Rank teams by any metric: Net Rating, Offensive Efficiency, Pace, and more.
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
                Compare two metrics across all teams. Visualize the offense vs defense landscape.
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
                Head-to-head comparison of key metrics between two teams side-by-side.
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem; font-style: italic; opacity: 0.6;">
                Try: "Compare Celtics and Lakers"
            </p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# Main Application
# ============================================================================

def main():
    # Get available seasons
    available_seasons = get_available_seasons()
    if not available_seasons:
        available_seasons = [(get_default_season() or "2024-25", None)]

    season_options = [season for season, _ in available_seasons]

    # Hero + season selector
    selected_season = render_hero(season_options)

    st.markdown("---")

    # Load data
    try:
        df = load_data(selected_season)
    except Exception as e:
        st.error("Failed to load NBA data. Please try again.")
        st.caption(str(e))
        if st.button("Retry"):
            st.cache_data.clear()
            st.rerun()
        return

    # Tabs for query mode
    tab_ai, tab_manual = st.tabs(["AI Query", "Manual Builder"])

    with tab_ai:
        render_ai_tab(selected_season, available_seasons)

    with tab_manual:
        render_manual_tab(df, selected_season)

    st.markdown("---")

    # Results or welcome screen
    if st.session_state.get('query_ran', False):
        result_df = st.session_state['result_df']
        spec = st.session_state['spec']
        explanation = st.session_state['explanation']
        query_dict = st.session_state['query_dict']
        display_season = st.session_state['selected_season']

        if len(result_df) == 0:
            st.warning("No data found. Try adjusting your filters.")
        else:
            render_results(result_df, spec, explanation, query_dict, display_season)
    else:
        render_welcome_screen()

    # Footer
    st.markdown("---")
    with st.expander("About CourtVision"):
        st.markdown("""
        **CourtVision** analyzes NBA team performance using data from the official NBA API.

        **Metrics computed:** ORtg, DRtg, Net Rating, Pace, PPG, eFG%, TS%, AST Rate, TOV Rate.
        All ratings use estimated possessions from team box scores (~99% accuracy vs play-by-play data).

        **Data source:** nba_api | **AI:** OpenAI for natural language parsing
        """)


if __name__ == "__main__":
    main()
