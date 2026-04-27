# CourtVision

AI-powered NBA team performance analytics. React + Vite frontend on Vercel, FastAPI backend on a non-AWS host.

---

## Project Structure

```
/
  frontend/          # React + Vite app — deploys to Vercel
  backend/           # FastAPI app — deploys separately from Vercel
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
   VITE_API_BASE_URL=https://your-backend-url
   ```
5. Deploy. `frontend/vercel.json` handles SPA routing rewrites.

### Backend → Non-AWS Host

The backend is a standard FastAPI ASGI service and already has everything needed for a non-AWS deployment:

- `backend/Dockerfile` for container hosts
- `backend/Procfile` for Python buildpack hosts
- `PORT` support for managed platforms
- `CORS_ORIGINS` support for your Vercel frontend

Because the NBA API may reject requests from AWS-hosted IP ranges, prefer a host with non-AWS egress. Good options are:

1. **DigitalOcean App Platform** or a **DigitalOcean Droplet**: best first choice if you want to avoid AWS egress. App Platform is simpler; a Droplet gives you the most control if the NBA API is picky about managed-platform IPs.
2. **Fly.io**: also a good Docker-based option. Pick a US or Toronto region near your users.
3. **Railway/Render**: easy FastAPI deploys, but verify their outbound IP/network path with the NBA API before relying on them for production.

#### DigitalOcean App Platform

1. Create a new App from your GitHub repo.
2. Add a Web Service for the backend.
3. Set the source directory to:
   ```
   backend
   ```
4. Use the existing `backend/Dockerfile`, or configure Python buildpack commands:
   ```
   Build command: pip install -r requirements.txt
   Run command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```
5. Set environment variables:
   ```
   OPENAI_API_KEY=sk-...
   CORS_ORIGINS=https://your-app.vercel.app
   ```
6. Deploy, then test:
   ```
   curl https://your-backend-url/health
   curl https://your-backend-url/seasons
   ```

If `/health` works but `/seasons`, `/query`, or `/metrics` fail with `NBA API unavailable`, the app is running but the NBA API is rejecting that provider's outbound network. In that case, use a DigitalOcean Droplet, Vultr, Hetzner, or another VPS provider and run the same Docker image there.

#### Fly.io

From the backend directory:

```bash
cd backend
fly launch --no-deploy
fly secrets set OPENAI_API_KEY=sk-... CORS_ORIGINS=https://your-app.vercel.app
fly deploy
```

Fly will detect `backend/Dockerfile`. Make sure the generated `fly.toml` uses internal port `8000`, matching the Dockerfile.

#### VPS/Droplet Docker

On a non-AWS VPS:

```bash
cd backend
docker build -t courtvision-backend .
docker run -d \
  --name courtvision-backend \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e CORS_ORIGINS=https://your-app.vercel.app \
  courtvision-backend
```

Put Caddy or Nginx in front of it for HTTPS, then set the Vercel frontend variable:

```bash
VITE_API_BASE_URL=https://api.your-domain.com
```

After changing `VITE_API_BASE_URL` in Vercel, redeploy the frontend so Vite bakes the new API URL into the production build.

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
