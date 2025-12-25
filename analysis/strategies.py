"""Manager strategy profiles and archetypes."""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def build_manager_strategy_profiles(
    lifecycle_df: pd.DataFrame,
    waiver_pickups_df: pd.DataFrame,
    trade_impact_df: pd.DataFrame,
    drafts_df: pd.DataFrame
) -> pd.DataFrame:
    """Build manager-level strategy profiles.
    
    For each team-season compute:
    - % of total VAR from draft
    - % from waivers
    - % from trades
    - FAAB efficiency (VAR per FAAB dollar)
    - Roster churn rate
    
    Args:
        lifecycle_df: Player lifecycle DataFrame
        waiver_pickups_df: Waiver pickup analysis DataFrame
        trade_impact_df: Trade impact DataFrame
        drafts_df: Draft picks DataFrame
        
    Returns:
        DataFrame with manager strategy profiles
    """
    profiles = []
    
    # Get team_key column name (might be different)
    team_key_col = 'team_key' if 'team_key' in lifecycle_df.columns else 'to_team_key'
    
    if team_key_col not in lifecycle_df.columns:
        logger.warning("No team_key column found in lifecycle_df")
        return pd.DataFrame()
    
    # Group by team-season
    for (season, team_key), group in lifecycle_df.groupby(['season_year', team_key_col]):
        # Calculate VAR by acquisition type (use VAR_total or VAR column)
        var_col = 'VAR_total' if 'VAR_total' in group.columns else 'VAR' if 'VAR' in group.columns else None
        
        if var_col:
            draft_var = group[group['acquisition_type'] == 'draft'][var_col].fillna(0).sum()
            keeper_var = group[group['acquisition_type'] == 'keeper'][var_col].fillna(0).sum()
            waiver_var = group[group['acquisition_type'].isin(['waiver', 'free_agent'])][var_col].fillna(0).sum()
            trade_var = group[group['acquisition_type'] == 'trade'][var_col].fillna(0).sum()
        else:
            draft_var = keeper_var = waiver_var = trade_var = 0
        
        total_var = draft_var + keeper_var + waiver_var + trade_var
        
        # Calculate percentages
        pct_draft = (draft_var / total_var * 100) if total_var > 0 else 0
        pct_keeper = (keeper_var / total_var * 100) if total_var > 0 else 0
        pct_waiver = (waiver_var / total_var * 100) if total_var > 0 else 0
        pct_trade = (trade_var / total_var * 100) if total_var > 0 else 0
        
        # Calculate FAAB efficiency
        team_waiver_key = 'team_key' if 'team_key' in waiver_pickups_df.columns else None
        if team_waiver_key and not waiver_pickups_df.empty:
            team_waivers = waiver_pickups_df[
                (waiver_pickups_df['season_year'] == season) &
                (waiver_pickups_df[team_waiver_key] == team_key)
            ]
        else:
            team_waivers = pd.DataFrame()
        
        faab_spent = team_waivers['acquisition_cost'].sum() if not team_waivers.empty else 0
        waiver_var_actual = team_waivers['var_after_pickup'].sum() if not team_waivers.empty else 0
        faab_efficiency = waiver_var_actual / faab_spent if faab_spent > 0 else None
        
        # Calculate roster churn (unique players / roster spots)
        unique_players = group['player_id'].nunique()
        # Estimate roster spots (would need from metadata)
        roster_churn_rate = None  # TODO: Calculate from roster size
        
        # Classify manager archetype
        archetype = classify_manager_archetype(
            pct_draft, pct_waiver, pct_trade, faab_efficiency
        )
        
        profiles.append({
            'season_year': season,
            'team_key': team_key,
            'total_var': total_var,
            'draft_var': draft_var,
            'keeper_var': keeper_var,
            'waiver_var': waiver_var,
            'trade_var': trade_var,
            'pct_var_from_draft': pct_draft,
            'pct_var_from_keeper': pct_keeper,
            'pct_var_from_waiver': pct_waiver,
            'pct_var_from_trade': pct_trade,
            'faab_spent': faab_spent,
            'faab_efficiency': faab_efficiency,
            'unique_players': unique_players,
            'roster_churn_rate': roster_churn_rate,
            'manager_archetype': archetype,
        })
    
    df = pd.DataFrame(profiles)
    logger.info(f"Built strategy profiles for {len(df)} team-seasons")
    return df


def classify_manager_archetype(
    pct_draft: float,
    pct_waiver: float,
    pct_trade: float,
    faab_efficiency: Optional[float]
) -> str:
    """Classify manager into strategy archetype.
    
    Args:
        pct_draft: % of VAR from draft
        pct_waiver: % of VAR from waivers
        pct_trade: % of VAR from trades
        faab_efficiency: VAR per FAAB dollar
        
    Returns:
        Archetype: DRAFT_AND_HOLD, WAIVER_HAWK, TRADER, or PASSIVE
    """
    # Waiver hawk: >30% from waivers
    if pct_waiver >= 30:
        return 'WAIVER_HAWK'
    
    # Trader: >20% from trades
    if pct_trade >= 20:
        return 'TRADER'
    
    # Draft and hold: >60% from draft+keeper, <10% from waiver
    if pct_draft >= 60 and pct_waiver < 10:
        return 'DRAFT_AND_HOLD'
    
    # Passive: <10% from waiver and <10% from trade
    if pct_waiver < 10 and pct_trade < 10:
        return 'PASSIVE'
    
    # Default to balanced
    return 'BALANCED'

