"""Generate a human-readable draft analysis summary."""
import pandas as pd
import os


def generate_draft_summary():
    """Generate a comprehensive draft analysis summary report."""
    
    data_dir = "data/cleaned_data"
    
    # Load all draft analysis files
    try:
        position_spending = pd.read_csv(f"{data_dir}/draft_position_spending.csv")
        strategies = pd.read_csv(f"{data_dir}/draft_manager_draft_strategies.csv")
        draft_picks = pd.read_csv(f"{data_dir}/draft_picks.csv")
    except FileNotFoundError as e:
        print(f"Error loading data files: {e}")
        return
    
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("FANTASY FOOTBALL DRAFT ANALYSIS SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    
    # Overall Statistics
    summary_lines.append("OVERALL DRAFT STATISTICS")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Total Draft Picks Analyzed: {len(draft_picks):,}")
    summary_lines.append(f"Seasons Covered: {draft_picks['season_year'].nunique()}")
    summary_lines.append(f"Total Managers: {strategies['manager'].nunique()}")
    summary_lines.append(f"Average Draft Budget per Season: ${strategies['avg_spending_per_season'].mean():.0f}")
    summary_lines.append("")
    
    # Position Spending Leaders
    summary_lines.append("POSITION SPENDING LEADERS")
    summary_lines.append("-" * 80)
    summary_lines.append("Managers who spend the most on each position:\n")
    
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_data = position_spending[position_spending['position'] == position].nlargest(3, 'total_spent_all_years')
        if not pos_data.empty:
            summary_lines.append(f"{position}:")
            for idx, row in pos_data.iterrows():
                summary_lines.append(f"  {row['manager']:20} ${row['total_spent_all_years']:>6.0f} ({row['pct_of_total_spending']:.1f}% of total spending)")
            summary_lines.append("")
    
    # Draft Strategies
    summary_lines.append("DRAFT STRATEGIES BY MANAGER")
    summary_lines.append("-" * 80)
    summary_lines.append("Key insights about each manager's draft approach:\n")
    
    for idx, row in strategies.iterrows():
        manager = row['manager']
        summary_lines.append(f"{manager}:")
        summary_lines.append(f"  Total Spending: ${row['total_spent_all_time']:,.0f} over {row['total_seasons']} seasons")
        summary_lines.append(f"  Average per Season: ${row['avg_spending_per_season']:.0f}")
        summary_lines.append(f"  Top Position: {row['top_position_spent']} ({row.get('top_position_pct', 0):.1f}% of spending)")
        summary_lines.append(f"  Early Round Focus: {row['early_round_spending_pct']:.1f}% spent in rounds 1-5")
        summary_lines.append(f"  Most Expensive Pick: {row['most_expensive_pick_player']} (${row['most_expensive_pick_cost']}, {row['most_expensive_pick_position']})")
        if 'qb_spending_pct' in row:
            summary_lines.append(f"  Position Breakdown: QB {row.get('qb_spending_pct', 0):.1f}% | RB {row.get('rb_spending_pct', 0):.1f}% | WR {row.get('wr_spending_pct', 0):.1f}% | TE {row.get('te_spending_pct', 0):.1f}%")
        summary_lines.append("")
    
    # Year-over-Year Trends
    try:
        yoy_trends = pd.read_csv(f"{data_dir}/draft_year_over_year_trends.csv")
        summary_lines.append("YEAR-OVER-YEAR POSITION PRICING TRENDS")
        summary_lines.append("-" * 80)
        
        # Filter out snake draft years (years with $0 average prices)
        # Only analyze auction draft years
        yoy_trends_auction = yoy_trends[yoy_trends['avg_price'] > 0].copy()
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_trends = yoy_trends_auction[yoy_trends_auction['position'] == position].sort_values('season_year')
            if not pos_trends.empty and len(pos_trends) > 1:
                first_year = pos_trends.iloc[0]
                last_year = pos_trends.iloc[-1]
                change = last_year['avg_price'] - first_year['avg_price']
                pct_change = (change / first_year['avg_price'] * 100) if first_year['avg_price'] > 0 else 0
                
                summary_lines.append(f"{position} Average Price: ${first_year['avg_price']:.1f} ({int(first_year['season_year'])}) → ${last_year['avg_price']:.1f} ({int(last_year['season_year'])})")
                summary_lines.append(f"  Change: ${change:+.1f} ({pct_change:+.1f}%)")
                
                # Show sample years in between if there are enough years
                if len(pos_trends) > 4:
                    sample_indices = [len(pos_trends)//4, len(pos_trends)//2, 3*len(pos_trends)//4]
                    sample_years = [pos_trends.iloc[i] for i in sample_indices if i < len(pos_trends) and i != 0 and i != len(pos_trends)-1]
                    if sample_years:
                        sample_text = ", ".join([f"{int(row['season_year'])}: ${row['avg_price']:.1f}" for row in sample_years])
                        summary_lines.append(f"  Sample years: {sample_text}")
                
                summary_lines.append("")
    except FileNotFoundError:
        pass
    
    # Write summary to file
    os.makedirs("data/insights", exist_ok=True)
    summary_text = "\n".join(summary_lines)
    
    with open("data/insights/draft_analysis_summary.txt", "w") as f:
        f.write(summary_text)
    
    print(summary_text)
    print(f"\nSummary saved to: data/insights/draft_analysis_summary.txt")


if __name__ == "__main__":
    generate_draft_summary()

