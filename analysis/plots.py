"""Generate plots for insight report."""
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


def plot_price_vs_var_by_position(analysis_df: pd.DataFrame, output_dir: Path):
    """Plot price vs VAR scatter by position."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    has_data = analysis_df['VAR'].notna() & analysis_df['normalized_price'].notna() & (analysis_df['normalized_price'] > 0)
    if not has_data.any():
        logger.warning("No data for price vs VAR plot")
        return
    
    df_plot = analysis_df[has_data].copy()
    
    positions = df_plot['position'].unique()
    n_positions = len(positions)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()
    
    for i, pos in enumerate(positions[:4]):  # QB, RB, WR, TE
        pos_data = df_plot[df_plot['position'] == pos]
        
        ax = axes[i]
        ax.scatter(pos_data['normalized_price'], pos_data['VAR'], alpha=0.6, s=50)
        
        # Add trendline
        if len(pos_data) > 1:
            z = np.polyfit(pos_data['normalized_price'], pos_data['VAR'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(pos_data['normalized_price'].min(), pos_data['normalized_price'].max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
        
        ax.set_xlabel('Normalized Price ($)')
        ax.set_ylabel('VAR')
        ax.set_title(f'{pos}: Price vs VAR')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    file_path = plots_dir / "price_vs_var_by_position.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved price vs VAR plot to {file_path}")


def plot_var_per_dollar_by_manager(manager_season_value_df: pd.DataFrame, output_dir: Path):
    """Plot VAR per dollar by manager (bar chart)."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if manager_season_value_df.empty:
        logger.warning("No data for VAR per dollar plot")
        return
    
    # Career aggregates
    manager_careers = manager_season_value_df.groupby('manager').agg({
        'total_VAR': 'sum',
        'total_spend': 'sum'
    }).reset_index()
    manager_careers['VAR_per_dollar'] = manager_careers['total_VAR'] / manager_careers['total_spend']
    manager_careers = manager_careers.sort_values('VAR_per_dollar', ascending=True)
    
    plt.figure(figsize=(10, 8))
    plt.barh(manager_careers['manager'], manager_careers['VAR_per_dollar'])
    plt.xlabel('VAR per Dollar')
    plt.title('Manager Efficiency: VAR per Dollar (Career)')
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "var_per_dollar_by_manager.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved VAR per dollar plot to {file_path}")


def plot_champion_vs_field_shares(champion_blueprint: dict, manager_season_value_df: pd.DataFrame, output_dir: Path):
    """Plot VAR source shares: champions vs non-champions."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if manager_season_value_df.empty:
        logger.warning("No data for champion shares plot")
        return
    
    # Calculate averages
    champions = manager_season_value_df[manager_season_value_df['champion_flag'] == True]
    non_champions = manager_season_value_df[manager_season_value_df['champion_flag'] == False]
    
    if champions.empty or non_champions.empty:
        logger.warning("Need both champions and non-champions for comparison plot")
        return
    
    champ_avg = {
        'Draft': champions['pct_VAR_from_draft'].mean(),
        'Keeper': champions['pct_VAR_from_keeper'].mean(),
        'Waiver': champions['pct_VAR_from_waiver'].mean(),
        'Trade': champions['pct_VAR_from_trade'].mean()
    }
    
    non_champ_avg = {
        'Draft': non_champions['pct_VAR_from_draft'].mean(),
        'Keeper': non_champions['pct_VAR_from_keeper'].mean(),
        'Waiver': non_champions['pct_VAR_from_waiver'].mean(),
        'Trade': non_champions['pct_VAR_from_trade'].mean()
    }
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(champ_avg))
    width = 0.35
    
    ax.bar(x - width/2, [champ_avg[k] for k in champ_avg.keys()], width, label='Champions', alpha=0.8)
    ax.bar(x + width/2, [non_champ_avg[k] for k in non_champ_avg.keys()], width, label='Non-Champions', alpha=0.8)
    
    ax.set_xlabel('VAR Source')
    ax.set_ylabel('Percentage of Total VAR')
    ax.set_title('VAR Source Distribution: Champions vs Non-Champions')
    ax.set_xticks(x)
    ax.set_xticklabels(champ_avg.keys())
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    file_path = plots_dir / "champions_vs_field_shares.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved champion shares plot to {file_path}")


def plot_wins_distribution_by_manager(manager_season_value_df: pd.DataFrame, output_dir: Path):
    """Plot wins distribution by manager (boxplot)."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if manager_season_value_df.empty:
        logger.warning("No data for wins distribution plot")
        return
    
    # Filter to managers with at least 3 seasons for meaningful boxplot
    manager_counts = manager_season_value_df['manager'].value_counts()
    managers_with_enough = manager_counts[manager_counts >= 3].index.tolist()
    plot_data = manager_season_value_df[manager_season_value_df['manager'].isin(managers_with_enough)]
    
    if plot_data.empty:
        logger.warning("No managers with 3+ seasons for wins distribution plot")
        return
    
    plt.figure(figsize=(14, 8))
    plot_data.boxplot(column='wins', by='manager', ax=plt.gca(), rot=45, grid=False)
    plt.title('Wins Distribution by Manager')
    plt.suptitle('')  # Remove default title
    plt.xlabel('Manager')
    plt.ylabel('Wins per Season')
    plt.tight_layout()
    
    file_path = plots_dir / "wins_distribution_by_manager.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved wins distribution plot to {file_path}")


