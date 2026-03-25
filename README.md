#  CourtVision V1

**AI-Powered NBA Team Performance Analytics Platform**

A comprehensive NBA analytics tool that combines advanced metrics, interactive visualizations, and natural language AI queries. Built with Python, Streamlit, and the NBA API.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Features

### 🎯 Core Analytics
- **Complete Metric Suite**: ORtg, DRtg, NET_RTG, eFG%, TS%, PACE, AST_RATE, TOV_RATE
- **Multiple Visualizations**: Leaderboards, scatter plots, team comparisons
- **Team Logos**: Official NBA logos in scatter plots for easy identification
- **Flexible Time Windows**: Season, Last 5/10/20 games
- **Multi-Season Support**: Analyze and compare different seasons

### 🤖 AI-Powered Queries
- **Natural Language**: Ask questions in plain English
- **Smart Validation**: Automatic detection of out-of-scope requests
- **Season Detection**: Automatically switches seasons when mentioned
- **Query Examples**:
  - "Top 10 teams by net rating in the last 10 games"
  - "Show me the efficiency landscape for 2023-24"
  - "Compare Celtics and Lakers"

### 🎨 Professional UI
- **Dark/Light Mode Support**: Adapts to your preference
- **Basketball Orange Accent**: Clean, sports-focused design
- **Real-time Updates**: Auto-refreshes data daily
- **Responsive Layout**: Works on desktop and tablet
- **Export Options**: Download charts and data as CSV

## REST API (Phase 1)

A FastAPI layer wraps the existing analytics logic over HTTP.

### Run the API locally

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`.

## React Frontend

A routed React frontend lives in `frontend/` and can also be controlled from the repo root.

### Run locally

Backend:

```bash
uvicorn api.main:app --reload
```

Frontend:

```bash
npm run dev
```

This starts the Vite app from `frontend/` and proxies API requests to `http://localhost:8000`.

### Build the frontend

```bash
npm run build
```

The production build is written to `frontend/dist`.

### Configure API base URL

For local development, no extra frontend environment variable is required if the API is running on `http://localhost:8000`.

For production, set:

```bash
VITE_API_BASE_URL=https://your-backend-origin
```

You can place this in `frontend/.env.local`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/seasons` | Available NBA seasons |
| POST | `/ai/parse` | Parse natural language → QuerySpec |
| POST | `/query` | Execute a structured chart query |
| POST | `/metrics` | Full team metrics for a season/window |

### Example

```bash
# Health check
curl http://localhost:8000/health

# Parse a natural language query
curl -X POST http://localhost:8000/ai/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "top 10 teams by net rating last 10 games"}'

# Run a leaderboard query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"season":"2024-25","chart_type":"leaderboard","metric":"NET_RTG","top_n":5}'
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd nba-ai-analyzer

# Install dependencies
pip install -r requirements.txt
```

### 2. Pull NBA Data

**Single Season:**
```bash
# Pull current season (2025-26)
python ingest.py 2025-26

# Pull specific season
python ingest.py 2024-25
```

**Multiple Seasons (Recommended):**
```bash
# Pulls last 5 seasons automatically
python pull_multiple_seasons.py
```

### 3. Launch CourtVision

**React Frontend + API (Recommended):**

```bash
uvicorn api.main:app --reload
npm run dev
```

Then open `http://localhost:5173`

**Streamlit AI Version:**
```bash
streamlit run streamlit_ai.py
```

Then open your browser to `http://localhost:8501`

## 📊 Usage

### Manual Mode
1. Select season from dropdown
2. Choose analysis type (Leaderboard/Scatter/Compare)
3. Configure metrics and filters
4. Click "Analyze"

### AI Mode
Just ask naturally in the sidebar:
- "Top 10 teams by net rating last 10 games"
- "Show me the efficiency landscape"
- "Compare Celtics vs Lakers in 2023-24"
- "Worst 5 defenses this season"

The AI automatically:
- Detects the chart type you want
- Extracts metrics and filters
- Switches seasons when mentioned
- Validates your request is supported

## 🏗️ Project Structure

```
nba-ai-analyzer/
├── streamlit_ai.py          # AI-powered UI (main app)
├── streamlit_app.py         # Manual mode UI
├── ai_query_parser.py       # Natural language query parser
├── query_engine.py          # Structured query system
├── visualize.py             # Chart rendering
├── metrics.py               # Metric calculations
├── data_loader.py           # Season management
├── ingest.py                # Data ingestion from NBA API
├── pull_multiple_seasons.py # Multi-season data puller
├── requirements.txt         # Python dependencies
├── ENABLE_CLAUDE_API.md     # Guide for Claude API integration
└── data/
    ├── processed/           # CSV data files
    │   ├── team_game_stats_2025_26.csv
    │   ├── team_game_stats_2024_25.csv
    │   └── team_game_stats_2023_24.csv
    └── team_logos/          # Cached NBA team logos
```

