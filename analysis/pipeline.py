"""Main analysis pipeline orchestrator."""
import pandas as pd
from typing import Dict
from pathlib import Path
import logging

from .data_loader import DataLoader
from .normalize import normalize_prices
from .var import calculate_var
from .tiers import assign_draft_tiers, assign_actual_tiers, calculate_tier_hit_rates
from .keepers import calculate_keeper_surplus, analyze_keeper_value
from .lifecycle_extended import build_complete_lifecycle
from .waivers import analyze_waiver_pickups
from .trades import analyze_trade_impact
from .strategies import build_manager_strategy_profiles
from .outputs import (
    save_analysis_ready_data,
    save_tier_summary,
    save_position_efficiency,
    save_keeper_surplus_summary,
    plot_price_vs_var,
    save_missing_players_report
)

logger = logging.getLogger(__name__)


def run_analysis(
    start_year: int,
    end_year: int,
    output_dir: str = "./out",
    baseline_season: int = 2014
) -> Dict:
    """Run the complete auction + keeper value analysis pipeline.
    
    Args:
        start_year: First season to analyze
        end_year: Last season to analyze (inclusive)
        output_dir: Directory to save outputs
        baseline_season: Season to use as baseline for normalization
        
    Returns:
        Dictionary with analysis results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting analysis pipeline for seasons {start_year}-{end_year}")
    
    # Step 1: Load data
    logger.info("Step 1: Loading data...")
    loader = DataLoader()
    drafts_df, results_df, league_meta, transactions_df = loader.load_data(
        start_year, end_year, include_transactions=True
    )
    
    if drafts_df.empty:
        raise ValueError("No draft data found for specified years")
    
    # Check if we have player points
    has_points = results_df['fantasy_points_total'].notna().any()
    if not has_points:
        logger.warning(
            "WARNING: No player fantasy points found in results. "
            "Analysis will be limited. You may need to add player stats extraction."
        )
    
    # Step 2: Normalize prices
    logger.info("Step 2: Normalizing prices...")
    drafts_normalized = normalize_prices(drafts_df, league_meta, baseline_season)
    
    # Step 3: Calculate VAR
    logger.info("Step 3: Calculating VAR...")
    analysis_df = calculate_var(results_df, drafts_normalized, league_meta)
    
    # Step 4: Assign tiers
    logger.info("Step 4: Assigning draft tiers...")
    analysis_df = assign_draft_tiers(analysis_df, league_meta)
    analysis_df = assign_actual_tiers(analysis_df, league_meta)
    
    # Step 5: Calculate tier hit rates
    logger.info("Step 5: Calculating tier hit rates...")
    tier_summary = calculate_tier_hit_rates(analysis_df)
    
    # Step 6: Keeper surplus analysis
    logger.info("Step 6: Analyzing keeper surplus...")
    analysis_df = calculate_keeper_surplus(analysis_df)
    keeper_summary = analyze_keeper_value(analysis_df)
    
    # Step 7: Extended lifecycle analysis (waivers, trades, roster churn)
    logger.info("Step 7: Building complete lifecycle (waivers/trades)...")
    
    lifecycle_df = pd.DataFrame()
    waiver_pickups_df = pd.DataFrame()
    trade_impact_df = pd.DataFrame()
    manager_profiles_df = pd.DataFrame()
    
    try:
        lifecycle_df = build_complete_lifecycle(
            drafts_df, transactions_df, results_df, league_meta
        )
        
        # Merge VAR data from analysis_df into lifecycle_df
        if not lifecycle_df.empty and 'VAR' in analysis_df.columns:
            var_data = analysis_df[['season_year', 'player_id', 'VAR']].copy()
            var_data = var_data[var_data['VAR'].notna()]  # Only include players with VAR
            
            lifecycle_df = lifecycle_df.merge(
                var_data,
                on=['season_year', 'player_id'],
                how='left',
                suffixes=('', '_from_analysis')
            )
            # Use VAR from analysis if available
            if 'VAR_from_analysis' in lifecycle_df.columns:
                # Fill VAR_total with VAR_from_analysis where available
                lifecycle_df['VAR_total'] = lifecycle_df['VAR_from_analysis'].fillna(
                    lifecycle_df.get('VAR_total', pd.Series(dtype=float))
                )
            elif 'VAR' in lifecycle_df.columns:
                lifecycle_df['VAR_total'] = lifecycle_df['VAR']
        
        # Step 8: Waiver pickup analysis
        logger.info("Step 8: Analyzing waiver pickups...")
        waiver_pickups_df = analyze_waiver_pickups(
            lifecycle_df, results_df, transactions_df, league_meta, analysis_df
        )
        
        # Step 9: Trade impact analysis
        logger.info("Step 9: Analyzing trade impact...")
        trade_impact_df = analyze_trade_impact(
            transactions_df, lifecycle_df, results_df, league_meta
        )
        
        # Step 10: Manager strategy profiles
        logger.info("Step 10: Building manager strategy profiles...")
        manager_profiles_df = build_manager_strategy_profiles(
            lifecycle_df, waiver_pickups_df, trade_impact_df, drafts_df
        )
        
    except Exception as e:
        logger.warning(f"Extended lifecycle analysis failed: {e}")
        logger.warning("Continuing with basic analysis only...")
    
    # Step 11: Save outputs
    logger.info("Step 7: Saving outputs...")
    
    # Save analysis-ready data per season
    for season in analysis_df['season_year'].unique():
        save_analysis_ready_data(analysis_df, output_path, int(season))
    
    # Save summaries
    if not tier_summary.empty:
        save_tier_summary(tier_summary, output_path)
    
    save_position_efficiency(analysis_df, output_path)
    
    if not keeper_summary.empty:
        save_keeper_surplus_summary(keeper_summary, output_path)
    
    # Generate plots
    plot_price_vs_var(analysis_df, output_path)
    
    # Extended plots
    try:
        from .outputs_extended import plot_faab_vs_var, plot_var_by_source
        
        if waiver_pickups_df is not None and not waiver_pickups_df.empty:
            plot_faab_vs_var(waiver_pickups_df, output_path)
        
        if manager_profiles_df is not None and not manager_profiles_df.empty:
            plot_var_by_source(manager_profiles_df, output_path)
    except ImportError:
        logger.debug("Extended plot functions not available")
    
    # Missing players report
    save_missing_players_report(drafts_df, results_df, output_path)
    
    # Save extended lifecycle outputs
    if not lifecycle_df.empty:
        lifecycle_path = output_path / "lifecycle_table.parquet"
        lifecycle_df.to_parquet(lifecycle_path, index=False)
        logger.info(f"Saved lifecycle table to {lifecycle_path}")
    
    if not waiver_pickups_df.empty:
        waiver_path = output_path / "waiver_pickups.csv"
        waiver_pickups_df.to_csv(waiver_path, index=False)
        logger.info(f"Saved waiver pickups to {waiver_path}")
        
        # Save pickup archetypes summary
        if 'pickup_type' in waiver_pickups_df.columns:
            archetypes = waiver_pickups_df.groupby(['pickup_type', 'position']).agg({
                'player_id': 'count',
                'var_after_pickup': 'mean',
                'cost_efficiency': 'mean',
            }).reset_index()
            archetypes.columns = ['pickup_type', 'position', 'count', 'avg_VAR', 'avg_cost_efficiency']
            archetypes_path = output_path / "pickup_archetypes.csv"
            archetypes.to_csv(archetypes_path, index=False)
            logger.info(f"Saved pickup archetypes to {archetypes_path}")
    
    if not trade_impact_df.empty:
        trade_path = output_path / "trade_impact.csv"
        trade_impact_df.to_csv(trade_path, index=False)
        logger.info(f"Saved trade impact to {trade_path}")
    
    if not manager_profiles_df.empty:
        profiles_path = output_path / "manager_strategy_profiles.csv"
        manager_profiles_df.to_csv(profiles_path, index=False)
        logger.info(f"Saved manager profiles to {profiles_path}")
    
    # Generate summary report
    generate_summary_report(
        analysis_df, tier_summary, keeper_summary, league_meta,
        output_path, start_year, end_year,
        lifecycle_df, waiver_pickups_df, trade_impact_df, manager_profiles_df
    )
    
    logger.info(f"Analysis complete! Outputs saved to {output_path}")
    
    return {
        'analysis_df': analysis_df,
        'tier_summary': tier_summary,
        'keeper_summary': keeper_summary,
        'lifecycle_df': lifecycle_df,
        'waiver_pickups_df': waiver_pickups_df,
        'trade_impact_df': trade_impact_df,
        'manager_profiles_df': manager_profiles_df,
        'league_meta': league_meta
    }


def generate_summary_report(
    analysis_df: pd.DataFrame,
    tier_summary: pd.DataFrame,
    keeper_summary: pd.DataFrame,
    league_meta: Dict,
    output_dir: Path,
    start_year: int,
    end_year: int,
    lifecycle_df: pd.DataFrame = None,
    waiver_pickups_df: pd.DataFrame = None,
    trade_impact_df: pd.DataFrame = None,
    manager_profiles_df: pd.DataFrame = None
):
    """Generate a markdown summary report.
    
    Args:
        analysis_df: Complete analysis DataFrame
        tier_summary: Tier hit rates summary
        keeper_summary: Keeper analysis summary
        league_meta: League metadata
        output_dir: Output directory
        start_year: Start year
        end_year: End year
    """
    output_path = output_dir / "ANALYSIS_SUMMARY.md"
    
    lines = []
    lines.append("# Auction + Keeper Value Analysis Summary")
    lines.append("")
    lines.append(f"**Analysis Period:** {start_year}-{end_year}")
    lines.append(f"**Baseline Season:** {min(league_meta.keys())}")
    lines.append("")
    
    # Overall statistics
    lines.append("## Overall Statistics")
    lines.append("")
    total_players = len(analysis_df)
    players_with_var = analysis_df['VAR'].notna().sum()
    players_with_points = analysis_df['fantasy_points_total'].notna().sum()
    
    lines.append(f"- Total Drafted Players: {total_players:,}")
    lines.append(f"- Players with VAR: {players_with_var:,} ({100*players_with_var/total_players:.1f}%)")
    lines.append(f"- Players with Points: {players_with_points:,} ({100*players_with_points/total_players:.1f}%)")
    lines.append("")
    
    # Key insights
    has_data = analysis_df['VAR'].notna() & analysis_df['normalized_price'].notna()
    if has_data.any():
        lines.append("## Key Insights")
        lines.append("")
        
        # Best value by position
        df_with_data = analysis_df[has_data].copy()
        best_value = df_with_data.nlargest(10, 'VAR_per_dollar')[['player_name', 'position', 'normalized_price', 'VAR', 'VAR_per_dollar']]
        
        lines.append("### Top 10 Value Picks (VAR per Dollar)")
        lines.append("")
        lines.append("| Player | Position | Price | VAR | VAR/$ |")
        lines.append("|--------|----------|-------|-----|-------|")
        for _, row in best_value.iterrows():
            lines.append(f"| {row['player_name']} | {row['position']} | ${row['normalized_price']:.1f} | {row['VAR']:.1f} | {row['VAR_per_dollar']:.2f} |")
        lines.append("")
        
        # Tier hit rates summary
        if not tier_summary.empty:
            lines.append("### Tier Hit Rates by Position")
            lines.append("")
            for position in ['QB', 'RB', 'WR', 'TE']:
                pos_tiers = tier_summary[tier_summary['position'] == position]
                if not pos_tiers.empty:
                    avg_hit_rate = pos_tiers['hit_rate'].mean()
                    lines.append(f"- **{position}**: {avg_hit_rate:.1%} average hit rate")
            lines.append("")
        
        # Keeper insights
        if not keeper_summary.empty:
            lines.append("### Keeper Analysis")
            lines.append("")
            keepers = analysis_df[analysis_df['is_keeper'] == True]
            total_keepers = len(keepers)
            if total_keepers > 0:
                avg_surplus = keepers['keeper_surplus'].mean()
                lines.append(f"- Total Keepers Analyzed: {total_keepers}")
                lines.append(f"- Average Keeper Surplus: ${avg_surplus:.2f}")
                if 'surplus_VAR_correlation' in keeper_summary.columns:
                    corr = keeper_summary['surplus_VAR_correlation'].iloc[0] if len(keeper_summary) > 0 else None
                    if pd.notna(corr):
                        lines.append(f"- Keeper Surplus vs VAR Correlation: {corr:.3f}")
            lines.append("")
        
        # Waiver pickup insights
        if waiver_pickups_df is not None and not waiver_pickups_df.empty:
            lines.append("### Waiver Pickup Analysis")
            lines.append("")
            total_pickups = len(waiver_pickups_df)
            league_winners = len(waiver_pickups_df[waiver_pickups_df['pickup_type'] == 'LEAGUE_WINNER'])
            solid_starters = len(waiver_pickups_df[waiver_pickups_df['pickup_type'] == 'SOLID_STARTER'])
            streamers = len(waiver_pickups_df[waiver_pickups_df['pickup_type'] == 'STREAMER'])
            became_keepers = waiver_pickups_df['became_keeper'].sum()
            
            lines.append(f"- Total Waiver/FA Pickups: {total_pickups}")
            lines.append(f"- League Winners: {league_winners} ({100*league_winners/total_pickups:.1f}%)")
            lines.append(f"- Solid Starters: {solid_starters} ({100*solid_starters/total_pickups:.1f}%)")
            lines.append(f"- Streamers: {streamers} ({100*streamers/total_pickups:.1f}%)")
            lines.append(f"- Became Keepers: {became_keepers} ({100*became_keepers/total_pickups:.1f}%)")
            lines.append("")
        
        # Manager strategy insights
        if manager_profiles_df is not None and not manager_profiles_df.empty:
            lines.append("### Manager Strategy Profiles")
            lines.append("")
            if 'manager_archetype' in manager_profiles_df.columns:
                archetype_counts = manager_profiles_df['manager_archetype'].value_counts()
                lines.append("Manager Archetype Distribution:")
                for archetype, count in archetype_counts.items():
                    lines.append(f"- {archetype}: {count}")
            lines.append("")
    
    lines.append("## Output Files")
    lines.append("")
    lines.append("- `analysis_ready_{season}.parquet`: Complete analysis-ready dataset per season")
    lines.append("- `tier_summary.csv`: Tier hit rates and bust rates")
    lines.append("- `position_efficiency.csv`: Dollar efficiency by position and tier")
    lines.append("- `keeper_surplus_summary.csv`: Keeper value analysis")
    lines.append("- `price_vs_var_by_position.png`: Scatter plots of price vs VAR")
    lines.append("- `missing_players.csv`: Players in drafts but missing from results")
    
    # Extended lifecycle outputs
    if lifecycle_df is not None and not lifecycle_df.empty:
        lines.append("- `lifecycle_table.parquet`: Complete player-season lifecycle")
    if waiver_pickups_df is not None and not waiver_pickups_df.empty:
        lines.append("- `waiver_pickups.csv`: Waiver/FA pickup analysis")
        lines.append("- `pickup_archetypes.csv`: Pickup classification summary")
    if trade_impact_df is not None and not trade_impact_df.empty:
        lines.append("- `trade_impact.csv`: Trade impact analysis")
    if manager_profiles_df is not None and not manager_profiles_df.empty:
        lines.append("- `manager_strategy_profiles.csv`: Manager strategy archetypes")
    
    lines.append("")
    
    lines.append("## Methodology")
    lines.append("")
    lines.append("1. **Price Normalization**: Prices normalized to baseline season accounting for keeper inflation")
    lines.append("2. **VAR Calculation**: Value Above Replacement = Player Points - Replacement Baseline Points")
    lines.append("3. **Tier Assignment**: Tiers based on normalized price ranks within position")
    lines.append("4. **Keeper Surplus**: Market Price Estimate - Keeper Cost")
    lines.append("")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    logger.info(f"Saved summary report to {output_path}")

