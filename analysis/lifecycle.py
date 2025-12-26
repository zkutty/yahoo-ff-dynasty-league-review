"""Player season lifecycle tracking (draft/keeper/waiver/trade)."""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def build_acquisition_timeline(
    drafts_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Build timeline of how each player was acquired in each season.
    
    For each player-season:
    - Identify earliest acquisition event (draft/keeper/waiver/FA/trade)
    - Track roster movements (trades, drops, pickups)
    
    Args:
        drafts_df: DataFrame with draft picks
        transactions_df: DataFrame with transactions (ADD, DROP, TRADE)
        league_meta: League metadata
        
    Returns:
        DataFrame with acquisition timeline: one row per (player, team, season, acquisition_event)
    """
    acquisitions = []
    
    # Process drafts and keepers (week 0 acquisitions)
    for _, draft_pick in drafts_df.iterrows():
        season = int(draft_pick['season_year'])
        player_id = draft_pick['player_id']
        team_key = draft_pick.get('team_key', '')
        
        acquisition_type = 'keeper' if draft_pick.get('is_keeper', False) else 'draft'
        cost = draft_pick.get('cost', 0)
        keeper_cost = draft_pick.get('keeper_cost') if acquisition_type == 'keeper' else None
        
        acquisitions.append({
            'season_year': season,
            'player_id': player_id,
            'player_name': draft_pick.get('player_name', ''),
            'position': draft_pick.get('position', ''),
            'team_key': team_key,
            'acquisition_type': acquisition_type,
            'acquisition_week': 0,  # Draft/keepers are week 0
            'acquisition_cost': keeper_cost if keeper_cost else cost,
            'transaction_id': None,
            'timestamp': None,
        })
    
    # Process transactions
    if not transactions_df.empty:
        for _, txn in transactions_df.iterrows():
            season = int(txn['season_year'])
            txn_type = str(txn.get('type', '')).lower()
            txn_id = txn.get('transaction_id', '')
            timestamp = txn.get('timestamp', '')
            
            # Parse transaction type
            if 'trade' in txn_type:
                # Trade will be handled separately - need to parse involved players
                continue
            elif 'add' in txn_type or 'drop' in txn_type:
                # Add/drop transaction
                # Note: Need to parse involved_players to get details
                # For now, this is a placeholder structure
                pass
    
    df = pd.DataFrame(acquisitions)
    
    if df.empty:
        logger.warning("No acquisitions found")
        return df
    
    logger.info(f"Built acquisition timeline for {len(df)} player acquisitions")
    return df


def build_lifecycle_table(
    acquisitions_df: pd.DataFrame,
    drafts_df: pd.DataFrame,
    results_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Build unified PLAYER_SEASON_LIFECYCLE table.
    
    Args:
        acquisitions_df: Acquisition timeline DataFrame
        drafts_df: Draft picks DataFrame
        results_df: Player results DataFrame
        transactions_df: Transactions DataFrame
        league_meta: League metadata
        
    Returns:
        DataFrame with one row per (player, season) with lifecycle metrics
    """
    lifecycle_list = []
    
    # Group by player-season
    for (season, player_id), group in acquisitions_df.groupby(['season_year', 'player_id']):
        # Get player info
        player_name = group['player_name'].iloc[0] if not group.empty else ''
        position = group['position'].iloc[0] if not group.empty else ''
        
        # Find earliest acquisition
        earliest = group.sort_values('acquisition_week').iloc[0]
        acquisition_type = earliest['acquisition_type']
        acquisition_week = earliest['acquisition_week']
        acquisition_cost = earliest['acquisition_cost']
        
        # Count teams played for
        teams_played_for = group['team_key'].nunique()
        
        # Get player results
        player_results = results_df[
            (results_df['season_year'] == season) &
            (results_df['player_id'] == player_id)
        ]
        
        total_points = player_results['fantasy_points_total'].iloc[0] if not player_results.empty else None
        total_points = float(total_points) if pd.notna(total_points) else None
        
        # Calculate VAR (would need replacement baseline)
        var_total = None  # Will be calculated separately
        
        # Check if became keeper next year
        became_keeper = False
        if season < max(acquisitions_df['season_year']):
            next_year = season + 1
            next_year_drafts = drafts_df[
                (drafts_df['season_year'] == next_year) &
                (drafts_df['player_id'] == player_id) &
                (drafts_df['is_keeper'] == True)
            ]
            became_keeper = not next_year_drafts.empty
        
        # Get final roster status (retained to end)
        # This would require checking if player was on roster at end of season
        retained_to_end = None  # TODO: Determine from end-of-season rosters
        
        lifecycle_list.append({
            'season_year': season,
            'player_id': player_id,
            'player_name': player_name,
            'position': position,
            'acquisition_type': acquisition_type,
            'acquisition_week': acquisition_week,
            'acquisition_cost': acquisition_cost,
            'teams_played_for': teams_played_for,
            'weeks_rostered': None,  # TODO: Calculate from weekly rosters
            'weeks_started': None,  # TODO: Calculate from weekly rosters
            'total_points': total_points,
            'VAR_total': var_total,
            'VAR_per_week': None,  # TODO: Calculate
            'retained_to_end': retained_to_end,
            'became_keeper': became_keeper,
        })
    
    df = pd.DataFrame(lifecycle_list)
    logger.info(f"Built lifecycle table for {len(df)} player-seasons")
    return df