## 📈 Supported Metrics

### Ratings (per 100 possessions)
- **ORtg**: Offensive Rating - Points scored per 100 possessions
- **DRtg**: Defensive Rating - Points allowed per 100 possessions
- **NET_RTG**: Net Rating - ORtg minus DRtg

### Shooting Efficiency
- **eFG%**: Effective Field Goal % - Accounts for 3-pointers being worth more
- **TS%**: True Shooting % - Accounts for 2s, 3s, and free throws

### Pace & Style
- **PACE**: Estimated possessions per game
- **AST_RATE**: Assists per possession
- **TOV_RATE**: Turnovers per possession
- **PPG**: Points per game

All metrics normalized using Dean Oliver's possession estimation formula.

## 🔧 Configuration

### Enable Claude API for AI Queries

The AI query parser currently uses rule-based parsing. To enable the full Claude API:

1. Install Anthropic SDK:
```bash
pip install anthropic
```

2. Set your API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

3. Follow instructions in [ENABLE_CLAUDE_API.md](ENABLE_CLAUDE_API.md)

Benefits:
- More robust natural language understanding
- Better handling of complex queries
- Typo tolerance
- Semantic intent detection

## 🎨 Customization

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

### Add a New Chart Type

1. Implement in `visualize.py`:
```python
def _render_new_chart(spec: ChartSpec, df: pd.DataFrame) -> plt.Figure:
    # your visualization code
    return fig
```

2. Update ChartType in `query_engine.py`

## 🧪 Testing

```bash
# Test query engine
python test_query.py

# Test team logos
python test_logos.py

# Test season data loading
python data_loader.py
```

## 🌟 Key Features Explained

### OUT_OF_SCOPE Validation
CourtVision intelligently rejects unsupported queries:
- ❌ Custom date ranges ("since Christmas")
- ❌ Clutch stats or quarter-specific filters
- ❌ Player-level statistics
- ❌ Live/real-time data
- ❌ Predictions or future games

Instead, it suggests valid alternatives.

### Automatic Season Switching
When you mention a season in your query, CourtVision:
1. Detects the season (e.g., "2023-24")
2. Validates it exists in your data
3. Loads the correct season automatically
4. Updates the UI dropdown to match

### Smart Caching
- Data cached for 24 hours for fast performance
- Logos cached locally (download once, use forever)
- Session state preserves query results

## 📝 Data Source

All data from [nba_api](https://github.com/swar/nba-api), which pulls from NBA.com's official stats API.

## 🗺️ Roadmap

**Current (V1.0):**
- ✅ Multi-season support
- ✅ AI natural language queries
- ✅ Professional UI with dark mode
- ✅ Team logo scatter plots
- ✅ OUT_OF_SCOPE validation
- ✅ Automatic season switching

**Future:**
- [ ] Cross-season trend analysis
- [ ] Player-level metrics
- [ ] Advanced stats (BPM, RAPTOR)
- [ ] Database backend (PostgreSQL)
- [ ] PDF/PowerPoint export
- [ ] Predictive models
- [ ] Lineup analysis

## 🐛 Known Limitations

- Team-level only (no player stats)
- Regular season data (playoff toggle coming)
- No injury/lineup context
- AI parser is rule-based (Claude API integration available but optional)

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Credits

Built with:
- [nba_api](https://github.com/swar/nba-api) - NBA data
- [Streamlit](https://streamlit.io/) - Web framework
- [Matplotlib](https://matplotlib.org/) - Visualizations
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [Claude API](https://www.anthropic.com) - AI query parsing (optional)

Metrics formulas based on Dean Oliver's "Basketball on Paper" and Basketball Reference.

## 💡 Tips

- Use `streamlit_ai.py` for the best experience
- Pull multiple seasons with `pull_multiple_seasons.py` for cross-season comparison
- Download logos once with `test_logos.py` for faster scatter plots
- Enable Claude API for more robust AI queries
- Check data freshness - runs auto-refresh daily

---

**Questions?** Check the code comments or open an issue - everything is documented!

Built with ❤️ for NBA analytics enthusiasts
