"""Extended lifecycle tracking with waivers, trades, and roster churn."""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def build_complete_lifecycle(
    drafts_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    results_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Build complete player-season lifecycle table with all acquisition types.
    
    Args:
        drafts_df: Draft picks DataFrame
        transactions_df: Transactions DataFrame (with player details)
        results_df: Player results DataFrame
        league_meta: League metadata
        
    Returns:
        DataFrame with one row per (player, season) with lifecycle metrics
    """
    lifecycle_list = []
    
    # Step 1: Identify all player acquisitions by type
    
    # Draft/keeper acquisitions (week 0)
    draft_acquisitions = drafts_df.copy()
    draft_acquisitions['acquisition_type'] = draft_acquisitions['is_keeper'].apply(
        lambda x: 'keeper' if x else 'draft'
    )
    draft_acquisitions['acquisition_week'] = 0
    draft_acquisitions['acquisition_cost'] = draft_acquisitions.apply(
        lambda row: row.get('keeper_cost') if row['is_keeper'] else row.get('cost', 0),
        axis=1
    )
    draft_acquisitions['transaction_id'] = None
    draft_acquisitions['team_key'] = draft_acquisitions.get('team_key', '')
    
    # Waiver/FA acquisitions from transactions
    waiver_adds_list = []
    if not transactions_df.empty:
        waiver_adds = transactions_df[
            (transactions_df['transaction_player_type'] == 'ADD') &
            (transactions_df['player_id'].notna())
        ].copy()
        
        if not waiver_adds.empty:
            # Calculate acquisition week from timestamp
            waiver_adds['acquisition_week'] = waiver_adds.apply(
                lambda row: _timestamp_to_week(row['timestamp'], row['season_year']),
                axis=1
            )
            waiver_adds['acquisition_type'] = waiver_adds.apply(
                lambda row: 'waiver' if (pd.notna(row.get('faab_bid')) and row.get('faab_bid', 0) > 0) or pd.notna(row.get('waiver_priority')) else 'free_agent',
                axis=1
            )
            waiver_adds['acquisition_cost'] = waiver_adds['faab_bid'].fillna(0)
            waiver_adds['team_key'] = waiver_adds['to_team_key']
    
    # Trade acquisitions
    trade_adds_list = []
    if not transactions_df.empty:
        trade_adds = transactions_df[
            (transactions_df['transaction_player_type'] == 'TRADE') &
            (transactions_df['to_team_key'].notna()) &
            (transactions_df['player_id'].notna())
        ].copy()
        
        if not trade_adds.empty:
            trade_adds['acquisition_week'] = trade_adds.apply(
                lambda row: _timestamp_to_week(row['timestamp'], row['season_year']),
                axis=1
            )
            trade_adds['acquisition_type'] = 'trade'
            trade_adds['acquisition_cost'] = 0  # Trades don't cost FAAB
            trade_adds['team_key'] = trade_adds['to_team_key']
    
    # Combine all acquisitions
    all_acquisitions = []
    
    # Add draft/keeper acquisitions
    for _, row in draft_acquisitions.iterrows():
        all_acquisitions.append({
            'season_year': row['season_year'],
            'player_id': row['player_id'],
            'player_name': row.get('player_name', ''),
            'position': row.get('position', ''),
            'team_key': row.get('team_key', ''),
            'acquisition_type': row['acquisition_type'],
            'acquisition_week': row['acquisition_week'],
            'acquisition_cost': row['acquisition_cost'],
            'transaction_id': row.get('transaction_id'),
        })
    
    # Add waiver/FA acquisitions
    if not transactions_df.empty and 'waiver_adds' in locals() and not waiver_adds.empty:
        for _, row in waiver_adds.iterrows():
            all_acquisitions.append({
                'season_year': row['season_year'],
                'player_id': row['player_id'],
                'player_name': row.get('player_name', ''),
                'position': None,  # Will fill from results
                'team_key': row.get('team_key'),
                'acquisition_type': row['acquisition_type'],
                'acquisition_week': row['acquisition_week'],
                'acquisition_cost': row['acquisition_cost'],
                'transaction_id': row.get('transaction_id'),
            })
    
    # Add trade acquisitions
    if not transactions_df.empty and 'trade_adds' in locals() and not trade_adds.empty:
        for _, row in trade_adds.iterrows():
            all_acquisitions.append({
                'season_year': row['season_year'],
                'player_id': row['player_id'],
                'player_name': row.get('player_name', ''),
                'position': None,
                'team_key': row.get('team_key'),
                'acquisition_type': row['acquisition_type'],
                'acquisition_week': row['acquisition_week'],
                'acquisition_cost': row['acquisition_cost'],
                'transaction_id': row.get('transaction_id'),
            })
    
    if not all_acquisitions:
        logger.warning("No acquisitions found")
        return pd.DataFrame()
    
    acquisitions_df = pd.DataFrame(all_acquisitions)
    
    # Step 2: For each player-season, get earliest acquisition
    # Group by player-season and get earliest
    lifecycle_list = []
    
    for (season, player_id), group in acquisitions_df.groupby(['season_year', 'player_id']):
        earliest = group.sort_values('acquisition_week').iloc[0]
        
        # Get player info from results or drafts
        player_results = results_df[
            (results_df['season_year'] == season) &
            (results_df['player_id'] == player_id)
        ]
        
        # Try to get position from earliest, then results, then drafts
        position = earliest.get('position')
        if not position or pd.isna(position):
            position = (
                player_results['position'].iloc[0] 
                if not player_results.empty and 'position' in player_results.columns 
                else None
            )
        
        player_name = earliest.get('player_name') or (
            player_results['player_name'].iloc[0] 
            if not player_results.empty and 'player_name' in player_results.columns
            else ''
        )
        
        total_points = None
        if not player_results.empty and 'fantasy_points_total' in player_results.columns:
            points_val = player_results['fantasy_points_total'].iloc[0]
            if pd.notna(points_val):
                try:
                    total_points = float(points_val)
                except (ValueError, TypeError):
                    pass
        
        # Count teams played for (tracks roster movements)
        teams_played_for = group['team_key'].nunique()
        
        # Check if became keeper next year
        became_keeper = False
        if season < acquisitions_df['season_year'].max():
            next_year_drafts = drafts_df[
                (drafts_df['season_year'] == season + 1) &
                (drafts_df['player_id'] == player_id) &
                (drafts_df['is_keeper'] == True)
            ]
            became_keeper = not next_year_drafts.empty
        
        # VAR_total will be populated later from analysis_df merge
        var_total = None
        
        lifecycle_list.append({
            'season_year': season,
            'player_id': player_id,
            'player_name': player_name,
            'position': position,
            'team_key': earliest.get('team_key'),  # Earliest team (may change if traded)
            'acquisition_type': earliest['acquisition_type'],
            'acquisition_week': earliest['acquisition_week'],
            'acquisition_cost': earliest['acquisition_cost'],
            'teams_played_for': teams_played_for,
            'total_points': total_points,
            'became_keeper': became_keeper,
            # Placeholders for metrics that need weekly roster data
            'weeks_rostered': None,
            'weeks_started': None,
            'VAR_total': var_total,
            'VAR_per_week': None,
            'retained_to_end': None,
        })
    
    df = pd.DataFrame(lifecycle_list)
    logger.info(f"Built complete lifecycle for {len(df)} player-seasons")
    return df


def _timestamp_to_week(timestamp: str, season_year: Optional[int] = None) -> int:
    """Convert Unix timestamp to week number.
    
    Args:
        timestamp: Unix timestamp as string
        season_year: Season year (for NFL season start reference)
        
    Returns:
        Week number (0 = draft/preseason, 1-17 = regular season)
    """
    try:
        ts = int(float(timestamp))
        dt = datetime.fromtimestamp(ts)
        
        # NFL season typically starts first Thursday in September
        # Week 1 is usually around Sept 5-11
        # For simplicity, estimate week from date
        # This is approximate - would need exact season start date for accuracy
        
        if season_year:
            # Estimate: week 1 starts around Sept 5-11
            season_start = datetime(season_year, 9, 5)
            
            # Weeks before season = 0 (draft/preseason)
            if dt < season_start:
                return 0
            
            # Calculate week from date difference
            days_diff = (dt - season_start).days
            week = (days_diff // 7) + 1
            
            # Cap at 17 weeks
            return min(week, 17)
        
        # Fallback: if no season_year, return 0
        return 0
        
    except (ValueError, TypeError):
        return 0

