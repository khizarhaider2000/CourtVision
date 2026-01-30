# visualize.py
# Connects query_engine to charts - automatically renders the right visualization

import matplotlib.pyplot as plt
import pandas as pd
from query_engine import ChartSpec
from typing import Tuple, Optional
import matplotlib
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from io import BytesIO
from PIL import Image
import numpy as np
from pathlib import Path
import os

# Use non-interactive backend for Streamlit
matplotlib.use('Agg')

# Support DATA_DIR environment variable for deployment (e.g., Render)
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))

# Cache directory for logos
LOGO_CACHE_DIR = DATA_DIR / "logos"
LOGO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Local custom logos directory
LOCAL_LOGOS_DIR = Path("team_logos")

# Mapping of team abbreviations to local logo filenames
LOCAL_LOGO_MAP = {
    "UTA": "Jazz.png",
    "LAL": "Lakers.png",
    "ORL": "Magic.png",
    "BKN": "Nets.png",
    "LAC": "Clippers.png",  # Added Clippers
}


# NBA team logo URLs - using NBA.com stats site (more reliable)
# Alternative source that's publicly accessible
TEAM_LOGOS = {
    "ATL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/atl.png",
    "BOS": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/bos.png",
    "BKN": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/bkn.png",
    "CHA": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/cha.png",
    "CHI": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/chi.png",
    "CLE": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/cle.png",
    "DAL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/dal.png",
    "DEN": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/den.png",
    "DET": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/det.png",
    "GSW": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/gs.png",
    "HOU": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/hou.png",
    "IND": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/ind.png",
    "LAC": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/lac.png",
    "LAL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/lal.png",
    "MEM": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mem.png",
    "MIA": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mia.png",
    "MIL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mil.png",
    "MIN": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/min.png",
    "NOP": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/no.png",
    "NYK": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/ny.png",
    "OKC": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/okc.png",
    "ORL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/orl.png",
    "PHI": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/phi.png",
    "PHX": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/phx.png",
    "POR": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/por.png",
    "SAC": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/sac.png",
    "SAS": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/sa.png",
    "TOR": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/tor.png",
    "UTA": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/utah.png",
    "WAS": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/wsh.png",
}


