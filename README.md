# 🏀 NBA Analytics Tool V1

A comprehensive NBA team analytics tool that computes advanced metrics and provides interactive visualizations. Built with Python, Streamlit, and the NBA API.

## Features

✅ **Complete Metric Suite**
- Offensive Rating (ORtg), Defensive Rating (DRtg), Net Rating
- Shooting efficiency: eFG%, True Shooting %
- Pace, Assist Rate, Turnover Rate
- All metrics normalized per 100 possessions

✅ **Multiple Visualization Types**
- **Leaderboard**: Top N teams by any metric
- **Scatter Plot**: Efficiency landscapes with team logos (ORtg vs DRtg)
- **Compare**: Head-to-head team comparisons

✅ **Team Logos in Scatter Plots**
- Automatically downloads and caches official NBA team logos
- Displays logos instead of circles for easier team identification
- Graceful fallback to circles if logos unavailable

✅ **Flexible Time Windows**
- Full season
- Last 5, 10, or 20 games

✅ **Two Query Modes**
- **Manual**: Dropdown-based query builder
- **AI Chat**: Natural language queries (optional)

## Project Structure

```
nba-analytics/
├── ingest.py              # Data ingestion from nba_api (multi-season)
├── data_loader.py         # Season management and data loading
├── pull_multiple_seasons.py  # Helper to pull multiple seasons
├── metrics.py             # Core metric calculations
├── query_engine.py        # Structured query system
├── charts.py              # Legacy chart functions
├── visualize.py           # Enhanced visualization layer
├── ai_query_parser.py     # Natural language query parser
├── app.py                 # CLI demo script
├── test_query.py          # Query engine tests
├── streamlit_app.py       # Basic Streamlit UI
├── streamlit_app_with_ai.py  # Enhanced UI with AI chat
├── requirements.txt       # Python dependencies
├── README.md              # Full documentation
├── QUICKSTART.md          # Quick start guide
├── MIGRATION.md           # Migration guide for multi-season
└── data/
    └── processed/
        ├── team_game_stats_2025_26.csv  # Current season
        ├── team_game_stats_2024_25.csv  # Last season
        └── team_game_stats_2023_24.csv  # etc...
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Pull NBA Data

**Single Season:**
```bash
# Pull current season (2025-26)
python ingest.py 2025-26

# Pull specific season
python ingest.py 2024-25

# Pull playoffs
python ingest.py 2024-25 "Playoffs"
```

**Multiple Seasons (Recommended):**
```bash
# Pulls last 5 seasons automatically
python pull_multiple_seasons.py
```

This will:
- Fetch team game logs from the NBA API
- Process and save to `data/processed/team_game_stats_YYYY_YY.csv`
- Take ~30 seconds per season
- Add small delays between requests to be API-friendly

**Available Seasons:**
- 2025-26 (current season, in progress)
- 2024-25, 2023-24, 2022-23, 2021-22, etc.
- Regular Season or Playoffs

### 3. Verify Your Data

```bash
# List available seasons
python data_loader.py
```

### 4. (Optional) Test Logo Functionality

```bash
python test_logos.py
```

This will download and verify all NBA team logos. First run takes ~10 seconds to download all logos. They're cached in `data/logos/` for instant loading afterwards.

### 5. (Optional) Run Tests

```bash
python test_query.py
```

Validates that the query engine works correctly.

## Usage

### Option 1: Streamlit UI (Recommended)

**Basic UI (Manual queries only):**
```bash
streamlit run streamlit_app.py
```

**Enhanced UI (with AI chat):**
```bash
streamlit run streamlit_app_with_ai.py
```

Then open your browser to http://localhost:8501

**In the app:**
1. **Select a season** from the dropdown at the top
2. Build your query using the sidebar
3. View charts, tables, and insights
4. Switch seasons to compare different years

### Option 2: Command Line

```bash
python app.py
```

This runs a demo that:
- Computes top 10 teams by Net Rating
- Generates an efficiency landscape plot
- Prints results to console

### Option 3: Python API

```python
from data_loader import load_season_data, get_available_seasons
from query_engine import run_query, spec_from_dict

# See what seasons you have
seasons = get_available_seasons()
print(f"Available: {[s for s, _ in seasons]}")

# Load a specific season
df = load_season_data("2025-26")

# Build a query
query_dict = {
    "chart_type": "leaderboard",
    "metric": "NET_RTG",
    "top_n": 10,
    "window": "LAST_10"
}

# Run query
spec = spec_from_dict(query_dict)
result_df, explanation = run_query(df, spec)

print(result_df)

