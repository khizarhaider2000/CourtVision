#!/usr/bin/env python3
# test_logos.py
# Quick test to verify team logos are downloading and rendering correctly

import matplotlib.pyplot as plt
from visualize import get_team_logo, TEAM_LOGOS
import sys

def test_single_logo(team="BOS"):
    """Test downloading and displaying a single team logo"""
    print(f"Testing logo for {team}...")
    
    logo = get_team_logo(team, zoom=0.3)
    
    if logo:
        print(f"✅ Successfully loaded {team} logo!")
        
        # Display it
        fig, ax = plt.subplots(figsize=(4, 4))
        ab = plt.matplotlib.offsetbox.AnnotationBbox(logo, (0.5, 0.5), frameon=True)
        ax.add_artist(ab)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"{team} Logo Test")
        ax.axis('off')
        
        plt.savefig(f"test_logo_{team}.png", dpi=150, bbox_inches='tight')
        print(f"📸 Saved test image: test_logo_{team}.png")
        plt.close()
        
        return True
    else:
        print(f"❌ Failed to load {team} logo")
        return False


def test_all_logos():
    """Test downloading all team logos"""
    print("Testing all NBA team logos...")
    print("=" * 60)
    
    success_count = 0
    failed_teams = []
    
    for team in TEAM_LOGOS.keys():
        print(f"  {team}...", end=" ")
        logo = get_team_logo(team, zoom=0.1)
        
        if logo:
            print("✅")
            success_count += 1
        else:
            print("❌")
            failed_teams.append(team)
    
    print("=" * 60)
    print(f"\nResults: {success_count}/{len(TEAM_LOGOS)} logos loaded successfully")
    
    if failed_teams:
        print(f"❌ Failed: {', '.join(failed_teams)}")
    else:
        print("🎉 All logos loaded successfully!")
    
    return success_count == len(TEAM_LOGOS)


def test_scatter_plot():
    """Create a sample scatter plot with logos to verify rendering"""
    print("\nCreating sample scatter plot with logos...")
    
    import pandas as pd
    from query_engine import ChartSpec
    from visualize import _render_scatter
    
    # Create sample data
    data = {
        'TEAM_ABBREVIATION': ['BOS', 'LAL', 'GSW', 'MIA', 'PHI', 'DEN'],
        'ORtg': [118.5, 115.2, 117.8, 116.3, 114.9, 119.1],
        'DRtg': [107.2, 112.5, 109.1, 108.8, 111.3, 106.5]
    }
    df = pd.DataFrame(data)
    
    # Create spec
    spec = ChartSpec(
        chart_type="scatter",
        window="SEASON",
        x_metric="ORtg",
        y_metric="DRtg"
    )
    
    # Render
    fig = _render_scatter(spec, df)
    plt.savefig("test_scatter_with_logos.png", dpi=150, bbox_inches='tight')
    print("✅ Sample scatter plot saved: test_scatter_with_logos.png")
    plt.close()


def main():
    print("NBA Team Logo Test Suite")
    print("=" * 60)
    print()
    
    # Test 1: Single logo
    print("Test 1: Loading single logo (Celtics)")
    print("-" * 60)
    test_single_logo("BOS")
    print()
    
    # Test 2: All logos
    print("Test 2: Loading all team logos")
    print("-" * 60)
    all_success = test_all_logos()
    print()
    
    # Test 3: Scatter plot
    if all_success:
        print("Test 3: Creating scatter plot with logos")
        print("-" * 60)
        try:
            test_scatter_plot()
            print()
        except Exception as e:
            print(f"❌ Scatter plot test failed: {e}")
            print()
    else:
        print("⚠️  Skipping scatter plot test (some logos failed)")
        print()
    
    print("=" * 60)
    print("Logo test complete!")
    print("\n💡 Tips:")
    print("  - Check the 'data/logos/' directory for cached logo files")
    print("  - View test_logo_*.png to see individual logos")
    print("  - View test_scatter_with_logos.png to see logos in a chart")
    print("  - If logos fail, check your internet connection")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
