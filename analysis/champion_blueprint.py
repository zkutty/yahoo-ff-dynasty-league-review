"""Champion blueprint analysis - what winners did differently."""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def build_champion_blueprint(
    manager_season_value_df: pd.DataFrame,
    draft_hit_rates_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Build champion blueprint analysis.
    
    For each champion season:
    - total_VAR, VAR_per_$, draft_VAR share, keeper share, trade share, waiver share
    - hit_rate, bust_rate
    
    Compare champions vs non-champions:
    - mean differences + simple effect sizes
    - identify 2-3 strongest differentiators
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        draft_hit_rates_df: Optional draft hit rates DataFrame
        
    Returns:
        DataFrame with champion analysis and comparisons
    """
    df = manager_season_value_df.copy()
    
    # Separate champions and non-champions
    champions = df[df['champion_flag'] == True].copy()
    non_champions = df[df['champion_flag'] == False].copy()
    
    if champions.empty:
        logger.warning("No champions found in data")
        return pd.DataFrame()
    
    # Build champion blueprint (one row per champion season)
    blueprint_rows = []
    
    for _, champ_row in champions.iterrows():
        # Get manager-season hit rates if available
        hit_rate = np.nan
        bust_rate = np.nan
        
        if draft_hit_rates_df is not None and not draft_hit_rates_df.empty:
            manager_hit = draft_hit_rates_df[
                (draft_hit_rates_df['scope'] == 'manager_season') &
                (draft_hit_rates_df['manager'] == champ_row['manager']) &
                (draft_hit_rates_df['season_year'] == champ_row['season_year'])
            ]
            if not manager_hit.empty:
                hit_rate = manager_hit['hit_rate'].iloc[0]
                bust_rate = manager_hit['bust_rate'].iloc[0]
        
        blueprint_rows.append({
            'season_year': champ_row['season_year'],
            'manager': champ_row['manager'],
            'wins': champ_row['wins'],
            'points_for': champ_row['points_for'],
            'total_VAR': champ_row['total_VAR'],
            'VAR_per_dollar': champ_row['VAR_per_dollar'],
            'pct_VAR_from_draft': champ_row['pct_VAR_from_draft'],
            'pct_VAR_from_keeper': champ_row['pct_VAR_from_keeper'],
            'pct_VAR_from_waiver': champ_row['pct_VAR_from_waiver'],
            'pct_VAR_from_trade': champ_row['pct_VAR_from_trade'],
            'draft_VAR': champ_row['draft_VAR'],
            'keeper_VAR': champ_row['keeper_VAR'],
            'waiver_VAR': champ_row['waiver_VAR'],
            'trade_VAR': champ_row['trade_VAR'],
            'keeper_spending_pct': champ_row['keeper_spending_pct'],
            'hit_rate': hit_rate,
            'bust_rate': bust_rate,
        })
    
    blueprint = pd.DataFrame(blueprint_rows)
    
    # Compare champions vs non-champions
    comparison_rows = []
    
    # Key metrics to compare
    metrics_to_compare = [
        'total_VAR', 'VAR_per_dollar',
        'pct_VAR_from_draft', 'pct_VAR_from_keeper',
        'pct_VAR_from_waiver', 'pct_VAR_from_trade',
        'draft_VAR', 'keeper_VAR', 'waiver_VAR', 'trade_VAR',
        'keeper_spending_pct'
    ]
    
    for metric in metrics_to_compare:
        if metric not in df.columns:
            continue
        
        champ_values = champions[metric].dropna()
        non_champ_values = non_champions[metric].dropna()
        
        if champ_values.empty or non_champ_values.empty:
            continue
        
        champ_mean = champ_values.mean()
        non_champ_mean = non_champ_values.mean()
        diff = champ_mean - non_champ_mean
        pct_diff = (diff / non_champ_mean * 100) if non_champ_mean != 0 else 0
        
        # Simple effect size (Cohen's d approximation)
        pooled_std = np.sqrt(
            (champ_values.var() + non_champ_values.var()) / 2
        )
        cohens_d = diff / pooled_std if pooled_std > 0 else 0
        
        comparison_rows.append({
            'metric': metric,
            'champion_mean': champ_mean,
            'non_champion_mean': non_champ_mean,
            'difference': diff,
            'pct_difference': pct_diff,
            'effect_size_cohens_d': cohens_d,
            'champion_n': len(champ_values),
            'non_champion_n': len(non_champ_values),
        })
    
    comparison = pd.DataFrame(comparison_rows)
    comparison = comparison.sort_values('effect_size_cohens_d', key=abs, ascending=False)
    
    # Identify top differentiators
    top_differentiators = comparison.nlargest(3, 'effect_size_cohens_d', keep='all')
    
    logger.info(f"Built champion blueprint with {len(blueprint)} champions")
    logger.info(f"Top 3 differentiators: {top_differentiators['metric'].tolist()}")
    
    return {
        'blueprint': blueprint,
        'comparison': comparison,
        'top_differentiators': top_differentiators
    }


