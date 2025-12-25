"""Waiver pickup analysis and classification."""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def classify_pickup_archetype(
    var_after_pickup: float,
    weeks_started: int,
    weeks_rostered: int,
    position: str,
    var_percentile: Optional[float] = None
) -> str:
    """Classify waiver pickup into archetype.
    
    Args:
        var_after_pickup: VAR accumulated after pickup
        weeks_started: Number of weeks player was started
        weeks_rostered: Number of weeks player was on roster
        position: Player position
        var_percentile: VAR percentile at position (optional, for league winner classification)
        
    Returns:
        Archetype: LEAGUE_WINNER, SOLID_STARTER, STREAMER, or DEAD_PICKUP
    """
    # LEAGUE_WINNER: Top VAR, multiple starts
    if var_percentile is not None and var_percentile >= 75 and weeks_started >= 4:
        return 'LEAGUE_WINNER'
    
    # DEAD_PICKUP: Negative VAR or never started
    if var_after_pickup <= 0 or weeks_started == 0:
        return 'DEAD_PICKUP'
    
    # STREAMER: Short tenure, at least one start
    if weeks_rostered <= 3 and weeks_started >= 1:
        return 'STREAMER'
    
    # SOLID_STARTER: Positive VAR, multiple starts
    if var_after_pickup > 0 and weeks_started >= 3:
        return 'SOLID_STARTER'
    
    # Default to dead pickup if doesn't meet other criteria
    return 'DEAD_PICKUP'


def analyze_waiver_pickups(
    lifecycle_df: pd.DataFrame,
    results_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    league_meta: Dict,
    analysis_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Analyze waiver and free agent pickups.
    
    Args:
        lifecycle_df: Player lifecycle DataFrame
        results_df: Player results DataFrame
        transactions_df: Transactions DataFrame
        league_meta: League metadata
        
    Returns:
        DataFrame with waiver pickup analysis
    """
    # Filter to waiver/FA acquisitions
    waiver_pickups = lifecycle_df[
        lifecycle_df['acquisition_type'].isin(['waiver', 'free_agent'])
    ].copy()
    
    if waiver_pickups.empty:
        logger.warning("No waiver pickups found")
        return pd.DataFrame()
    
    # Calculate VAR percentiles by position for league winner classification
    # Need to merge with results to get VAR
    # For now, use total_points as proxy
    
    pickup_analysis = []
    
    for _, pickup in waiver_pickups.iterrows():
        season = pickup['season_year']
        player_id = pickup['player_id']
        position = pickup['position']
        
        # Get VAR from analysis_df if available, otherwise from lifecycle
        var_after_pickup = 0
        if analysis_df is not None and not analysis_df.empty:
            player_var = analysis_df[
                (analysis_df['season_year'] == season) &
                (analysis_df['player_id'] == player_id)
            ]
            if not player_var.empty and 'VAR' in player_var.columns:
                var_val = player_var['VAR'].iloc[0]
                var_after_pickup = float(var_val) if pd.notna(var_val) else 0
        else:
            var_after_pickup = pickup.get('VAR_total') or 0
        
        weeks_started = pickup.get('weeks_started') or 0
        weeks_rostered = pickup.get('weeks_rostered') or 0
        
        # Calculate cost efficiency
        acquisition_cost = pickup.get('acquisition_cost', 0) or 0
        cost_efficiency = var_after_pickup / acquisition_cost if acquisition_cost > 0 else None
        
        # Get VAR percentile at position (if available)
        var_percentile = None
        if position:
            position_pickups = waiver_pickups[waiver_pickups['position'] == position]
            if not position_pickups.empty and 'VAR_total' in position_pickups.columns:
                var_values = position_pickups['VAR_total'].fillna(0)
                if var_after_pickup is not None:
                    var_percentile = (var_values <= var_after_pickup).sum() / len(var_values) * 100
        
        # Classify archetype
        pickup_type = classify_pickup_archetype(
            var_after_pickup,
            weeks_started,
            weeks_rostered,
            position,
            var_percentile
        )
        
        pickup_analysis.append({
            'season_year': season,
            'player_id': player_id,
            'player_name': pickup.get('player_name', ''),
            'position': position,
            'team_key': pickup.get('team_key'),
            'acquisition_type': pickup['acquisition_type'],
            'acquisition_week': pickup['acquisition_week'],
            'acquisition_cost': acquisition_cost,
            'var_after_pickup': var_after_pickup,
            'weeks_rostered': weeks_rostered,
            'weeks_started': weeks_started,
            'pickup_type': pickup_type,
            'cost_efficiency': cost_efficiency,
            'var_percentile': var_percentile,
            'became_keeper': pickup.get('became_keeper', False),
        })
    
    df = pd.DataFrame(pickup_analysis)
    logger.info(f"Analyzed {len(df)} waiver pickups")
    return df

