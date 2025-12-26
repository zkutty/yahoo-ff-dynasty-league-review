"""Generate insight-first analysis report."""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def generate_insight_report(
    manager_season_value_df: pd.DataFrame,
    draft_hit_rates_df: pd.DataFrame,
    keeper_surplus_df: pd.DataFrame,
    champion_blueprint: Dict,
    trade_impact_df: pd.DataFrame = None,
    analysis_df: pd.DataFrame = None,
    league_meta: Dict = None,
    output_dir: Path = None,
    start_year: int = None,
    end_year: int = None,
    distribution_df: pd.DataFrame = None,
    consistency_scores_df: pd.DataFrame = None,
    archetypes_df: pd.DataFrame = None,
    season_volatility_df: pd.DataFrame = None,
    signal_strength_df: pd.DataFrame = None,
    schedule_df: pd.DataFrame = None,
    expected_wins_df: pd.DataFrame = None,
    manager_luck_profile_df: pd.DataFrame = None,
    championship_luck_df: pd.DataFrame = None,
    weekly_matchups_df: pd.DataFrame = None,
    team_week_perf_df: pd.DataFrame = None,
    manager_season_lineup_stats_df: pd.DataFrame = None,
    loss_breakdown_df: pd.DataFrame = None
) -> str:
    """Generate an insight-first markdown report.
    
    Structure:
    A) League inefficiencies: $/VAR by position, pricing trends vs value
    B) Manager efficiency leaderboard: VAR/$, total VAR, shares
    C) Draft skill: hit rates, bust rates, top-pick VAR
    D) Keeper skill: surplus vs realized VAR
    E) Trade skill: net VAR impact
    F) Champion blueprint: what winners did differently
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        draft_hit_rates_df: Draft hit rates DataFrame
        keeper_surplus_df: Keeper surplus summary DataFrame
        champion_blueprint: Champion blueprint dictionary
        trade_impact_df: Optional trade impact DataFrame
        analysis_df: Optional analysis DataFrame for league-wide metrics
        league_meta: Optional league metadata
        output_dir: Output directory path
        start_year: Start year for analysis
        end_year: End year for analysis
        
    Returns:
        Markdown report string
    """
    lines = []
    lines.append("# Fantasy Football League Review: Outcome-Linked Analysis")
    lines.append("")
    lines.append(f"**Analysis Period:** {start_year}-{end_year}")
    lines.append("")
    lines.append("## Assumptions & Methodology")
    lines.append("")
    lines.append("- **Replacement Baseline:** Points of player ranked at `num_teams * starters_per_position` for each position")
    lines.append("- **VAR Calculation:** Player Points - Replacement Baseline Points")
    lines.append("- **Price Normalization:** Prices normalized to baseline season accounting for keeper inflation")
    lines.append("- **Consistency Score:** Normalized score = `(1 / (1 + std)) * median`, scaled to 0-100")
    lines.append("- **Archetype Definitions:**")
    lines.append("  - CONSISTENT_CONTENDER: median_wins ≥ league_median AND std_wins ≤ league_median_std")
    lines.append("  - BOOM_BUST: std_wins ≥ league_75th_percentile_std")
    lines.append("  - LOTTERY: championships ≥ 1 AND median_wins < league_median")
    lines.append("  - STEADY_BUT_UNLUCKY: median_wins ≥ league_60th_percentile AND championships = 0")
    lines.append("- **Gini Coefficient:** Measure of VAR concentration (0 = perfectly equal, 1 = all value in one team)")
    lines.append("- **Expected Wins (All-Play Model):** For each week, rank all teams by points. Team earns (num_teams - rank) / (num_teams - 1) expected wins. Sum across weeks.")
    lines.append("- **Win Luck:** actual_wins - expected_wins. Positive = lucky, negative = unlucky")
    lines.append("- **PA_diff:** points_against - league_avg_PA. Positive = faced tougher schedule (more points allowed)")
    lines.append("- **Schedule Difficulty:** Normalized opponent strength. Positive = harder schedule")
    lines.append("- **Lineup Efficiency:** actual_points / optimal_points (proportion of maximum points achieved)")
    lines.append("- **Bench Waste Rate:** total_bench_points / total_optimal_points (wasted potential)")
    lines.append("- **Loss Types:** UNLUCKY_LOSS (high score but lost), LINEUP_LOSS (inefficient lineup), DEPTH_LOSS (insufficient roster), SKILL_LOSS (otherwise)")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # A) League Inefficiencies
    lines.append("## A. League Inefficiencies")
    lines.append("")
    
    if analysis_df is not None:
        # $/VAR by position
        has_var = analysis_df['VAR'].notna() & analysis_df['normalized_price'].notna() & (analysis_df['normalized_price'] > 0)
        if has_var.any():
            df_with_var = analysis_df[has_var].copy()
            df_with_var['dollar_per_VAR'] = df_with_var['normalized_price'] / df_with_var['VAR']
            
            pos_efficiency = df_with_var.groupby('position').agg({
                'dollar_per_VAR': 'mean',
                'VAR_per_dollar': 'mean',
                'VAR': 'mean',
                'normalized_price': 'mean',
                'player_id': 'count'
            }).reset_index()
            pos_efficiency.columns = ['position', 'avg_dollar_per_VAR', 'avg_VAR_per_dollar', 'avg_VAR', 'avg_price', 'count']
            
            lines.append("### Spending Efficiency by Position")
            lines.append("")
            lines.append("| Position | Avg $/VAR | Avg VAR/$ | Avg VAR | Avg Price | Players |")
            lines.append("|----------|-----------|-----------|---------|-----------|---------|")
            for _, row in pos_efficiency.iterrows():
                lines.append(f"| {row['position']} | ${row['avg_dollar_per_VAR']:.2f} | {row['avg_VAR_per_dollar']:.3f} | {row['avg_VAR']:.1f} | ${row['avg_price']:.1f} | {int(row['count'])} |")
            lines.append("")
            
            # Best and worst positions for value
            best_pos = pos_efficiency.loc[pos_efficiency['avg_VAR_per_dollar'].idxmax()]
            worst_pos = pos_efficiency.loc[pos_efficiency['avg_VAR_per_dollar'].idxmin()]
            lines.append(f"**Best Value Position:** {best_pos['position']} (${best_pos['avg_VAR_per_dollar']:.3f} VAR per dollar)")
            lines.append("")
            lines.append(f"**Worst Value Position:** {worst_pos['position']} (${worst_pos['avg_VAR_per_dollar']:.3f} VAR per dollar)")
            lines.append("")
    
    # B) Manager Efficiency Leaderboard
    lines.append("## B. Manager Efficiency Leaderboard")
    lines.append("")
    
    if not manager_season_value_df.empty:
        # Career aggregates
        manager_careers = manager_season_value_df.groupby('manager').agg({
            'total_VAR': 'sum',
            'total_spend': 'sum',
            'VAR_per_dollar': 'mean',
            'wins': 'sum',
            'champion_flag': 'sum',
            'season_year': 'nunique'
        }).reset_index()
        manager_careers.columns = ['manager', 'total_VAR', 'total_spend', 'avg_VAR_per_dollar', 'total_wins', 'championships', 'seasons']
        manager_careers['VAR_per_dollar'] = manager_careers['total_VAR'] / manager_careers['total_spend']
        manager_careers = manager_careers.sort_values('VAR_per_dollar', ascending=False)
        
        lines.append("### Top Managers by VAR per Dollar (Career)")
        lines.append("")
        lines.append("| Rank | Manager | VAR/$ | Total VAR | Total Spend | Wins | Championships | Seasons |")
        lines.append("|------|---------|-------|-----------|-------------|------|---------------|---------|")
        for i, (_, row) in enumerate(manager_careers.head(10).iterrows(), 1):
            lines.append(f"| {i} | {row['manager']} | {row['VAR_per_dollar']:.3f} | {row['total_VAR']:.1f} | ${row['total_spend']:.0f} | {int(row['total_wins'])} | {int(row['championships'])} | {int(row['seasons'])} |")
        lines.append("")
        
        # VAR sources breakdown
        avg_sources = manager_season_value_df.groupby('manager').agg({
            'pct_VAR_from_draft': 'mean',
            'pct_VAR_from_keeper': 'mean',
            'pct_VAR_from_waiver': 'mean',
            'pct_VAR_from_trade': 'mean'
        }).reset_index()
        
        lines.append("### Manager VAR Sources (Average % by Source)")
        lines.append("")
        lines.append("| Manager | Draft % | Keeper % | Waiver % | Trade % |")
        lines.append("|---------|---------|----------|----------|---------|")
        for _, row in avg_sources.head(10).iterrows():
            lines.append(f"| {row['manager']} | {row['pct_VAR_from_draft']:.1f}% | {row['pct_VAR_from_keeper']:.1f}% | {row['pct_VAR_from_waiver']:.1f}% | {row['pct_VAR_from_trade']:.1f}% |")
        lines.append("")
    
    # C) Draft Skill
    lines.append("## C. Draft Skill Analysis")
    lines.append("")
    
    if not draft_hit_rates_df.empty:
        # Manager career hit rates
        manager_hits = draft_hit_rates_df[
            draft_hit_rates_df['scope'] == 'manager_career'
        ].sort_values('hit_rate', ascending=False)
        
        if not manager_hits.empty:
            lines.append("### Hit Rates (Career)")
            lines.append("")
            lines.append("| Manager | Hit Rate | Bust Rate | Top 3 Pick VAR | Avg VAR |")
            lines.append("|---------|----------|-----------|----------------|---------|")
            for _, row in manager_hits.head(10).iterrows():
                top3 = f"{row['top3_pick_VAR']:.1f}" if pd.notna(row['top3_pick_VAR']) else "N/A"
                avg_var = f"{row['avg_VAR']:.1f}" if pd.notna(row['avg_VAR']) else "N/A"
                lines.append(f"| {row['manager']} | {row['hit_rate']:.1f}% | {row['bust_rate']:.1f}% | {top3} | {avg_var} |")
            lines.append("")
        
        # League-wide by tier
        tier_hits = draft_hit_rates_df[
            (draft_hit_rates_df['scope'] == 'league') &
            (draft_hit_rates_df['expected_tier'].notna())
        ].sort_values('expected_tier')
        
        if not tier_hits.empty:
            lines.append("### Hit Rates by Draft Tier (League-Wide)")
            lines.append("")
            lines.append("| Tier | Hit Rate | Bust Rate | Avg VAR | Players |")
            lines.append("|------|----------|-----------|---------|---------|")
            for _, row in tier_hits.iterrows():
                lines.append(f"| Tier {int(row['expected_tier'])} | {row['hit_rate']:.1f}% | {row['bust_rate']:.1f}% | {row['avg_VAR']:.1f} | {int(row['count'])} |")
            lines.append("")
    
    # D) Keeper Skill
    lines.append("## D. Keeper Skill")
    lines.append("")
    
    if not keeper_surplus_df.empty:
        lines.append("### Keeper Surplus Analysis")
        lines.append("")
        lines.append("| Position | Avg Surplus | Avg VAR | Surplus-VAR Correlation |")
        lines.append("|----------|-------------|---------|------------------------|")
        for _, row in keeper_surplus_df.iterrows():
            corr = f"{row.get('surplus_VAR_correlation', np.nan):.3f}" if 'surplus_VAR_correlation' in row and pd.notna(row.get('surplus_VAR_correlation')) else "N/A"
            lines.append(f"| {row['position']} | ${row.get('avg_surplus', 0):.2f} | {row.get('avg_VAR', 0):.1f} | {corr} |")
        lines.append("")
    
    # E) Trade Skill
    if trade_impact_df is not None and not trade_impact_df.empty:
        lines.append("## E. Trade Impact Analysis")
        lines.append("")
        
        # Aggregate by manager if we can link trades to managers
        lines.append(f"**Total Trades Analyzed:** {len(trade_impact_df)}")
        lines.append("")
        
        wins = (trade_impact_df['team_a_result'] == 'WIN').sum() + (trade_impact_df['team_b_result'] == 'WIN').sum()
        losses = (trade_impact_df['team_a_result'] == 'LOSS').sum() + (trade_impact_df['team_b_result'] == 'LOSS').sum()
        total_sides = len(trade_impact_df) * 2
        win_pct = (wins / total_sides * 100) if total_sides > 0 else 0
        
        lines.append(f"**Trade Win Rate:** {win_pct:.1f}% ({wins} wins, {losses} losses)")
        lines.append("")
    
    # F) Champion Blueprint
    lines.append("## F. Champion Blueprint")
    lines.append("")
    
    if champion_blueprint and 'blueprint' in champion_blueprint:
        blueprint = champion_blueprint['blueprint']
        comparison = champion_blueprint.get('comparison', pd.DataFrame())
        top_diff = champion_blueprint.get('top_differentiators', pd.DataFrame())
        
        lines.append("### What Champions Did Differently")
        lines.append("")
        
        if not top_diff.empty:
            lines.append("**Top 3 Differentiators:**")
            lines.append("")
            for i, (_, row) in enumerate(top_diff.iterrows(), 1):
                pct = row['pct_difference']
                effect = row['effect_size_cohens_d']
                lines.append(f"{i}. **{row['metric']}**: Champions {pct:+.1f}% different (effect size: {effect:.2f})")
            lines.append("")
        
        lines.append("### Champion Seasons")
        lines.append("")
        lines.append("| Season | Manager | VAR/$ | Total VAR | Draft % | Keeper % | Waiver % | Trade % |")
        lines.append("|--------|---------|-------|-----------|---------|----------|----------|---------|")
        for _, row in blueprint.iterrows():
            lines.append(f"| {int(row['season_year'])} | {row['manager']} | {row['VAR_per_dollar']:.3f} | {row['total_VAR']:.1f} | {row['pct_VAR_from_draft']:.1f}% | {row['pct_VAR_from_keeper']:.1f}% | {row['pct_VAR_from_waiver']:.1f}% | {row['pct_VAR_from_trade']:.1f}% |")
        lines.append("")
        
        if not comparison.empty:
            lines.append("### Champions vs Non-Champions Comparison")
            lines.append("")
            lines.append("| Metric | Champion Mean | Non-Champion Mean | Difference | Effect Size |")
            lines.append("|--------|---------------|-------------------|------------|-------------|")
            for _, row in comparison.head(10).iterrows():
                lines.append(f"| {row['metric']} | {row['champion_mean']:.2f} | {row['non_champion_mean']:.2f} | {row['difference']:+.2f} | {row['effect_size_cohens_d']:.2f} |")
            lines.append("")
    
    # Summary
    # Add plot references
    plots_dir = output_dir / "plots" if output_dir else None
    if plots_dir and plots_dir.exists():
        lines.append("---")
        lines.append("")
        lines.append("## Visualizations")
        lines.append("")
        plot_files = ['price_vs_var_by_position.png', 'var_per_dollar_by_manager.png', 'champions_vs_field_shares.png']
        for plot_file in plot_files:
            if (plots_dir / plot_file).exists():
                lines.append(f"![{plot_file}](plots/{plot_file})")
                lines.append("")
    
    # G) Consistency vs Volatility
    lines.append("## G. Consistency vs Volatility")
    lines.append("")
    
    if distribution_df is not None and not distribution_df.empty:
        # Most and least consistent
        if consistency_scores_df is not None and not consistency_scores_df.empty:
            most_consistent = consistency_scores_df.iloc[0]
            least_consistent = consistency_scores_df.iloc[-1]
            
            lines.append("### Most Consistent Managers")
            lines.append("")
            lines.append(f"**Most Consistent (Wins):** {most_consistent['manager']} (Score: {most_consistent['consistency_score_wins']:.1f})")
            lines.append(f"- Median Wins: {most_consistent['median_wins']:.1f}")
            lines.append(f"- Std Wins: {most_consistent['std_wins']:.2f}")
            lines.append("")
            
            lines.append(f"**Most Volatile (Wins):** {least_consistent['manager']} (Score: {least_consistent['consistency_score_wins']:.1f})")
            lines.append(f"- Median Wins: {least_consistent['median_wins']:.1f}")
            lines.append(f"- Std Wins: {least_consistent['std_wins']:.2f}")
            lines.append("")
        
        # Are champions more consistent or volatile?
        champions = distribution_df[distribution_df['championships'] > 0]
        non_champions = distribution_df[distribution_df['championships'] == 0]
        
        if not champions.empty and not non_champions.empty:
            champ_mean_std = champions['std_wins'].mean()
            non_champ_mean_std = non_champions['std_wins'].mean()
            
            lines.append("### Champions vs Non-Champions: Consistency")
            lines.append("")
            lines.append(f"- **Champions Avg Std Wins:** {champ_mean_std:.2f}")
            lines.append(f"- **Non-Champions Avg Std Wins:** {non_champ_mean_std:.2f}")
            if champ_mean_std < non_champ_mean_std:
                lines.append(f"- **Insight:** Champions are more consistent (lower std)")
            else:
                lines.append(f"- **Insight:** Champions are more volatile (higher std)")
            lines.append("")
        
        # Consistency score rankings
        if consistency_scores_df is not None and not consistency_scores_df.empty:
            lines.append("### Consistency Score Rankings (Top 5)")
            lines.append("")
            lines.append("| Rank | Manager | Consistency Score (Wins) | Median Wins | Std Wins |")
            lines.append("|------|---------|-------------------------|-------------|----------|")
            for i, (_, row) in enumerate(consistency_scores_df.head(5).iterrows(), 1):
                lines.append(f"| {i} | {row['manager']} | {row['consistency_score_wins']:.1f} | {row['median_wins']:.1f} | {row['std_wins']:.2f} |")
            lines.append("")
    
    # Archetype distribution
    if archetypes_df is not None and not archetypes_df.empty:
        lines.append("### Manager Archetypes")
        lines.append("")
        arch_counts = archetypes_df['archetype'].value_counts()
        for arch_type, count in arch_counts.items():
            lines.append(f"- **{arch_type}**: {count} managers")
        lines.append("")
        
        # Show examples of each archetype
        for arch_type in ['CONSISTENT_CONTENDER', 'BOOM_BUST', 'LOTTERY', 'STEADY_BUT_UNLUCKY']:
            examples = archetypes_df[archetypes_df['archetype'] == arch_type]
            if not examples.empty:
                lines.append(f"**{arch_type} Examples:**")
                for _, row in examples.head(3).iterrows():
                    lines.append(f"- {row['manager']}: {row['median_wins']:.1f} median wins, {row['std_wins']:.2f} std, {int(row['championships'])} championships")
                lines.append("")
    
    # Is high variance rewarded?
    if distribution_df is not None and not distribution_df.empty:
        # Correlate std_wins with championships
        corr_std_champs = distribution_df['std_wins'].corr(distribution_df['championships'])
        lines.append("### Is High Variance Rewarded?")
        lines.append("")
        lines.append(f"- **Correlation (Std Wins vs Championships):** {corr_std_champs:.3f}")
        if corr_std_champs > 0.2:
            lines.append("- **Insight:** Higher variance is positively correlated with championships")
        elif corr_std_champs < -0.2:
            lines.append("- **Insight:** Consistency is more rewarded than variance")
        else:
            lines.append("- **Insight:** No strong relationship between variance and championships")
        lines.append("")
    
    # H) Schedule Luck & Points Against
    lines.append("## H. Schedule Luck & Points Against")
    lines.append("")
    
    if schedule_df is not None and not schedule_df.empty:
        # Most/least unlucky managers
        if expected_wins_df is not None and not expected_wins_df.empty:
            merged = schedule_df.merge(
                expected_wins_df,
                on=['season_year', 'manager'],
                how='left'
            )
            merged['win_luck'] = merged['wins'] - merged['expected_wins'].fillna(merged['wins'])
            
            if manager_luck_profile_df is not None and not manager_luck_profile_df.empty:
                lines.append("### Most Unlucky Managers (Career)")
                lines.append("")
                unlucky_sorted = manager_luck_profile_df.sort_values('mean_win_luck').head(5)
                lines.append("| Manager | Avg Win Luck | Unlucky Seasons | Avg PA_diff |")
                lines.append("|---------|--------------|-----------------|-------------|")
                for _, row in unlucky_sorted.iterrows():
                    lines.append(f"| {row['manager']} | {row['mean_win_luck']:.2f} | {int(row['total_unlucky_seasons'])} ({row['pct_seasons_unlucky']:.1f}%) | {row['mean_PA_diff']:.1f} |")
                lines.append("")
                
                lines.append("### Most Lucky Managers (Career)")
                lines.append("")
                lucky_sorted = manager_luck_profile_df.sort_values('mean_win_luck', ascending=False).head(5)
                lines.append("| Manager | Avg Win Luck | Lucky Seasons | Avg PA_diff |")
                lines.append("|---------|--------------|---------------|-------------|")
                for _, row in lucky_sorted.iterrows():
                    lines.append(f"| {row['manager']} | {row['mean_win_luck']:.2f} | {int(row['total_lucky_seasons'])} ({row['pct_seasons_lucky']:.1f}%) | {row['mean_PA_diff']:.1f} |")
                lines.append("")
            
            # PA_diff analysis
            lines.append("### Schedule Difficulty (Points Against)")
            lines.append("")
            pa_analysis = schedule_df.groupby('manager').agg({
                'PA_diff': 'mean',
                'avg_points_against': 'mean'
            }).reset_index()
            pa_analysis = pa_analysis.sort_values('PA_diff', ascending=False)
            lines.append("| Manager | Avg PA_diff | Avg Points Against |")
            lines.append("|---------|-------------|-------------------|")
            for _, row in pa_analysis.head(5).iterrows():
                lines.append(f"| {row['manager']} | {row['PA_diff']:+.1f} | {row['avg_points_against']:.1f} |")
            lines.append("")
            lines.append("*Positive PA_diff = faced tougher schedule (opponents scored more)*")
            lines.append("")
    
    # Championship luck analysis
    if championship_luck_df is not None and not championship_luck_df.empty:
        lines.append("### Championship Luck Analysis")
        lines.append("")
        lines.append("| Season | Manager | Wins Over Expected | PA_diff | PF Percentile | Type |")
        lines.append("|--------|---------|-------------------|---------|---------------|------|")
        for _, row in championship_luck_df.iterrows():
            wo_exp = f"{row['wins_over_expected']:.2f}" if pd.notna(row['wins_over_expected']) else "N/A"
            pa = f"{row['PA_diff']:+.1f}" if pd.notna(row['PA_diff']) else "N/A"
            pf_pct = f"{row['points_for_percentile']:.1f}%" if pd.notna(row['points_for_percentile']) else "N/A"
            champ_type = row.get('championship_type', 'UNKNOWN')
            lines.append(f"| {int(row['season_year'])} | {row['manager']} | {wo_exp} | {pa} | {pf_pct} | {champ_type} |")
        lines.append("")
        
        # Summary stats
        lucky_champs = championship_luck_df[championship_luck_df['championship_type'] == 'LUCKY']
        dominant_champs = championship_luck_df[championship_luck_df['championship_type'] == 'DOMINANT']
        balanced_champs = championship_luck_df[championship_luck_df['championship_type'] == 'BALANCED']
        
        lines.append(f"**Championship Breakdown:**")
        lines.append(f"- Dominant: {len(dominant_champs)} ({len(dominant_champs)/len(championship_luck_df)*100:.1f}%)")
        lines.append(f"- Balanced: {len(balanced_champs)} ({len(balanced_champs)/len(championship_luck_df)*100:.1f}%)")
        lines.append(f"- Lucky: {len(lucky_champs)} ({len(lucky_champs)/len(championship_luck_df)*100:.1f}%)")
        lines.append("")
        
        # Is this league more luck-driven?
        if not merged.empty:
            overall_mean_abs_luck = merged['win_luck'].abs().mean()
            lines.append("### Is This League More Luck-Driven?")
            lines.append("")
            lines.append(f"- **Mean Absolute Win Luck:** {overall_mean_abs_luck:.2f} wins")
            lines.append(f"- **Interpretation:** Average manager deviates {overall_mean_abs_luck:.2f} wins from expected per season")
            if overall_mean_abs_luck > 1.5:
                lines.append("- **Insight:** High luck component - schedule significantly impacts outcomes")
            elif overall_mean_abs_luck < 1.0:
                lines.append("- **Insight:** Low luck component - outcomes closely match performance")
            else:
                lines.append("- **Insight:** Moderate luck component - schedule affects outcomes but skill still matters")
            lines.append("")
    
    # I) Lineup Skill, Bench Waste & True Luck
    lines.append("## I. Lineup Skill, Bench Waste & True Luck")
    lines.append("")
    
    if manager_season_lineup_stats_df is not None and not manager_season_lineup_stats_df.empty and len(manager_season_lineup_stats_df) > 0:
        # Who leaves the most points on the bench?
        lines.append("### Bench Waste Leaders")
        lines.append("")
        bench_waste = manager_season_lineup_stats_df.sort_values('avg_points_left_on_bench', ascending=False)
        lines.append("| Manager | Avg Bench Points | Bench Waste Rate | Avg Efficiency |")
        lines.append("|---------|------------------|------------------|----------------|")
        for _, row in bench_waste.head(5).iterrows():
            waste_rate = f"{row['bench_waste_rate']*100:.1f}%" if pd.notna(row['bench_waste_rate']) else "N/A"
            efficiency = f"{row['avg_lineup_efficiency']:.3f}" if pd.notna(row['avg_lineup_efficiency']) else "N/A"
            bench_pts = f"{row['avg_points_left_on_bench']:.1f}" if pd.notna(row['avg_points_left_on_bench']) else "N/A"
            lines.append(f"| {row['manager']} | {bench_pts} | {waste_rate} | {efficiency} |")
        lines.append("")
        
        # Most efficient lineups
        lines.append("### Most Efficient Lineup Managers")
        lines.append("")
        efficient = manager_season_lineup_stats_df.sort_values('avg_lineup_efficiency', ascending=False)
        lines.append("| Manager | Avg Efficiency | % Weeks >= 95% | Median Efficiency |")
        lines.append("|---------|----------------|----------------|-------------------|")
        for _, row in efficient.head(5).iterrows():
            avg_eff = f"{row['avg_lineup_efficiency']:.3f}" if pd.notna(row['avg_lineup_efficiency']) else "N/A"
            pct_high = f"{row['pct_weeks_high_efficiency']:.1f}%" if pd.notna(row['pct_weeks_high_efficiency']) else "N/A"
            median_eff = f"{row['median_lineup_efficiency']:.3f}" if pd.notna(row['median_lineup_efficiency']) else "N/A"
            lines.append(f"| {row['manager']} | {avg_eff} | {pct_high} | {median_eff} |")
        lines.append("")
        
        # Do champions have higher lineup efficiency?
        if manager_season_value_df is not None and not manager_season_value_df.empty:
            champ_managers = set(manager_season_value_df[manager_season_value_df['champion_flag'] == True]['manager'].unique())
            champ_lineup = manager_season_lineup_stats_df[manager_season_lineup_stats_df['manager'].isin(champ_managers)]
            non_champ_lineup = manager_season_lineup_stats_df[~manager_season_lineup_stats_df['manager'].isin(champ_managers)]
            
            if not champ_lineup.empty and not non_champ_lineup.empty:
                champ_avg_eff = champ_lineup['avg_lineup_efficiency'].mean()
                non_champ_avg_eff = non_champ_lineup['avg_lineup_efficiency'].mean()
                
                lines.append("### Do Champions Have Higher Lineup Efficiency?")
                lines.append("")
                lines.append(f"- **Champions Avg Efficiency:** {champ_avg_eff:.3f}")
                lines.append(f"- **Non-Champions Avg Efficiency:** {non_champ_avg_eff:.3f}")
                lines.append(f"- **Difference:** {champ_avg_eff - non_champ_avg_eff:+.3f}")
                if champ_avg_eff > non_champ_avg_eff:
                    lines.append("- **Insight:** Champions set better lineups on average")
                else:
                    lines.append("- **Insight:** Lineup efficiency is not a key differentiator for champions")
                lines.append("")
    
    # Loss classification
    if loss_breakdown_df is not None and not loss_breakdown_df.empty and len(loss_breakdown_df) > 0:
        lines.append("### Loss Classification")
        lines.append("")
        loss_counts = loss_breakdown_df.groupby(['manager', 'loss_type']).size().reset_index(name='count')
        loss_pcts = loss_breakdown_df.groupby('loss_type').size() / len(loss_breakdown_df) * 100
        
        lines.append("**Loss Type Distribution (League-Wide):**")
        for loss_type, pct in loss_pcts.items():
            lines.append(f"- {loss_type}: {pct:.1f}%")
        lines.append("")
        
        # Managers with most unlucky losses
        unlucky_losses = loss_breakdown_df[loss_breakdown_df['loss_type'] == 'UNLUCKY_LOSS']
        if not unlucky_losses.empty:
            manager_unlucky = unlucky_losses.groupby('manager').size().sort_values(ascending=False)
            lines.append("**Most Unlucky Losses:**")
            for manager, count in manager_unlucky.head(5).items():
                lines.append(f"- {manager}: {count} unlucky losses")
            lines.append("")
    else:
        lines.append("*Weekly lineup analysis requires weekly roster snapshots which are not currently available in the data.*")
        lines.append("*To enable this analysis, weekly roster data must be fetched from the Yahoo API or derived from transactions.*")
        lines.append("")
    
    # Signal strength insights
    if signal_strength_df is not None and not signal_strength_df.empty:
        lines.append("### Value-to-Wins Conversion")
        lines.append("")
        lines.append("Managers with strongest correlation between VAR and wins:")
        lines.append("")
        sig_sorted = signal_strength_df.sort_values('corr_total_VAR_wins', ascending=False)
        lines.append("| Manager | VAR→Wins Corr | Draft VAR→Wins | Keeper VAR→Wins |")
        lines.append("|---------|---------------|----------------|-----------------|")
        for _, row in sig_sorted.head(5).iterrows():
            draft_corr = f"{row['corr_draft_VAR_wins']:.3f}" if pd.notna(row['corr_draft_VAR_wins']) else "N/A"
            keeper_corr = f"{row['corr_keeper_VAR_wins']:.3f}" if pd.notna(row['corr_keeper_VAR_wins']) else "N/A"
            total_corr = f"{row['corr_total_VAR_wins']:.3f}" if pd.notna(row['corr_total_VAR_wins']) else "N/A"
            lines.append(f"| {row['manager']} | {total_corr} | {draft_corr} | {keeper_corr} |")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Key Takeaways")
    lines.append("")
    
    takeaways = []
    
    if not manager_season_value_df.empty:
        best_manager = manager_season_value_df.groupby('manager')['VAR_per_dollar'].mean().idxmax()
        best_var_per_dollar = manager_season_value_df.groupby('manager')['VAR_per_dollar'].mean().max()
        takeaways.append(f"**Most Efficient Manager:** {best_manager} (${best_var_per_dollar:.3f} VAR per dollar)")
    
    if champion_blueprint and 'top_differentiators' in champion_blueprint:
        top = champion_blueprint['top_differentiators']
        if not top.empty:
            top_metric = top.iloc[0]['metric']
            takeaways.append(f"**Biggest Champion Differentiator:** {top_metric}")
    
    if consistency_scores_df is not None and not consistency_scores_df.empty:
        most_consistent = consistency_scores_df.iloc[0]['manager']
        takeaways.append(f"**Most Consistent Manager:** {most_consistent}")
    
    if distribution_df is not None and not distribution_df.empty:
        most_champs = distribution_df.loc[distribution_df['championships'].idxmax()]
        takeaways.append(f"**Most Championships:** {most_champs['manager']} ({int(most_champs['championships'])})")
    
    for takeaway in takeaways:
        lines.append(f"- {takeaway}")
    
    lines.append("")
    
    report_text = '\n'.join(lines)
    
    if output_dir:
        output_path = output_dir / "league_review_v2.md"
        with open(output_path, 'w') as f:
            f.write(report_text)
        logger.info(f"Saved insight report to {output_path}")
    
    return report_text

