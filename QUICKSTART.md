# 🚀 Quick Start Checklist

Follow these steps to get your NBA Analytics Tool running!

## Step 1: Install Dependencies ✅

```bash
pip install -r requirements.txt
```

**What this installs:**
- pandas, numpy (data handling)
- matplotlib (charts)
- nba_api (NBA data)
- streamlit (web UI)

---

## Step 2: Get the Data ✅

**Option A: Single Season (Quick)**
```bash
python ingest.py 2025-26
```

**Option B: Multiple Seasons (Recommended)**
```bash
python pull_multiple_seasons.py
```

**What this does:**
- Pulls NBA game logs from NBA API
- Saves to `data/processed/team_game_stats_YYYY_YY.csv`
- Takes ~30 seconds per season
- Option B pulls 5 recent seasons (2021-22 through 2025-26)

**Expected output:**
```
✅ Saved: data/processed/team_game_stats_2025_26.csv
📊 Rows: 1,230
📅 Date range: 2025-10-21 to 2026-01-13
```

**Verify what you have:**
```bash
python data_loader.py
```

---

## Step 3: Verify Everything Works ✅

**Test metrics calculations:**
```bash
python test_query.py
```

**Expected output:**
```
[PASS] Leaderboard test
[PASS] Scatter test
[PASS] Compare test
[PASS] Invalid metric rejection test
All query_engine tests passed.
```

**Test team logos (optional but recommended):**
```bash
python test_logos.py
```

This downloads all 30 NBA team logos. First run takes ~10 seconds. They're cached for instant loading afterwards.

---

## Step 4: Launch the App! 🎉

### Option A: Basic UI (easiest)

```bash
streamlit run streamlit_app.py
```

Then open: http://localhost:8501

**Features:**
- **Season dropdown** - pick which year to analyze
- Dropdown-based query builder
- All chart types
- Data table export

### Option B: UI with AI Chat

```bash
streamlit run streamlit_app_with_ai.py
```

**Extra features:**
- Natural language queries
- AI-powered query parsing
- Everything from Option A

---

## Step 5: Try Some Queries! 💡

**First: Select a season from the dropdown at the top**
- 2025-26: Current season (in progress)
- 2024-25: Last completed season
- Earlier seasons if you downloaded them

### In Manual Mode:

**Query 1: Best Teams Right Now**
- Chart Type: Leaderboard
- Metric: NET_RTG
- Top N: 10
- Window: LAST_10
- Click "Run Query"

**Query 2: Efficiency Landscape**
- Chart Type: Scatter
- X: ORtg
- Y: DRtg
- Window: SEASON
- Click "Run Query"

**Query 3: Rivalry Matchup**
- Chart Type: Compare
- Team 1: BOS (Celtics)
- Team 2: LAL (Lakers)
- Window: SEASON
- Click "Run Query"

### In AI Mode:

Just type naturally:
- "Show me the top 10 teams by net rating in the last 10 games"
- "efficiency landscape"
- "compare celtics and lakers"

---

## Troubleshooting

### "No season data found"
```bash
# Pull at least one season
python ingest.py 2025-26
```

### "Module not found" error
```bash
pip install -r requirements.txt
```

### "File not found: team_game_stats.csv"
**Old command won't work anymore!** Use:
```bash
python ingest.py 2025-26
```
Files now include season in name: `team_game_stats_2025_26.csv`

### Season not appearing in dropdown
```bash
# Check your files
ls data/processed/

# Files should be named: team_game_stats_YYYY_YY.csv
# If you have old file: team_game_stats.csv (no season)
# It will show as "Unknown Season (Legacy)" in dropdown
```

### Migrating from old version
See `MIGRATION.md` for detailed migration guide.

### Data looks wrong
```bash
# Delete old data and re-pull
rm -rf data/processed/team_game_stats.csv
python ingest.py
```

### Tests fail
Check that you've run `ingest.py` first. The tests need data to work.

### Port 8501 already in use
```bash
# Use a different port
streamlit run streamlit_app.py --server.port 8502
```

---

## Next Steps

Once the basic app works:

1. **Explore the data**
   - Try different metrics
   - Compare different time windows
   - Look for surprising patterns

2. **Customize the queries**
   - Edit `streamlit_app.py` to add presets
   - Modify `query_engine.py` defaults

3. **Add your own charts**
   - Create new visualization in `visualize.py`
   - Add chart type to `query_engine.py`

4. **Extend the metrics**
   - Add new formulas to `metrics.py`
   - Update `TEAM_METRICS_ALLOWLIST`

---

## Common Use Cases

### "I want to find the best defensive team"
- Leaderboard → DRtg → Top 10 → SEASON
- (Lower DRtg is better, so use order: asc)

### "Who has the best offense lately?"
- Leaderboard → ORtg → Top 10 → LAST_10

### "Show me which teams are balanced"
- Scatter → ORtg vs DRtg → SEASON
- Look for teams in the top-left quadrant (high O, low D)

### "How do my team's rivals stack up?"
- Compare → [Your team] vs [Rival] → SEASON

---

## Understanding the Results

### Leaderboard Charts
- **Bars**: Longer = better (except DRtg where shorter is better)
- **Colors**: Green = positive, Red = negative (for NET_RTG)
- **Numbers**: Exact values shown on bars

### Scatter Plots
- **Red dashed lines**: League average
- **Quadrants**: 
  - Top-left = Elite (high offense, low defense)
  - Bottom-right = Weak (low offense, high defense)

### Comparison Charts
- **Side-by-side bars**: Direct metric comparison
- **All key metrics shown**: ORtg, DRtg, NET_RTG, PACE

---

## What to Do if Something Breaks

1. Check the error message in Streamlit (it's usually helpful!)
2. Verify your data file exists: `ls data/processed/`
3. Re-run tests: `python test_query.py`
4. Check the README.md for detailed docs
5. Look at the code comments - everything is explained

---

## You're All Set! 🎯

Your NBA Analytics Tool V1 is ready to use. Start exploring team performance data and have fun discovering insights!

**Pro tip:** Try comparing your favorite team's performance in their last 5 games vs their season average. You might be surprised!
