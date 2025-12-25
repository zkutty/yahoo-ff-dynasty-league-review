"""Extended outputs for waiver/trade/strategy analysis."""
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def plot_faab_vs_var(
    waiver_pickups_df: pd.DataFrame,
    output_dir: Path
):
    """Create FAAB vs VAR scatter plot for waiver pickups.
    
    Args:
        waiver_pickups_df: Waiver pickups DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter to pickups with FAAB and VAR data
    has_data = (
        waiver_pickups_df['acquisition_cost'].notna() &
        (waiver_pickups_df['acquisition_cost'] > 0) &
        waiver_pickups_df['var_after_pickup'].notna()
    )
    df_plot = waiver_pickups_df[has_data].copy()
    
    if df_plot.empty:
        logger.warning("No data for FAAB vs VAR plot")
        return
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Color by pickup type if available
    if 'pickup_type' in df_plot.columns:
        for pickup_type in df_plot['pickup_type'].unique():
            type_data = df_plot[df_plot['pickup_type'] == pickup_type]
            ax.scatter(
                type_data['acquisition_cost'],
                type_data['var_after_pickup'],
                alpha=0.6,
                label=pickup_type,
                s=50
            )
        ax.legend(title='Pickup Type')
    else:
        ax.scatter(
            df_plot['acquisition_cost'],
            df_plot['var_after_pickup'],
            alpha=0.6,
            s=50
        )
    
    ax.set_xlabel('FAAB Spent ($)')
    ax.set_ylabel('VAR After Pickup')
    ax.set_title(f'FAAB vs VAR: Waiver Pickups (n={len(df_plot)})')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "faab_vs_var.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved FAAB vs VAR plot to {output_path}")


def plot_var_by_source(
    manager_profiles_df: pd.DataFrame,
    output_dir: Path
):
    """Create stacked bar chart showing VAR by acquisition source.
    
    Args:
        manager_profiles_df: Manager strategy profiles DataFrame
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if manager_profiles_df.empty:
        logger.warning("No data for VAR by source plot")
        return
    
    # Aggregate by season
    if 'season_year' in manager_profiles_df.columns:
        by_season = manager_profiles_df.groupby('season_year').agg({
            'draft_var': 'sum',
            'keeper_var': 'sum',
            'waiver_var': 'sum',
            'trade_var': 'sum',
        }).reset_index()
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        seasons = by_season['season_year']
        bottom = None
        
        ax.bar(seasons, by_season['draft_var'], label='Draft', bottom=bottom)
        bottom = by_season['draft_var']
        
        ax.bar(seasons, by_season['keeper_var'], label='Keeper', bottom=bottom)
        bottom = bottom + by_season['keeper_var']
        
        ax.bar(seasons, by_season['waiver_var'], label='Waiver/FA', bottom=bottom)
        bottom = bottom + by_season['waiver_var']
        
        ax.bar(seasons, by_season['trade_var'], label='Trade', bottom=bottom)
        
        ax.set_xlabel('Season')
        ax.set_ylabel('Total VAR')
        ax.set_title('VAR by Acquisition Source Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        output_path = output_dir / "var_by_acquisition_source.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved VAR by source plot to {output_path}")

