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
from .value_analysis import build_analysis_ready_player_season, build_manager_season_value
from .draft_hit_rates import build_draft_hit_rates
from .champion_blueprint import build_champion_blueprint
from .insight_report import generate_insight_report
from .consistency import (
    calculate_manager_outcome_distributions,
    calculate_consistency_scores,
    classify_manager_archetypes,
    calculate_season_volatility,
    calculate_manager_signal_strength,
    calculate_rolling_consistency
)
from .schedule_luck import (
    build_weekly_matchups_table,
    calculate_expected_wins,
    build_manager_season_schedule,
    calculate_schedule_difficulty,
    build_manager_luck_profile,
    analyze_championship_luck
)
from .weekly_lineups import (
    load_weekly_matchups_from_json,
    load_weekly_lineups_from_json,
    build_weekly_lineups_table,
    calculate_weekly_expected_wins,
    classify_losses,
    build_manager_season_lineup_stats
)
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
    
    # Also load teams and standings for manager analysis
    teams_df = pd.DataFrame()
    standings_df = pd.DataFrame()
    try:
        teams_path = loader.cleaned_data_dir / "teams.csv"
        if teams_path.exists():
            teams_df = pd.read_csv(teams_path)
            teams_df = teams_df[(teams_df['season_year'] >= start_year) & (teams_df['season_year'] <= end_year)]
        
        standings_path = loader.cleaned_data_dir / "standings.csv"
        if standings_path.exists():
            standings_df = pd.read_csv(standings_path)
            standings_df = standings_df[(standings_df['season_year'] >= start_year) & (standings_df['season_year'] <= end_year)]
    except Exception as e:
        logger.warning(f"Could not load teams/standings: {e}")
    
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
    
    # Step 11: Build outcome-linked analysis tables
    logger.info("Step 11: Building outcome-linked analysis tables...")
    
    # Build analysis-ready player-season table
    player_season_df = pd.DataFrame()
    try:
        player_season_df = build_analysis_ready_player_season(
            analysis_df,
            trades_df=transactions_df if not transactions_df.empty else None,
            standings_df=standings_df if not standings_df.empty else None
        )
    except Exception as e:
        logger.warning(f"Failed to build player-season table: {e}")
    
    # Build manager-season value table
    manager_season_value_df = pd.DataFrame()
    try:
        manager_season_value_df = build_manager_season_value(
            analysis_df,
            teams_df=teams_df if not teams_df.empty else pd.DataFrame(),
            standings_df=standings_df if not standings_df.empty else pd.DataFrame(),
            trades_df=transactions_df if not transactions_df.empty else None,
            waiver_pickups_df=waiver_pickups_df if not waiver_pickups_df.empty else None,
            lifecycle_df=lifecycle_df if not lifecycle_df.empty else None,
            league_meta=league_meta
        )
    except Exception as e:
        logger.warning(f"Failed to build manager-season value table: {e}")
    
    # Build draft hit rates
    draft_hit_rates_df = pd.DataFrame()
    try:
        draft_hit_rates_df = build_draft_hit_rates(analysis_df)
    except Exception as e:
        logger.warning(f"Failed to build draft hit rates: {e}")
    
    # Build champion blueprint
    champion_blueprint = {}
    try:
        if not manager_season_value_df.empty:
            champion_blueprint = build_champion_blueprint(
                manager_season_value_df,
                draft_hit_rates_df=draft_hit_rates_df if not draft_hit_rates_df.empty else None
            )
    except Exception as e:
        logger.warning(f"Failed to build champion blueprint: {e}")
    
    # Step 12: Save outputs
    logger.info("Step 12: Saving outputs...")
    
    # Save new analysis-ready player-season table
    if not player_season_df.empty:
        player_season_path = output_path / "analysis_ready_player_season.parquet"
        player_season_df.to_parquet(player_season_path, index=False)
        logger.info(f"Saved player-season table to {player_season_path}")
    
    # Save manager-season value
    if not manager_season_value_df.empty:
        manager_value_path = output_path / "manager_season_value.csv"
        manager_season_value_df.to_csv(manager_value_path, index=False)
        logger.info(f"Saved manager-season value to {manager_value_path}")
    
    # Save draft hit rates
    if not draft_hit_rates_df.empty:
        hit_rates_path = output_path / "draft_hit_rates.csv"
        draft_hit_rates_df.to_csv(hit_rates_path, index=False)
        logger.info(f"Saved draft hit rates to {hit_rates_path}")
    
    # Save champion blueprint
    if champion_blueprint:
        if 'blueprint' in champion_blueprint and not champion_blueprint['blueprint'].empty:
            blueprint_path = output_path / "champion_blueprint.csv"
            champion_blueprint['blueprint'].to_csv(blueprint_path, index=False)
            logger.info(f"Saved champion blueprint to {blueprint_path}")
        
        if 'comparison' in champion_blueprint and not champion_blueprint['comparison'].empty:
            comparison_path = output_path / "champion_comparison.csv"
            champion_blueprint['comparison'].to_csv(comparison_path, index=False)
            logger.info(f"Saved champion comparison to {comparison_path}")
    
    # Save analysis-ready data per season (original format)
    for season in analysis_df['season_year'].unique():
        save_analysis_ready_data(analysis_df, output_path, int(season))
    
    # Save summaries
    if not tier_summary.empty:
        save_tier_summary(tier_summary, output_path)
    
    save_position_efficiency(analysis_df, output_path)
    
    if not keeper_summary.empty:
        save_keeper_surplus_summary(keeper_summary, output_path)
    
    # Step 13: Weekly lineup and matchup analysis
    logger.info("Step 13: Building weekly lineup and matchup analysis...")
    
    # Load weekly matchups from JSON (preferred source)
    weekly_matchups_df = pd.DataFrame()
    try:
        weekly_matchups_df = load_weekly_matchups_from_json(
            loader.league_data_dir,
            start_year,
            end_year
        )
        
        # Merge manager info from teams
        if not weekly_matchups_df.empty and not teams_df.empty:
            weekly_matchups_df = weekly_matchups_df.merge(
                teams_df[['season_year', 'team_key', 'manager']].drop_duplicates(),
                on=['season_year', 'team_key'],
                how='left'
            )
    except Exception as e:
        logger.warning(f"Could not load weekly matchups from JSON: {e}")
    
    # Fallback: try CSV matchups
    if weekly_matchups_df.empty:
        matchups_df = pd.DataFrame()
        try:
            matchups_path = loader.cleaned_data_dir / "matchups.csv"
            if matchups_path.exists():
                matchups_df = pd.read_csv(matchups_path)
                matchups_df = matchups_df[
                    (matchups_df['season_year'] >= start_year) & 
                    (matchups_df['season_year'] <= end_year)
                ]
                weekly_matchups_df = build_weekly_matchups_table(
                    matchups_df,
                    teams_df if not teams_df.empty else pd.DataFrame(),
                    standings_df if not standings_df.empty else None
                )
        except Exception as e:
            logger.warning(f"Could not load matchups from CSV: {e}")
    
    # Load weekly lineups (placeholder - will be empty if not available)
    weekly_lineups_df = pd.DataFrame()
    try:
        weekly_lineups_df = load_weekly_lineups_from_json(
            loader.league_data_dir,
            teams_df if not teams_df.empty else pd.DataFrame(),
            start_year,
            end_year
        )
    except Exception as e:
        logger.warning(f"Could not load weekly lineups: {e}")
    
    # Build team-week performance analysis (if lineup data available)
    team_week_perf_df = pd.DataFrame()
    manager_season_lineup_stats_df = pd.DataFrame()
    loss_breakdown_df = pd.DataFrame()
    
    if not weekly_lineups_df.empty:
        try:
            team_week_perf_df = build_weekly_lineups_table(
                weekly_lineups_df,
                teams_df if not teams_df.empty else pd.DataFrame(),
                league_meta
            )
            
            manager_season_lineup_stats_df = build_manager_season_lineup_stats(
                team_week_perf_df,
                teams_df if not teams_df.empty else pd.DataFrame()
            )
            
            loss_breakdown_df = classify_losses(
                team_week_perf_df,
                weekly_matchups_df if not weekly_matchups_df.empty else pd.DataFrame()
            )
        except Exception as e:
            logger.warning(f"Weekly lineup analysis failed: {e}")
    
    # Step 14: Schedule luck and points-against analysis (using weekly matchups if available)
    logger.info("Step 14: Analyzing schedule luck and points-against...")
    
    schedule_df = pd.DataFrame()
    expected_wins_df = pd.DataFrame()
    schedule_difficulty_df = pd.DataFrame()
    manager_luck_profile_df = pd.DataFrame()
    championship_luck_df = pd.DataFrame()
    
    if not weekly_matchups_df.empty:
        try:
            
            # Calculate expected wins (will use weekly if available, otherwise season totals)
            expected_wins_df = calculate_expected_wins(
                weekly_matchups_df,
                standings_df=standings_df if not standings_df.empty else None,
                teams_df=teams_df if not teams_df.empty else None,
                matchups_df=matchups_df
            )
            
            # Build schedule analysis
            schedule_df = build_manager_season_schedule(
                weekly_matchups_df,
                standings_df if not standings_df.empty else pd.DataFrame(),
                teams_df=teams_df if not teams_df.empty else None
            )
            
            # Calculate schedule difficulty
            if not weekly_matchups_df.empty:
                schedule_difficulty_df = calculate_schedule_difficulty(weekly_matchups_df)
            else:
                schedule_difficulty_df = pd.DataFrame()
            
            # Build manager luck profiles
            if not schedule_df.empty and not expected_wins_df.empty:
                manager_luck_profile_df = build_manager_luck_profile(
                    schedule_df,
                    expected_wins_df,
                    manager_season_value_df if not manager_season_value_df.empty else None
                )
                
                # Analyze championship luck
                championship_luck_df = analyze_championship_luck(
                    schedule_df,
                    expected_wins_df,
                    standings_df if not standings_df.empty else pd.DataFrame(),
                    teams_df if not teams_df.empty else pd.DataFrame()
                )
            else:
                manager_luck_profile_df = pd.DataFrame()
                championship_luck_df = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Schedule luck analysis failed: {e}")
    
    # Save schedule luck outputs
    if not schedule_df.empty:
        schedule_path = output_path / "manager_season_schedule.csv"
        schedule_df.to_csv(schedule_path, index=False)
        logger.info(f"Saved manager-season schedule to {schedule_path}")
    
    if not expected_wins_df.empty:
        expected_wins_path = output_path / "manager_season_expected_wins.csv"
        expected_wins_df.to_csv(expected_wins_path, index=False)
        logger.info(f"Saved expected wins to {expected_wins_path}")
    
    if not schedule_difficulty_df.empty:
        difficulty_path = output_path / "schedule_difficulty.csv"
        schedule_difficulty_df.to_csv(difficulty_path, index=False)
        logger.info(f"Saved schedule difficulty to {difficulty_path}")
    
    if not manager_luck_profile_df.empty:
        luck_path = output_path / "manager_luck_profile.csv"
        manager_luck_profile_df.to_csv(luck_path, index=False)
        logger.info(f"Saved manager luck profiles to {luck_path}")
    
    if not championship_luck_df.empty:
        champ_luck_path = output_path / "championship_luck_analysis.csv"
        championship_luck_df.to_csv(champ_luck_path, index=False)
        logger.info(f"Saved championship luck analysis to {champ_luck_path}")
    
    # Step 15: Consistency and volatility analysis
    logger.info("Step 15: Analyzing consistency and volatility...")
    
    distribution_df = pd.DataFrame()
    consistency_scores_df = pd.DataFrame()
    archetypes_df = pd.DataFrame()
    season_volatility_df = pd.DataFrame()
    signal_strength_df = pd.DataFrame()
    rolling_consistency_df = pd.DataFrame()
    
    if not manager_season_value_df.empty:
        try:
            distribution_df = calculate_manager_outcome_distributions(manager_season_value_df)
            consistency_scores_df = calculate_consistency_scores(distribution_df)
            archetypes_df = classify_manager_archetypes(distribution_df)
            season_volatility_df = calculate_season_volatility(manager_season_value_df)
            signal_strength_df = calculate_manager_signal_strength(manager_season_value_df)
            rolling_consistency_df = calculate_rolling_consistency(manager_season_value_df)
        except Exception as e:
            logger.warning(f"Consistency analysis failed: {e}")
    
    # Save consistency outputs
    if not distribution_df.empty:
        dist_path = output_path / "manager_outcome_distribution.csv"
        distribution_df.to_csv(dist_path, index=False)
        logger.info(f"Saved manager outcome distributions to {dist_path}")
    
    if not consistency_scores_df.empty:
        cons_path = output_path / "manager_consistency_scores.csv"
        consistency_scores_df.to_csv(cons_path, index=False)
        logger.info(f"Saved consistency scores to {cons_path}")
    
    if not archetypes_df.empty:
        arch_path = output_path / "manager_archetypes.csv"
        archetypes_df.to_csv(arch_path, index=False)
        logger.info(f"Saved manager archetypes to {arch_path}")
    
    if not season_volatility_df.empty:
        vol_path = output_path / "season_volatility.csv"
        season_volatility_df.to_csv(vol_path, index=False)
        logger.info(f"Saved season volatility to {vol_path}")
    
    if not signal_strength_df.empty:
        sig_path = output_path / "manager_signal_strength.csv"
        signal_strength_df.to_csv(sig_path, index=False)
        logger.info(f"Saved signal strength to {sig_path}")
    
    if not rolling_consistency_df.empty:
        roll_path = output_path / "manager_rolling_consistency.csv"
        rolling_consistency_df.to_csv(roll_path, index=False)
        logger.info(f"Saved rolling consistency to {roll_path}")
    
    # Generate plots
    from .plots import (
        plot_price_vs_var_by_position, plot_var_per_dollar_by_manager, 
        plot_champion_vs_field_shares, plot_wins_distribution_by_manager,
        plot_var_distribution_by_manager, plot_mean_vs_std_wins,
        plot_championships_vs_median_wins, plot_wins_vs_expected_wins,
        plot_pa_diff_by_manager, plot_pf_vs_pa_scatter,
        plot_championship_luck_quadrant
    )
    
    plot_price_vs_var(analysis_df, output_path)
    plot_price_vs_var_by_position(analysis_df, output_path)
    
    if not manager_season_value_df.empty:
        plot_var_per_dollar_by_manager(manager_season_value_df, output_path)
        plot_wins_distribution_by_manager(manager_season_value_df, output_path)
        plot_var_distribution_by_manager(manager_season_value_df, output_path)
    
    if not distribution_df.empty:
        plot_mean_vs_std_wins(distribution_df, output_path)
        plot_championships_vs_median_wins(distribution_df, output_path)
    
    if champion_blueprint and not manager_season_value_df.empty:
        plot_champion_vs_field_shares(champion_blueprint, manager_season_value_df, output_path)
    
    # Schedule luck plots
    if not schedule_df.empty and not expected_wins_df.empty:
        plot_wins_vs_expected_wins(schedule_df, expected_wins_df, output_path)
        plot_pa_diff_by_manager(schedule_df, output_path)
        plot_pf_vs_pa_scatter(schedule_df, output_path)
    
    if not championship_luck_df.empty:
        plot_championship_luck_quadrant(championship_luck_df, output_path)
    
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
    
    # Generate insight-first report
    try:
        generate_insight_report(
            manager_season_value_df=manager_season_value_df,
            draft_hit_rates_df=draft_hit_rates_df,
            keeper_surplus_df=keeper_summary,
            champion_blueprint=champion_blueprint,
            trade_impact_df=trade_impact_df if not trade_impact_df.empty else None,
            analysis_df=analysis_df,
            league_meta=league_meta,
            output_dir=output_path,
            start_year=start_year,
            end_year=end_year,
            distribution_df=distribution_df,
            consistency_scores_df=consistency_scores_df,
            archetypes_df=archetypes_df,
            season_volatility_df=season_volatility_df,
            signal_strength_df=signal_strength_df,
            schedule_df=schedule_df,
            expected_wins_df=expected_wins_df,
            manager_luck_profile_df=manager_luck_profile_df,
            championship_luck_df=championship_luck_df,
            weekly_matchups_df=weekly_matchups_df,
            team_week_perf_df=team_week_perf_df,
            manager_season_lineup_stats_df=manager_season_lineup_stats_df,
            loss_breakdown_df=loss_breakdown_df
        )
    except Exception as e:
        logger.warning(f"Failed to generate insight report: {e}")
        # Fall back to old report
        generate_summary_report(
            analysis_df, tier_summary, keeper_summary, league_meta,
            output_path, start_year, end_year,
            lifecycle_df, waiver_pickups_df, trade_impact_df, manager_profiles_df
        )
    
    logger.info(f"Analysis complete! Outputs saved to {output_path}")
    
    # Print console summary
    print_console_summary(manager_season_value_df, analysis_df)
    
    return {
        'analysis_df': analysis_df,
        'tier_summary': tier_summary,
        'keeper_summary': keeper_summary,
        'lifecycle_df': lifecycle_df,
        'waiver_pickups_df': waiver_pickups_df,
        'trade_impact_df': trade_impact_df,
        'manager_profiles_df': manager_profiles_df,
        'player_season_df': player_season_df,
        'manager_season_value_df': manager_season_value_df,
        'draft_hit_rates_df': draft_hit_rates_df,
        'champion_blueprint': champion_blueprint,
        'distribution_df': distribution_df,
        'consistency_scores_df': consistency_scores_df,
        'archetypes_df': archetypes_df,
        'season_volatility_df': season_volatility_df,
        'signal_strength_df': signal_strength_df,
        'rolling_consistency_df': rolling_consistency_df,
        'weekly_matchups_df': weekly_matchups_df,
        'schedule_df': schedule_df,
        'expected_wins_df': expected_wins_df,
        'schedule_difficulty_df': schedule_difficulty_df,
        'manager_luck_profile_df': manager_luck_profile_df,
        'championship_luck_df': championship_luck_df,
        'weekly_matchups_df': weekly_matchups_df,
        'weekly_lineups_df': weekly_lineups_df,
        'team_week_perf_df': team_week_perf_df,
        'manager_season_lineup_stats_df': manager_season_lineup_stats_df,
        'loss_breakdown_df': loss_breakdown_df,
        'league_meta': league_meta
    }


