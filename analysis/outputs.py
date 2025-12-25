"""Generate analysis outputs (CSV, Parquet, plots)."""
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Set style for plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


def save_analysis_ready_data(
    df: pd.DataFrame,
    output_dir: Path,
    season: int
):
    """Save analysis-ready dataset per season as Parquet.
    
    Args:
        df: Analysis-ready DataFrame
        output_dir: Output directory
        season: Season year
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    season_data = df[df['season_year'] == season].copy()
    output_path = output_dir / f"analysis_ready_{season}.parquet"
    season_data.to_parquet(output_path, index=False)
    logger.info(f"Saved analysis-ready data for {season} to {output_path}")


def save_tier_summary(
    tier_summary: pd.DataFrame,
    output_dir: Path
):
    """Save tier summary to CSV.
    
    Args:
        tier_summary: Tier hit rates DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "tier_summary.csv"
    tier_summary.to_csv(output_path, index=False)
    logger.info(f"Saved tier summary to {output_path}")


def save_position_efficiency(
    df: pd.DataFrame,
    output_dir: Path
):
    """Calculate and save position efficiency metrics.
    
    Args:
        df: Analysis-ready DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter to players with VAR and price data
    has_data = df['VAR'].notna() & df['normalized_price'].notna() & (df['normalized_price'] > 0)
    df_with_data = df[has_data].copy()
    
    if df_with_data.empty:
        logger.warning("No data for position efficiency calculation")
        return
    
    # Calculate by position and tier
    efficiency = df_with_data.groupby(['position', 'expected_tier']).agg({
        'player_id': 'count',
        'VAR_per_dollar': ['mean', 'median'],
        'dollar_per_VAR': ['mean', 'median'],
        'normalized_price': 'mean',
        'VAR': 'mean',
    }).reset_index()
    
    efficiency.columns = [
        'position', 'expected_tier',
        'count', 'avg_VAR_per_dollar', 'median_VAR_per_dollar',
        'avg_dollar_per_VAR', 'median_dollar_per_VAR',
        'avg_price', 'avg_VAR'
    ]
    
    output_path = output_dir / "position_efficiency.csv"
    efficiency.to_csv(output_path, index=False)
    logger.info(f"Saved position efficiency to {output_path}")


def save_keeper_surplus_summary(
    keeper_summary: pd.DataFrame,
    output_dir: Path
):
    """Save keeper surplus summary to CSV.
    
    Args:
        keeper_summary: Keeper analysis DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "keeper_surplus_summary.csv"
    keeper_summary.to_csv(output_path, index=False)
    logger.info(f"Saved keeper surplus summary to {output_path}")


def plot_price_vs_var(
    df: pd.DataFrame,
    output_dir: Path
):
    """Create price vs VAR scatter plots by position.
    
    Args:
        df: Analysis-ready DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter to players with both price and VAR
    has_data = df['VAR'].notna() & df['normalized_price'].notna() & (df['normalized_price'] > 0)
    df_plot = df[has_data].copy()
    
    if df_plot.empty:
        logger.warning("No data for price vs VAR plot")
        return
    
    positions = ['QB', 'RB', 'WR', 'TE']
    n_positions = len(positions)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, position in enumerate(positions):
        if idx >= len(axes):
            break
        
        ax = axes[idx]
        pos_data = df_plot[df_plot['position'] == position]
        
        if pos_data.empty:
            ax.text(0.5, 0.5, f'No data for {position}', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{position}: Price vs VAR')
            continue
        
        # Scatter plot
        scatter = ax.scatter(
            pos_data['normalized_price'],
            pos_data['VAR'],
            alpha=0.6,
            s=50
        )
        
        # Add trend line (LOESS or simple linear)
        try:
            z = np.polyfit(pos_data['normalized_price'], pos_data['VAR'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(pos_data['normalized_price'].min(), 
                               pos_data['normalized_price'].max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.8, label='Trend')
            ax.legend()
        except:
            pass
        
        ax.set_xlabel('Normalized Price ($)')
        ax.set_ylabel('VAR (Value Above Replacement)')
        ax.set_title(f'{position}: Price vs VAR (n={len(pos_data)})')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "price_vs_var_by_position.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved price vs VAR plot to {output_path}")


def save_missing_players_report(
    drafts_df: pd.DataFrame,
    results_df: pd.DataFrame,
    output_dir: Path
):
    """Save report of players in drafts but missing from results.
    
    Args:
        drafts_df: Draft DataFrame
        results_df: Results DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Merge to find missing
    merged = drafts_df.merge(
        results_df,
        on=['season_year', 'player_id'],
        how='left',
        indicator=True
    )
    
    missing = merged[merged['_merge'] == 'left_only'].copy()
    
    if not missing.empty:
        # Get columns with draft suffix or original name
        cols = ['season_year', 'player_id']
        for col in ['player_name', 'position', 'cost']:
            if col in missing.columns:
                cols.append(col)
            elif f'{col}_draft' in missing.columns:
                cols.append(f'{col}_draft')
            elif f'{col}_result' in missing.columns:
                cols.append(f'{col}_result')
        
        missing_report = missing[cols].copy()
        # Rename columns back to standard names
        missing_report.columns = [c.replace('_draft', '').replace('_result', '') for c in missing_report.columns]
        
        if 'cost' in missing_report.columns:
            missing_report = missing_report.sort_values(['season_year', 'cost'], ascending=[True, False])
        else:
            missing_report = missing_report.sort_values('season_year')
        
        output_path = output_dir / "missing_players.csv"
        missing_report.to_csv(output_path, index=False)
        logger.warning(f"Found {len(missing_report)} players missing from results - saved to {output_path}")
    else:
        logger.info("All drafted players found in results")