def plot_var_distribution_by_manager(manager_season_value_df: pd.DataFrame, output_dir: Path):
    """Plot VAR distribution by manager (boxplot)."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if manager_season_value_df.empty:
        logger.warning("No data for VAR distribution plot")
        return
    
    # Filter to managers with at least 3 seasons
    manager_counts = manager_season_value_df['manager'].value_counts()
    managers_with_enough = manager_counts[manager_counts >= 3].index.tolist()
    plot_data = manager_season_value_df[manager_season_value_df['manager'].isin(managers_with_enough)]
    
    if plot_data.empty:
        logger.warning("No managers with 3+ seasons for VAR distribution plot")
        return
    
    plt.figure(figsize=(14, 8))
    plot_data.boxplot(column='total_VAR', by='manager', ax=plt.gca(), rot=45, grid=False)
    plt.title('Total VAR Distribution by Manager')
    plt.suptitle('')
    plt.xlabel('Manager')
    plt.ylabel('Total VAR per Season')
    plt.tight_layout()
    
    file_path = plots_dir / "VAR_distribution_by_manager.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved VAR distribution plot to {file_path}")


def plot_mean_vs_std_wins(distribution_df: pd.DataFrame, output_dir: Path):
    """Plot mean vs std wins scatter."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if distribution_df.empty:
        logger.warning("No data for mean vs std wins plot")
        return
    
    # Filter to managers with at least 3 seasons
    plot_data = distribution_df[distribution_df['seasons_played'] >= 3].copy()
    
    if plot_data.empty:
        logger.warning("No managers with 3+ seasons for mean vs std wins plot")
        return
    
    plt.figure(figsize=(10, 8))
    plt.scatter(plot_data['mean_wins'], plot_data['std_wins'], alpha=0.6, s=100)
    
    # Label points
    for _, row in plot_data.iterrows():
        plt.annotate(row['manager'], (row['mean_wins'], row['std_wins']), 
                    fontsize=8, alpha=0.7)
    
    plt.xlabel('Mean Wins per Season')
    plt.ylabel('Std Wins per Season')
    plt.title('Manager Consistency: Mean vs Std Dev of Wins')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "mean_vs_std_wins_scatter.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved mean vs std wins plot to {file_path}")


