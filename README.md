# CourtVision

AI-powered NBA team performance analytics. React + Vite frontend on Vercel, FastAPI backend on AWS.

---

## Project Structure

```
/
  frontend/          # React + Vite app — deploys to Vercel
  backend/           # FastAPI app — deploys to AWS
  archive_candidates/ # Legacy Streamlit UI and scripts (review before deleting)
  scripts/           # Local dev helpers
  .github/workflows/ # CI
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv ../.venv
source ../.venv/bin/activate       # Windows: ..\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in OPENAI_API_KEY if needed
uvicorn api.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local         # optional — leave blank for dev proxy
npm run dev
```

Open `http://localhost:5173`. Vite proxies all `/health`, `/seasons`, `/ai`, `/query`, `/metrics` requests to the backend on port 8000.

### One-command start (both together)

```bash
bash scripts/start-local.sh
bash scripts/stop-local.sh   # to stop
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/seasons` | Available NBA seasons |
| POST | `/ai/parse` | Natural language → QuerySpec |
| POST | `/query` | Execute structured chart query |
| POST | `/metrics` | Full team metrics for a season/window |

### Quick test

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/ai/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "top 10 teams by net rating last 10 games"}'

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"season":"2024-25","chart_type":"leaderboard","metric":"NET_RTG","top_n":5}'
```

---

## Deployment

### Frontend → Vercel

1. Connect your GitHub repo to Vercel.
2. Set **Root Directory** to `frontend`.
3. Vercel auto-detects Vite — no build command changes needed.
4. Add environment variable in Vercel dashboard:
   ```
   VITE_API_BASE_URL=https://your-aws-backend-url
   ```
5. Deploy. `frontend/vercel.json` handles SPA routing rewrites.

### Backend → AWS

The backend is a standard ASGI app. Recommended options:

**AWS App Runner (simplest):**
1. Push `backend/` (or the full repo) to ECR or connect GitHub.
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port 8080`
4. Set environment variables:
   ```
   OPENAI_API_KEY=sk-...
   CORS_ORIGINS=https://your-app.vercel.app
   PORT=8080
   ```

**AWS Elastic Beanstalk:**
1. Deploy from `backend/` directory.
2. `Procfile` is already present: `web: uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. Set the same environment variables above.

**Docker (ECS / App Runner via ECR):**
```bash
cd backend
docker build -t courtvision-backend .
docker run -p 8000:8000 --env-file .env courtvision-backend
```

> **Important:** Set `CORS_ORIGINS` to your Vercel domain on AWS. Without it, browser requests from Vercel will be blocked by CORS.

---

## Backend Tests

```bash
cd backend
pytest -q
```

---

## Metrics Reference

All metrics are team-level, per 100 possessions (Dean Oliver formula):

| Metric | Description |
|--------|-------------|
| ORtg | Offensive Rating — points scored per 100 possessions |
| DRtg | Defensive Rating — points allowed per 100 possessions (lower = better) |
| NET_RTG | Net Rating — ORtg minus DRtg |
| eFG | Effective FG% — accounts for 3-pointers |
| TS | True Shooting % — accounts for 2s, 3s, free throws |
| PACE | Estimated possessions per 48 minutes |
| AST_RATE | Assists per possession |
| TOV_RATE | Turnovers per possession |

---

## AI Query Parser

The `/ai/parse` endpoint parses natural language into a structured `QuerySpec`. It uses a rule-based parser by default. If `OPENAI_API_KEY` is set, it uses the OpenAI API for more robust parsing.

Example queries:
- "Top 10 teams by net rating in the last 10 games"
- "Show me the efficiency landscape for 2023-24"
- "Compare Celtics and Lakers this season"
- "Worst 5 defenses last 20 games"

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables AI-powered query parsing |
| `CORS_ORIGINS` | Production | Comma-separated list of allowed frontend origins |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | Production | Backend URL (e.g. `https://api.example.com`) |

---

## archive_candidates/

This folder contains legacy code moved during the restructure. Review before deleting:

| File | Notes |
|------|-------|
| `streamlit_ai.py` | Original Streamlit UI — superseded by React frontend |
| `visualize.py` | Matplotlib chart renderer — only used by Streamlit UI |
| `lineups.py` | Lineup analysis — not yet integrated into React UI |
| `ingest.py` | Script to download NBA data to CSV files |
| `pull_multiple_seasons.py` | Bulk season data downloader |
| `Dockerfile` | Old Render single-container build |
| `render.yaml` | Render deployment config |
| `keepalive.yml` | GitHub Action that pinged Render — no longer needed |
