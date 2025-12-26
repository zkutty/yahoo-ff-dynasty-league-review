"""Draft hit rate analysis by manager and league-wide."""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def build_draft_hit_rates(
    analysis_df: pd.DataFrame
) -> pd.DataFrame:
    """Build draft hit rate analysis.
    
    By manager-season and league-wide:
    - expected_tier -> actual tier distribution
    - hit_rate = % players finishing >= expectation (actual_tier <= expected_tier)
    - bust_rate = % players below replacement (VAR < 0)
    - top3_pick_VAR, top5_spend_VAR, etc.
    
    Args:
        analysis_df: Complete analysis DataFrame with tiers and VAR
        
    Returns:
        DataFrame with hit rate statistics
    """
    df = analysis_df.copy()
    
    # Filter to players with both expected and actual tiers
    has_tiers = df['expected_tier'].notna() & df['actual_finish_tier'].notna()
    df_with_tiers = df[has_tiers].copy()
    
    if df_with_tiers.empty:
        logger.warning("No players with both expected and actual tiers")
        return pd.DataFrame()
    
    # Calculate hit and bust flags
    df_with_tiers['hit'] = df_with_tiers['actual_finish_tier'] <= df_with_tiers['expected_tier']
    df_with_tiers['bust'] = df_with_tiers['VAR'] < 0
    
    hit_rates = []
    
    # League-wide hit rates by tier
    for tier in sorted(df_with_tiers['expected_tier'].dropna().unique()):
        tier_data = df_with_tiers[df_with_tiers['expected_tier'] == tier]
        
        hit_rates.append({
            'scope': 'league',
            'manager': None,
            'season_year': None,
            'expected_tier': tier,
            'count': len(tier_data),
            'hit_rate': tier_data['hit'].mean() * 100,
            'bust_rate': tier_data['bust'].mean() * 100,
            'avg_VAR': tier_data['VAR'].mean() if tier_data['VAR'].notna().any() else np.nan,
            'median_VAR': tier_data['VAR'].median() if tier_data['VAR'].notna().any() else np.nan,
            'avg_normalized_price': tier_data['normalized_price'].mean(),
            'top3_pick_VAR': np.nan,  # Will calculate separately
            'top5_spend_VAR': np.nan,
        })
    
    # Manager-season hit rates
    for (season, manager), group in df_with_tiers.groupby(['season_year', 'manager']):
        # Overall hit rate for this manager-season
        hit_rate = group['hit'].mean() * 100
        bust_rate = group['bust'].mean() * 100
        
        # Top 3 picks by price
        top3 = group.nlargest(3, 'normalized_price')
        top3_var = top3['VAR'].sum() if top3['VAR'].notna().any() else np.nan
        
        # Top 5 spend VAR (sum of top 5 by price)
        top5 = group.nlargest(5, 'normalized_price')
        top5_var = top5['VAR'].sum() if top5['VAR'].notna().any() else np.nan
        
        hit_rates.append({
            'scope': 'manager_season',
            'manager': manager,
            'season_year': season,
            'expected_tier': None,
            'count': len(group),
            'hit_rate': hit_rate,
            'bust_rate': bust_rate,
            'avg_VAR': group['VAR'].mean() if group['VAR'].notna().any() else np.nan,
            'median_VAR': group['VAR'].median() if group['VAR'].notna().any() else np.nan,
            'avg_normalized_price': group['normalized_price'].mean(),
            'top3_pick_VAR': top3_var,
            'top5_spend_VAR': top5_var,
        })
    
    # Manager career hit rates
    for manager, manager_data in df_with_tiers.groupby('manager'):
        hit_rate = manager_data['hit'].mean() * 100
        bust_rate = manager_data['bust'].mean() * 100
        
        # Top 3 picks VAR (average per season)
        top3_var_by_season = []
        for season in manager_data['season_year'].unique():
            season_data = manager_data[manager_data['season_year'] == season]
            top3 = season_data.nlargest(3, 'normalized_price')
            if top3['VAR'].notna().any():
                top3_var_by_season.append(top3['VAR'].sum())
        avg_top3_var = np.mean(top3_var_by_season) if top3_var_by_season else np.nan
        
        hit_rates.append({
            'scope': 'manager_career',
            'manager': manager,
            'season_year': None,
            'expected_tier': None,
            'count': len(manager_data),
            'hit_rate': hit_rate,
            'bust_rate': bust_rate,
            'avg_VAR': manager_data['VAR'].mean() if manager_data['VAR'].notna().any() else np.nan,
            'median_VAR': manager_data['VAR'].median() if manager_data['VAR'].notna().any() else np.nan,
            'avg_normalized_price': manager_data['normalized_price'].mean(),
            'top3_pick_VAR': avg_top3_var,
            'top5_spend_VAR': np.nan,  # Can calculate if needed
        })
    
    result = pd.DataFrame(hit_rates)
    logger.info(f"Built draft hit rates table with {len(result)} rows")
    return result