def print_console_summary(manager_season_value_df: pd.DataFrame, analysis_df: pd.DataFrame):
    """Print brief console summary highlighting top managers and inefficiencies."""
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    # Top 5 managers by VAR/$
    if not manager_season_value_df.empty:
        print("\nTop 5 Managers by VAR per Dollar (Career):")
        print("-" * 80)
        manager_careers = manager_season_value_df.groupby('manager').agg({
            'total_VAR': 'sum',
            'total_spend': 'sum',
            'VAR_per_dollar': 'mean'
        }).reset_index()
        manager_careers['VAR_per_dollar'] = manager_careers['total_VAR'] / manager_careers['total_spend']
        manager_careers = manager_careers.sort_values('VAR_per_dollar', ascending=False)
        
        for i, (_, row) in enumerate(manager_careers.head(5).iterrows(), 1):
            print(f"{i}. {row['manager']:20s} ${row['VAR_per_dollar']:.3f} VAR/$  (Total VAR: {row['total_VAR']:.1f}, Spend: ${row['total_spend']:.0f})")
    
    # Top 3 league inefficiencies
    if analysis_df is not None:
        has_var = analysis_df['VAR'].notna() & analysis_df['normalized_price'].notna() & (analysis_df['normalized_price'] > 0)
        if has_var.any():
            df_with_var = analysis_df[has_var].copy()
            df_with_var['VAR_per_dollar'] = df_with_var['VAR'] / df_with_var['normalized_price']
            
            pos_efficiency = df_with_var.groupby('position').agg({
                'VAR_per_dollar': 'mean',
                'dollar_per_VAR': lambda x: (df_with_var.loc[x.index, 'normalized_price'] / df_with_var.loc[x.index, 'VAR']).mean()
            }).reset_index()
            pos_efficiency.columns = ['position', 'avg_VAR_per_dollar', 'avg_dollar_per_VAR']
            
            print("\nTop 3 League Inefficiencies (by $/VAR):")
            print("-" * 80)
            pos_efficiency = pos_efficiency.sort_values('avg_dollar_per_VAR', ascending=False)
            for i, (_, row) in enumerate(pos_efficiency.head(3).iterrows(), 1):
                print(f"{i}. {row['position']:10s} ${row['avg_dollar_per_VAR']:.2f} per VAR  ({row['avg_VAR_per_dollar']:.3f} VAR/$)")
    
    print("\n" + "=" * 80)


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

