#!/usr/bin/env python3
"""
Run this locally to pre-fetch NBA regular-season and playoff data as JSON.

EC2's AWS IP is blocked by stats.nba.com; your local machine is not.

Usage (from repo root):
    python scripts/fetch_data.py

Output:
    backend/data/2024-25.json
    backend/data/playoffs/2024-25.json
    ... one regular-season and one playoff file per season when available
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
(DATA_DIR / "playoffs").mkdir(exist_ok=True)


def fetch_season(season: str, season_type: str) -> None:
    out_file = DATA_DIR / f"{season}.json"
    if season_type == "Playoffs":
        out_file = DATA_DIR / "playoffs" / f"{season}.json"

    if out_file.exists():
        kb = out_file.stat().st_size // 1024
        print(f"  [skip]  {season} {season_type}  —  already exists ({kb} KB)")
        return

    print(f"  [fetch] {season} {season_type} ...", end=" ", flush=True)

    for attempt in range(3):
        try:
            time.sleep(0.6)  # be polite to NBA API
            lg = LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                timeout=60,
            )
            df = lg.get_data_frames()[0]
            if df.empty:
                print("EMPTY — skipping")
                return
            df["SEASON_TYPE"] = season_type
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
        fetch_season(season, "Regular Season")
        fetch_season(season, "Playoffs")
    print("\nAll done.")
