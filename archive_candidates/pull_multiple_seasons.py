#!/usr/bin/env python3
# pull_multiple_seasons.py
# Helper script to pull data for multiple seasons at once

from ingest import main as pull_season
import time

# Define the seasons you want to pull
SEASONS_TO_PULL = [
    "2025-26",  # Current season (in progress)
    "2024-25",  # Last season
    "2023-24",
    "2022-23",
    "2021-22",
    "2020-21",
    "2019-20"
]

SEASON_TYPE = "Regular Season"


def main():
    print("=" * 60)
    print("NBA MULTI-SEASON DATA PULLER")
    print("=" * 60)
    print(f"\nPulling {len(SEASONS_TO_PULL)} seasons...")
    print(f"Seasons: {', '.join(SEASONS_TO_PULL)}")
    print(f"Type: {SEASON_TYPE}\n")
    
    success_count = 0
    failed_seasons = []
    
    for i, season in enumerate(SEASONS_TO_PULL, 1):
        print(f"\n[{i}/{len(SEASONS_TO_PULL)}] Processing {season}...")
        print("-" * 60)
        
        try:
            pull_season(season=season, season_type=SEASON_TYPE)
            success_count += 1
            print(f"✅ {season} complete!")
            
            # Small delay to be nice to the API
            if i < len(SEASONS_TO_PULL):
                print("⏳ Waiting 2 seconds before next request...")
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Failed to pull {season}: {e}")
            failed_seasons.append(season)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully pulled: {success_count}/{len(SEASONS_TO_PULL)} seasons")
    
    if failed_seasons:
        print(f"❌ Failed seasons: {', '.join(failed_seasons)}")
    else:
        print("🎉 All seasons downloaded successfully!")
    
    print("\n💡 To use these seasons, select them in the Streamlit app dropdown")


if __name__ == "__main__":
    main()