def plot_championships_vs_median_wins(distribution_df: pd.DataFrame, output_dir: Path):
    """Plot championships vs median wins."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if distribution_df.empty:
        logger.warning("No data for championships vs median wins plot")
        return
    
    plt.figure(figsize=(10, 8))
    plt.scatter(distribution_df['median_wins'], distribution_df['championships'], 
               alpha=0.6, s=100, c=distribution_df['std_wins'], cmap='viridis')
    plt.colorbar(label='Std Wins')
    
    # Label champions
    champions = distribution_df[distribution_df['championships'] > 0]
    for _, row in champions.iterrows():
        plt.annotate(row['manager'], (row['median_wins'], row['championships']), 
                    fontsize=8, alpha=0.7)
    
    plt.xlabel('Median Wins per Season')
    plt.ylabel('Total Championships')
    plt.title('Championships vs Median Wins (color = std wins)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "championships_vs_median_wins.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved championships vs median wins plot to {file_path}")


def plot_wins_vs_expected_wins(schedule_df: pd.DataFrame, expected_wins_df: pd.DataFrame, output_dir: Path):
    """Plot wins vs expected wins scatter."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if schedule_df.empty or expected_wins_df.empty:
        logger.warning("No data for wins vs expected wins plot")
        return
    
    merged = schedule_df.merge(
        expected_wins_df,
        on=['season_year', 'manager'],
        how='inner'
    )
    
    if merged.empty:
        logger.warning("No matching data for wins vs expected wins plot")
        return
    
    plt.figure(figsize=(10, 8))
    plt.scatter(merged['expected_wins'], merged['wins'], alpha=0.6, s=50)
    
    # Add diagonal line (y=x)
    max_wins = max(merged['expected_wins'].max(), merged['wins'].max())
    plt.plot([0, max_wins], [0, max_wins], 'r--', alpha=0.8, linewidth=2, label='Expected = Actual')
    
    plt.xlabel('Expected Wins (All-Play)')
    plt.ylabel('Actual Wins')
    plt.title('Actual Wins vs Expected Wins (All-Play Model)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "wins_vs_expected_wins_scatter.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved wins vs expected wins plot to {file_path}")


def plot_pa_diff_by_manager(schedule_df: pd.DataFrame, output_dir: Path):
    """Plot PA_diff by manager (boxplot)."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if schedule_df.empty:
        logger.warning("No data for PA_diff plot")
        return
    
    # Filter to managers with at least 3 seasons
    manager_counts = schedule_df['manager'].value_counts()
    managers_with_enough = manager_counts[manager_counts >= 3].index.tolist()
    plot_data = schedule_df[schedule_df['manager'].isin(managers_with_enough)]
    
    if plot_data.empty:
        logger.warning("No managers with 3+ seasons for PA_diff plot")
        return
    
    plt.figure(figsize=(14, 8))
    plot_data.boxplot(column='PA_diff', by='manager', ax=plt.gca(), rot=45, grid=False)
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='League Average')
    plt.title('Points Against Difference (PA_diff) by Manager')
    plt.suptitle('')
    plt.xlabel('Manager')
    plt.ylabel('PA_diff (points_against - league_avg)')
    plt.legend()
    plt.tight_layout()
    
    file_path = plots_dir / "PA_diff_by_manager_boxplot.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved PA_diff plot to {file_path}")


def plot_pf_vs_pa_scatter(schedule_df: pd.DataFrame, output_dir: Path):
    """Plot points_for vs points_against scatter."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if schedule_df.empty:
        logger.warning("No data for PF vs PA plot")
        return
    
    plt.figure(figsize=(10, 8))
    plt.scatter(schedule_df['avg_points_against'], schedule_df['avg_points_for'], alpha=0.6, s=50)
    
    plt.xlabel('Average Points Against (Schedule Difficulty)')
    plt.ylabel('Average Points For (Team Performance)')
    plt.title('Points For vs Points Against (All Manager-Seasons)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "PF_vs_PA_scatter.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved PF vs PA plot to {file_path}")


def plot_championship_luck_quadrant(championship_luck_df: pd.DataFrame, output_dir: Path):
    """Plot championship luck quadrant (PF percentile vs wins_over_expected)."""
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    if championship_luck_df.empty:
        logger.warning("No data for championship luck quadrant")
        return
    
    plot_data = championship_luck_df[
        championship_luck_df['points_for_percentile'].notna() &
        championship_luck_df['wins_over_expected'].notna()
    ].copy()
    
    if plot_data.empty:
        logger.warning("Insufficient data for championship luck quadrant")
        return
    
    plt.figure(figsize=(10, 8))
    
    # Color by championship type
    colors = {
        'DOMINANT': 'green',
        'BALANCED': 'blue',
        'LUCKY': 'orange'
    }
    
    for champ_type in plot_data['championship_type'].unique():
        type_data = plot_data[plot_data['championship_type'] == champ_type]
        color = colors.get(champ_type, 'gray')
        plt.scatter(
            type_data['points_for_percentile'],
            type_data['wins_over_expected'],
            alpha=0.7,
            s=100,
            label=champ_type,
            color=color
        )
        
        # Label points
        for _, row in type_data.iterrows():
            plt.annotate(
                f"{int(row['season_year'])}",
                (row['points_for_percentile'], row['wins_over_expected']),
                fontsize=8,
                alpha=0.8
            )
    
    # Add quadrant lines
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    plt.axvline(x=50, color='black', linestyle='--', alpha=0.5, linewidth=1)
    
    plt.xlabel('Points For Percentile')
    plt.ylabel('Wins Over Expected')
    plt.title('Championship Type: Performance vs Luck')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    file_path = plots_dir / "championships_luck_quadrant.png"
    plt.savefig(file_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved championship luck quadrant to {file_path}")

