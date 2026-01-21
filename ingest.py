# Gets data from nba_api and processes it into a canonical format

from nba_api.stats.endpoints import LeagueGameLog
import pandas as pd
from pathlib import Path

OUT_DIR = Path("data/processed") # create data/processed directory
OUT_DIR.mkdir(parents=True, exist_ok=True) # ensure directory exists

def pull_team_game_logs(season: str, season_type: str) -> pd.DataFrame:
    """
    Pulls team game logs for a specified NBA season and season type.

    Args:
        season (str): The NBA season in 'YYYY-YY'

        season_type (str): The type of season ('Regular Season', 'Playoffs', etc.)      
    Returns:
        pd.DataFrame: DataFrame containing the team game logs.
    """
    
    # return one row per team per game
    # example: Lakers vs Celtics on 2024-01-01 will have two rows, one for each team
    lg = LeagueGameLog(season=season, season_type_all_star=season_type)
    df = lg.get_data_frames()[0].copy()
    return df

def main(season: str = "2025-26", season_type: str = "Regular Season"):
    """
    Pull and save NBA team game logs for a specific season.
    
    Args:
        season: NBA season in 'YYYY-YY' format (e.g., '2024-25', '2023-24')
        season_type: Type of season ('Regular Season', 'Playoffs', etc.)
    """
    print(f"Fetching data for {season} {season_type}...")
    df = pull_team_game_logs(season, season_type)
    
    # define the columns we want to keep
    wanted = [
        "GAME_ID", "GAME_DATE",
        "TEAM_ID", "TEAM_ABBREVIATION",
        "MATCHUP", "WL",
        "PTS", "FGA", "FGM", "FG3A", "FG3M",
        "FTA", "FTM",
        "OREB", "DREB", "AST", "TOV", "MIN"
    ]
    
    # select only the wanted columns that are present in the dataframe to prevent code crash
    available = [c for c in wanted if c in df.columns]
    canonical = df[available].copy()

   # Normalize GAME_DATE to datetime format
    if "GAME_DATE" in canonical.columns:
        canonical["GAME_DATE"] = pd.to_datetime(canonical["GAME_DATE"])

    # Save with season-specific filename
    season_slug = season.replace("-", "_")  # "2023-24" -> "2023_24"
    out_path = OUT_DIR / f"team_game_stats_{season_slug}.csv"
    canonical.to_csv(out_path, index=False)
    
    # Print summary
    print(f"✅ Saved: {out_path}")
    print(f"📊 Rows: {len(canonical):,}")
    print(f"📅 Date range: {canonical['GAME_DATE'].min()} to {canonical['GAME_DATE'].max()}")
    print("\nSample data:")
    print(canonical.head(3))
    print(f"\n💡 To use this season, select '{season}' in the app or use:")
    print(f"   DATA_PATH = Path('data/processed/team_game_stats_{season_slug}.csv')")


if __name__ == "__main__":
    import sys
    
    # Allow command-line arguments: python ingest.py 2023-24 "Regular Season"
    if len(sys.argv) > 1:
        season_arg = sys.argv[1]
        season_type_arg = sys.argv[2] if len(sys.argv) > 2 else "Regular Season"
        main(season=season_arg, season_type=season_type_arg)
    else:
        # Default: pull current season
        print("Usage: python ingest.py [SEASON] [SEASON_TYPE]")
        print("Example: python ingest.py 2023-24 'Regular Season'")
        print("\nPulling current season by default...\n")
        main()