def get_team_logo(team_abbrev: str, zoom: float = 0.1) -> Optional[OffsetImage]:
    """
    Download and cache team logo, return as OffsetImage for matplotlib.
    
    Priority order:
    1. Local custom logo (team_logos folder)
    2. Cached logo (data/logos folder)
    3. Download from ESPN CDN
    
    Args:
        team_abbrev: Team abbreviation (e.g., 'BOS', 'LAL')
        zoom: Size of the logo (0.1 = small, 0.3 = large)
    
    Returns:
        OffsetImage or None if logo not available
    """
    
    # Standard size for all logos (square)
    LOGO_SIZE = (400, 400)
    
    def _normalize_logo_image(img: Image.Image) -> Image.Image:
        # Ensure predictable colors across different image modes.
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            return background
        return img.convert("RGB")

    def _resize_with_padding(img: Image.Image) -> Image.Image:
        # Preserve aspect ratio and pad to square to avoid logo squashing.
        target_w, target_h = LOGO_SIZE
        src_w, src_h = img.size
        if src_w == 0 or src_h == 0:
            return img.resize(LOGO_SIZE, Image.Resampling.LANCZOS)
        scale = min(target_w / src_w, target_h / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", LOGO_SIZE, (255, 255, 255))
        offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
        canvas.paste(resized, offset)
        return canvas

    # Check for local custom logo first
    if team_abbrev in LOCAL_LOGO_MAP:
        local_path = LOCAL_LOGOS_DIR / LOCAL_LOGO_MAP[team_abbrev]
        if local_path.exists():
            try:
                img = Image.open(local_path)
                img = _normalize_logo_image(img)
                
                # Resize to standard size for consistency without squashing
                img = _resize_with_padding(img)
                
                img_array = np.array(img)
                imagebox = OffsetImage(img_array, zoom=zoom)
                return imagebox
            except Exception as e:
                print(f"Warning: Could not load local logo for {team_abbrev}: {e}")
                # Fall through to try ESPN CDN
    
    # Check if ESPN logo is not available for this team
    if team_abbrev not in TEAM_LOGOS:
        return None
    
    # Check cache next
    cache_file = LOGO_CACHE_DIR / f"{team_abbrev}.png"
    
    try:
        if cache_file.exists():
            # Load from cache
            img = Image.open(cache_file)
        else:
            # Download logo with proper headers
            logo_url = TEAM_LOGOS[team_abbrev]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(logo_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            img = _normalize_logo_image(img)
            
            # Save to cache
            img.save(cache_file, "PNG")
        
        # Resize to standard size for consistency without squashing
        img = _resize_with_padding(img)
        
        # Convert to numpy array for matplotlib
        img_array = np.array(img)
        
        # Create OffsetImage
        imagebox = OffsetImage(img_array, zoom=zoom)
        
        return imagebox
        
    except Exception as e:
        # If logo fetch fails, return None (will fall back to circle)
        print(f"Warning: Could not load logo for {team_abbrev}: {e}")
        return None


def render_chart(spec: ChartSpec, result_df: pd.DataFrame) -> plt.Figure:
    """
    Takes a ChartSpec and result DataFrame, returns the appropriate matplotlib Figure.
    """
    
    if spec.chart_type == "leaderboard":
        return _render_leaderboard(spec, result_df)
    elif spec.chart_type == "scatter":
        return _render_scatter(spec, result_df)
    elif spec.chart_type == "compare":
        return _render_compare(spec, result_df)
    else:
        raise ValueError(f"Unsupported chart_type: {spec.chart_type}")


def _render_leaderboard(spec: ChartSpec, df: pd.DataFrame) -> plt.Figure:
    """Bar chart for leaderboard queries"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Sort to ensure proper ordering
    ascending = (spec.order == "asc")
    df_sorted = df.sort_values(spec.metric, ascending=ascending)
    
    # Create bar chart
    bars = ax.barh(df_sorted["TEAM_ABBREVIATION"], df_sorted[spec.metric])
    
    # Color bars - green for positive, red for negative (useful for NET_RTG)
    if spec.metric == "NET_RTG":
        colors = ['green' if x > 0 else 'red' for x in df_sorted[spec.metric]]
        for bar, color in zip(bars, colors):
            bar.set_color(color)
            bar.set_alpha(0.7)
    # Color bars for DRtg - green for low (good), red for high (bad)
    elif spec.metric == "DRtg":
        # Lower is better for defense
        median_val = df_sorted[spec.metric].median()
        colors = ['green' if x < median_val else 'red' for x in df_sorted[spec.metric]]
        for bar, color in zip(bars, colors):
            bar.set_color(color)
            bar.set_alpha(0.7)
    
    # Set x-axis label with percentage indicator if applicable
    xlabel = spec.metric
    if spec.metric in ["eFG", "TS", "AST_RATE", "TOV_RATE"]:
        xlabel = f"{spec.metric} (%)"
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("Team", fontsize=12)

    # Add context to title for DRtg
    title = f"Top {spec.top_n} Teams by {spec.metric} ({spec.window})"
    if spec.metric == "DRtg":
        title += " [Lower = Better Defense]"
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Format x-axis ticks as percentages for percentage metrics
    if spec.metric in ["eFG", "TS", "AST_RATE", "TOV_RATE"]:
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x*100:.0f}'))

    # Zoom x-axis to data range so small differences are visible
    values = df_sorted[spec.metric]
    val_min, val_max = values.min(), values.max()
    val_range = val_max - val_min if val_max != val_min else 1
    padding = val_range * 0.15
    ax.set_xlim(val_min - padding, val_max + padding * 2)  # extra right padding for labels

    # Add value labels on bars
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        # Format percentage metrics differently (eFG, TS show as percentages)
        if spec.metric in ["eFG", "TS", "AST_RATE", "TOV_RATE"]:
            # These are stored as decimals (0.58), display as percentages (58.0%)
            label = f' {row[spec.metric] * 100:.1f}%'
        else:
            # Other metrics show with 1 decimal place
            label = f' {row[spec.metric]:.1f}'
        ax.text(row[spec.metric], i, label, va='center', fontsize=9)

    plt.tight_layout()
    return fig


def _render_scatter(spec: ChartSpec, df: pd.DataFrame) -> plt.Figure:
    """Scatter plot for efficiency landscape with team logos"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # DYNAMIC AXIS LIMITS - Add padding around data
    x_data = df[spec.x_metric]
    y_data = df[spec.y_metric]
    
    # Calculate data range
    x_min, x_max = x_data.min(), x_data.max()
    y_min, y_max = y_data.min(), y_data.max()
    
    # Add 5% padding on each side for better visibility
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    # Try to plot with logos
    logos_plotted = 0
    placed_points: list[tuple[float, float]] = []
    
    # Logo size adjustment:
    # zoom=0.03 - Very small (good for 30+ teams)
    # zoom=0.06 - Small/medium (current default, works well)
    # zoom=0.08 - Medium
    # zoom=0.12 - Large (may overlap)

    def _separate_point(x: float, y: float) -> tuple[float, float]:
        # Keep nearby points from fully overlapping by nudging in data units.
        local_x_range = x_range if x_range > 0 else 1
        local_y_range = y_range if y_range > 0 else 1
        min_sep = 0.04
        if all(
            ((x - px) / local_x_range) ** 2 + ((y - py) / local_y_range) ** 2 >= min_sep**2
            for px, py in placed_points
        ):
            return x, y
        for ring in range(1, 5):
            radius = min_sep * ring
            for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                x_try = x + radius * local_x_range * np.cos(angle)
                y_try = y + radius * local_y_range * np.sin(angle)
                if all(
                    ((x_try - px) / local_x_range) ** 2 + ((y_try - py) / local_y_range) ** 2
                    >= min_sep**2
                    for px, py in placed_points
                ):
                    return x_try, y_try
        return x, y
    
    for _, row in df.iterrows():
        x = row[spec.x_metric]
        y = row[spec.y_metric]
        team = row["TEAM_ABBREVIATION"]
        x_plot, y_plot = _separate_point(x, y)
        placed_points.append((x_plot, y_plot))
        
        # Try to get team logo
        logo = get_team_logo(team, zoom=0.08)
        
        if logo:
            # Plot logo as the marker
            ab = AnnotationBbox(logo, (x_plot, y_plot), frameon=False, pad=0)
            ax.add_artist(ab)
            logos_plotted += 1
        else:
            # Fallback to circle if logo not available
            ax.scatter(x_plot, y_plot, s=100, alpha=0.6, c='steelblue', edgecolors='black')
            ax.text(x_plot, y_plot, team, fontsize=8, ha='center', va='bottom')
    
    # If no logos were plotted, fall back to original style
    if logos_plotted == 0:
        ax.scatter(x_data, y_data, s=100, alpha=0.6, c='steelblue', edgecolors='black')
        for _, row in df.iterrows():
            ax.text(row[spec.x_metric], row[spec.y_metric], row["TEAM_ABBREVIATION"],
                   fontsize=8, ha='center', va='bottom')
    
    if placed_points:
        x_min = min(x_min, min(p[0] for p in placed_points))
        x_max = max(x_max, max(p[0] for p in placed_points))
        y_min = min(y_min, min(p[1] for p in placed_points))
        y_max = max(y_max, max(p[1] for p in placed_points))
    
    x_range_lims = x_max - x_min
    y_range_lims = y_max - y_min
    
    x_padding = x_range_lims * 0.08 if x_range_lims > 0 else 1
    y_padding = y_range_lims * 0.08 if y_range_lims > 0 else 1
    
    ax.set_xlim(x_min - x_padding, x_max + x_padding)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)
    
    ax.set_xlabel(spec.x_metric, fontsize=12)
    ax.set_ylabel(spec.y_metric, fontsize=12)
    ax.set_title(f"{spec.x_metric} vs {spec.y_metric} ({spec.window})", 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add league average lines
    avg_x = x_data.mean()
    avg_y = y_data.mean()
    ax.axvline(avg_x, color='red', linestyle='--', alpha=0.5, label=f'Avg {spec.x_metric}')
    ax.axhline(avg_y, color='red', linestyle='--', alpha=0.5, label=f'Avg {spec.y_metric}')
    ax.legend(loc='best')
    
    # Add quadrant labels for ORtg vs DRtg
    if spec.x_metric == "ORtg" and spec.y_metric == "DRtg":
        xlims = ax.get_xlim()
        ylims = ax.get_ylim()

        # Calculate padding (3% of axis range) to give labels breathing room
        x_pad = (xlims[1] - xlims[0]) * 0.03
        y_pad = (ylims[1] - ylims[0]) * 0.03

        # Bottom-right: Elite (high ORtg, low DRtg = good offense + good defense)
        ax.text(xlims[1] - x_pad, ylims[0] + y_pad,
               'Elite\n(High O, Low D)', ha='right', va='bottom',
               fontsize=10, style='italic', alpha=0.7,
               bbox=dict(boxstyle='round,pad=0.5', facecolor='#4CAF50', alpha=0.15, edgecolor='#4CAF50'))

        # Top-left: Struggling (low ORtg, high DRtg = bad offense + bad defense)
        ax.text(xlims[0] + x_pad, ylims[1] - y_pad,
               'Struggling\n(Low O, High D)', ha='left', va='top',
               fontsize=10, style='italic', alpha=0.7,
               bbox=dict(boxstyle='round,pad=0.5', facecolor='#F44336', alpha=0.15, edgecolor='#F44336'))
    
    plt.tight_layout()
    return fig


def _render_compare(spec: ChartSpec, df: pd.DataFrame) -> plt.Figure:
    """Grouped bar chart for team comparison"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Select key metrics to compare
    metrics = ["ORtg", "DRtg", "NET_RTG", "PACE"]
    available_metrics = [m for m in metrics if m in df.columns]
    
    x = range(len(available_metrics))
    width = 0.35
    
    teams = df["TEAM_ABBREVIATION"].tolist()
    
    # Plot bars for each team
    for i, team in enumerate(teams):
        team_data = df[df["TEAM_ABBREVIATION"] == team]
        values = [team_data[m].values[0] for m in available_metrics]
        offset = width * (i - len(teams)/2 + 0.5)
        ax.bar([pos + offset for pos in x], values, width, label=team, alpha=0.8)
    
    # Zoom y-axis to data range so small differences between teams are visible
    all_values = []
    for team in teams:
        team_data = df[df["TEAM_ABBREVIATION"] == team]
        all_values.extend([team_data[m].values[0] for m in available_metrics])
    if all_values:
        v_min, v_max = min(all_values), max(all_values)
        v_range = v_max - v_min if v_max != v_min else 1
        ax.set_ylim(v_min - v_range * 0.3, v_max + v_range * 0.3)

    ax.set_xlabel('Metrics', fontsize=12)
    ax.set_ylabel('Value', fontsize=12)
    ax.set_title(f'Team Comparison: {" vs ".join(teams)} ({spec.window})',
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(available_metrics)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    return fig


def create_summary_text(spec: ChartSpec, result_df: pd.DataFrame, explanation: str) -> str:
    """
    Generate a summary text block for display alongside the chart.
    """
    lines = [
        f"**Query Type:** {spec.chart_type.title()}",
        f"**Time Window:** {spec.window}",
        f"**Teams Analyzed:** {len(result_df)}",
        "",
        "**Explanation:**",
        explanation,
    ]
    
    if spec.chart_type == "leaderboard" and len(result_df) > 0:
        top_team = result_df.iloc[0]
        lines.extend([
            "",
            f"**Top Team:** {top_team['TEAM_ABBREVIATION']} ({spec.metric}: {top_team[spec.metric]:.1f})"
        ])
    
    if spec.chart_type == "scatter":
        lines.extend([
            "",
            f"**League Average {spec.x_metric}:** {result_df[spec.x_metric].mean():.1f}",
            f"**League Average {spec.y_metric}:** {result_df[spec.y_metric].mean():.1f}",
        ])
    
    return "\n".join(lines)