# Compare across seasons
df_current = load_season_data("2025-26")
df_last = load_season_data("2024-25")
# Run same query on both to compare!
```

## Query Examples

### Manual Mode

1. **Leaderboard**: Top 10 by Net Rating, Last 10 Games
   - Chart Type: leaderboard
   - Metric: NET_RTG
   - Top N: 10
   - Window: LAST_10

2. **Scatter**: Offensive vs Defensive Rating, Season
   - Chart Type: scatter
   - X: ORtg
   - Y: DRtg
   - Window: SEASON

3. **Compare**: Celtics vs Lakers
   - Chart Type: compare
   - Teams: BOS, LAL
   - Window: SEASON

### AI Chat Mode

Just ask naturally:
- "Show me the top 10 teams by net rating in the last 10 games"
- "Efficiency landscape for the season"
- "Compare Celtics and Lakers"
- "Worst 5 defenses in the last 20 games"
- "Best offenses this season"

## Metric Definitions

### Ratings (per 100 possessions)
- **ORtg**: Offensive Rating = 100 × (Points Scored / Possessions)
- **DRtg**: Defensive Rating = 100 × (Points Allowed / Opponent Possessions)
- **NET_RTG**: Net Rating = ORtg - DRtg

### Shooting Efficiency
- **eFG%**: Effective Field Goal % = (FGM + 0.5 × 3PM) / FGA
- **TS%**: True Shooting % = PTS / (2 × (FGA + 0.44 × FTA))

### Pace & Style
- **PACE**: Estimated possessions per game
- **AST_RATE**: Assists / Possessions
- **TOV_RATE**: Turnovers / Possessions
- **PPG**: Points per game

### Possession Estimation
POSS ≈ FGA + 0.44 × FTA - OREB + TOV

This is the standard Dean Oliver formula used across the NBA analytics community.

## Architecture

### Data Flow

```
nba_api → ingest.py → team_game_stats.csv
                              ↓
                     prepare_team_games_for_metrics()
                              ↓
                    [Normalized + Possessions + Metrics]
                              ↓
                        query_engine.py
                     [Validates + Aggregates]
                              ↓
                         visualize.py
                    [Generates Chart + Summary]
                              ↓
                          Streamlit UI
```

### Key Design Decisions

1. **Canonical Dataset**: One row per team per game
   - Easy to filter by time window
   - Opponent pairing happens at query time

2. **Query Engine**: Separates concerns
   - Validation: Ensures valid metric/window combos
   - Aggregation: Computes metrics correctly
   - Explanation: Describes what was computed

3. **Opponent Pairing**: For defensive metrics
   - DRtg requires knowing points allowed
   - Each team's game row is joined with opponent's game row
   - This is why offense-only metrics are faster

4. **Modular Charts**: Each chart type is isolated
   - Easy to add new chart types
   - Consistent styling across charts

## Extending the Tool

### Add a New Metric

1. Add calculation to `metrics.py`:
```python
def add_new_metric(df: pd.DataFrame) -> pd.DataFrame:
    df["NEW_METRIC"] = ...  # your formula
    return df
```

2. Add to allowlist in `query_engine.py`:
```python
TEAM_METRICS_ALLOWLIST = {
    ...,
    "NEW_METRIC",
}
```

3. Update aggregation functions if needed

### Add a New Chart Type

1. Add to `visualize.py`:
```python
def _render_new_chart(spec: ChartSpec, df: pd.DataFrame) -> plt.Figure:
    # your visualization code
    return fig
```

2. Add to `query_engine.py` ChartType literal and validation

### Add Player-Level Metrics

Currently only supports team-level. For players:
1. Create new endpoint in `ingest.py` (use `LeagueGameLog` with player_or_team='P')
2. Create parallel `player_metrics.py` with player calculations
3. Update `query_engine.py` to handle `entity="player"`

## Known Limitations (V1.1)

- Team-level only (no player stats)
- No cross-season comparisons yet (can view one season at a time)
- No playoff vs regular season toggle in UI
- AI query parser is rule-based (not using Claude API yet)
- No database (CSV files only)
- No injury/lineup context

## Roadmap

**V1.1 (Current):**
- [x] Multi-season support
- [x] Season selector in UI
- [x] Backward compatibility with old data

**V2+:**
- [ ] Cross-season comparisons (team performance trends)
- [ ] Player-level metrics
- [ ] Playoff vs Regular Season toggle
- [ ] Advanced metrics (BPM, RAPTOR, etc.)
- [ ] Lineup analysis
- [ ] Database backend (SQLite/PostgreSQL)
- [ ] Real Claude API for query parsing
- [ ] Export to PDF/PowerPoint
- [ ] Predictive models
- [ ] Head-to-head game predictions

## Data Source

All data comes from [nba_api](https://github.com/swar/nba-api), which pulls from NBA.com's official stats API.

## License

MIT License - feel free to use and modify!

## Credits

Built with:
- [nba_api](https://github.com/swar/nba-api) - NBA data
- [Streamlit](https://streamlit.io/) - Web UI
- [Matplotlib](https://matplotlib.org/) - Visualizations
- [Pandas](https://pandas.pydata.org/) - Data manipulation

Metrics formulas based on Dean Oliver's "Basketball on Paper" and Basketball Reference.

---

**Questions?** Open an issue or check the code comments - everything is documented!
