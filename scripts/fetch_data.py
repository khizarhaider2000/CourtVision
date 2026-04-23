#!/usr/bin/env python3
"""
Run this locally (NOT on EC2) to pre-fetch NBA season data and save as JSON.

EC2's AWS IP is blocked by stats.nba.com; your local machine is not.

Usage (from repo root):
    python scripts/fetch_data.py

Output:
    backend/data/2024-25.json
    backend/data/2023-24.json
    ... one file per season

Then upload to EC2:
    bash scripts/sync_to_ec2.sh /path/to/key.pem
"""
import sys
import time
from pathlib import Path

# Reuse backend code for headers + season list
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from nba_api.stats.endpoints import LeagueGameLog
from nba_api.stats.library.http import NBAStatsHTTP

NBAStatsHTTP.HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

from data_loader import AVAILABLE_SEASONS

DATA_DIR = Path(__file__).parent.parent / "backend" / "data"
DATA_DIR.mkdir(exist_ok=True)


def fetch_season(season: str) -> None:
    out_file = DATA_DIR / f"{season}.json"

    if out_file.exists():
        kb = out_file.stat().st_size // 1024
        print(f"  [skip]  {season}  —  already exists ({kb} KB)")
        return

    print(f"  [fetch] {season} ...", end=" ", flush=True)

    for attempt in range(3):
        try:
            time.sleep(0.6)  # be polite to NBA API
            lg = LeagueGameLog(
                season=season,
                season_type_all_star="Regular Season",
                timeout=60,
            )
            df = lg.get_data_frames()[0]
            if df.empty:
                print("EMPTY — skipping")
                return
            df.to_json(out_file, orient="records", date_format="iso")
            kb = out_file.stat().st_size // 1024
            print(f"done  ({len(df)} rows, {kb} KB)")
            return
        except Exception as exc:
            if attempt == 2:
                print(f"FAILED after 3 attempts: {exc}")
            else:
                wait = 3 + attempt * 3
                print(f"error, retrying in {wait}s...", end=" ", flush=True)
                time.sleep(wait)


if __name__ == "__main__":
    print(f"Output directory: {DATA_DIR}\n")
    for season in AVAILABLE_SEASONS:
        fetch_season(season)
    print("\nAll done. Run  bash scripts/sync_to_ec2.sh <key.pem>  to upload.")
