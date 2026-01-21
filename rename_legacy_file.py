#!/usr/bin/env python3
# rename_legacy_file.py
# Helper script to rename your old team_game_stats.csv to the new format

import pandas as pd
from pathlib import Path
import sys

DATA_DIR = Path("data/processed")
LEGACY_FILE = DATA_DIR / "team_game_stats.csv"


def detect_season_from_data(file_path: Path) -> str:
    """
    Detect which season the data is from by looking at game dates.
    """
    df = pd.read_csv(file_path)
    
    if "GAME_DATE" not in df.columns:
        print("⚠️ Can't auto-detect season (no GAME_DATE column)")
        return None
    
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    
    # Get date range
    min_date = df["GAME_DATE"].min()
    max_date = df["GAME_DATE"].max()
    
    print(f"📅 Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # NBA seasons run from October to April
    # If max date is in 2024, it's probably the 2023-24 season
    # If max date is in 2025, it's probably the 2024-25 season
    year = max_date.year
    
    # If games go into April/May, that's the end year of the season
    if max_date.month >= 4:
        season = f"{year-1}-{str(year)[2:]}"
    else:
        # If we're in Oct-March, we're in the middle of a season
        season = f"{year}-{str(year+1)[2:]}"
    
    return season


def main():
    if not LEGACY_FILE.exists():
        print("✅ No legacy file found. You're all set!")
        print(f"Looking for: {LEGACY_FILE}")
        return
    
    print("🔍 Found legacy file: team_game_stats.csv")
    print("=" * 60)
    
    # Detect season
    print("\n📊 Analyzing data to detect season...")
    detected_season = detect_season_from_data(LEGACY_FILE)
    
    if detected_season:
        print(f"✅ Detected season: {detected_season}")
        suggested_name = f"team_game_stats_{detected_season.replace('-', '_')}.csv"
        print(f"💡 Suggested filename: {suggested_name}")
    else:
        suggested_name = None
    
    print("\n" + "=" * 60)
    print("OPTIONS:")
    print("=" * 60)
    
    if detected_season:
        print(f"\n1. Rename to detected season ({detected_season})")
        print("2. Manually specify season")
        print("3. Cancel (keep as is)")
        
        choice = input("\nYour choice (1/2/3): ").strip()
        
        if choice == "1":
            season = detected_season
        elif choice == "2":
            season = input("Enter season (e.g., 2024-25): ").strip()
        else:
            print("❌ Cancelled. File not renamed.")
            return
    else:
        print("\n1. Manually specify season")
        print("2. Cancel (keep as is)")
        
        choice = input("\nYour choice (1/2): ").strip()
        
        if choice == "1":
            season = input("Enter season (e.g., 2024-25): ").strip()
        else:
            print("❌ Cancelled. File not renamed.")
            return
    
    # Validate season format
    if not season or "-" not in season:
        print("❌ Invalid season format. Use format: YYYY-YY (e.g., 2024-25)")
        return
    
    # Create new filename
    season_slug = season.replace("-", "_")
    new_file = DATA_DIR / f"team_game_stats_{season_slug}.csv"
    
    # Check if target already exists
    if new_file.exists():
        print(f"⚠️ Warning: {new_file.name} already exists!")
        overwrite = input("Overwrite? (y/n): ").strip().lower()
        if overwrite != "y":
            print("❌ Cancelled. File not renamed.")
            return
    
    # Rename the file
    print(f"\n📝 Renaming...")
    print(f"   From: {LEGACY_FILE.name}")
    print(f"   To:   {new_file.name}")
    
    LEGACY_FILE.rename(new_file)
    
    print(f"\n✅ Success! File renamed to: {new_file.name}")
    print("\n💡 Next step: Refresh your Streamlit app to see the updated season label!")
    print(f"   The season will now appear as: {season}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
