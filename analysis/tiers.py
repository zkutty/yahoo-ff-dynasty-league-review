"""Draft expectation tier analysis."""
import pandas as pd
from typing import Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


def assign_draft_tiers(
    df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Assign draft expectation tiers based on normalized prices.
    
    For each position + season:
    - Sort players by normalized_price descending
    - Define tier boundaries:
      tier_size = num_teams * starters_at_position
      tier1 = ranks 1..tier_size (e.g., WR1)
      tier2 = next tier_size (WR2), etc.
    
    Args:
        df: DataFrame with draft picks and normalized_price
        league_meta: League metadata
        
    Returns:
        DataFrame with 'expected_tier' column added
    """
    df = df.copy()
    df['expected_tier'] = np.nan
    df['price_rank_within_position'] = np.nan
    
    for season in df['season_year'].unique():
        meta = league_meta.get(int(season), {})
        num_teams = meta.get('num_teams', 12)
        starting_slots = meta.get('starting_slots_by_position', {
            'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1
        })
        
        season_mask = df['season_year'] == season
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_mask = season_mask & (df['position'] == position)
            pos_drafts = df[pos_mask].copy()
            
            if pos_drafts.empty:
                continue
            
            # Sort by normalized price descending
            pos_drafts = pos_drafts.sort_values('normalized_price', ascending=False)
            pos_drafts['price_rank'] = range(1, len(pos_drafts) + 1)
            
            # Determine tier size
            starters_at_pos = starting_slots.get(position, 1)
            tier_size = num_teams * starters_at_pos
            
            # Assign tiers
            pos_drafts['expected_tier'] = (pos_drafts['price_rank'] - 1) // tier_size + 1
            pos_drafts['price_rank_within_position'] = pos_drafts['price_rank']
            
            # Update original dataframe
            df.loc[pos_mask, 'expected_tier'] = pos_drafts['expected_tier'].values
            df.loc[pos_mask, 'price_rank_within_position'] = pos_drafts['price_rank_within_position'].values
    
    logger.info(f"Assigned draft tiers to {df['expected_tier'].notna().sum()} players")
    return df


def assign_actual_tiers(
    df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Assign actual finish tiers based on end-of-season points ranks.
    
    Args:
        df: DataFrame with fantasy_points_total and VAR already calculated
        league_meta: League metadata
        
    Returns:
        DataFrame with 'actual_finish_tier' column added
    """
    df = df.copy()
    df['actual_finish_tier'] = np.nan
    df['points_rank_within_position'] = np.nan
    
    for season in df['season_year'].unique():
        meta = league_meta.get(int(season), {})
        num_teams = meta.get('num_teams', 12)
        starting_slots = meta.get('starting_slots_by_position', {
            'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1
        })
        
        season_mask = df['season_year'] == season
        has_points = df['fantasy_points_total'].notna()
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_mask = season_mask & (df['position'] == position) & has_points
            pos_results = df[pos_mask].copy()
            
            if pos_results.empty:
                continue
            
            # Sort by points descending
            pos_results = pos_results.sort_values('fantasy_points_total', ascending=False)
            pos_results['points_rank'] = range(1, len(pos_results) + 1)
            
            # Determine tier size
            starters_at_pos = starting_slots.get(position, 1)
            tier_size = num_teams * starters_at_pos
            
            # Assign tiers
            pos_results['actual_finish_tier'] = (pos_results['points_rank'] - 1) // tier_size + 1
            pos_results['points_rank_within_position'] = pos_results['points_rank']
            
            # Update original dataframe
            df.loc[pos_mask, 'actual_finish_tier'] = pos_results['actual_finish_tier'].values
            df.loc[pos_mask, 'points_rank_within_position'] = pos_results['points_rank_within_position'].values
    
    logger.info(f"Assigned actual tiers to {df['actual_finish_tier'].notna().sum()} players")
    return df


def calculate_tier_hit_rates(
    df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate tier hit rates and bust rates.
    
    Returns:
        DataFrame with hit rate statistics by tier and position
    """
    # Filter to players with both expected and actual tiers
    has_tiers = df['expected_tier'].notna() & df['actual_finish_tier'].notna()
    df_with_tiers = df[has_tiers].copy()
    
    if df_with_tiers.empty:
        logger.warning("No players with both expected and actual tiers")
        return pd.DataFrame()
    
    # Calculate hit rate (% actual tier <= expected tier)
    df_with_tiers['hit'] = df_with_tiers['actual_finish_tier'] <= df_with_tiers['expected_tier']
    
    # Calculate bust rate (% below replacement, i.e., VAR < 0)
    df_with_tiers['bust'] = df_with_tiers['VAR'] < 0
    
    # Calculate by position and tier
    tier_summary = df_with_tiers.groupby(['position', 'expected_tier']).agg({
        'player_id': 'count',
        'hit': 'mean',
        'bust': 'mean',
        'VAR': ['mean', 'median'],
        'normalized_price': 'mean',
        'fantasy_points_total': 'mean',
    }).reset_index()
    
    tier_summary.columns = [
        'position', 'expected_tier', 'count',
        'hit_rate', 'bust_rate',
        'avg_VAR', 'median_VAR',
        'avg_normalized_price', 'avg_fantasy_points'
    ]
    
    logger.info(f"Calculated tier hit rates for {len(tier_summary)} tier/position combinations")
    return tier_summary

