"""Trade impact analysis."""
import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def analyze_trade_impact(
    transactions_df: pd.DataFrame,
    lifecycle_df: pd.DataFrame,
    results_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Analyze trade impact on VAR for each team.
    
    For each trade:
    - Aggregate VAR delivered by traded players after trade date
    - Compare VAR gained vs VAR lost per team
    - Classify trade as WIN/LOSS/NEUTRAL
    
    Args:
        transactions_df: Transactions DataFrame
        lifecycle_df: Player lifecycle DataFrame
        results_df: Player results DataFrame
        league_meta: League metadata
        
    Returns:
        DataFrame with trade impact analysis
    """
    # Filter to trade transactions
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Check which column has trade info - could be 'transaction_type' (overall) or transaction_player_type (per player)
    if 'transaction_type' in transactions_df.columns:
        trades = transactions_df[
            transactions_df['transaction_type'].str.contains('trade', case=False, na=False)
        ].copy()
    elif 'transaction_player_type' in transactions_df.columns:
        trades = transactions_df[
            transactions_df['transaction_player_type'] == 'TRADE'
        ].copy()
    else:
        logger.warning("No trade transaction type column found")
        return pd.DataFrame()
    
    if trades.empty:
        logger.warning("No trade transactions found")
        return pd.DataFrame()
    
    # Group trades by transaction_id
    trade_analysis = []
    
    for trade_id in trades['transaction_id'].unique():
        trade_txns = trades[trades['transaction_id'] == trade_id]
        
        if len(trade_txns) < 2:
            # Need at least 2 sides to a trade
            continue
        
        season = trade_txns['season_year'].iloc[0]
        trade_week = trade_txns['acquisition_week'].iloc[0] if 'acquisition_week' in trade_txns.columns else None
        
        # Identify teams involved
        teams = trade_txns['to_team_key'].unique()
        teams = [t for t in teams if pd.notna(t)]
        
        if len(teams) < 2:
            continue
        
        team_a = teams[0]
        team_b = teams[1]
        
        # Get players going to each team
        # In flattened transactions, each player row has a to_team_key
        team_a_players = trade_txns[
            (trade_txns['to_team_key'] == team_a) &
            (trade_txns['player_id'].notna())
        ]['player_id'].unique().tolist()
        
        team_b_players = trade_txns[
            (trade_txns['to_team_key'] == team_b) &
            (trade_txns['player_id'].notna())
        ]['player_id'].unique().tolist()
        
        # Also identify players leaving each team (from_team_key)
        team_a_lost = trade_txns[
            (trade_txns['from_team_key'] == team_a) &
            (trade_txns['player_id'].notna())
        ]['player_id'].unique().tolist()
        
        team_b_lost = trade_txns[
            (trade_txns['from_team_key'] == team_b) &
            (trade_txns['player_id'].notna())
        ]['player_id'].unique().tolist()
        
        # Calculate VAR for players after trade (would need weekly VAR or post-trade points)
        # For now, use total VAR as proxy (will need enhancement with weekly data)
        
        team_a_var_gained = 0
        team_a_var_lost = 0
        team_b_var_gained = 0
        team_b_var_lost = 0
        
        # Get VAR from lifecycle or results
        for player_id in team_a_players:
            if lifecycle_df is not None and not lifecycle_df.empty:
                player_results = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['player_id'] == player_id)
                ]
                if not player_results.empty:
                    var_col = 'VAR_total' if 'VAR_total' in player_results.columns else 'VAR'
                    if var_col in player_results.columns:
                        var = player_results[var_col].iloc[0]
                        team_a_var_gained += var if pd.notna(var) else 0
        
        for player_id in team_b_players:
            if lifecycle_df is not None and not lifecycle_df.empty:
                player_results = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['player_id'] == player_id)
                ]
                if not player_results.empty:
                    var_col = 'VAR_total' if 'VAR_total' in player_results.columns else 'VAR'
                    if var_col in player_results.columns:
                        var = player_results[var_col].iloc[0]
                        team_b_var_gained += var if pd.notna(var) else 0
        
        # Calculate VAR lost (players leaving)
        for player_id in team_a_lost:
            if lifecycle_df is not None and not lifecycle_df.empty:
                player_results = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['player_id'] == player_id)
                ]
                if not player_results.empty:
                    var_col = 'VAR_total' if 'VAR_total' in player_results.columns else 'VAR'
                    if var_col in player_results.columns:
                        var = player_results[var_col].iloc[0]
                        team_a_var_lost += var if pd.notna(var) else 0
        
        for player_id in team_b_lost:
            if lifecycle_df is not None and not lifecycle_df.empty:
                player_results = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['player_id'] == player_id)
                ]
                if not player_results.empty:
                    var_col = 'VAR_total' if 'VAR_total' in player_results.columns else 'VAR'
                    if var_col in player_results.columns:
                        var = player_results[var_col].iloc[0]
                        team_b_var_lost += var if pd.notna(var) else 0
        
        # Calculate net VAR swing
        team_a_net = team_a_var_gained - team_a_var_lost
        team_b_net = team_b_var_gained - team_b_var_lost
        
        # Classify trade outcome
        team_a_result = 'WIN' if team_a_net > team_b_net else ('LOSS' if team_a_net < team_b_net else 'NEUTRAL')
        team_b_result = 'WIN' if team_b_net > team_a_net else ('LOSS' if team_b_net < team_a_net else 'NEUTRAL')
        
        trade_analysis.append({
            'season_year': season,
            'transaction_id': trade_id,
            'trade_week': trade_week,
            'team_a': team_a,
            'team_b': team_b,
            'team_a_players_count': len(team_a_players),
            'team_b_players_count': len(team_b_players),
            'team_a_var_gained': team_a_var_gained,
            'team_a_var_lost': team_a_var_lost,
            'team_b_var_gained': team_b_var_gained,
            'team_b_var_lost': team_b_var_lost,
            'team_a_net_var': team_a_net,
            'team_b_net_var': team_b_net,
            'team_a_result': team_a_result,
            'team_b_result': team_b_result,
        })
    
    df = pd.DataFrame(trade_analysis)
    logger.info(f"Analyzed {len(df)} trades")
    return df

