# data_loader.py
# Handles loading data from different seasons

import pandas as pd
from pathlib import Path
from typing import List, Tuple, Optional
from metrics import prepare_team_games_for_metrics

DATA_DIR = Path("data/processed")


def get_available_seasons() -> List[Tuple[str, Path]]:
    """
    Scan data directory for available season files.
    
    Returns:
        List of tuples: (season_display_name, file_path)
        Example: [("2024-25", Path("data/processed/team_game_stats_2024_25.csv")), ...]
    """
    if not DATA_DIR.exists():
        return []
    
    season_files = []
    
    # Find all team_game_stats files
    for file_path in DATA_DIR.glob("team_game_stats_*.csv"):
        # Extract season from filename: team_game_stats_2023_24.csv -> 2023-24
        filename = file_path.stem  # removes .csv
        if filename.startswith("team_game_stats_"):
            season_slug = filename.replace("team_game_stats_", "")
            season_display = season_slug.replace("_", "-")  # 2023_24 -> 2023-24
            season_files.append((season_display, file_path))
    
    # Also check for legacy filename (backward compatibility)
    legacy_file = DATA_DIR / "team_game_stats.csv"
    if legacy_file.exists():
        # Try to detect the season from the data itself
        try:
            df_legacy = pd.read_csv(legacy_file, nrows=5)
            if "GAME_DATE" in df_legacy.columns:
                # Get a sample date to guess the season
                df_legacy["GAME_DATE"] = pd.to_datetime(df_legacy["GAME_DATE"])
                year = df_legacy["GAME_DATE"].max().year
                # Guess season based on year (Oct-Apr spans two years)
                season_guess = f"{year-1}-{str(year)[2:]}"
                season_files.append((f"{season_guess} (Please Rename File)", legacy_file))
            else:
                season_files.append(("Unknown Season (Legacy File)", legacy_file))
        except:
            season_files.append(("Unknown Season (Legacy File)", legacy_file))
    
    # Sort by season (most recent first)
    season_files.sort(reverse=True)
    
    return season_files


def load_season_data(season: str) -> pd.DataFrame:
    """
    Load and prepare data for a specific season.
    
    Args:
        season: Season in 'YYYY-YY' format (e.g., '2024-25') or legacy label
    
    Returns:
        Prepared DataFrame with metrics computed
    """
    # Handle legacy file (backward compatibility)
    if "Legacy" in season or "Rename File" in season:
        file_path = DATA_DIR / "team_game_stats.csv"
    else:
        season_slug = season.replace("-", "_")
        file_path = DATA_DIR / f"team_game_stats_{season_slug}.csv"
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"No data found for season {season}. "
            f"Run: python ingest.py 2025-26 (or your desired season)"
        )
    
    df_raw = pd.read_csv(file_path)
    return prepare_team_games_for_metrics(df_raw)


def get_season_info(season: str) -> dict:
    """
    Get metadata about a specific season's data.
    
    Returns:
        Dict with: teams, games, date_range, total_team_games
    """
    df = load_season_data(season)
    
    return {
        "teams": sorted(df["TEAM_ABBREVIATION"].unique().tolist()),
        "num_teams": df["TEAM_ABBREVIATION"].nunique(),
        "total_team_games": len(df),
        "date_range": (
            df["GAME_DATE"].min().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].min()) else "Unknown",
            df["GAME_DATE"].max().strftime("%Y-%m-%d") if pd.notna(df["GAME_DATE"].max()) else "Unknown"
        ),
    }


def get_default_season() -> Optional[str]:
    """
    Get the most recent season available.
    
    Returns:
        Season string (e.g., '2024-25') or None if no data
    """
    seasons = get_available_seasons()
    if not seasons:
        return None
    return seasons[0][0]  # First tuple, first element (season name)


# Example usage
if __name__ == "__main__":
    print("Available Seasons:")
    print("-" * 50)
    
    seasons = get_available_seasons()
    
    if not seasons:
        print("No season data found!")
        print("Run: python ingest.py [SEASON]")
    else:
        for season, path in seasons:
            print(f"\n📅 {season}")
            print(f"   File: {path.name}")
            
            try:
                info = get_season_info(season)
                print(f"   Teams: {info['num_teams']}")
                print(f"   Games: {info['total_team_games']}")
                print(f"   Range: {info['date_range'][0]} to {info['date_range'][1]}")
            except Exception as e:
                print(f"   Error loading: {e}")
    
    print("\n" + "-" * 50)
    default = get_default_season()
    if default:
        print(f"Default season: {default}")
