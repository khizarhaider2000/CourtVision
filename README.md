# CourtVision

CourtVision is a full-stack NBA analytics app for exploring team performance across regular-season and playoff data. It combines a React/Vite frontend with a FastAPI backend that pulls NBA data, computes team metrics with Pandas, and returns JSON responses for charts, tables, and natural-language queries.

The app is designed around three workflows:

- **AI Query**: ask questions like "top playoff offenses" or "compare Lakers and Nuggets in the playoffs"
- **Analytics**: build structured leaderboard, scatter, and comparison queries with filters
- **Teams**: view sortable team metric tables for a selected season, mode, and time window

## Features

- Regular Season and Playoffs modes with validated `season_type` handling
- Team-level metrics: `NET_RTG`, `ORtg`, `DRtg`, `PACE`, `PPG`, `eFG`, `TS`, `AST_RATE`, `TOV_RATE`, and `Opp_TOV%`
- Time windows: full season, last 5 games, last 10 games, and last 20 games
- Natural-language parser with rule-based defaults and optional OpenAI support
- Cached NBA season datasets with live `nba_api` fallback
- JSON-safe FastAPI responses for charts and data tables
- React charts, comparison views, sortable tables, CSV export, loading states, and API error states
- Production frontend on Vercel and Dockerized backend deployment support for Render

## Tech Stack

| Layer | Tools |
|------|-------|
| Frontend | React, Vite, CSS Modules |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Data | Pandas, NumPy, nba_api |
| Deployment | Vercel, Render, Docker |
| Testing | Pytest, FastAPI TestClient, Vite production build |

## Architecture

```text
Browser
  |
  v
React/Vite frontend on Vercel
  |
  | JSON requests
  v
FastAPI backend on Render
  |
  | cached JSON or live nba_api
  v
NBA stats data -> Pandas metric aggregation -> JSON response
```

The frontend sends requests to the backend using `VITE_API_BASE_URL`. The backend validates request fields, loads regular-season or playoff data separately, computes metrics, and returns API responses consumed by the chart and table components.

## Project Structure

```text
/
  frontend/            React + Vite app
  backend/             FastAPI app, analytics logic, tests, cached data
  backend/data/        Cached regular-season JSON datasets
  backend/data/playoffs/ Cached playoff JSON datasets when generated
  scripts/             Local helper scripts and data ingestion
  archive_candidates/  Legacy Streamlit code and old deployment files
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

API docs are available at:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

In development, Vite proxies API calls to the backend on port `8000`.

### Start Both Locally

```bash
bash scripts/start-local.sh
bash scripts/stop-local.sh
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Backend health check |
| `GET` | `/seasons` | Supported NBA seasons |
| `POST` | `/ai/parse` | Parse natural-language query into a structured request |
| `POST` | `/query` | Run leaderboard, scatter, or comparison analytics |
| `POST` | `/metrics` | Return full team metrics table |

### Example Requests

```bash
curl http://localhost:8000/health
```

```bash
curl -X POST http://localhost:8000/ai/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "top playoff offenses"}'
```

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "season": "2024-25",
    "season_type": "Playoffs",
    "chart_type": "leaderboard",
    "metric": "NET_RTG",
    "top_n": 5,
    "window": "SEASON"
  }'
```

```bash
curl -X POST http://localhost:8000/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "season": "2024-25",
    "season_type": "Regular Season",
    "window": "LAST_10"
  }'
```

## Data Modes

CourtVision keeps regular-season and playoff data separate.

| Mode | `season_type` | Cache path |
|------|---------------|------------|
| Regular Season | `Regular Season` | `backend/data/{season}.json` |
| Playoffs | `Playoffs` | `backend/data/playoffs/{season}.json` |

If a cached file exists, the backend reads it first. If not, it calls `nba_api` with the matching `season_type_all_star` value.

To refresh local cached data:

```bash
python scripts/fetch_data.py
```

## Metrics

| Metric | Description |
|--------|-------------|
| `ORtg` | Offensive rating, points scored per 100 possessions |
| `DRtg` | Defensive rating, points allowed per 100 possessions |
| `NET_RTG` | Net rating, `ORtg - DRtg` |
| `PACE` | Estimated possessions per game |
| `PPG` | Points per game |
| `eFG` | Effective field goal percentage |
| `TS` | True shooting percentage |
| `AST_RATE` | Assists per possession |
| `TOV_RATE` | Turnovers per possession |
| `Opp_TOV%` | Opponent turnover percentage forced |

## Natural-Language Queries

The parser converts plain-English prompts into structured analytics requests. It uses a rule-based parser by default and can use OpenAI when `OPENAI_API_KEY` is configured.

Examples:

- "Top 10 teams by net rating last 10 games"
- "Top playoff offenses"
- "Best playoff net rating"
- "Compare Lakers and Nuggets in the playoffs"
- "Show offensive vs defensive ratings for all teams"
- "Worst 5 defenses last 20 games"

## Deployment

### Frontend: Vercel

1. Create a Vercel project from the repo.
2. Set the root directory to `frontend`.
3. Add the backend URL:

```text
VITE_API_BASE_URL=https://your-backend-url
```

4. Redeploy after changing environment variables.

### Backend: Render

The backend can be deployed as a Docker web service.

Recommended Render settings:

```text
Language: Docker
Root Directory: backend
Docker Build Context Directory: backend/.
Dockerfile Path: Dockerfile
Health Check Path: /health
```

Environment variables:

```text
CORS_ORIGINS=https://www.courtvision.site,https://your-vercel-app.vercel.app
OPENAI_API_KEY=optional_openai_key
```

After deployment, test:

```bash
curl https://your-render-service.onrender.com/health
curl https://your-render-service.onrender.com/seasons
```

Then set the Render URL as `VITE_API_BASE_URL` in Vercel.

## Environment Variables

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `CORS_ORIGINS` | Production | Comma-separated list of frontend origins allowed to call the API |
| `OPENAI_API_KEY` | No | Enables OpenAI-backed natural-language parsing |
| `PORT` | Platform-provided | Render/Docker runtime port |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | Production | Backend API origin, for example `https://courtvision-1p9p.onrender.com` |

## Testing

Run backend tests:

```bash
cd backend
../.venv/bin/python -m pytest -q
```

Verify the frontend production build:

```bash
cd frontend
npm run build
```

## Notes

- The backend is intentionally deployed outside Vercel because it is a long-running Python API service.
- Docker is used as the backend deployment recipe so Render can build and run the FastAPI service consistently.
- Some hosting providers may have outbound network issues with `stats.nba.com`; cached datasets help reduce reliance on live NBA API calls.
