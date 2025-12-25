"""Value Above Replacement (VAR) calculation."""
import pandas as pd
from typing import Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_replacement_baseline(
    results_df: pd.DataFrame,
    league_meta: Dict,
    season: int
) -> Dict[str, float]:
    """Calculate replacement baseline points for each position.
    
    Replacement rank = num_teams * starters_at_position
    
    Args:
        results_df: DataFrame with player results (must have position, fantasy_points_total)
        league_meta: League metadata dictionary
        season: Season year
        
    Returns:
        Dictionary mapping position -> replacement_points
    """
    meta = league_meta.get(season, {})
    num_teams = meta.get('num_teams', 12)
    starting_slots = meta.get('starting_slots_by_position', {
        'QB': 1,
        'RB': 2,
        'WR': 2,
        'TE': 1,
        'FLEX': 1,
    })
    
    season_results = results_df[results_df['season_year'] == season].copy()
    
    # Filter out players without points
    season_results = season_results[season_results['fantasy_points_total'].notna()]
    
    if season_results.empty:
        logger.warning(f"No player results with points for season {season}")
        return {}
    
    replacement_baselines = {}
    
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_results = season_results[season_results['position'] == position].copy()
        
        if pos_results.empty:
            logger.warning(f"No {position} results for season {season}")
            replacement_baselines[position] = 0.0
            continue
        
        # Sort by points descending
        pos_results = pos_results.sort_values('fantasy_points_total', ascending=False)
        
        # Replacement rank
        starters_at_pos = starting_slots.get(position, 1)
        # For FLEX, use RB+WR+TE combined
        if position == 'FLEX':
            # FLEX replacement is typically the worst starter across RB/WR/TE
            # Use the max of RB/WR/TE replacement ranks
            flex_replacements = []
            for flex_pos in ['RB', 'WR', 'TE']:
                flex_starters = starting_slots.get(flex_pos, 0)
                flex_rank = num_teams * flex_starters
                if flex_rank <= len(pos_results):
                    flex_replacements.append(pos_results.iloc[flex_rank - 1]['fantasy_points_total'])
            replacement_baselines[position] = max(flex_replacements) if flex_replacements else 0.0
        else:
            replacement_rank = num_teams * starters_at_pos
            
            if replacement_rank <= len(pos_results):
                replacement_baselines[position] = pos_results.iloc[replacement_rank - 1]['fantasy_points_total']
            else:
                # If not enough players, use median or minimum
                replacement_baselines[position] = pos_results['fantasy_points_total'].min()
    
    return replacement_baselines


def calculate_var(
    results_df: pd.DataFrame,
    drafts_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Calculate Value Above Replacement (VAR) for all drafted players.
    
    Args:
        results_df: DataFrame with player results
        drafts_df: DataFrame with draft picks (should have normalized_price)
        league_meta: League metadata
        
    Returns:
        DataFrame with VAR added to results
    """
    # Merge drafts and results
    merged = drafts_df.merge(
        results_df,
        on=['season_year', 'player_id', 'player_name', 'position'],
        how='left',
        suffixes=('_draft', '_result')
    )
    
    # Calculate replacement baselines per season/position
    merged['replacement_baseline_points'] = np.nan
    merged['VAR'] = np.nan
    
    for season in merged['season_year'].unique():
        season_mask = merged['season_year'] == season
        baselines = calculate_replacement_baseline(results_df, league_meta, int(season))
        
        for position, baseline_points in baselines.items():
            pos_mask = (merged['position'] == position) & season_mask
            merged.loc[pos_mask, 'replacement_baseline_points'] = baseline_points
            
            # Calculate VAR
            points = merged.loc[pos_mask, 'fantasy_points_total']
            var_values = points - baseline_points
            merged.loc[pos_mask, 'VAR'] = var_values
    
    # Calculate dollar efficiency metrics
    merged['dollar_per_VAR'] = merged['normalized_price'] / merged['VAR']
    merged['VAR_per_dollar'] = merged['VAR'] / merged['normalized_price']
    
    # Replace infinities with NaN
    merged['dollar_per_VAR'] = merged['dollar_per_VAR'].replace([np.inf, -np.inf], np.nan)
    merged['VAR_per_dollar'] = merged['VAR_per_dollar'].replace([np.inf, -np.inf], np.nan)
    
    logger.info(f"Calculated VAR for {merged['VAR'].notna().sum()} players")
    
    return merged

